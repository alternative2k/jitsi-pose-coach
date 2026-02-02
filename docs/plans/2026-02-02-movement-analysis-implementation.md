# Movement Analysis Webapp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a movement analysis webapp with continuous video recording and real-time skeleton detection using YOLOv8-Pose.

**Architecture:** FastAPI backend with YOLOv8-Pose for pose detection and FFmpeg for video processing, simple HTML/CSS/JS frontend with MediaRecorder for chunking, WebSocket for real-time skeleton data streaming.

**Tech Stack:** FastAPI, YOLOv8-Pose, FFmpeg, HTML/CSS/JS, WebSocket

---

## Task 1: Create Project Structure and Dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/README.md`
- Modify: None

**Step 1: Write requirements.txt**

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-multipart==0.0.6
pillow==10.1.0
opencv-python-headless==4.8.1.78
ultralytics==8.1.0
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
pydantic==2.5.0
pydantic-settings==2.1.0
```

**Step 2: Write backend/README.md**

```markdown
# Movement Analysis Backend

FastAPI backend for movement analysis webapp.

## Setup
pip install -r requirements.txt

## Download YOLOv8 Model
```bash
mkdir -p models
curl -O https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt -o models/yolov8m-pose.pt
```

## Run
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Step 3: Create directories**

Run: `mkdir -p backend/models backend/sessions backend/handlers`

**Step 4: Commit**

```bash
git add backend/requirements.txt backend/README.md
git commit -m "feat: add project structure and dependencies"
```

---

## Task 2: Create Authentication Module

**Files:**
- Create: `backend/auth.py`
- Test: None (file-based auth, will test integration)

**Step 1: Write auth.py**

```python
import hashlib
import json
from typing import Optional
from pathlib import Path

USERS_FILE = Path("backend/users.json")

def hash_password(password: str) -> str:
    """Hash password using SHA-256 (simple auth)"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_users_file():
    """Create users file if not exists"""
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({}))

def verify_user(username: str, password: str) -> bool:
    """Verify user credentials"""
    init_users_file()
    users = json.loads(USERS_FILE.read_text())

    if username not in users:
        return False

    return users[username] == hash_password(password)

def add_user(username: str, password: str) -> bool:
    """Add new user (returns False if exists)"""
    init_users_file()
    users = json.loads(USERS_FILE.read_text())

    if username in users:
        return False

    users[username] = hash_password(password)
    USERS_FILE.write_text(json.dumps(users, indent=2))
    return True
```

**Step 2: Commit**

```bash
git add backend/auth.py
git commit -m "feat: add file-based authentication module"
```

---

## Task 3: Create Session Management Module

**Files:**
- Create: `backend/session_manager.py`

**Step 1: Write session_manager.py**

```python
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
```

**Step 2: Commit**

```bash
git add backend/session_manager.py
git commit -m "feat: add session management module"
```

---

## Task 4: Create WebSocket Manager

**Files:**
- Create: `backend/handlers/websocket_manager.py`

**Step 1: Write websocket_manager.py**

```python
from typing import Set, Dict
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # session_id -> WebSocket

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_skeleton_data(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)

    async def send_error(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json({
                "action": "error",
                "message": message
            })
```

**Step 2: Commit**

```bash
git add backend/handlers/websocket_manager.py
git commit -m "feat: add WebSocket manager"
```

---

## Task 5: Create YOLOv8 Pose Detector

**Files:**
- Create: `backend/pose_detector.py`
- Create: `backend/models/yolov8m-pose.pt` (download separately)

**Step 1: Write pose_detector.py**

