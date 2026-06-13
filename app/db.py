import sqlite3
import click
from flask import current_app, g
from app.config import Config

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE_URI'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database with all required tables."""
    db = get_db()
    
    # 1. Users
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # 2. Job Descriptions (Updated with content_hash)
    db.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            content_hash TEXT,
            jd_text TEXT,
            jd_skills TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Resumes
    db.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            jd_id INTEGER,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            resume_text TEXT,
            resume_skills TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (jd_id) REFERENCES job_descriptions(id)
        )
    """)

    # 4. Messages
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'ai')),
            message TEXT NOT NULL,
            emotion_context TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 5. Evaluation Scores
    db.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            username TEXT NOT NULL,
            score_type TEXT NOT NULL CHECK(score_type IN ('technical', 'emotional','code')),
            score_value REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 6. Code Checks
    db.execute("""
        CREATE TABLE IF NOT EXISTS code_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TEXT,
            language TEXT,
            question_context TEXT,
            code TEXT,
            result_json TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 7. Chats
    db.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            username TEXT,
            jd_id INTEGER,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (jd_id) REFERENCES job_descriptions(id)
        )
    """)
    
    db.commit()

@click.command('init-db')
def init_db_command():
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)