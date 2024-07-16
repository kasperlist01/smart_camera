document.addEventListener('DOMContentLoaded', function () {
    // Установка соединения с сервером через Socket.IO
    const socket = io.connect('http://localhost:5001');

    // Обработка успешного соединения
    socket.on('connect', function() {
        console.log("Socket connected successfully");
    });

    // Обработка ошибок соединения
    socket.on('connect_error', (error) => {
        console.error('Connection Error:', error);
    });

    // Нахождение элементов в DOM
    const video = document.querySelector('video');
    const canvas = document.querySelector('canvas');
    const context = canvas.getContext('2d');
    const startButton = document.getElementById('startButton');
    let localStream = null;

    // Обработчик нажатия на кнопку 'Start Camera'
    startButton.onclick = async function() {
        if (!localStream) {
            try {
                // Запрос доступа к медиа (камере)
                localStream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = localStream;
                video.play();
                sendFramePeriodically();
            } catch (error) {
                alert('Failed to get video stream. Please ensure the camera is connected and allowed.');
            }
        } else {
            // Остановка потока видео
            stopVideoStream();
        }
    };

    // Функция для остановки видео потока
    function stopVideoStream() {
        if (localStream) {
            localStream.getTracks().forEach(track => track.stop());
            localStream = null;
            video.srcObject = null;
        }
    }

    // Периодическая отправка кадров на сервер
    function sendFramePeriodically() {
        if (video.paused || video.ended || !localStream) return;
        canvas.width = video.videoWidth * 0.7;
        canvas.height = video.videoHeight * 0.7;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const data = canvas.toDataURL('image/jpeg', 1);
        socket.emit('send_frame', data.split(',')[1]);
        requestAnimationFrame(sendFramePeriodically);
    }

    // Обработка получения кадра от сервера
    socket.on('receive_frame', function(data) {
        if (!data.image) {
            return;
        }
        const img = new Image();
        img.onload = function() {
            const processedCanvas = document.getElementById('processedCanvas');
            const processedContext = processedCanvas.getContext('2d');
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
