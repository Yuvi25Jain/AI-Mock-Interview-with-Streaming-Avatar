import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Secret key for session management
    SECRET_KEY = os.getenv('SECRET_KEY', 'secretkey') # Default fallback provided

    # API Keys
    HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
    HEYGEN_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # Database Path (Saved in 'instance' folder)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(os.path.dirname(BASE_DIR), 'instance')
    DATABASE_URI = os.path.join(INSTANCE_DIR, 'chat.db')

    # Upload Paths
    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, 'uploads')
    JD_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'jds')
    RESUME_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')

    # LLM model names & endpoints
    OLLAMA_CHAT_MODEL = os.getenv('OLLAMA_CHAT_MODEL', 'smollm:135m')
    OLLAMA_TOOL_MODEL = os.getenv('OLLAMA_TOOL_MODEL', 'smollm:135m')
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    GOOGLE_CHAT_MODEL = os.getenv('GOOGLE_CHAT_MODEL', 'gemini-2.5-flash')

    # Ensure directories exist
    @staticmethod
    def init_app(app):
        os.makedirs(Config.INSTANCE_DIR, exist_ok=True)
        os.makedirs(Config.JD_UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.RESUME_UPLOAD_FOLDER, exist_ok=True)