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