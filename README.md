# 🎯 MOCKMATE – AI Powered Mock Interview Platform with Streaming Avatar

## 📌 Project Overview

MOCKMATE is an AI-powered mock interview platform designed to help students and job seekers prepare for technical interviews through personalized resume analysis, job description matching, AI-generated interview questions, coding assessments, performance analytics, and AI-based interview interaction.

The platform analyzes the candidate's resume against a target job description, identifies matching and missing skills, generates customized interview questions, conducts coding evaluations, and provides detailed feedback to improve interview readiness.

---

## 🚀 Key Features

### 🔐 User Authentication
- Secure user registration and login system.
- Session-based authentication using Flask.
- Personalized interview history for each user.

---

### 📄 Resume & Job Description Analysis
- Upload Resume and Job Description in PDF format.
- Extracts text using PyMuPDF.
- OCR support using EasyOCR for scanned documents.
- AI-based skill extraction and analysis.
- Identifies matching skills and areas for improvement.
- Generates customized technical interview questions.

---

### 🤖 AI Mock Interview Assistant
- Interactive AI-based interview workflow.
- Context-aware interview questions based on Resume and JD.
- Conversation history tracking.
- Local LLM integration using Ollama.
- Designed for real-time avatar-based interaction using HeyGen Streaming API.

---

### 💻 Coding Assessment Module
- Programming challenges with problem statements.
- Code editor interface.
- Execution and evaluation workflow.
- Performance-based assessment.

---

### 📊 Performance Analytics & Feedback
- Interview performance dashboard.
- Skill-based feedback.
- Strengths and improvement areas.
- Progress tracking across multiple interview sessions.

---

### 📜 Interview History
- Stores previous interview sessions.
- Tracks interview dates and activity history.
- Enables users to review their preparation journey.

---

## 🏗️ System Architecture

```
User
 |
 v
Flask Web Application
 |
 +-- Authentication Module
 |
 +-- Resume/JD Analyzer
 |       |
 |       +-- PyMuPDF
 |       +-- EasyOCR
 |       +-- Ollama LLM
 |
 +-- AI Interview Module
 |       |
 |       +-- LangChain
 |       +-- Ollama
 |       +-- HeyGen Avatar Integration
 |
 +-- Coding Evaluation Module
 |
 +-- Analytics & Feedback
 |
SQLite Database
```

---

## 🛠️ Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Jinja2 Templates

### Backend
- Python
- Flask
- Flask Blueprints
- SQLite

### Artificial Intelligence & NLP
- Ollama Local LLM
- LangChain
- Google Gemini API (fallback support)
- Faster Whisper (Speech-to-Text)

### Document Processing
- PyMuPDF
- EasyOCR
- Pillow
- NumPy

### Avatar & Communication
- HeyGen Streaming Avatar API
- LiveKit

---

## 📂 Project Structure

```
AI-Mock-Interview-with-Streaming-Avatar/
│
├── app/
│   ├── routes/              # Application routes
│   ├── services/            # AI, OCR and analysis services
│   ├── templates/           # HTML pages
│   ├── static/              # CSS, JS, assets
│   ├── db.py                # Database operations
│   └── config.py            # Application configuration
│
├── instance/
│   └── chat.db              # SQLite database
│
├── tests/                   # Testing files
├── screenshots/             # Project UI screenshots
├── run.py                   # Flask application entry point
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

---

## ⚙️ Installation & Setup

### 1. Clone Repository

```bash
git clone https://github.com/Yuvi25Jain/AI-Mock-Interview-with-Streaming-Avatar.git

cd AI-Mock-Interview-with-Streaming-Avatar
```

---

### 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate Environment:

**Windows**

```bash
venv\Scripts\activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Install & Run Ollama

Install Ollama from:

https://ollama.com/

Download a supported model:

```bash
ollama pull llama3.2
```

Verify:

```bash
ollama list
```

---

### 5. Configure Environment Variables

Add your API keys in the configuration file:

- HeyGen API Key
- Google Gemini API Key (optional fallback)

---

### 6. Run the Application

```bash
python run.py
```

Open the browser:

```
http://127.0.0.1:5000
```

---

## 📸 Application Modules

- Login & Registration Interface
- Resume Upload Interface
- Job Description Analysis
- Skill Gap Analysis
- AI Interview Room
- Coding Round
- Performance Dashboard
- Analytics Dashboard
- Interview History

---

## 🔮 Future Enhancements

- Improve real-time avatar interaction.
- Deploy cloud-based scalable LLM services.
- Advanced coding evaluation engine.
- AI-powered interview scoring.
- Multi-language interview support.
- Voice emotion analysis and personalized feedback.

---

## 👨‍💻 Developed By

**Yuvanshi Bhalawat , Yukti Baldua , Siya Purohit , Tulja Vishwakarma**

AI Mock Interview Platform

---

## ⭐ Acknowledgements

- Flask Community
- Ollama
- LangChain
- HeyGen
- LiveKit
- Open Source AI Community