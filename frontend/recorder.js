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