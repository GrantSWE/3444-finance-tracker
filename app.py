import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'CHANGE_ME'
DATABASE = 'useres.db'
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            )
        ''')
        conn.commit()
        try:
            hashed_pw = generate_password_hash('password123')
            cursor.execute('INSERT INTO users(username, password, email) VALUES (Duncan, Password!123, DuncanWrenn@my.unt.edu)
            conn.commit()
        except sqlite3.IntegrityError:
            pass
            
@app.route("/")
def home():
    return render_template("public/home.html")


@app.route("/login")
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
        
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with sqlite3.connect(DATABASE) AS CONN:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,)
            user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route("/register")
def register():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    error = None
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        
        if len(password) < 9:
            error = "Password must be at least 9 characters long."
        elif not username or not email or not full_name:
            error = "All fields are required."
        else:
            with sqpite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                try:
                    hashed_pw = generate_password_hash(password)
                    cursor.execute('''
                        INSERT INTO users (full_name, email, username, password)
                        VALUES (?, ?, ?, ?)
                    ''', (full_name, email, username, hashed_pw))
                    conn.commit()
                    
                    session['user'] = username
                    return redirect(url_for('dashboard'))
                
                except sqlite3.IntegrityError as e:
                    if 'email' in str(e):
                        error = 'This email has already been registered.'
                    else:
                        error = 'That username is already taken.'
    return render_template('register.html', error=error)
    app.run(debug=True)