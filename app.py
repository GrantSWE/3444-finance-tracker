import os
import smtplib
import sqlite3
from datetime import datetime, timezone, date as date_value
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from email.mime.text import MIMEText
from functools import wraps

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "fallback-secure-string-123456"),
    DATABASE=os.environ.get(
        "DATABASE_PATH",
        os.path.join(app.root_path, "finance_tracker.db"),
    ),
    SCHEMA_PATH=os.path.join(app.root_path, "schema.sql"),
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAIL_SERVER=os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT", 587)),
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME", "your-email"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD", "your-password"),
    MAIL_DEFAULT_SENDER=os.environ.get(
        "MAIL_DEFAULT_SENDER",
        "FINANCETRACKEREMAIL@GMAIL.COM",
    ),
    APP_BASE_URL=os.environ.get("APP_BASE_URL", "127.0.0.1:5000"),
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db



@app.teardown_appcontext
def close_db(error):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db():
    database = get_db()
    with open(app.config["SCHEMA_PATH"], encoding="utf-8") as schema_file:
        database.executescript(schema_file.read())


def login_required(view):
    @wraps(view)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required."}), 401
            return redirect(url_for("login"))

        g.current_user_id = session["user_id"]
        return view(*args, **kwargs)

    return decorated_function


def transaction_to_dict(transaction):
    return dict(transaction)


def validate_transaction_payload(payload, partial=False):
    if not isinstance(payload, dict):
        return None, "Request body must contain a JSON object."

    editable_fields = {
        "account_id",
        "title",
        "description",
        "amount",
        "type",
        "category",
        "date",
    }
    supplied_fields = editable_fields.intersection(payload)

    if partial and not supplied_fields:
        return None, "Provide at least one transaction field to update."

    if not partial:
        required_fields = {"title", "amount", "type", "category", "date"}
        missing_fields = sorted(
            field
            for field in required_fields
            if field not in payload or payload[field] in (None, "")
        )
        if missing_fields:
            return None, f"Missing required fields: {', '.join(missing_fields)}."

    values = {}

    for field in ("title", "category"):
        if field in payload:
            value = payload[field]
            if not isinstance(value, str) or not value.strip():
                return None, f"{field} must be a non-empty string."
            values[field] = value.strip()

    if "description" in payload:
        description = payload["description"]
        if description is not None and not isinstance(description, str):
            return None, "description must be a string or null."
        values["description"] = description.strip() if description else None

    if "amount" in payload:
        if isinstance(payload["amount"], bool):
            return None, "amount must be a positive number."
        try:
            amount = Decimal(str(payload["amount"]))
        except (InvalidOperation, ValueError):
            return None, "amount must be a positive number."
        if not amount.is_finite() or amount <= 0:
            return None, "amount must be a positive number."
        values["amount"] = float(amount)

    if "type" in payload:
        transaction_type = payload["type"]
        if not isinstance(transaction_type, str):
            return None, "type must be either income or expense."
        transaction_type = transaction_type.strip().lower()
        if transaction_type not in {"income", "expense"}:
            return None, "type must be either income or expense."
        values["type"] = transaction_type

    if "date" in payload:
        transaction_date = payload["date"]
        if not isinstance(transaction_date, str):
            return None, "date must use YYYY-MM-DD format."
        try:
            values["date"] = date_value.fromisoformat(transaction_date).isoformat()
        except ValueError:
            return None, "date must use YYYY-MM-DD format."

    if "account_id" in payload:
        account_id = payload["account_id"]
        if account_id is None:
            values["account_id"] = None
        else:
            if isinstance(account_id, bool) or (
                isinstance(account_id, float) and not account_id.is_integer()
            ):
                return None, "account_id must be a positive integer or null."
            try:
                account_id = int(account_id)
            except (TypeError, ValueError):
                return None, "account_id must be a positive integer or null."
            if account_id <= 0:
                return None, "account_id must be a positive integer or null."
            values["account_id"] = account_id

    return values, None


