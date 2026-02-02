# Movement Analysis Webapp Design

**Date**: 2026-02-02
**Purpose**: Movement analysis tool for real-time skeleton detection and continuous video recording

## Overview

A web application hosted on Hetzner CPX32 server that allows users to:
- Login via simple file-based authentication
- Record continuous video from webcam or mobile device
- View real-time skeleton detection using YOLOv8-Pose
- Analyze movement data (joint angles, limb speed, body lean)
- Store recorded videos as MP4 on server with no data loss

## Technology Stack

- **Frontend**: Simple HTML/CSS/JS (no build framework)
- **Backend**: FastAPI (Python)
- **Pose Detection**: YOLOv8-Pose
- **Video Processing**: FFmpeg
- **Hosting**: Hetzner CPX32 server
- **Future**: Docker containerization

## Architecture

### Backend (FastAPI)
```
backend/
├── main.py                    # FastAPI app with routes and WebSocket
├── video_processor.py         # FFmpeg streaming and MP4 merging
├── pose_detector.py           # YOLOv8-Pose wrapper
├── auth.py                    # File-based login
├── handlers/
│   ├── upload_streaming.py   # Video chunk handling
│   └── websocket_manager.py  # WebSocket connections
├── models/                    # YOLOv8 model files
├── sessions/{username}/       # Session folders
│   └── session-{id}/
│       ├── final/session-{timestamp}.mp4
│       ├── temp_chunks/chunk-{seq}.webm
│       └── metadata.json
└── uploads/
```

### Frontend
```
frontend/
├── index.html                 # Single-page app
├── recorder.js                # MediaRecorder chunking
├── websocket.js               # WebSocket client
└── skeleton.js                # Canvas skeleton overlay
```

## Data Flow

### Continuous Recording (No Data Loss)
1. User clicks "Start" → Frontend opens WebSocket, requests camera via `getUserMedia()`
2. Frontend starts MediaRecorder with `timeslice=1000ms` (1-second chunks)
3. Each chunk POSTs to `/video/chunk` immediately
4. Backend appends chunks to continuous MP4 stream using FFmpeg
5. On logout/close → FFmpeg merges all chunks into final `session-{timestamp}.mp4`

### Parallel Skeleton Detection
1. Every 100ms, frontend captures frame → WebSocket
2. Backend runs YOLOv8-Pose → returns joint coordinates + movement numbers
3. Frontend updates skeleton overlay and data display

### Session Management
- Session folders based on username: `sessions/{username}/session-{id}/`
- Temp chunks stored with sequential naming
- Final MP4 in `/final/` subfolder
- Metadata.json tracks timestamps and settings

## Client State
```javascript
{
  authState: 'guest' | 'authenticated',
  username: string,
  sessionId: string,
  isRecording: boolean,
  isPreviewVisible: boolean,
  isSkeletonVisible: boolean,
  dataView: 'detailed' | 'simplified',
  connectionStatus: 'disconnected' | 'connecting' | 'connected'
}
```

## WebSocket Protocol

**Client → Server**:
```json
{"action": "frame", "image": "base64_jpeg"}
{"action": "end_session", "sessionId": "..."}
```

**Server → Client**:
```json
{"action": "skeleton", "joints": [...], "metrics": {...}}
{"action": "error", "message": "..."}
```

## Movement Data Structure
```javascript
{
  joints: [
    { name: "nose", x: 0.5, y: 0.3, confidence: 0.95 },
    { name: "left_shoulder", x: 0.4, y: 0.4, confidence: 0.9 },
    // ... 17 YOLOv8 keypoints
  ],
  metrics: {
    leanAngle: 12.5,
    limbSpeed: 2.3,
    rangeOfMotion: 45
  },
  timestamp: 1234567890
}
```

## UI Layout

**Login Page**:
- Centered card with username/password fields
- "Login" button → `/auth/login`
- Error message display

**Main Dashboard**:
```
Header: "Movement Analysis Tool"    [Logout]
------------------------------------------------
[START] button (large, centered)
------------------------------------------------
When active:
[Close Preview]  [Toggle Skeleton]
Video Preview | Skeleton Overlay
               |
               | Movement Data (switchable)
               | - Joint angles / Simplified
               | Table/graph display
```

## Error Handling

**Network Interruptions**:
- WebSocket: Auto-reconnect with exponential backoff, buffer data locally
- Video chunks: Retry 3x with backoff, store failed chunks in IndexedDB
- Session recovery: Check for orphaned chunks on reconnect

**Recording Edge Cases**:
- Camera denied: Show error modal with permission link
- MediaRecorder unsupported: Fallback to canvas capture
- FFmpeg merge fail: Keep temp chunks, offer retry/delete option
- Browser close: Beforeunload event, sync cleanup

**YOLOv8 Errors**:
- Model load fail: Graceful degradation, show video without skeleton
- Inference timeout: Skip frame, continue next
- Invalid data: Filter low-confidence joints, interpolate keypoints

**Resource Limits (CPX32)**:
- Disk: Monitor `/sessions/`, warn at 80% usage
- CPU: Throttle skeleton detection if CPU > 90%
- Memory: Clear buffer every 500 frames

## Testing Strategy

**Local Development**:
- Camera access test (desktop + mobile)
- Video recording/chunk upload verification
- FFmpeg merge: 5-minute session → continuous MP4
- Skeleton detection test on various poses
- WebSocket reconnection simulation

**Server-Side**:
- Authentication tests (valid/invalid)
- Chunk upload (100+ chunks) → folder structure
- FFmpeg merge (50 chunks) → playable MP4
- YOLOv8 inference speed (<100ms target)
- Resource limit tests

**Integration**:
- Full workflow: Login → Start → Record → Stop → Logout → Verify MP4
- Network interruption: WiFi disconnect → reconnect → verify continuation
- Mobile device: iOS/Android camera test
- Concurrent users: 3 users recording simultaneously

## Deployment

**Hetzner CPX32 Setup**:
```bash
sudo apt update
sudo apt install -y python3-pip ffmpeg nginx
pip3 install fastapi uvicorn websockets python-multipart pillow opencv-python-headless
pip install ultralytics  # YOLOv8
```

**Directory Structure**:
```
/var/www/movement-analysis/
├── backend/
├── frontend/
├── users.json
└── .env
```

**Nginx**:
- Proxy pass to FastAPI :8000
- SSL with Let's Encrypt

**Environment Variables**:
```
PORT=8000
SECRET_KEY=<random>
FFMPEG_PATH=/usr/bin/ffmpeg
MAX_DISK_USAGE_GB=100
```

**Systemd Service**:
- Auto-start FastAPI on boot
- Log rotation

**Monitoring**:
- Daily disk space check, alert at 80%