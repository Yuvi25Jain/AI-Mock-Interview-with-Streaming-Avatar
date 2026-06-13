import pytest
from app import create_app
from app.db import init_db, get_db

class DummyLLM:
    def invoke(self, *args, **kwargs):
        return "technical: 8.0\nemotional: 7.5"

@pytest.fixture
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    app = create_app({
        'TESTING': True,
        'DATABASE_URI': str(db_path),
        'SECRET_KEY': 'test'
    })
    monkeypatch.setattr('app.routes.api.LLMFactory.get_ollama_chat', staticmethod(lambda: DummyLLM()))
    with app.app_context():
        init_db()
        yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_start_submit_and_dashboard(client, app):
    # create user and login
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (username, password) VALUES (?,?)", ('tester','pw'))
        db.commit()

    # login
    client.post('/login', data={'username':'tester','password':'pw'})

    # start session
    r = client.post('/start_chat_session')
    assert r.status_code == 200
    chat_id = r.get_json()['chat_id']

    # submit code score
    r2 = client.post('/submit_code_score', json={'score': 8.5})
    assert r2.status_code == 200

    # session data should include the code score
    r3 = client.get('/get_session_data')
    assert r3.status_code == 200
    data = r3.get_json()
    codes = [e for e in data['evaluation_scores'] if e['score_type']=='code' and e['chat_id']==chat_id]
    assert len(codes) == 1
    assert abs(float(codes[0]['score_value']) - 8.5) < 1e-6