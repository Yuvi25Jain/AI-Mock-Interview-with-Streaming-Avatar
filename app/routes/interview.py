import uuid
import os
import requests
from flask import Blueprint, request, jsonify, session, current_app, render_template, redirect, url_for
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from faster_whisper import WhisperModel
from app.db import get_db
from app.services.llm_factory import LLMFactory

bp = Blueprint('interview', __name__)

@bp.route('/interview')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('interview/index.html')

@bp.route('/start_chat_session', methods=['POST'])
def start_chat_session():
    """
    Initializes a new chat session in the DB.
    Expects 'jd_id' in the JSON body to link this session to a specific Job Description.
    """
    chat_id = str(uuid.uuid4())
    session["chat_id"] = chat_id
    
    data = request.json or {}
    jd_id = data.get('jd_id')  # Passed from the Analyze page "Enter Interview" button

    # Persist chat metadata linked to the JD
    db = get_db()
    db.execute(
        "INSERT INTO chats (id, username, jd_id, started_at, last_activity) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (chat_id, session.get("username"), jd_id)
    )
    db.commit()

    return jsonify({"chat_id": chat_id})

@bp.route('/start_session', methods=['POST'])
def start_heygen_session():
    """Starts the HeyGen Interactive Avatar session."""
    api_key = current_app.config['HEYGEN_API_KEY']
    avatar_id = current_app.config['HEYGEN_AVATAR_ID']
    
    try:
        # 1. Get Token
        headers = {'X-API-KEY': api_key}
        resp = requests.post("https://api.heygen.com/v1/streaming.create_token", headers=headers)
        resp.raise_for_status()
        token = resp.json()['data']['token']
        session["session_token"] = token

        # 2. Start Session
        auth_headers = {'Authorization': f'Bearer {token}'}
        body = {"version": "v2", "avatar_id": avatar_id, "quality": "medium", "video_encoding": "VP8"}
        resp = requests.post("https://api.heygen.com/v1/streaming.new", json=body, headers=auth_headers)
        resp.raise_for_status()
        data = resp.json()['data']

        session["session_id"] = data['session_id']
        
        # 3. Start Avatar
        requests.post("https://api.heygen.com/v1/streaming.start", 
                      json={"session_id": data['session_id']}, headers=auth_headers).raise_for_status()

        return jsonify({"session_id": data['session_id'], "livekit_url": data['url'], "livekit_token": data['access_token']})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/stop_session', methods=['POST'])
def stop_session():
    sid = session.get("session_id")
    token = session.get("session_token")
    if sid and token:
        try:
            requests.post("https://api.heygen.com/v1/streaming.stop", 
                          json={"session_id": sid}, 
                          headers={'Authorization': f'Bearer {token}'})
        except:
            pass
    session["session_id"] = None
    return jsonify({"message": "Stopped"})

@bp.route('/interact', methods=['POST'])
def interact():
    print("Audio request received")  # Debug: Confirm backend hit
    if 'audio' not in request.files:
        print("No audio file in request")
        return jsonify({"error": "No audio"}), 400

    # 1. Save and Transcribe
    audio = request.files['audio']
    unique_filename = f"audio_{uuid.uuid4().hex}.wav"
    audio.save(unique_filename)
    print(f"Audio saved as {unique_filename}")  # Debug
    
    try:
        model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(unique_filename)
        user_text = " ".join(s.text for s in segments)
        print(f"Transcribed text: '{user_text}'")  # Debug
    finally:
        if os.path.exists(unique_filename):
            os.remove(unique_filename)

    if not user_text.strip():
        print("No speech detected")
        return jsonify({"user_text": "", "gemini_text": "I didn't hear anything."})

    # 2. Prepare LLM Context
    emotion_context = request.form.get('emotion_context', "{}")
    
    # Retrieve context from session (populated during Analyze phase)
    resume_skills = session.get('resume_skills', 'N/A')
    jd_skills = session.get('jd_skills', 'N/A')
    questions = session.get('questions', [])
    
    system_prompt = f"""
    You are an AI Interviewer. 
    Context:
    Resume Skills: {resume_skills}
    JD Skills: {jd_skills}
    Questions: {questions}
    User Emotion: {emotion_context}
    
    Rules: 
    1. Ask one question at a time based on the Context.
    2. Be professional but conversational.
    3. Keep responses concise (under 3 sentences) suitable for a spoken avatar.
    """
    
    messages = [SystemMessage(content=system_prompt)]
    
    # Fetch History (Context Window)
    db = get_db()
    chat_id = session.get("chat_id")
    if chat_id:
        rows = db.execute("SELECT role, message FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT 6", (chat_id,)).fetchall()
        # Reconstruct history in chronological order
        for row in reversed(rows):
            if row['role'] == 'user': messages.append(HumanMessage(content=row['message']))
            else: messages.append(AIMessage(content=row['message']))
    
    messages.append(HumanMessage(content=user_text))

    # 3. Get LLM Response
    print("Generating LLM response")  # Debug before LLM call
    llm = LLMFactory.get_ollama_chat()
    response_text = llm.invoke(messages)
    print(f"LLM response: '{response_text}'")  # Debug
    
    # Handle LangChain output (it might return an object or string depending on version)
    if hasattr(response_text, 'content'):
        response_text = response_text.content

    # 4. Speak (HeyGen)
    token = session.get("session_token")
    sid = session.get("session_id")
    if token and sid:
        try:
            requests.post("https://api.heygen.com/v1/streaming.task", 
                          json={"session_id": sid, "text": response_text, "task_type": "repeat"},
                          headers={'Authorization': f'Bearer {token}'})
        except Exception as e:
            print(f"HeyGen Error: {e}")

    # 5. Save to DB
    if chat_id:
        db.execute("INSERT INTO messages (chat_id, role, message, emotion_context) VALUES (?, ?, ?, ?)", 
                   (chat_id, 'user', user_text, emotion_context))
        db.execute("INSERT INTO messages (chat_id, role, message) VALUES (?, ?, ?)", 
                   (chat_id, 'ai', response_text))
        
        # Update last_activity for dashboard sorting
        db.execute("UPDATE chats SET last_activity = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))
        db.commit()

    return jsonify({"user_text": user_text, "gemini_text": response_text})