```python
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
from typing import Dict, List

MODEL_PATH = Path("backend/models/yolov8m-pose.pt")

class PoseDetector:
    def __init__(self):
        self.model = None
        self.load_model()

    def load_model(self):
        """Load YOLOv8 pose model"""
        if not MODEL_PATH.exists():
            print(f"Model file not found at {MODEL_PATH}")
            return

        self.model = YOLO(str(MODEL_PATH))

    def detect_pose(self, image_bytes: bytes) -> Dict:
        """Detect pose from image bytes"""
        if self.model is None:
            return {"joints": [], "metrics": {}}

        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return {"joints": [], "metrics": {}}

        # Run detection
        results = self.model(image, verbose=False)

        if not results or len(results) == 0:
            return {"joints": [], "metrics": {}}

        result = results[0]

        # Get keypoints if detected
        if result.keypoints is None:
            return {"joints": [], "metrics": {}}

        keypoints = result.keypoints.xyn.cpu().numpy()[0]  # Normalized coordinates

        # Convert to joint data
        joints = []
        joint_names = [
            "nose", "left_eye", "right_eye", "left_ear", "right_ear",
            "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_wrist", "right_wrist", "left_hip", "right_hip",
            "left_knee", "right_knee", "left_ankle", "right_ankle"
        ]

        for i, (x, y, conf) in enumerate(keypoints):
            if conf > 0.5:  # Confidence threshold
                joints.append({
                    "name": joint_names[i],
                    "x": float(x),
                    "y": float(y),
                    "confidence": float(conf)
                })

        # Calculate basic metrics
        metrics = self._calculate_metrics(joints)

        return {"joints": joints, "metrics": metrics}

    def _calculate_metrics(self, joints: List[Dict]) -> Dict:
        """Calculate movement metrics from joints"""
        metrics = {
            "leanAngle": 0.0,
            "limbSpeed": 0.0,
            "rangeOfMotion": 0.0
        }

        # Find key joints
        joints_dict = {j["name"]: j for j in joints}

        if "left_shoulder" in joints_dict and "left_hip" in joints_dict:
            # Calculate body lean angle
            shoulder = joints_dict["left_shoulder"]
            hip = joints_dict["left_hip"]

            # Simple vertical angle from hip to shoulder
            dx = shoulder["x"] - hip["x"]
            dy = shoulder["y"] - hip["y"]

            if dy != 0:
                angle = np.degrees(np.arctan2(dx, dy))
                metrics["leanAngle"] = abs(angle)

        return metrics
```

**Step 2: Commit**

```bash
git add backend/pose_detector.py
git commit -m "feat: add YOLOv8 pose detector"
```

---

## Task 6: Create Video Processor (FFmpeg)

**Files:**
- Create: `backend/video_processor.py`

**Step 1: Write video_processor.py**

```python
import subprocess
import asyncio
from pathlib import Path
from typing import List, Optional

class VideoProcessor:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"

    async def append_chunk_to_mp4(self, chunk_path: str, output_path: str, chunk_idx: int):
        """Append video chunk to continuous MP4 stream"""
        try:
            if chunk_idx == 0:
                # First chunk - initialize MP4
                cmd = [
                    self.ffmpeg_path,
                    "-i", chunk_path,
                    "-c:v", "copy",
                    "-c:a", "copy",
                    "-f", "mp4",
                    output_path
                ]
            else:
                # Append chunk - re-encode to ensure continuous stream
                # Note: This simplified version re-encodes for compatibility
                cmd = [
                    self.ffmpeg_path,
                    "-i", output_path,
                    "-i", chunk_path,
                    "-filter_complex", "[0:v:0][1:v:0]concat=n=2:v=1[outv]",
                    "-map", "[outv]",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-y",
                    output_path
                ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"FFmpeg error: {stderr.decode()}")
                return False

            return True

        except Exception as e:
            print(f"Error processing video: {e}")
            return False

    async def merge_final_video(self, chunks: List[str], output_path: str) -> bool:
        """Merge all chunks into final MP4"""
        try:
            # Create concat file for FFmpeg
            concat_file = Path(output_path).parent / "concat.txt"
            concat_lines = [
                f"file '{Path(chunk).resolve()}'"
                for chunk in chunks
            ]
            concat_file.write_text("\n".join(concat_lines))

            # Merge using concat demuxer
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-y",
                output_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"FFmpeg merge error: {stderr.decode()}")
                return False

            # Cleanup concat file
            concat_file.unlink()

            return True

        except Exception as e:
            print(f"Error merging video: {e}")
            return False

    def reencode_chunk_to_mp4(self, input_path: str, output_path: str) -> bool:
        """Re-encode chunk to MP4 format"""
        try:
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                "-y",
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            return result.returncode == 0

        except Exception as e:
            print(f"Error re-encoding: {e}")
            return False
```

