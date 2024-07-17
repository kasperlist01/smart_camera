document.addEventListener('DOMContentLoaded', function () {
    const socket = io.connect('http://localhost:5001');

    socket.on('connect', function() {
        console.log("Socket connected successfully");
    });

    socket.on('connect_error', (error) => {
        console.error('Connection Error:', error);
    });

    const video = document.querySelector('video');
    const canvas = document.querySelector('canvas');
    const context = canvas.getContext('2d');
    const detectionsDiv = document.getElementById('detections'); // Элемент для вывода детекций
    const startButton = document.getElementById('startButton');
    const switchCameraButton = document.getElementById('switchCameraButton');
    let localStream = null;
    let lastValidDetection = ""; // Хранение последнего действительного сообщения о детекциях
    let currentCameraIndex = 0;
    let videoDevices = [];

    startButton.onclick = async function() {
        if (!localStream) {
            try {
                await startCamera();
                sendFramePeriodically();
            } catch (error) {
                alert('Failed to get video stream. Please ensure the camera is connected and allowed.');
            }
        } else {
            stopVideoStream();
        }
    };

    switchCameraButton.onclick = async function() {
        currentCameraIndex = (currentCameraIndex + 1) % videoDevices.length;
        await startCamera();
    };

    async function startCamera() {
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
        }

        const devices = await navigator.mediaDevices.enumerateDevices();
        videoDevices = devices.filter(device => device.kind === 'videoinput');
        
        if (videoDevices.length > 0) {
            const videoConstraints = {
                deviceId: { exact: videoDevices[currentCameraIndex].deviceId }
            };
            localStream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints });
            video.srcObject = localStream;
            video.play();
            
            if (videoDevices.length > 1) {
                switchCameraButton.style.display = 'block';
            } else {
                switchCameraButton.style.display = 'none';
            }
        } else {
            alert('No camera found');
        }
    }

    function stopVideoStream() {
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
            video.srcObject = null;
            switchCameraButton.style.display = 'none';
        }
    }

    function sendFramePeriodically() {
        if (video.paused || video.ended || !localStream) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const data = canvas.toDataURL('image/jpeg').split(',')[1]; // Уменьшение качества JPEG
        socket.emit('send_frame', data);
        requestAnimationFrame(sendFramePeriodically);
    }

    socket.on('receive_frame', function(data) {
        if (data.image) {
            const img = new Image();
            img.onload = function() {
                const processedCanvas = document.getElementById('processedCanvas');
                const processedContext = processedCanvas.getContext('2d');
                processedCanvas.width = img.width;
                processedCanvas.height = img.height;
                processedContext.clearRect(0, 0, processedCanvas.width, processedCanvas.height);
                processedContext.drawImage(img, 0, 0, processedCanvas.width, processedCanvas.height);
            };
            img.src = 'data:image/jpeg;base64,' + data.image;
        }
    });

    socket.on('receive_message', function(data) {
        if (data.message && data.message !== 'Frame skipped') {
            lastValidDetection = data.message; // Обновление последнего валидного сообщения
            detectionsDiv.style.display = 'block';
            detectionsDiv.textContent = lastValidDetection;
        } else if (data.message === 'Frame skipped') {
            // Показываем последнее валидное сообщение, если текущее - "Frame skipped"
            if (lastValidDetection) {
                detectionsDiv.style.display = 'block';
                detectionsDiv.textContent = lastValidDetection;
            }
        }
    });
});
