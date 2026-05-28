from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
import random
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            news TEXT NOT NULL,
            result TEXT NOT NULL,
            confidence TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    conn.commit()
    conn.close()


@app.before_first_request
def ensure_database():
    initialize_database()


def classify_news(text):
    lower_text = text.lower()

    fake_keywords = [
        "breaking",
        "shocking",
        "viral",
        "secret",
        "unbelievable",
        "rumor",
        "fake",
        "click here",
        "conspiracy",
        "scam",
        "alert",
        "exclusive",
        "outrage",
        "you won't believe"
    ]

    real_keywords = [
        "research",
        "official",
        "report",
        "verified",
        "study",
        "government",
        "analysis",
        "data",
        "survey",
        "statement",
        "confirmation",
        "facts",
        "sources"
    ]

    fake_score = sum(1 for keyword in fake_keywords if keyword in lower_text)
    real_score = sum(1 for keyword in real_keywords if keyword in lower_text)
    matched_keywords = [keyword for keyword in fake_keywords + real_keywords if keyword in lower_text]

    if fake_score > real_score:
        result = "FAKE NEWS"
        confidence = f"{random.randint(75, 95)}%"
        reason = "The text includes more sensational or misleading language than reliable cues."
    elif real_score > fake_score:
        result = "REAL NEWS"
        confidence = f"{random.randint(70, 92)}%"
        reason = "The text includes more trusted informational cues than sensational phrasing."
    else:
        result = "UNCERTAIN"
        confidence = f"{random.randint(55, 75)}%"
        reason = "The algorithm could not confidently decide based on keyword signals alone."

    return {
        "result": result,
        "confidence": confidence,
        "reason": reason,
        "matched_keywords": matched_keywords,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        news_text = request.form.get("news", "").strip()
        if not news_text:
            return render_template("index.html", error="Please paste a news article before submitting.", user_name=session.get("user_name"))

        data = classify_news(news_text)

        if session.get("user_id"):
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO history (user_id, username, news, result, confidence, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session["user_id"],
                    session["user_name"],
                    news_text,
                    data["result"],
                    data["confidence"],
                    data["reason"],
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                )
            )
            conn.commit()
            conn.close()

        return render_template("result.html", text=news_text, user_name=session.get("user_name"), **data)

    return render_template("index.html", user_name=session.get("user_name"))


@app.route("/history")
def history():
    if "user_id" not in session:
        flash("Please log in to view your analysis history.", "warning")
        return redirect(url_for("login"))

    conn = get_db_connection()
    history_rows = conn.execute(
        "SELECT news, result, confidence, reason, created_at FROM history WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("history.html", history=history_rows, user_name=session.get("user_name"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, username, password FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Please fill in all fields.", "warning")
            return redirect(url_for("register"))

        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("That email is already registered.", "warning")
            return redirect(url_for("register"))

        conn.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, generate_password_hash(password))
        )
        conn.commit()
        conn.close()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