**Step 2: Commit**

```bash
git add backend/video_processor.py
git commit -m "feat: add video processor with FFmpeg"
```

---

## Task 7: Create Main FastAPI Application

**Files:**
- Create: `backend/main.py`
- Create: `backend/.env.example`

**Step 1: Write backend/.env.example**

```
SECRET_KEY=change-this-secret-key
PORT=8000
FFMPEG_PATH=ffmpeg
MAX_DISK_USAGE_GB=100
```

**Step 2: Write backend/main.py**

```python
from fastapi import FastAPI, UploadFile, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import base64
import uuid
import os
from io import BytesIO
from PIL import Image

from auth import verify_user
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

@app.post("/video/chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
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
```

**Step 3: Commit**

```bash
git add backend/main.py backend/.env.example
git commit -m "feat: add main FastAPI application"
```

---

## Task 8: Create Frontend HTML

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/styles.css`

**Step 1: Write frontend/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movement Analysis Tool</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="styles.css">
</head>
<body class="bg-gray-900 text-white min-h-screen">
    <!-- Login Page -->
    <div id="loginPage" class="hidden">
        <div class="min-h-screen flex items-center justify-center">
            <div class="bg-gray-800 p-8 rounded-lg shadow-xl max-w-md w-full">
                <h1 class="text-2xl font-bold mb-6 text-center">Movement Analysis Tool</h1>
                <form id="loginForm" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium mb-2">Username</label>
                        <input type="text" id="username" class="w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium mb-2">Password</label>
                        <input type="password" id="password" class="w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 outline-none">
                    </div>
                    <p id="loginError" class="text-red-500 text-sm hidden"></p>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 p-2 rounded font-medium">Login</button>
                </form>
            </div>
        </div>
    </div>

    <!-- Main Dashboard -->
    <div id="dashboardPage" class="hidden">
        <div class="container mx-auto p-4">
            <header class="flex justify-between items-center mb-6">
                <h1 class="text-xl font-bold">Movement Analysis Tool</h1>
                <button id="logoutBtn" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded">Logout</button>
            </header>

            <!-- Start Screen -->
            <div id="startScreen" class="text-center py-20">
                <button id="startBtn" class="bg-green-600 hover:bg-green-700 px-8 py-4 rounded-lg text-xl font-bold">Start Recording</button>
            </div>

            <!-- Recording Screen -->
            <div id="recordingScreen" class="hidden">
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                    <!-- Preview Area -->
                    <div class="bg-gray-800 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                            <h2 class="font-bold">Camera Preview</h2>
                            <button id="togglePreviewBtn" class="bg-gray-600 hover:bg-gray-700 px-3 py-1 rounded text-sm">Hide Preview</button>
                        </div>
                        <div id="videoContainer" class="relative bg-black rounded overflow-hidden aspect-video">
                            <video id="videoPreview" autoplay muted playsinline class="w-full h-full object-cover"></video>
                            <canvas id="skeletonCanvas" class="absolute top-0 left-0 w-full h-full"></canvas>
                        </div>
                        <div id="recordingIndicator" class="hidden mt-2 flex items-center text-red-500">
                            <span class="animate-pulse mr-2">●</span>
                            Recording...
                        </div>
                    </div>

                    <!-- Skeleton & Data Area -->
                    <div class="bg-gray-800 rounded-lg p-4">
                        <div class="flex justify-between items-center mb-2">
                            <h2 class="font-bold">Skeleton & Movement Data</h2>
                            <button id="toggleSkeletonBtn" class="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm">Toggle View</button>
                        </div>
                        <div id="skeletonContainer" class="relative bg-black rounded overflow-hidden aspect-video mb-2">
                            <video id="skeletonVideo" autoplay muted playsinline class="w-full h-full object-cover"></video>
                            <canvas id="skeletonOnlyCanvas" class="absolute top-0 left-0 w-full h-full"></canvas>
                        </div>

                        <!-- Movement Data -->
                        <div id="movementData" class="bg-gray-700 rounded p-3">
                            <div class="flex justify-between mb-2">
                                <button id="dataViewDetailed" class="bg-blue-600 px-3 py-1 rounded text-sm active">Detailed</button>
                                <button id="dataViewSimple" class="bg-gray-600 px-3 py-1 rounded text-sm">Simplified</button>
                            </div>
                            <div id="detailedData" class="text-sm">
                                <p>Waiting for skeleton data...</p>
                            </div>
                            <div id="simpleData" class="hidden text-sm">
                                <p>Waiting for metrics...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="recorder.js"></script>
    <script src="websocket.js"></script>
    <script src="skeleton.js"></script>
</body>
</html>
```

