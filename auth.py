"""Authentication blueprint: login, register, logout, password reset.

Exposes `auth_bp` and the `@login_required` decorator. Uses session-based
auth (`session['user']`) with bcrypt-hashed passwords. Password reset is
token-based and the generated token is surfaced via `flash` — there is no
email delivery. Successful login also triggers a background feed fetch via
`trigger_background_fetch`.
"""

import sqlite3
import secrets
from functools import wraps
from flask import Blueprint, request, redirect, url_for, session, flash, render_template
from config import DB_FILE
from db import create_user, get_user, check_password, hash_password
from feeds import trigger_background_fetch

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator that redirects to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user(username)
        if user and check_password(password, user['password_hash']):
            session["user"] = username
            trigger_background_fetch()
            return redirect(url_for("main.index"))
        flash("Invalid username or password.", "error")
    return render_template('login.html')


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
        elif len(password) < 12:
            flash("Password must be at least 12 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif not create_user(username, password):
            flash("Username already taken.", "error")
        else:
            flash("Account created! You can now log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template('register.html')


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        token = request.form.get("token", "").strip()
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not token:
            # Step 1: generate a reset token for the username
            username = request.form.get("username", "").strip()
            user = get_user(username)
            if not user:
                flash("No account found with that username.", "error")
            else:
                token = secrets.token_urlsafe(32)
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('UPDATE users SET reset_token = ? WHERE username = ?', (token, username))
                conn.commit()
                conn.close()
                flash(f"Your reset token: {token}", "info")
                return render_template('reset_password.html', step=2, token=token)
        else:
            # Step 2: validate token and set new password
            if len(new_password) < 12:
                flash("Password must be at least 12 characters.", "error")
                return render_template('reset_password.html', step=2, token=token)
            if new_password != confirm:
                flash("Passwords do not match.", "error")
                return render_template('reset_password.html', step=2, token=token)
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE reset_token = ?', (token,))
            user = c.fetchone()
            if not user:
                flash("Invalid or expired reset token.", "error")
                return render_template('reset_password.html', step=1)
            c.execute('UPDATE users SET password_hash = ?, reset_token = NULL WHERE id = ?',
                      (hash_password(new_password), user['id']))
            conn.commit()
            conn.close()
            flash("Password reset successfully! You can now log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template('reset_password.html', step=1)


@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("auth.login"))
