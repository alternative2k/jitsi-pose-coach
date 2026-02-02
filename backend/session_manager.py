import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

SESSIONS_DIR = Path("backend/sessions")

class SessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, dict] = {}

    def create_session(self, username: str) -> dict:
        """Create new session for user"""
        session_id = str(uuid.uuid4())
        session_dir = SESSIONS_DIR / username / session_id

        # Create directories
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "temp_chunks").mkdir(exist_ok=True)
        (session_dir / "final").mkdir(exist_ok=True)

        session = {
            "session_id": session_id,
            "username": username,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
            "chunks": [],
            "session_dir": str(session_dir)
        }

        self.active_sessions[session_id] = session

        # Save metadata
        (session_dir / "metadata.json").write_text(
            json.dumps({"status": "active", "created_at": session["created_at"]})
        )

        return session

    def add_chunk(self, session_id: str, chunk_idx: int, chunk_path: str):
        """Add chunk to session"""
        if session_id not in self.active_sessions:
            return False

        self.active_sessions[session_id]["chunks"].append({
            "index": chunk_idx,
            "path": chunk_path
        })
        return True

    def close_session(self, session_id: str) -> Optional[dict]:
        """Close session and return metadata"""
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions[session_id]
        session["status"] = "closed"
        session["closed_at"] = datetime.utcnow().isoformat()

        # Update metadata
        session_dir = Path(session["session_dir"])
        metadata_file = session_dir / "metadata.json"
        metadata = json.loads(metadata_file.read_text())
        metadata["closed_at"] = session["closed_at"]
        metadata_file.write_text(json.dumps(metadata))

        del self.active_sessions[session_id]

        return session