**Step 2: Write frontend/styles.css**

```css
body {
    font-family: system-ui, -apple-system, sans-serif;
}

#videoContainer video,
#skeletonContainer video {
    object-fit: cover;
}

.skeleton-line {
    stroke: rgba(59, 130, 246, 0.8);
    stroke-width: 3;
}

.skeleton-point {
    fill: red;
    stroke: white;
    stroke-width: 2;
    r: 5;
}

.active {
    background-color: #2563eb !important;
}
```

**Step 3: Commit**

```bash
git add frontend/index.html frontend/styles.css
git commit -m "feat: add frontend HTML and styles"
```

---

## Task 9: Implement Recorder.js

**Files:**
- Create: `frontend/recorder.js`

**Step 1: Write frontend/recorder.js**

```javascript
// State
const state = {
    sessionId: null,
    username: null,
    isRecording: false,
    mediaRecorder: null,
    stream: null,
    websocket: null,
    skeletonVisible: true,
    dataView: 'detailed'
};

// UI Elements
const elements = {
    loginPage: document.getElementById('loginPage'),
    dashboardPage: document.getElementById('dashboardPage'),
    startScreen: document.getElementById('startScreen'),
    recordingScreen: document.getElementById('recordingScreen'),
    loginForm: document.getElementById('loginForm'),
    username: document.getElementById('username'),
    password: document.getElementById('password'),
    loginError: document.getElementById('loginError'),
    startBtn: document.getElementById('startBtn'),
    logoutBtn: document.getElementById('logoutBtn'),
    videoPreview: document.getElementById('videoPreview'),
    skeletonVideo: document.getElementById('skeletonVideo'),
    recordingIndicator: document.getElementById('recordingIndicator'),
    togglePreviewBtn: document.getElementById('togglePreviewBtn'),
    toggleSkeletonBtn: document.getElementById('toggleSkeletonBtn'),
    dataViewDetailed: document.getElementById('dataViewDetailed'),
    dataViewSimple: document.getElementById('dataViewSimple'),
    detailedData: document.getElementById('detailedData'),
    simpleData: document.getElementById('simpleData')
};

// Login
elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: elements.username.value,
                password: elements.password.value
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Login failed');
        }

        // Login successful
        state.sessionId = data.session_id;
        state.username = data.username;

        loginPage.classList.add('hidden');
        dashboardPage.classList.remove('hidden');

    } catch (error) {
        elements.loginError.textContent = error.message;
        elements.loginError.classList.remove('hidden');
    }
});

// Logout
elements.logoutBtn.addEventListener('click', async () => {
    if (state.isRecording) {
        await stopRecording();
    }

    state.sessionId = null;
    state.username = null;
    dashboardPage.classList.add('hidden');
    loginPage.classList.remove('hidden');
});

// Start recording
elements.startBtn.addEventListener('click', async () => {
    try {
        // Request camera access
        state.stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480 },
            audio: true
        });

        // Setup video elements
        elements.videoPreview.srcObject = state.stream;
        elements.skeletonVideo.srcObject = state.stream;

        // Start MediaRecorder with 1-second chunks
        state.mediaRecorder = new MediaRecorder(state.stream, {
            mimeType: 'video/webm;codecs=vp8,opus'
        });

        const chunks = [];
        let chunkIndex = 0;

        state.mediaRecorder.ondataavailable = async (event) => {
            if (event.data.size > 0) {
                chunks.push(event.data);

                // Immediately upload chunk
                const blob = new Blob([event.data], { type: 'video/webm' });
                await uploadChunk(blob, chunkIndex);
                chunkIndex++;
            }
        };

        state.mediaRecorder.start(1000); // 1-second chunks

        // Start WebSocket for skeleton detection
        startWebSocket();

        // Update UI
        state.isRecording = true;
        startScreen.classList.add('hidden');
        recordingScreen.classList.remove('hidden');
        recordingIndicator.classList.remove('hidden');

    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Failed to start recording. Please check camera permissions.');
    }
});

// Upload chunk to server
async function uploadChunk(blob, chunkIndex) {
    const formData = new FormData();
    formData.append('chunk', blob);
    formData.append('chunk_index', chunkIndex);
    formData.append('session_id', state.sessionId);

    try {
        const response = await fetch('/video/chunk', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            console.error('Chunk upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
    }
}

// Stop recording
async function stopRecording() {
    if (!state.isRecording) return;

    if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
        state.mediaRecorder.stop();
    }

    // Stop WebSocket
    if (state.websocket) {
        state.websocket.send(JSON.stringify({
            action: 'end_session',
            sessionId: state.sessionId
        }));
        state.websocket.close();
    }

    // Stop stream
    if (state.stream) {
        state.stream.getTracks().forEach(track => track.stop());
    }

    // Update UI
    state.isRecording = false;
    startScreen.classList.remove('hidden');
    recordingScreen.classList.add('hidden');
    elements.videoPreview.srcObject = null;
    elements.skeletonVideo.srcObject = null;
}

// Toggle preview
elements.togglePreviewBtn.addEventListener('click', () => {
    const container = document.getElementById('videoContainer');
    if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        elements.togglePreviewBtn.textContent = 'Hide Preview';
    } else {
        container.classList.add('hidden');
        elements.togglePreviewBtn.textContent = 'Show Preview';
    }
});

// Toggle skeleton view
elements.toggleSkeletonBtn.addEventListener('click', () => {
    const container = document.getElementById('skeletonContainer');
    if (container.classList.contains('hidden')) {
        container.classList.remove('hidden');
        elements.toggleSkeletonBtn.textContent = 'Toggle View';
    } else {
        container.classList.add('hidden');
        elements.toggleSkeletonBtn.textContent = 'Show Skeleton';
    }
});

// Data view toggle
elements.dataViewDetailed.addEventListener('click', () => {
    state.dataView = 'detailed';
    elements.dataViewDetailed.classList.add('active');
    elements.dataViewSimple.classList.remove('active');
    detailedData.classList.remove('hidden');
    simpleData.classList.add('hidden');
});

elements.dataViewSimple.addEventListener('click', () => {
    state.dataView = 'simplified';
    elements.dataViewSimple.classList.add('active');
    elements.dataViewDetailed.classList.remove('active');
    simpleData.classList.remove('hidden');
    detailedData.classList.add('hidden');
});
```

