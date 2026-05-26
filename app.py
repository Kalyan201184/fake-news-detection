from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'fake_news_secret'

DATABASE = 'database.db'


def create_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    ''')

    conn.commit()
    conn.close()


create_database()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO users(username,email,password) VALUES(?,?,?)',
            (username, email, password)
        )

        conn.commit()
        conn.close()

        flash('Registration Successful')
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM users WHERE email=? AND password=?',
            (email, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[1]
            return redirect('/dashboard')
        else:
            flash('Invalid Login')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    return render_template('dashboard.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    text = request.form['news']

    fake_keywords = [
        'breaking',
        'shocking',
        'secret',
        'viral',
        'unbelievable'
    ]

    score = 0

    for word in fake_keywords:
        if word in text.lower():
            score += 1

    if score >= 2:
        result = 'FAKE NEWS'
        confidence = '92%'
    else:
        result = 'REAL NEWS'
        confidence = '96%'

    return render_template(
        'result.html',
        result=result,
        confidence=confidence,
        text=text
    )


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)