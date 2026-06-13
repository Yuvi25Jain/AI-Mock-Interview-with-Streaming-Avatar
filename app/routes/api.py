import json
import re
from flask import Blueprint, request, jsonify, session, render_template, current_app
from app.services.emotion_service import EmotionService
from app.services.llm_factory import LLMFactory
from app.db import get_db

bp = Blueprint('api', __name__)
emotion_service = EmotionService()

# --- Helper Functions ---

def get_code_evaluator():
    """Lazily create and cache a CodeEvaluator."""
    ex = getattr(current_app, "extensions", None)
    if ex is None:
        current_app.extensions = {}
        ex = current_app.extensions

    if "code_evaluator" not in ex:
        from app.services.code_evaluator import CodeEvaluator
        ex["code_evaluator"] = CodeEvaluator()
    return ex["code_evaluator"]

def _parse_scores_from_text(text):
    """Extracts numerical scores from LLM analysis text."""
    if not text:
        return None, None

    try:
        j = json.loads(text)
        return (float(j.get('technical')) if j.get('technical') is not None else None,
                float(j.get('emotional')) if j.get('emotional') is not None else None)
    except Exception:
        pass

    def find_score(name):
        # Group the alternation so the capture group is always part of the same branch
        pattern_num = rf'(?:{name})[^0-9\n]*([0-9]+(?:\.[0-9]+)?)'
        m = re.search(pattern_num, text, re.I)
        if m and m.group(1):
            return float(m.group(1))
        pattern_frac = rf'(?:{name})[^/]*([0-9]+)\/([0-9]+)'
        m = re.search(pattern_frac, text, re.I)
        if m and m.group(1) and m.group(2):
            return float(m.group(1)) / float(m.group(2)) * 10.0
        return None

    tech = find_score('technical')
    emo = find_score('emotional|emotion')
    return tech, emo

# --- Coding Round ---

@bp.route('/coding_round')
def coding_page():
    if 'user_id' not in session: 
        return "Login required", 401
    
    # Check if we are in an active chat session to persist context
    chat_id = request.args.get('chat_id') or session.get('chat_id')
    question = session.get("coding_question", "Write a function that reverses a string.")
    
    return render_template("interview/coding.html", question=question, chat_id=chat_id)

