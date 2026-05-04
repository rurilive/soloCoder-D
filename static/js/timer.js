document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const minutesDisplay = document.getElementById('minutes');
    const secondsDisplay = document.getElementById('seconds');
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const pomodoroCountDisplay = document.getElementById('pomodoro-count');
    const totalTimeDisplay = document.getElementById('total-time');

    // 快速时间按钮
    const quickTimeBtns = document.querySelectorAll('.quick-time-btn');
    
    // 时间输入框
    const customMinutesInput = document.getElementById('custom-minutes');
    const customSecondsInput = document.getElementById('custom-seconds');

    // 状态变量
    let totalSeconds = 25 * 60;
    let timerInterval = null;
    let isRunning = false;
    let pomodoroCount = 0;
    let totalWorkMinutes = 0;
    
    // 保存初始时间，用于重置
    let initialSeconds = totalSeconds;

    // 初始化
    updateDisplay();
    updateStats();

    // 更新计时器显示
    function updateDisplay() {
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        
        minutesDisplay.textContent = minutes.toString().padStart(2, '0');
        secondsDisplay.textContent = seconds.toString().padStart(2, '0');
    }

    // 更新统计信息
    function updateStats() {
        pomodoroCountDisplay.textContent = pomodoroCount;
        totalTimeDisplay.textContent = `${totalWorkMinutes}分钟`;
    }

    // 设置时间
    function setTime(minutes, seconds = 0) {
        if (isRunning) {
            pauseTimer();
        }
        
        // 验证输入
        minutes = Math.max(1, Math.min(120, parseInt(minutes) || 0));
        seconds = Math.max(0, Math.min(59, parseInt(seconds) || 0));
        
        totalSeconds = minutes * 60 + seconds;
        initialSeconds = totalSeconds;
        
        // 更新输入框
        customMinutesInput.value = minutes;
        customSecondsInput.value = seconds;
        
        updateDisplay();
    }

    // 开始计时器
    function startTimer() {
        if (isRunning) return;
        
        // 如果总秒数为0，先从输入框获取时间
        if (totalSeconds <= 0) {
            const minutes = parseInt(customMinutesInput.value) || 25;
            const seconds = parseInt(customSecondsInput.value) || 0;
            totalSeconds = minutes * 60 + seconds;
            initialSeconds = totalSeconds;
            updateDisplay();
        }
        
        isRunning = true;
        startBtn.style.display = 'none';
        pauseBtn.style.display = 'inline-block';
        
        timerInterval = setInterval(() => {
            if (totalSeconds > 0) {
                totalSeconds--;
                updateDisplay();
            } else {
                timerComplete();
            }
        }, 1000);
    }

    // 暂停计时器
    function pauseTimer() {
        if (!isRunning) return;
        
        isRunning = false;
        clearInterval(timerInterval);
        timerInterval = null;
        
        startBtn.style.display = 'inline-block';
        pauseBtn.style.display = 'none';
    }

    // 重置计时器
    function resetTimer() {
        pauseTimer();
        
        // 从输入框获取当前时间
        const minutes = parseInt(customMinutesInput.value) || 25;
        const seconds = parseInt(customSecondsInput.value) || 0;
        totalSeconds = minutes * 60 + seconds;
        initialSeconds = totalSeconds;
        
        updateDisplay();
    }

    // 计时器完成
    function timerComplete() {
        pauseTimer();
        
        // 播放提示音（如果浏览器支持）
        playNotificationSound();
        
        // 更新统计
        pomodoroCount++;
        totalWorkMinutes += Math.ceil(initialSeconds / 60);
        updateStats();
        
        // 显示完成消息
        alert('时间到！休息一下吧！');
    }

    // 播放通知音
    function playNotificationSound() {
        try {
            // 创建一个简单的音频上下文
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (e) {
            console.log('音频播放不支持');
        }
    }

    // 事件监听器
    startBtn.addEventListener('click', startTimer);
    pauseBtn.addEventListener('click', pauseTimer);
    resetBtn.addEventListener('click', resetTimer);
    
    // 快速时间按钮点击事件
    quickTimeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const minutes = parseInt(btn.dataset.minutes);
            setTime(minutes, 0);
        });
    });
    
    // 时间输入框变化事件
    customMinutesInput.addEventListener('change', () => {
        const minutes = parseInt(customMinutesInput.value) || 25;
        const seconds = parseInt(customSecondsInput.value) || 0;
        setTime(minutes, seconds);
    });
    
    customSecondsInput.addEventListener('change', () => {
        const minutes = parseInt(customMinutesInput.value) || 25;
        const seconds = parseInt(customSecondsInput.value) || 0;
        setTime(minutes, seconds);
    });

    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            e.preventDefault();
            if (isRunning) {
                pauseTimer();
            } else {
                startTimer();
            }
        } else if (e.code === 'KeyR') {
            resetTimer();
        }
    });
});