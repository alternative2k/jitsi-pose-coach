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