**Step 2: Commit**

```bash
git add frontend/recorder.js
git commit -m "feat: add recorder.js with camera and chunking"
```

---

## Task 10: Implement WebSocket Client

**Files:**
- Create: `frontend/websocket.js`

**Step 1: Write frontend/websocket.js**

```javascript
function startWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws/skeleton`;

    state.websocket = new WebSocket(wsUrl);

    state.websocket.onopen = () => {
        console.log('WebSocket connected');

        // Send connect message
        state.websocket.send(JSON.stringify({
            action: 'connect',
            sessionId: state.sessionId,
            username: state.username
        }));

        // Start frame capture loop
        startFrameCapture();
    };

    state.websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.action === 'skeleton') {
            // Update skeleton display
            if (state.skeletonVisible) {
                drawSkeleton(data.joints);
            }

            // Update movement data display
            updateMovementData(data);
        } else if (data.action === 'error') {
            console.error('WebSocket error:', data.message);
        } else if (data.action === 'session_closed') {
            console.log('Session closed');
        }
    };

    state.websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    state.websocket.onclose = () => {
        console.log('WebSocket disconnected');
    };
}

function startFrameCapture() {
    const captureInterval = 100; // 100ms

    setInterval(() => {
        if (!state.isRecording) return;

        // Capture frame from video
        const video = document.getElementById('videoPreview');
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert to base64 and send
        const imageData = canvas.toDataURL('image/jpeg', 0.7);
        const base64Data = imageData.split(',')[1];

        if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
            state.websocket.send(JSON.stringify({
                action: 'frame',
                image: base64Data
            }));
        }
    }, captureInterval);
}
```

**Step 2: Commit**

```bash
git add frontend/websocket.js
git commit -m "feat: add WebSocket client for skeleton detection"
```

---

## Task 11: Implement Skeleton Display

**Files:**
- Create: `frontend/skeleton.js`

**Step 1: Write frontend/skeleton.js**

```javascript
// Define skeleton connections (keypoint indices from MediaPipe/YOLO)
const SKELETON_CONNECTIONS = [
    [0, 1], [0, 2], [1, 3], [2, 4], // Face
    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10], // Arms
    [5, 11], [6, 12], [11, 12], // Shoulders to hips
    [11, 13], [13, 15], [12, 14], [14, 16] // Legs
];

