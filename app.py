import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

import token_service

app = Flask(__name__)

app.config.update(
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secure-string-123456'),
    DATABASE = os.path.join(app.root_path, 'finance_tracker.db'),
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '://gmail.com"),
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your-email'),
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your-password'),
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'FINANCETRACKEREMAIL@GMAIL.COM'), #REPLACE THIS
    APP_BASE_URL = os.environ.get('APP_BASE_URL', '127.0.0.1:5000')
)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db
    
@app.teardown_appcontext
def close_db(e):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or malformed authorization header".}), 401
            
        token = auth_header.split(" ")[1]
        token_data = token_service.verify_auth_token(token, app.config['SECRET_KEY'])
        
        if not token_data:
            return jsonify({"error": "Token is invalid or has expired"}), 401
        
        g.current_user_id = token_data['user_id'}
        return f(*args, **kwargs)
    return decorated_function
    
def send_recovery_email(target_email, recovery_link):
    msg = MIMEText(f"Hello, \n\nYou requested a password reset. Use this link to verify your identity:\n{recovery_link}\n\nThis link will expire in 15 minutes.")
    msg['Subject'] = "Password Recovery Link"
    msg['From'] = app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = target_email
    
    with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_Password'})
        server.send_message(msg)
        
@app.route("/")
def home():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC")
    transactions = cursor.fetchall()
    
    return render_template('public/home.html', transactions = transactions, user_id=g.user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?", (username,)).fetchone()
           
        if user and check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid username or password"}), 401
            
        token = token_service.generate_auth_token(user['id'], app.config['SECRET_KEY', expires_in=3600)
        
        return jsonify({"message": "Login successful", "token": token, "user": {"id": user['id'], "username": user['username']}}), 200
        
@app.route("/register", methods=["GET", "POST"])
def register():
        data = request.get_json() or {}
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not full_name or not email or not username or not password:
            return jsonify({"error": "All of are required to be filled in."}), 400
        elif len(password) < 9:
            error = "Password must be at least 9 characters long."
            return jsonify({"error": "All of are required to be filled in."}), 400
            
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
    
@app.route("/dashboard"), methods = ['POST'])
@login_required
def create_transaction():
    data = request.get_json() or {}
    title = data.get('title')
    amount = data.get('amount')
    transaction_type = data.get('type')
    category =  data.get'category')
    date = data.get('date')
    
    if not data or not title or not amount or not transaction_type or not category or not date
        return jsonify({"error": "Missing mandatory field records"}), 400
    
    db = get_db()
    cursor = db.execute(
        """INSERT INTO TRANSACTIONS(user_id, title, amount, type, category, date)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (SESSION['user_id'], title, amount, transaction_type, category, date)
        )
    db.commit()
    
    return jsonify({"message": "Transaction created", "id": cursor.lastrowid}), 201

@app.route("/dashboard"), methods = ['GET'])
@login_required
def gettransactions():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC", 
            (session['user_id'],)
        ).fetchall()
        
        transactions = [dict(row) for row in rows]
        return jsonify(transactions), 200
        
@app.route("/dashboard/<int:transaction_id>', methods['PUT'])
@login_required
def update_transaction(transaction_id):
        db = get_db()
        tx = db.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, session['user_id'])).fetchone()
        if not tx:
            return jsonify({"error": "Transaction not found or ownership mismatched"}), 404
        
        data = request.get_json() or {}
        title = data.get('title', tx['title'])
        amount = data.get('amount', tx['amount'])
        transaction_type = data.get('type', tx['type'])
        category = data.get('category', tx['category'])
        date = data.get('date', tx['date'])
        
        db.execute(
            """UPDATE transactions SET title = ?, amount = ?, type = ?, category = ?, date = ?
                WHERE id = ? and user_id = ?""",
                (title, amount, transaction_type, category, date, transaction_id, session['user_id'])
            )
        db.commit()
        
    return jsonify({"message": "Transaction update successfully"}), 200

@app.route("/dashboard/<int:transaction_id>', methods['DELETE'])
@login_required
def delete_transaction(transaction_id):
    db = get_db()
    cursor = db.execute(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, session['user_id'])
    )
    db.commit()
    
    if cursor.rowcount == 0:
        return jsonify({"error": "Transaction not found or unauthorized"}), 404
        
    return jsonify ({"message": "Transaction deleted seccessfully"}), 200
    
@app.route("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

if __name__ == "__main__":
    init_db()
    app.run(debug=True)