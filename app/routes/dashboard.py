import os
import json
import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, send_from_directory, flash
from werkzeug.utils import secure_filename
from app.db import get_db
from app.services.jd_analyzer import JDAnalyzer

bp = Blueprint('dashboard', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'

def clear_analysis_session():
    """Helper to clear stale analysis data from the session."""
    keys_to_clear = [
        'resume_skills', 'common_skills', 'missing_skills', 
        'questions', 'current_analyzed_jd_id'
    ]
    for key in keys_to_clear:
        session.pop(key, None)

def calculate_file_hash(file_stream):
    """Calculates MD5 hash of a file stream."""
    hasher = hashlib.md5()
    # Read in chunks to avoid memory issues with large files
    buf = file_stream.read(65536)
    while len(buf) > 0:
        hasher.update(buf)
        buf = file_stream.read(65536)
    
    # Reset file pointer to beginning so it can be saved later
    file_stream.seek(0)
    return hasher.hexdigest()

@bp.route('/dashboard')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    db = get_db()

    # Fetch JDs for the "Start New Session" list
    jds = db.execute(
        "SELECT id, filename, filepath, uploaded_at FROM job_descriptions WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,)
    ).fetchall()

    return render_template('dashboard/dashboard.html', jds=jds)

@bp.route('/upload_jd', methods=['GET', 'POST'])
def upload_jd():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        file = request.files.get('jd_file')
        if file and allowed_file(file.filename):
            
            # 1. Check for Duplicates via Hash
            file_hash = calculate_file_hash(file)
            db = get_db()
            
            existing = db.execute(
                "SELECT id FROM job_descriptions WHERE user_id = ? AND content_hash = ?",
                (session['user_id'], file_hash)
            ).fetchone()
            
            if existing:
                # If duplicate, redirect to dashboard immediately (prevent re-upload)
                # You could also add flash('JD already exists!', 'warning') if you have flash messages in your template
                return redirect(url_for('dashboard.index'))

            # 2. Save File
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config['JD_UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # 3. Analyze & Insert
            analyzer = JDAnalyzer()
            jd_text = analyzer.extract_text_from_pdf(save_path)
            jd_skills = analyzer.extract_skills(jd_text, is_jd=True)

            db.execute(
                "INSERT INTO job_descriptions (user_id, filename, filepath, content_hash, jd_text, jd_skills) VALUES (?, ?, ?, ?, ?, ?)",
                (session['user_id'], filename, save_path, file_hash, jd_text, jd_skills)
            )
            db.commit()
            return redirect(url_for('dashboard.index'))

    return render_template('dashboard/upload_jd.html')

@bp.route('/analyze/<int:jd_id>', methods=['GET', 'POST'])
def analyze(jd_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    jd = db.execute("SELECT * FROM job_descriptions WHERE id = ? AND user_id = ?", (jd_id, session['user_id'])).fetchone()
    if not jd:
        return "JD not found", 404

    # Check for Stale Data
    if request.method == 'GET':
        if session.get('current_analyzed_jd_id') != jd_id:
            clear_analysis_session()

    if request.method == 'POST':
        file = request.files.get('resume_file')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(current_app.config['RESUME_UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # Analyze Resume
            analyzer = JDAnalyzer()
            resume_text = analyzer.extract_text_from_pdf(save_path)
            resume_skills = analyzer.extract_skills(resume_text, is_jd=False)

            # Save Resume to DB
            db.execute(
                "INSERT INTO resumes (user_id, jd_id, filename, filepath, resume_text, resume_skills) VALUES (?, ?, ?, ?, ?, ?)",
                (session['user_id'], jd_id, filename, save_path, resume_text, resume_skills)
            )
            db.commit()

            # Compare and Generate Questions
            common, missing = analyzer.get_comparison(resume_skills, jd['jd_skills'])
            common_list = common.get('common_skills', []) if common else []
            questions_json = analyzer.generate_interview_questions(json.dumps(common))
            
            # Update Session
            session['resume_skills'] = resume_skills
            session['jd_skills'] = jd['jd_skills']
            session['common_skills'] = common_list
            session['missing_skills'] = missing.get('skills_to_learn', []) if missing else []
            session['questions'] = questions_json.get('questions', []) if questions_json else []
            
            # Mark this JD as current
            session['current_analyzed_jd_id'] = jd_id

    context = {
        'jd': jd,
        'resume_skills': session.get("resume_skills"),
        'jd_skills': session.get("jd_skills", jd['jd_skills']),
        'common_skills': session.get("common_skills"),
        'missing_skills': session.get("missing_skills"),
        'questions': session.get("questions")
    }

    return render_template('dashboard/analyze.html', **context)

@bp.route('/uploads/jds/<path:filename>')
def serve_jd(filename):
    return send_from_directory(current_app.config['JD_UPLOAD_FOLDER'], filename)