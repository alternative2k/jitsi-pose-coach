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