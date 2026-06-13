from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.db import get_db

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET'])
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        
        db = get_db()
        user = db.execute(
            "SELECT id, username FROM users WHERE username = ? AND password = ?", 
            (username, password)
        ).fetchone()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard.index'))
        else:
            # User not found: Store attempted credentials in session and redirect to signup
            session['signup_username'] = username
            session['signup_password'] = password
            flash("User not found. Redirecting to signup...")
            return redirect(url_for('auth.signup'))
            
    return render_template('auth/login.html')

@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    # Pre-fill from session if coming from failed login
    prefill_username = session.pop('signup_username', '')  # Pop to clear after use
    prefill_password = session.pop('signup_password', '')
    
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Missing fields")
            return render_template('auth/signup.html', username=username, password=password)

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            
            # Auto-login: Set session and redirect to dashboard
            user_id = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()['id']
            session['user_id'] = user_id
            session['username'] = username
            flash("Account created and logged in!")
            return redirect(url_for('dashboard.index'))
        except Exception:
            flash("Username already exists")
            return render_template('auth/signup.html', username=username, password=password)
    
    # GET request: Render with pre-filled values
    return render_template('auth/signup.html', username=prefill_username, password=prefill_password)

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))