function drawSkeleton(joints) {
    const canvas = document.getElementById('skeletonCanvas');
    const skeletonCanvas = document.getElementById('skeletonOnlyCanvas');

    // Get video dimensions
    const video = document.getElementById('videoPreview');
    const width = canvas.width = canvas.clientWidth || 640;
    const height = canvas.height = canvas.clientHeight || 480;

    // Clear canvases
    [canvas, skeletonCanvas].forEach(c => {
        const ctx = c.getContext('2d');
        ctx.clearRect(0, 0, c.width, c.height);
    });

    // Draw on both canvases
    [canvas, skeletonCanvas].forEach(c => {
        const ctx = c.getContext('2d');

        // Create joint lookup
        const jointMap = {};
        joints.forEach(j => {
            jointMap[j.name] = {
                x: j.x * c.width,
                y: j.y * c.height
            };
        });

        // Draw connections
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.8)';
        ctx.lineWidth = 3;

        SKELETON_CONNECTIONS.forEach(([startIdx, endIdx]) => {
            const jointNames = [
                "nose", "left_eye", "right_eye", "left_ear", "right_ear",
                "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
                "left_wrist", "right_wrist", "left_hip", "right_hip",
                "left_knee", "right_knee", "left_ankle", "right_ankle"
            ];

            const start = jointMap[jointNames[startIdx]];
            const end = jointMap[jointNames[endIdx]];

            if (start && end) {
                ctx.beginPath();
                ctx.moveTo(start.x, start.y);
                ctx.lineTo(end.x, end.y);
                ctx.stroke();
            }
        });

        // Draw joint points
        joints.forEach(joint => {
            const x = joint.x * c.width;
            const y = joint.y * c.height;

            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fillStyle = 'red';
            ctx.fill();
            ctx.strokeStyle = 'white';
            ctx.lineWidth = 2;
            ctx.stroke();
        });
    });
}