def account_belongs_to_user(database, account_id, user_id):
    if account_id is None:
        return True

    account = database.execute(
        "SELECT id FROM accounts WHERE id = ? AND user_id = ?",
        (account_id, user_id),
    ).fetchone()
    return account is not None


@app.errorhandler(404)
def not_found(error):
    if request.path.startswith("/api/transactions"):
        return jsonify({"error": "Resource not found."}), 404
    return error


def send_recovery_email(target_email, recovery_link):
    message = MIMEText(
        "Hello,\n\n"
        "You requested a password reset. Use this link to verify your identity:\n"
        f"{recovery_link}\n\n"
        "This link will expire in 15 minutes."
    )
    message["Subject"] = "Password Recovery Link"
    message["From"] = app.config["MAIL_DEFAULT_SENDER"]
    message["To"] = target_email

    with smtplib.SMTP(app.config["MAIL_SERVER"], app.config["MAIL_PORT"]) as server:
        server.starttls()
        server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        server.send_message(message)


@app.route("/")
def home():
    return render_template("public/home.html", user_id=session.get("user_id"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."
        else:
            user = get_db().execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("dashboard"))

            error = "Invalid username or password."

    return render_template("auth/login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not full_name or not email or not username or not password:
            error = "All fields are required."
        elif len(password) < 9:
            error = "Password must be at least 9 characters long."
        elif not any(character.isdigit() for character in password):
            error = "Password must include at least one number."
        elif not any(
            not character.isalnum() and not character.isspace()
            for character in password
        ):
            error = "Password must include at least one special character."
        else:
            database = get_db()
            existing_user = database.execute(
                """
                SELECT email, username
                FROM users
                WHERE email = ? OR username = ?
                """,
                (email, username),
            ).fetchone()

            if existing_user:
                if existing_user["email"] == email:
                    error = "This email has already been registered."
                else:
                    error = "That username is already taken."
            else:
                password_hash = generate_password_hash(
                    password,
                    method="pbkdf2:sha256",
                    salt_length=16,
                )

                try:
                    cursor = database.execute(
                        """
                        INSERT INTO users (full_name, email, username, password_hash)
                        VALUES (?, ?, ?, ?)
                        """,
                        (full_name, email, username, password_hash),
                    )
                    database.commit()
                except sqlite3.IntegrityError:
                    database.rollback()
                    error = "That email or username is already registered."
                else:
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    session["username"] = username
                    return redirect(url_for("dashboard"))

    return render_template("auth/register.html", error=error)


@app.route("/dashboard")
@login_required

def get_category_spending(database, user_id, year_month=None):
    target_month = year_month or datetime.now().strftime("%Y-%m")
    rows = database.execute(
        """
        WITH monthly_expenses AS (
            SELECT
                LOWER(TRIM(category)) AS norm_category,
                SUM(amount) AS total_spent,
                COUNT(id) AS transaction_count
            FROM transactions
            WHERE user_id = ?
              AND type = 'expense'
              AND strftime('%Y-%m', datae) = strftime('%Y-%m', 'now, 'localtime)
            GROUP BY LOWER(TRIM(category))
        ),
        total_monthly AS (
            SELECT COALESCE(SUM(total_spent), 0) as grand_total
            FROM monthly_expenses
        )
        SELECT
            c.id as category_id,
            c.category_name,
            COALESCE(me.total_spent, 0) AS total_spent,
            COALESCE(me.transaction_count, 0), as transaction_count,
            CASE
                WHEN tm.grand_total > 0
                THEN ROUND ((COALESCE(me.total_spent, 0) * 100.0) / tm.grand_total, 2)
                ELSE 0.0
            END AS pct_of_total_spent
        FROM categories c
        LEFT JOIN monthly_expenses me
            ON LOWER(c.category_name) = me.norm_category
        CROSS JOIN total_monthly tm
        WHERE c.category_type = 'expense'
        ORDER BY total_spent DESC, c.category_name ASC;
        """,
        (user_id, target_month),
    ).feetchall()
    return [dict(row) for row in rows]

def get_goal_metrics(database, user_id, goal_id):
    goal = database.execute(
        """
        SELECT
            id,
            goal_name,
            target_amount,
            current_amount,
            target_date,
            ROUNT((current_amount*100.0) / target_amount, 2) AS completion_pct
            MAX(target_amount - current_amount, 0) AS remaining_amount
        FROM savings_goals
        WHERE id = ? AND user_id = ?
        """,
        (goal_id, user_id),
    ).fetchone()
    if not goal:
        return None
        
    milestones = database.execute(
    """
    SELECT
        id,
        milestone_name,
        target_amount,
        target_percentage,
        is_achieved,
        achieved_at
        CASE
            WHEN ? >= target_amount THEN 100.0
            ELSE ROUND ((? * 100.0) / target_amount, 2)
        END AS milestone_progress
        MAX(target_amount -?, 0) AS amount_to_milestone
    FROM goal_milestones
    WHERE goal_id = ? AND user_id = ?
    ORDER BY target_amount ASC
    """,
    (
        goal["current_amount"],
        goal_id,
        user_id,
    ),
    ).fetchall()
    
    return{
        "goal": dict(goal)
        "milestones": [dict(m) for m in milestones],
    }
def sync_goal_milestones(database, user_id, goal_id, new_balance):
    now_iso = datetime.now(timezone.utc).isoformat()
    database.execute(
        """
        UPDATE goal_milestones
        SET is_achieved = 1,
            achieved_at = COALESCE(achieved_at, ?)
        WHERE goal_id = ?
        AND user_id = ?
        AND is_achieved = 0
        AND target_amount <= ?
        """,
        (now_iso, goal_id, user_id, float(new_balance)),
    )

def execute_saving_allocation(
    database,
    user_id,
    total_deposit_amount,
    source_account_id = None,
    transaction_id = None,
):
    remaining_pool = Decimal(str(total_deposit_amount)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    if remaining_pool <= 0:
        raise ValueError("Allocation deposit amount must be greater than zero.")

    rules = database.execute(
        """
        SELECT
            r.id,
            r.goal_id,
            r.source_account_id,
            r.allocation_type,
            r.allocation_value,
            g.current_amount,
            g.target_amount
        FROM saving_allocation_rules r
        JOIN savings_goals g ON r.goal_id = g.id
        WHERE r.user_id = ?
          AND r.is_active = 1
        ORDER BY r.priority_order ASC, r.id ASC
        """,
        (user_id,),
    ).fetchall()

    if not rules:
        return []

    allocations_made = []
    initial_pool = remaining_pool
     try:
        for rule in rules:
            if remaining_pool <= Decimal("0.00"):
                break

            rule_value = Decimal(str(rule["allocation_value"]))
            if rule["allocation_type"] == "percentage":
                desired_amount = (initial_pool * rule_value / Decimal("100")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                desired_amount = rule_value.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            # Cap at remaining deposit pool and remaining goal gap
            goal_gap = max(
                Decimal(str(rule["target_amount"])) - Decimal(str(rule["current_amount"])),
                Decimal("0.00"),
            )
            alloc_amount = min(desired_amount, remaining_pool, goal_gap)

            if alloc_amount <= Decimal("0.00"):
                continue

            acct_id = source_account_id or rule["source_account_id"]

            # Deduct from source account if linked
            if acct_id is not None:
                acct = database.execute(
                    "SELECT balance FROM accounts WHERE id = ? AND user_id = ?",
                    (acct_id, user_id),
                ).fetchone()
                if not acct:
                    raise ValueError(f"Source account {acct_id} not found.")
                if Decimal(str(acct["balance"])) < alloc_amount:
                    raise ValueError(f"Insufficient funds in account {acct_id}.")

                database.execute(
                    "UPDATE accounts SET balance = balance - ? WHERE id = ? AND user_id = ?",
                    (float(alloc_amount), acct_id, user_id),
                )

            # Update savings goal balance
            new_goal_balance = Decimal(str(rule["current_amount"])) + alloc_amount
            database.execute(
                """
                UPDATE savings_goals
                SET current_amount = ?
                WHERE id = ? AND user_id = ?
                """,
                (float(new_goal_balance), rule["goal_id"], user_id),
            )

            # Record allocation ledger entry
            cursor = database.execute(
                """
                INSERT INTO saving_allocations (
                    user_id,
                    goal_id,
                    rule_id,
                    source_account_id,
                    transaction_id,
                    allocated_amount
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    rule["goal_id"],
                    rule["id"],
                    acct_id,
                    transaction_id,
                    float(alloc_amount),
                ),
            )

            # Check and unlock any reached milestones
            _sync_goal_milestones(database, user_id, rule["goal_id"], new_goal_balance)

            remaining_pool -= alloc_amount
            allocations_made.append(
                {
                    "allocation_id": cursor.lastrowid,
                    "goal_id": rule["goal_id"],
                    "allocated_amount": float(alloc_amount),
                    "new_goal_balance": float(new_goal_balance),
                }
            )

        database.commit()
        return allocations_made
    except Exception:
        database.rollback()
        raise
        
        
@app.route("/api/transactions", methods=["POST"])
@login_required
def create_transaction():
    data = request.get_json(silent=True)
    values, validation_error = validate_transaction_payload(data)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    user_id = session["user_id"]
    database = get_db()
    if not account_belongs_to_user(database, values.get("account_id"), user_id):
        return jsonify({"error": "Account not found."}), 404

    cursor = database.execute(
        """
        INSERT INTO transactions (
            user_id,
            account_id,
            title,
            description,
            amount,
            type,
            category,
            date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            values.get("account_id"),
            values["title"],
            values.get("description"),
            values["amount"],
            values["type"],
            values["category"],
            values["date"],
        ),
    )
    database.commit()

    transaction = database.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (cursor.lastrowid, user_id),
    ).fetchone()
    return jsonify({"transaction": transaction_to_dict(transaction)}), 201


@app.route("/api/transactions", methods=["GET"])
@login_required
def get_transactions():
    rows = get_db().execute(
        """
        SELECT *
        FROM transactions
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    transactions = [transaction_to_dict(row) for row in rows]
    return jsonify({"transactions": transactions}), 200


@app.route("/api/transactions/<int:transaction_id>", methods=["PUT"])
@login_required
def update_transaction(transaction_id):
    if transaction_id <= 0:
        return jsonify({"error": "Invalid transaction ID."}), 400

    database = get_db()
    transaction = database.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, session["user_id"]),
    ).fetchone()
    if not transaction:
        return jsonify({"error": "Transaction not found."}), 404

    data = request.get_json(silent=True)
    values, validation_error = validate_transaction_payload(data, partial=True)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    account_id = values.get("account_id", transaction["account_id"])
    if not account_belongs_to_user(database, account_id, session["user_id"]):
        return jsonify({"error": "Account not found."}), 404

    database.execute(
        """
        UPDATE transactions
        SET account_id = ?,
            title = ?,
            description = ?,
            amount = ?,
            type = ?,
            category = ?,
            date = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            account_id,
            values.get("title", transaction["title"]),
            values.get("description", transaction["description"]),
            values.get("amount", transaction["amount"]),
            values.get("type", transaction["type"]),
            values.get("category", transaction["category"]),
            values.get("date", transaction["date"]),
            transaction_id,
            session["user_id"],
        ),
    )
    database.commit()

    updated_transaction = database.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, session["user_id"]),
    ).fetchone()
    return jsonify({"transaction": transaction_to_dict(updated_transaction)}), 200


@app.route("/api/transactions/<int:transaction_id>", methods=["DELETE"])
@login_required
def delete_transaction(transaction_id):
    if transaction_id <= 0:
        return jsonify({"error": "Invalid transaction ID."}), 400

    database = get_db()
    cursor = database.execute(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, session["user_id"]),
    )
    database.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "Transaction not found."}), 404

    return jsonify({"message": "Transaction deleted successfully."}), 200


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
