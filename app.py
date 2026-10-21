
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-demo-secret-key"

DB_NAME = "job_portal.db"


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            salary TEXT,
            description TEXT NOT NULL,
            employer_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(job_id, user_id)
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    keyword = request.args.get("keyword", "").strip()
    location = request.args.get("location", "").strip()
    category = request.args.get("category", "").strip()

    conn = get_db()
    query = "SELECT * FROM jobs WHERE 1=1"
    values = []

    if keyword:
        query += " AND (title LIKE ? OR company LIKE ?)"
        values.extend(["%" + keyword + "%", "%" + keyword + "%"])

    if location:
        query += " AND location LIKE ?"
        values.append("%" + location + "%")

    if category:
        query += " AND category LIKE ?"
        values.append("%" + category + "%")

    query += " ORDER BY id DESC"
    jobs = conn.execute(query, values).fetchall()
    conn.close()

    return render_template("index.html", jobs=jobs)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "seeker")

        if not name or not email or len(password) < 8:
            flash("Enter valid details. Password must have 8 characters.")
            return redirect(url_for("register"))

        if role not in ("seeker", "employer"):
            flash("Invalid account type.")
            return redirect(url_for("register"))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                (name, email, generate_password_hash(password), role)
            )
            conn.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.")
        finally:
            conn.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash("Login successful!")
            return redirect(url_for("home"))

        flash("Incorrect email or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("home"))


@app.route("/post-job", methods=["GET", "POST"])
def post_job():
    if "user_id" not in session or session.get("role") != "employer":
        flash("Please log in with an employer account.")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        category = request.form.get("category", "").strip()
        salary = request.form.get("salary", "").strip()
        description = request.form.get("description", "").strip()

        if not all([title, company, location, category, description]):
            flash("Please fill in all required fields.")
            return redirect(url_for("post_job"))

        conn = get_db()
        conn.execute("""
            INSERT INTO jobs
            (title, company, location, category, salary, description, employer_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, company, location, category, salary,
              description, session["user_id"]))
        conn.commit()
        conn.close()

        flash("Job posted successfully!")
        return redirect(url_for("home"))

    return render_template("post_job.html")


@app.route("/apply/<int:job_id>", methods=["POST"])
def apply(job_id):
    if "user_id" not in session or session.get("role") != "seeker":
        flash("Please log in with a job seeker account to apply.")
        return redirect(url_for("login"))

    conn = get_db()
    job = conn.execute(
        "SELECT id FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()

    if not job:
        conn.close()
        flash("Job not found.")
        return redirect(url_for("home"))

    try:
        conn.execute(
            "INSERT INTO applications (job_id, user_id) VALUES (?, ?)",
            (job_id, session["user_id"])
        )
        conn.commit()
        flash("Application submitted successfully!")
    except sqlite3.IntegrityError:
        flash("You have already applied for this job.")
    finally:
        conn.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)
