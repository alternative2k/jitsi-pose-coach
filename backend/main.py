from fastapi import FastAPI, UploadFile, HTTPException, Depends, WebSocket, WebSocketDisconnect, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import base64
import uuid
import os
import json
from io import BytesIO
from PIL import Image

from auth import verify_user, add_user
from session_manager import SessionManager
from handlers.websocket_manager import WebSocketManager
from pose_detector import PoseDetector
from video_processor import VideoProcessor

app = FastAPI(title="Movement Analysis API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Managers
session_manager = SessionManager()
ws_manager = WebSocketManager()
pose_detector = PoseDetector()
video_processor = VideoProcessor()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class VideoChunk(BaseModel):
    chunk_index: int
    session_id: str

# Routes
@app.get("/")
async def root():
    return FileResponse("frontend/index.html")

@app.post("/auth/login")
async def login(request: LoginRequest):
    if not verify_user(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create new session
    session = session_manager.create_session(request.username)

    return {"session_id": session["session_id"], "username": request.username}

@app.post("/auth/users")
async def create_user(request: LoginRequest):
    """Create first user (for setup only)"""
    # Only allow user creation if no users exist yet
    USERS_FILE = Path("backend/users.json")
    if USERS_FILE.exists():
        users = json.loads(USERS_FILE.read_text())
        if len(users) > 0:
            raise HTTPException(status_code=403, detail="Users already exist")

    if not add_user(request.username, request.password):
        raise HTTPException(status_code=400, detail="User already exists")

    return {"message": "User created successfully"}

@app.post("/video/chunk")
async def upload_chunk(
    chunk: UploadFile,
    chunk_index: int = Form(...),
    session_id: str = Form(...)
):
    """Upload video chunk"""
    if session_id not in session_manager.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_manager.active_sessions[session_id]
    session_dir = Path(session["session_dir"])
    chunk_path = session_dir / "temp_chunks" / f"chunk_{chunk_index}.webm"

    # Save chunk
    chunk_path.write_bytes(await chunk.read())

    # Add to session
    session_manager.add_chunk(session_id, chunk_index, str(chunk_path))

    # Append to continuous MP4
    output_path = session_dir / "final" / "recording.mp4"

    # Re-encode chunk to MP4 first
    mp4_chunk_path = chunk_path.parent / f"chunk_{chunk_index}.mp4"
    video_processor.reencode_chunk_to_mp4(str(chunk_path), str(mp4_chunk_path))

    await video_processor.append_chunk_to_mp4(str(mp4_chunk_path), str(output_path), chunk_index)

    return {"status": "success", "chunk_index": chunk_index}

@app.websocket("/ws/skeleton")
async def skeleton_detection(websocket: WebSocket):
    await websocket.accept()

    session_id = None
    username = None

    try:
        data = await websocket.receive_json()

        if data.get("action") == "connect":
            session_id = data.get("sessionId")
            username = data.get("username")

            if not session_id:
                await websocket.close()
                return

            ws_manager.connect(websocket, session_id)

            # Send confirmation
            await websocket.send_json({"action": "connected"})

        # Process frames
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "frame":
                # Decode base64 image
                image_data = base64.b64decode(data.get("image", ""))

                # Detect pose
                result = pose_detector.detect_pose(image_data)

                # Send skeleton data
                await ws_manager.send_skeleton_data(session_id, {
                    "action": "skeleton",
                    **result
                })

            elif data.get("action") == "end_session":
                # Close session and merge video
                session = session_manager.close_session(session_id)

                if session:
                    chunks_dir = Path(session["session_dir"]) / "temp_chunks"
                    final_path = Path(session["session_dir"]) / "final" / f"session_{session_id[:8]}.mp4"

                    # Get all chunks sorted by index
                    chunks = sorted(chunks_dir.glob("*.mp4"), key=lambda p: int(p.stem.split("_")[1]))

                    # Merge to final MP4
                    await video_processor.merge_final_video([str(c) for c in chunks], str(final_path))

                await websocket.send_json({"action": "session_closed"})
                break

    except WebSocketDisconnect:
        ws_manager.disconnect(session_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if session_id:
            ws_manager.disconnect(session_id)