document.addEventListener('DOMContentLoaded', function () {
    const socket = io('https://172.20.10.3:5003', {
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
    const modelSelect = document.getElementById('modelSelect');
    const detectionResults = document.getElementById('detectionResults'); // Элемент для отображения результатов
    const translatedResults = document.getElementById('translatedResults'); // Элемент для отображения переведенных результатов
    let localStream = null;
    let usingFrontCamera = false; // Задняя камера по умолчанию
    let lastDetections = []; // Хранение последних детекций
    let detectionTimeout; // Таймаут для очистки старых детекций

    startButton.onclick = async function() {
        if (!localStream) {
            try {
                console.log("Requesting camera access");
                await startCamera(usingFrontCamera);
                console.log("Camera access granted");
                sendFramePeriodically();
                startButton.innerHTML = '<i class="fas fa-video"></i> Выключить камеру'; // Изменение надписи на кнопке
            } catch (error) {
                console.error("Failed to get video stream:", error);
                alert('Failed to get video stream. Please ensure the camera is connected and allowed.');
            }
        } else {
            stopVideoStream();
            startButton.innerHTML = '<i class="fas fa-video"></i> Включить камеру'; // Изменение надписи на кнопке
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

    modelSelect.onchange = function() {
        const selectedModel = modelSelect.value;
        console.log("Selected model:", selectedModel);
        socket.emit('set_model', { model_type: selectedModel });
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
        detectionResults.innerHTML = ''; // Очистка результатов
        translatedResults.innerHTML = ''; // Очистка переведенных результатов
        lastDetections = []; // Сброс последних детекций
        if (detectionTimeout) clearTimeout(detectionTimeout);
    }

    function sendFramePeriodically() {
        if (video.paused || video.ended || !localStream) return;
        canvas.width = video.videoWidth; // Уменьшение разрешения
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const data = canvas.toDataURL('image/jpeg').split(',')[1]; // Уменьшение качества JPEG
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
        updateDetectionResults(data.detections); // Обновление результатов
    });

    function updateDetectionResults(detections) {
        if (detections && detections.length > 0) {
            lastDetections = detections; // Обновляем последние детекции
            if (detectionTimeout) clearTimeout(detectionTimeout); // Очищаем предыдущий таймаут
            detectionTimeout = setTimeout(() => {
                lastDetections = []; // Очищаем детекции после 2 секунд
                detectionResults.innerHTML = '';
                translatedResults.innerHTML = '';
            }, 2000);
        }

        detectionResults.innerHTML = ''; // Очистка предыдущих результатов
        if (lastDetections.length === 0) {
            detectionResults.innerHTML = '';
            translatedResults.innerHTML = '';
            return;
        }

        const leftColumn = document.createElement('ul');
        const rightColumn = document.createElement('ul');
        lastDetections.forEach((detection, index) => {
            const listItem = document.createElement('li');
            listItem.textContent = `${detection.translated_class_name || detection.class_name} (${(detection.confidence * 100).toFixed(2)}%)`;
            if (index % 2 === 0) {
                leftColumn.appendChild(listItem);
            } else {
                rightColumn.appendChild(listItem);
            }
        });

        detectionResults.appendChild(leftColumn);
        detectionResults.appendChild(rightColumn);
    }
});
