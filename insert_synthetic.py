import sqlite3
import os
import hashlib
from datetime import datetime, timedelta
import random

# Database path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DATABASE_URI = os.path.join(INSTANCE_DIR, 'chat.db')

def get_db():
    return sqlite3.connect(DATABASE_URI, detect_types=sqlite3.PARSE_DECLTYPES)

def insert_synthetic_data():
    db = get_db()
    cursor = db.cursor()

    # Insert user "test" if not exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ('test',))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('test', '123456'))
        user_id = cursor.lastrowid
    else:
        user_id = user[0]

    # Insert a job description for the user
    jd_text = "We are looking for a Python developer with experience in Flask, SQLAlchemy, and machine learning."
    jd_skills = "Python, Flask, SQLAlchemy, Machine Learning"
    content_hash = hashlib.md5(jd_text.encode()).hexdigest()
    cursor.execute("""
        INSERT INTO job_descriptions (user_id, filename, filepath, content_hash, jd_text, jd_skills)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, 'sample_jd.pdf', 'instance/uploads/jds/sample_jd.pdf', content_hash, jd_text, jd_skills))
    jd_id = cursor.lastrowid

    # Sample messages for chats
    sample_messages = [
        ("user", "Hello, I'm excited for this interview.", None),
        ("ai", "Hello! Let's start with your experience in Python.", None),
        ("user", "I have 3 years of experience.", "happy"),
        ("ai", "Great! Can you tell me about a project?", None),
        ("user", "I built a web app with Flask.", "confident"),
        ("ai", "Sounds good. Now, a coding question: Write a function to reverse a string.", None),
        ("user", "def reverse_string(s): return s[::-1]", "focused"),
        ("ai", "Good! Next question.", None),
    ]

    # Insert 3 chats
    for i in range(1, 4):
        chat_id = f"chat_{i}_{user_id}"
        started_at = datetime.now() - timedelta(days=i)
        cursor.execute("""
            INSERT INTO chats (id, username, jd_id, started_at, last_activity)
            VALUES (?, ?, ?, ?, ?)
        """, (chat_id, 'test', jd_id, started_at, started_at + timedelta(minutes=30)))

        # Insert messages for the chat
        for j, (role, message, emotion) in enumerate(sample_messages):
            timestamp = started_at + timedelta(minutes=j*5)
            cursor.execute("""
                INSERT INTO messages (chat_id, role, message, emotion_context, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, role, message, emotion, timestamp))

        # Insert evaluation scores
        scores = {
            'technical': round(random.uniform(6.0, 9.5), 1),
            'emotional': round(random.uniform(7.0, 10.0), 1),
            'code': round(random.uniform(5.5, 8.5), 1)
        }
        for score_type, score_value in scores.items():
            cursor.execute("""
                INSERT INTO evaluation_scores (chat_id, username, score_type, score_value, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (chat_id, 'test', score_type, score_value, started_at + timedelta(minutes=35)))

    db.commit()
    db.close()
    print("Synthetic data inserted successfully.")

if __name__ == "__main__":
    insert_synthetic_data()