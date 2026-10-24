import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key-change-before-deployment"
)

DATABASE = "finance_tracker.db"


def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.commit()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL
                type TEXT CHECK(type IN ('income', 'expense', 'transafer')) NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                source_account TEXT NOT NULL,
                destination_account TEXT -- Used primarily for tranferrals
            )
        """)
        conn.commit()


@app.route("/")
def home():
    return render_template("public/home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))

    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            error = "Username and password are required."

        else:
            with sqlite3.connect(DATABASE) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT * FROM users WHERE username = ?",
                    (username,)
                )

                user = cursor.fetchone()

            if user and check_password_hash(user["password"], password):
                session["user"] = user["username"]
                session["user_id"] = user["id"]

                return redirect(url_for("dashboard"))

            error = "Invalid username or password."

    return render_template("auth/login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
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

        else:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE email = ? OR username = ?
                    """,
                    (email, username)
                )

                existing_user = cursor.fetchone()

                if existing_user:
                    cursor.execute(
                        "SELECT id FROM users WHERE email = ?",
                        (email,)
                    )

                    if cursor.fetchone():
                        error = "This email has already been registered."
                    else:
                        error = "That username is already taken."

                else:
                    hashed_password = generate_password_hash(password)

                    cursor.execute(
                        """
                        INSERT INTO users (
                            full_name,
                            email,
                            username,
                            password
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            full_name,
                            email,
                            username,
                            hashed_password
                        )
                    )

                    conn.commit()

                    user_id = cursor.lastrowid

                    session["user"] = username
                    session["user_id"] = user_id

                    return redirect(url_for("dashboard"))

    return render_template("auth/register.html", error=error)


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

def add_transaction(type, amount, category, source_account, destination_account=None, description=None, date=None, db_name="finance_tracker.db"):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO transactions (date, name, amount, category, description, source_account, destination_account)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (date, type.lower(), amount, category, description, source_account, destination_account))
    
    conn.commit()
    conn.close()
    print(f"Successfully recorder {type}: ${amount:.2f} ({category})")

def get_all_transactions():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute( "SELECT * FROM transactions ORDER BY date DESC")

    rows = cursor.fetchall()
    conn.close()
    return rows
    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)