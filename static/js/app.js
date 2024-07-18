document.addEventListener('DOMContentLoaded', function () {
    const socket = io('https://192.168.3.38:5003', {
        transports: ['websocket', 'polling'],
        path: '/socket.io'
    });

    socket.on('connect', function() {
        console.log("Socket connected successfully");
    });

    socket.on('connect_error', (error) => {
        console.error('Connection Error:', error);
    });

    const video = document.querySelector('video');
    const canvas = document.querySelector('canvas');
    const context = canvas.getContext('2d');
    const processedCanvas = document.getElementById('processedCanvas');
    const processedContext = processedCanvas.getContext('2d');
    const startButton = document.getElementById('startButton');
    const toggleButton = document.getElementById('toggleButton');
    let localStream = null;
    let usingFrontCamera = false; // Задняя камера по умолчанию

    startButton.onclick = async function() {
        if (!localStream) {
            try {
                console.log("Requesting camera access");
                await startCamera(usingFrontCamera);
                console.log("Camera access granted");
                sendFramePeriodically();
                startButton.innerHTML = '<i class="fas fa-video"></i> Stop Camera'; // Изменение надписи на кнопке
            } catch (error) {
                console.error("Failed to get video stream:", error);
                alert('Failed to get video stream. Please ensure the camera is connected and allowed.');
            }
        } else {
            stopVideoStream();
            startButton.innerHTML = '<i class="fas fa-video"></i> Start Camera'; // Изменение надписи на кнопке
            clearCanvas();
        }
    };

    toggleButton.onclick = function() {
        usingFrontCamera = !usingFrontCamera;
        if (localStream) {
            startButton.click();  // Нажимаем кнопку "Start Camera" для остановки камеры
            startButton.click();  // Нажимаем кнопку "Start Camera" снова для запуска камеры с другой стороны
        }
    };

    async function startCamera(front) {
        const constraints = {
            video: {
                facingMode: front ? 'user' : 'environment'
            }
        };
        localStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = localStream;
        video.play();
    }

    function stopVideoStream() {
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
            video.srcObject = null;
            console.log("Camera stopped");
        }
    }

    function clearCanvas() {
        processedContext.clearRect(0, 0, processedCanvas.width, processedCanvas.height);
    }

    function sendFramePeriodically() {
        if (video.paused || video.ended || !localStream) return;
        canvas.width = video.videoWidth; // Уменьшение разрешения
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const data = canvas.toDataURL('image/jpeg', 0.8).split(',')[1]; // Уменьшение качества JPEG
        console.log("Sending frame to server");
        socket.emit('send_frame', data);
        requestAnimationFrame(sendFramePeriodically);
    }

    socket.on('receive_frame', function(data) {
        if (!data.image) {
            return;
        }
        const img = new Image();
        img.onload = function() {
            processedCanvas.width = img.width;
            processedCanvas.height = img.height;
            processedContext.clearRect(0, 0, processedCanvas.width, processedCanvas.height);
            processedContext.drawImage(img, 0, 0, processedCanvas.width, processedCanvas.height);
        };
        img.onerror = function() {
            console.error("Error loading the processed image.");
        };
        img.src = 'data:image/jpeg;base64,' + data.image;
    });
});