@bp.route('/evaluate_code', methods=['POST'])
def evaluate():
    data = request.json
    chat_id = data.get('chat_id')
    user_id = session.get('user_id')
    
    ce = get_code_evaluator()
    res = ce.evaluate(
        code=data.get('code'),
        language=data.get('language', 'python'),
        question=data.get('question'),
        user_id=user_id,
        filename="coding_round"
    )
    
    # If this is part of a real interview session, save the score immediately
    if chat_id and res.get('score') is not None:
        db = get_db()
        db.execute("""
            INSERT INTO evaluation_scores (chat_id, username, score_type, score_value) 
            VALUES (?, ?, ?, ?)
        """, (chat_id, session.get('username', 'user'), 'code', res['score']))
        
        # Update last activity
        db.execute("UPDATE chats SET last_activity = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))
        db.commit()

    return jsonify(res)

@bp.route('/get_coding_hint', methods=['POST'])
def hint():
    ce = get_code_evaluator()
    h = ce.get_hint(request.json.get('question'))
    return jsonify({"hint": h})

# --- Emotion Tracking ---

@bp.route('/track_emotion', methods=['POST'])
def track_emotion():
    frame = request.json.get("frame")
    if frame:
        emotion_service.process_frame(frame)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@bp.route('/get_and_clear_emotion_avg', methods=['GET'])
def get_emotions():
    return jsonify(emotion_service.get_and_reset_average())

# --- Analytics & Session Management ---

@bp.route('/analytics/<chat_id>', methods=['GET'])
def analytics(chat_id):
    db = get_db()
    
    # 1. Check if we already have scores (Avoid re-running LLM on refresh)
    existing_scores = db.execute("""
        SELECT score_type, score_value FROM evaluation_scores WHERE chat_id = ?
    """, (chat_id,)).fetchall()
    
    tech_score = next((r['score_value'] for r in existing_scores if r['score_type'] == 'technical'), None)
    emo_score = next((r['score_value'] for r in existing_scores if r['score_type'] == 'emotional'), None)
    
    # If we have both scores, return early (Fast Path)
    # We also need the analysis text. Typically, you'd store this in a 'chat_analysis' table.
    # For now, if scores exist, we might just return them. 
    # But if the user wants the TEXT analysis, we might need to re-generate or store it.
    # To keep it simple: if scores exist, we assume analysis is done. 
    # Ideally, store the analysis text in the DB too. 
    
    if tech_score is not None and emo_score is not None:
        # For this version, we'll re-generate text or return a placeholder if strict speed is needed.
        # But let's re-run ONLY if missing.
        pass 

    # 2. Fetch Transcript
    rows = db.execute("SELECT role, message, emotion_context, timestamp FROM messages WHERE chat_id = ? ORDER BY id ASC", (chat_id,)).fetchall()
    transcript = ""
    for row in rows:
        transcript += f"[{row['timestamp']}] {row['role'].upper()}: {row['message']}\n"
        if row['emotion_context'] and row['emotion_context'] != "{}":
            transcript += f"  [EMOTION]: {row['emotion_context']}\n"

    # 3. Run LLM Analysis
    llm = LLMFactory.get_ollama_chat()
    prompt = f"Analyze this interview transcript for technical and emotional performance. Provide a Technical Score (0-10) and Emotional Score (0-10) and constructive feedback:\n{transcript}"
    analysis_text = llm.invoke(prompt)

    # 4. Parse & Save Scores (Only if they don't exist yet to avoid duplicates)
    new_tech, new_emo = _parse_scores_from_text(analysis_text)
    
    # Fallbacks
    if new_tech is None: new_tech = 5.0
    if new_emo is None: new_emo = 5.0

    username = session.get('username', 'user')

    if tech_score is None:
        db.execute("INSERT INTO evaluation_scores (chat_id, username, score_type, score_value) VALUES (?, ?, ?, ?)",
                   (chat_id, username, 'technical', new_tech))
        tech_score = new_tech

    if emo_score is None:
        db.execute("INSERT INTO evaluation_scores (chat_id, username, score_type, score_value) VALUES (?, ?, ?, ?)",
                   (chat_id, username, 'emotional', new_emo))
        emo_score = new_emo
        
    db.commit()

    return jsonify({"analysis": analysis_text, "technical_score": tech_score, "emotional_score": emo_score})

@bp.route('/analysis_page')
def analysis_page():
    # Helper to render the standalone analysis page if accessed directly
    return render_template("dashboard/analysis.html", chat_id=session.get("chat_id"))

@bp.route('/get_session_data', methods=['GET'])
def get_session_data():
    """
    Returns the Master List of sessions for the Dashboard Sidebar.
    Joins Chats + Job Descriptions + Scores.
    """
    db = get_db()
    
    # Query: Get all chats for current user, ordered by latest activity
    # We join Job Descriptions to get the 'Role Name' (filename)
    query = """
        SELECT 
            c.id as chat_id,
            c.started_at,
            c.last_activity,
            jd.filename as role_name,
            (SELECT COUNT(*) FROM messages m WHERE m.chat_id = c.id) as message_count
        FROM chats c
        LEFT JOIN job_descriptions jd ON c.jd_id = jd.id
        WHERE c.username = ?
        ORDER BY c.started_at DESC
    """
    
    username = session.get('username')
    cursor = db.execute(query, (username,))
    sessions_raw = cursor.fetchall()
    
    # Fetch all scores for these chats efficiently
    scores_query = """
        SELECT chat_id, score_type, score_value 
        FROM evaluation_scores 
        WHERE username = ?
    """
    scores_cursor = db.execute(scores_query, (username,))
    all_scores = scores_cursor.fetchall()
    
    # Map scores to chat_ids
    scores_map = {}
    for s in all_scores:
        if s['chat_id'] not in scores_map:
            scores_map[s['chat_id']] = {}
        scores_map[s['chat_id']][s['score_type']] = s['score_value']

    # Build final JSON
    sessions_list = []
    for s in sessions_raw:
        cid = s['chat_id']
        s_scores = scores_map.get(cid, {})
        sessions_list.append({
            "chat_id": cid,
            "role_name": s['role_name'] if s['role_name'] else "General Interview",
            "date": s['started_at'],
            "last_time": s['last_activity'],
            "message_count": s['message_count'],
            "scores": {
                "technical": s_scores.get('technical', '-'),
                "emotional": s_scores.get('emotional', '-'),
                "code": s_scores.get('code', '-')
            }
        })
        
    # We also return a flat list of scores for the aggregate charts
    # (filtering out incomplete sessions if needed)
    flat_scores = []
    for s in all_scores:
        flat_scores.append({
            "chat_id": s['chat_id'],
            "score_type": s['score_type'],
            "score_value": s['score_value']
        })

    return jsonify({"sessions": sessions_list, "evaluation_scores": flat_scores})

@bp.route('/get_session_details/<chat_id>', methods=['GET'])
def get_session_details(chat_id):
    """
    Returns full details for a single session (Transcript + Analysis).
    """
    db = get_db()

    # 1. Fetch Metadata (Role Name)
    meta = db.execute("""
        SELECT c.started_at, jd.filename 
        FROM chats c
        LEFT JOIN job_descriptions jd ON c.jd_id = jd.id
        WHERE c.id = ?
    """, (chat_id,)).fetchone()
    
    role_name = meta['filename'] if meta and meta['filename'] else "Interview"

    # 2. Fetch Transcript
    msg_rows = db.execute(
        "SELECT role, message, emotion_context, timestamp FROM messages WHERE chat_id = ? ORDER BY id ASC",
        (chat_id,)
    ).fetchall()

    transcript = [
        {"role": r["role"], "message": r["message"], "emotion_context": r["emotion_context"], "timestamp": r["timestamp"]}
        for r in msg_rows
    ]

    # 3. Fetch Scores
    score_rows = db.execute("SELECT score_type, score_value FROM evaluation_scores WHERE chat_id = ?", (chat_id,)).fetchall()
    scores = {"technical": None, "emotional": None, "code": None}
    for r in score_rows:
        scores[r["score_type"]] = r["score_value"]

    # 4. Generate Analysis (On the fly)
    analysis_text = ""
    if len(transcript) > 2:
        # Always generate analysis for sessions with sufficient transcript
        transcript_text = ""
        for msg in transcript:
            transcript_text += f"[{msg['timestamp']}] {msg['role'].upper()}: {msg['message']}\n"
            if msg['emotion_context'] and msg['emotion_context'] != "{}":
                transcript_text += f"  [EMOTION]: {msg['emotion_context']}\n"
        
        llm = LLMFactory.get_ollama_chat()
        prompt = f"Analyze this interview transcript for technical and emotional performance. Provide a Technical Score (0-10) and Emotional Score (0-10) and constructive feedback:\n{transcript_text}"
        try:
            analysis_text = llm.invoke(prompt)
        except Exception as e:
            analysis_text = "Failed to generate analysis."
    
        # Parse and insert scores only if not already present
        new_tech, new_emo = _parse_scores_from_text(analysis_text)
        if new_tech is None: new_tech = 5.0
        if new_emo is None: new_emo = 5.0
        
        username = session.get('username', 'user')
        if scores['technical'] is None:
            db.execute("INSERT INTO evaluation_scores (chat_id, username, score_type, score_value) VALUES (?, ?, ?, ?)",
                       (chat_id, username, 'technical', new_tech))
            scores['technical'] = new_tech
        if scores['emotional'] is None:
            db.execute("INSERT INTO evaluation_scores (chat_id, username, score_type, score_value) VALUES (?, ?, ?, ?)",
                       (chat_id, username, 'emotional', new_emo))
            scores['emotional'] = new_emo
        db.commit()
    else:
        analysis_text = "No analysis generated yet."

    return jsonify({
        "chat_id": chat_id,
        "role_name": role_name,
        "transcript": transcript,
        "evaluation_scores": scores,
        "analysis": analysis_text
    })