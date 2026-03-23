import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("./chat_data")
DATA_DIR.mkdir(exist_ok=True)
PROJECTS_FILE = DATA_DIR / "projects.json"
CHATS_FILE = DATA_DIR / "chats.json"
RATINGS_FILE = DATA_DIR / "ratings.json"
SESSION_LOGS_FILE = DATA_DIR / "session_logs.json"

for file_path in [PROJECTS_FILE, CHATS_FILE, RATINGS_FILE, SESSION_LOGS_FILE]:
    if not file_path.exists():
        with open(file_path, "w") as f:
            if file_path == RATINGS_FILE:
                json.dump([], f)
            else:
                json.dump({}, f)


class ChatRepository:
    def __init__(self):
        self.chat_sessions = {}
        self.projects = {}
        self.chat_metadata = {}
        self.load_data()

    def load_data(self):
        try:
            with open(PROJECTS_FILE, "r") as f:
                self.projects = json.load(f)
            with open(CHATS_FILE, "r") as f:
                self.chat_metadata = json.load(f)
        except Exception:
            pass

    def save_projects(self):
        with open(PROJECTS_FILE, "w") as f:
            json.dump(self.projects, f, indent=4)

    def save_chats(self):
        with open(CHATS_FILE, "w") as f:
            json.dump(self.chat_metadata, f, indent=4)

    def save_rating(self, question: str, response: str, rating: int):
        with open(RATINGS_FILE, "r") as f:
            ratings = json.load(f)

        ratings.append({
            "question": question,
            "response": response,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        })

        with open(RATINGS_FILE, "w") as f:
            json.dump(ratings, f, indent=4)

    def load_session_logs(self):
        try:
            with open(SESSION_LOGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_session_logs(self, logs):
        with open(SESSION_LOGS_FILE, "w") as f:
            json.dump(logs, f, indent=4)

    def create_session_log(self, session_id, name, role):
        logs = self.load_session_logs()
        logs[session_id] = {
            "user_name": name,
            "user_role": role,
            "started_at": datetime.now().isoformat(),
            "interactions": []
        }
        self.save_session_logs(logs)

    def append_interaction(self, session_id, question, response_preview, response_time_ms, assistant_type=None, model=None):
        logs = self.load_session_logs()
        if session_id not in logs:
            logs[session_id] = {
                "user_name": "Unknown",
                "user_role": "Unknown",
                "started_at": datetime.now().isoformat(),
                "interactions": []
            }
        logs[session_id]["interactions"].append({
            "question": question,
            "response_preview": response_preview[:200],
            "response_time_ms": response_time_ms,
            "assistant_type": assistant_type,
            "model": model,
            "rating": None,
            "timestamp": datetime.now().isoformat()
        })
        self.save_session_logs(logs)

    def update_interaction_rating(self, session_id, question, rating):
        logs = self.load_session_logs()
        if session_id in logs:
            for interaction in reversed(logs[session_id]["interactions"]):
                if interaction["question"] == question:
                    interaction["rating"] = rating
                    break
            self.save_session_logs(logs)


# Module-level singleton
_repo = None


def get_repository() -> ChatRepository:
    global _repo
    if _repo is None:
        _repo = ChatRepository()
    return _repo