function updateMovementData(data) {
    const joints = data.joints || [];
    const metrics = data.metrics || {};

    if (state.dataView === 'detailed') {
        // Detailed view
        let html = '<h3 class="font-bold mb-2">Joint Coordinates</h3>';

        if (joints.length > 0) {
            html += '<table class="w-full text-xs"><thead><tr><th class="text-left">Joint</th><th>X</th><th>Y</th><th>Conf</th></tr></thead><tbody>';

            joints.slice(0, 10).forEach(joint => { // Show first 10
                html += `
                    <tr>
                        <td class="pr-2">${joint.name}</td>
                        <td class="pr-2">${joint.x.toFixed(2)}</td>
                        <td class="pr-2">${joint.y.toFixed(2)}</td>
                        <td>${joint.confidence.toFixed(2)}</td>
                    </tr>
                `;
            });

            html += '</tbody></table>';
            html += `<p class="mt-2 text-gray-400">Showing 10 of ${joints.length} joints</p>`;
        } else {
            html = '<p>No skeleton detected</p>';
        }

        elements.detailedData.innerHTML = html;

    } else {
        // Simplified view
        let html = '<h3 class="font-bold mb-2">Movement Metrics</h3>';

        if (metrics.leanAngle !== undefined) {
            html += `
                <div class="space-y-2">
                    <div>
                        <span class="text-gray-400">Body Lean Angle:</span>
                        <span class="font-bold ml-2">${metrics.leanAngle.toFixed(1)}°</span>
                    </div>
                    <div>
                        <span class="text-gray-400">Limb Speed:</span>
                        <span class="font-bold ml-2">${metrics.limbSpeed?.toFixed(2) || '0.00'} m/s</span>
                    </div>
                    <div>
                        <span class="text-gray-400">Range of Motion:</span>
                        <span class="font-bold ml-2">${metrics.rangeOfMotion?.toFixed(1) || '0.0'}°</span>
                    </div>
                </div>
            `;
        } else {
            html = '<p>Waiting for metrics...</p>';
        }

        elements.simpleData.innerHTML = html;
    }
}
```

**Step 2: Commit**

```bash
git add frontend/skeleton.js
git commit -m "feat: add skeleton display and movement data visualization"
```

---

## Task 12: Add First User and Test

**Files:**
- Modify: `backend/main.py` (add create user endpoint)
- Create: `backend/users.json`

**Step 1: Modify main.py - add user creation endpoint**

Add this route after `/auth/login`:

```python
@app.post("/auth/users")
async def create_user(request: LoginRequest):
    """Create first user (for setup only)"""
    from auth import add_user

    if not add_user(request.username, request.password):
        raise HTTPException(status_code=400, detail="User already exists")

    return {"message": "User created successfully"}
```

**Step 2: Create initial users.json**

Run: `echo '{}' > backend/users.json`

**Step 3: Test application locally**

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Download YOLOv8 model
mkdir -p backend/models
curl -Lo backend/models/yolov8m-pose.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt

# Start server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Step 4: Create first user via API**

```bash
curl -X POST http://localhost:8000/auth/users \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'
```

**Step 5: Test in browser**

1. Open http://localhost:8000
2. Try login with admin/password
3. Click "Start" button
4. Grant camera permissions
5. Verify skeleton overlay appears
6. Wait 5 seconds
7. Check session folder: `ls backend/sessions/admin/`

**Step 6: Commit**

```bash
git add backend/main.py backend/users.json
git commit -m "feat: add user creation endpoint and initial setup"
```

---

## Task 13: Add Environment Configuration

**Files:**
- Create: `backend/config.py`

**Step 1: Write backend/config.py**

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    secret_key: str = "dev-secret-key-change-me"
    port: int = 8000
    ffmpeg_path: str = "ffmpeg"
    max_disk_usage_gb: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 2: Update main.py to use config**

Add at top after imports:

```python
from config import settings
```

**Step 3: Update main.py endpoints**

In `/auth/users`, add admin check:

```python
# Only allow user creation if no users exist yet
USERS_FILE = Path("backend/users.json")
if USERS_FILE.exists():
    users = json.loads(USERS_FILE.read_text())
    if len(users) > 0:
        raise HTTPException(status_code=403, detail="Users already exist")
