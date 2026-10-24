import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from token_service import TokenService, load_env_file

load_env_file()
app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "dev_fallback_cookie_encription_key_554"
)
DATABASE = "finance_tracker.db"
token_service = TokenService()
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db
    
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.before_request
def authenticate_user():
    if request.path.startswith('/static') or request.path in ['/login', '/register']:
        g.user_id = None
        return
    
    token = request.cookies.get('auth_token')
    verification = token_service.verifcy_token(token)
    
    If verification["status"] == "VALID":
        g.user_id = verification["user_id"]
    else:
        g.user_id = None
        flash("Please log in to manage your financial tracking dashboard.", "error")
        return redirect(url_for('login_route'))
        
        
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
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC")
    transactions = cursor.fetchall()
    
    return render_template('public/home.html', transactions = transactions, user_id=g.user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        user = db.execute(
            'SELECT id, password_hash FROM useres WHERE username = ?',
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            token = token_service.generate_token(user_id=user['id'], expires_in_seconds=3600)
            
            response = make_response(redirect(url_for('/')))
            response.set_cookie(
                'auth_token',
                token,
                httponly=True
                samesite='Strict',
                secure=True
            )
            flash("Welcome back! Credentials verified.", "success")
            return response
    return render_template("auth/login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not full_name or not email or not username or not password:
            error = "All fields are required."
            return render_template('auth/register.html')
        elif len(password) < 9:
            error = "Password must be at least 9 characters long."
            return render_template('auth/register.html')
            
        db = get_db()

        Try:
            hashed_password = generate_password_hash(
                password,
                method='pbkdf2:sha256',
                salt_length=16
            )
            
            db.execute(
                'INSERT INTO users (full_name, email, username, password) VALUES (?, ?, ?, ?)'
            )
            db.commit()
            flash("Registration successful! Please log in with your new credentials!")
            return redirect(url_for('login_route'))
        except sqlite3.IntegrityError:
            flash(f"The username '{username}' is already registered. Please choose another.")
        
        except Exception as e:
            flash("An unexpected registration system error has occured. Please try again.")
    return render_template('auth/register.html')
    
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
    response = make_response(redirect(url_for('login_route")))
    response.delete_cookie('auth_token')
    flash("Session terminated successfully.", "info")
    return response

if __name__ == "__main__":
    init_db()
    app.run(debug=True)