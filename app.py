import os
import smtplib
import sqlite3
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
            return redirect(url_for("login"))

        g.current_user_id = session["user_id"]
        return view(*args, **kwargs)

    return decorated_function


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
    database = get_db()
    transactions = database.execute(
        "SELECT * FROM transactions ORDER BY date DESC"
    ).fetchall()

    return render_template(
        "public/home.html",
        transactions=transactions,
        user_id=session.get("user_id"),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("get_transactions"))

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
                return redirect(url_for("get_transactions"))

            error = "Invalid username or password."

    return render_template("auth/login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("get_transactions"))

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
                    return redirect(url_for("get_transactions"))

    return render_template("auth/register.html", error=error)


@app.route("/dashboard", methods=["POST"])
@login_required
def create_transaction():
    data = request.get_json() or {}
    title = data.get("title")
    amount = data.get("amount")
    transaction_type = data.get("type")
    category = data.get("category")
    date = data.get("date")

    if not data or not title or not amount or not transaction_type or not category or not date:
        return jsonify({"error": "Missing mandatory field records"}), 400

    database = get_db()
    cursor = database.execute(
        """
        INSERT INTO transactions (user_id, title, amount, type, category, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session["user_id"], title, amount, transaction_type, category, date),
    )
    database.commit()

    return jsonify({"message": "Transaction created", "id": cursor.lastrowid}), 201


@app.route("/dashboard", methods=["GET"])
@login_required
def get_transactions():
    rows = get_db().execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC",
        (session["user_id"],),
    ).fetchall()

    transactions = [dict(row) for row in rows]
    return jsonify(transactions), 200


@app.route("/dashboard/<int:transaction_id>", methods=["PUT"])
@login_required
def update_transaction(transaction_id):
    database = get_db()
    transaction = database.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, session["user_id"]),
    ).fetchone()
    if not transaction:
        return jsonify({"error": "Transaction not found or ownership mismatched"}), 404

    data = request.get_json() or {}
    title = data.get("title", transaction["title"])
    amount = data.get("amount", transaction["amount"])
    transaction_type = data.get("type", transaction["type"])
    category = data.get("category", transaction["category"])
    date = data.get("date", transaction["date"])

    database.execute(
        """
        UPDATE transactions
        SET title = ?, amount = ?, type = ?, category = ?, date = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            title,
            amount,
            transaction_type,
            category,
            date,
            transaction_id,
            session["user_id"],
        ),
    )
    database.commit()

    return jsonify({"message": "Transaction update successfully"}), 200


@app.route("/dashboard/<int:transaction_id>", methods=["DELETE"])
@login_required
def delete_transaction(transaction_id):
    database = get_db()
    cursor = database.execute(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, session["user_id"]),
    )
    database.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "Transaction not found or unauthorized"}), 404

    return jsonify({"message": "Transaction deleted seccessfully"}), 200


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