```

**Step 4: Commit**

```bash
git add backend/config.py
git commit -m "feat: add environment configuration"
```

---

## Task 14: Fix FFmpeg Merging (Simplified Approach)

**Files:**
- Modify: `backend/video_processor.py`

**Step 1: Replace video_processor.py with simpler merge logic**

```python
import subprocess
import asyncio
from pathlib import Path
from typing import List

class VideoProcessor:
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"

    async def append_chunk_to_mp4(self, chunk_path: str, output_path: str, chunk_idx: int):
        """Simplified chunk handling using concat file approach"""
        try:
            if chunk_idx == 0:
                # First chunk - just save as MP4
                cmd = [
                    self.ffmpeg_path,
                    "-i", chunk_path,
                    "-c", "copy",
                    "-y",
                    output_path
                ]
            else:
                # For subsequent chunks, use concat demuxer
                # Create concat file
                concat_file = Path(output_path).parent / "concat.txt"

                if not concat_file.exists():
                    # Create initial concat with previous output
                    concat_file.write_text(f"file '{Path(output_path).name}'\n")

                # Add new chunk
                concat_content = concat_file.read_text()
                concat_content += f"file '{Path(chunk_path).name}'\n"
                concat_file.write_text(concat_content)

                # Merge using concat
                cmd = [
                    self.ffmpeg_path,
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(concat_file),
                    "-c", "copy",
                    "-y",
                    output_path
                ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"FFmpeg error: {stderr.decode()}")
                return False

            return True

        except Exception as e:
            print(f"Error processing video: {e}")
            return False

    async def merge_final_video(self, chunks: List[str], output_path: str) -> bool:
        """Merge all chunks into final MP4 (at session end)"""
        try:
            # Create concat file
            concat_file = Path(output_path).parent / "concat.txt"
            concat_lines = [
                f"file '{Path(chunk).resolve()}'"
                for chunk in sorted(chunks)
            ]
            concat_file.write_text("\n".join(concat_lines))

            # Merge
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-y",
                output_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"FFmpeg merge error: {stderr.decode()}")
                return False

            concat_file.unlink()
            return True

        except Exception as e:
            print(f"Error merging video: {e}")
            return False

    def reencode_chunk_to_mp4(self, input_path: str, output_path: str) -> bool:
        """Re-encode chunk to MP4 format"""
        try:
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "aac",
                "-y",
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            print(f"Error re-encoding: {e}")
            return False
```

**Step 2: Commit**

```bash
git add backend/video_processor.py
git commit -m "fix: simplify FFmpeg chunk merging logic"
```

---

## Testing Checklist

**After implementing all tasks, run these tests:**

1. **Setup Test**:
   - Install dependencies: `pip install -r backend/requirements.txt`
   - Start server: `uvicorn backend.main:app --reload`
   - Download model: `curl -Lo backend/models/yolov8m-pose.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt`

2. **Authentication Test**:
   - Access http://localhost:8000
   - Login with username/password
   - Verify session created in `backend/sessions/{username}/`

3. **Recording Test**:
   - Click "Start"
   - Grant camera permissions
   - Record for 10 seconds
   - Verify chunks appear in `temp_chunks/`
   - Verify skeleton overlay appears
   - Verify movement data updates

4. **Stop/Logout Test**:
   - Click "Logout"
   - Verify session closes
   - Check final MP4 in `final/` folder
   - Verify MP4 is playable

5. **WebSocket Test**:
   - Disconnect/reconnect camera
   - Verify WebSocket reconnects
   - Verify skeleton detection continues

6. **Error Handling**:
   - Try login with wrong password
   - Try accessing with no session ID
   - Check browser console for errors

---

## Deployment Notes

**Hetzner CPX32 Setup**:
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-pip ffmpeg nginx

# Install Python packages
pip install -r requirements.txt

# Download model
mkdir -p backend/models
curl -Lo backend/models/yolov8m-pose.pt https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m-pose.pt

# Create first user
curl -X POST http://localhost:8000/auth/users \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# Run with uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Nginx Configuration**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```