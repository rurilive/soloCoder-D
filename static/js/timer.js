document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const minutesDisplay = document.getElementById('minutes');
    const secondsDisplay = document.getElementById('seconds');
    const timerLabel = document.getElementById('timer-label');
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const modeBtns = document.querySelectorAll('.mode-btn');
    const pomodoroCountDisplay = document.getElementById('pomodoro-count');
    const totalTimeDisplay = document.getElementById('total-time');

    // 时间配置（分钟）
    const timeConfig = {
        'work': 25,
        'short-break': 5,
        'long-break': 15
    };

    // 状态变量
    let currentMode = 'work';
    let totalSeconds = timeConfig[currentMode] * 60;
    let timerInterval = null;
    let isRunning = false;
    let pomodoroCount = 0;
    let totalWorkMinutes = 0;

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

    // 更新模式标签
    function updateModeLabel() {
        const labels = {
            'work': '工作时间',
            'short-break': '短休息时间',
            'long-break': '长休息时间'
        };
        timerLabel.textContent = labels[currentMode];
    }

    // 切换模式
    function switchMode(mode) {
        if (isRunning) {
            pauseTimer();
        }
        
        currentMode = mode;
        totalSeconds = timeConfig[currentMode] * 60;
        
        // 更新模式按钮样式
        modeBtns.forEach(btn => {
            btn.classList.remove('mode-active');
            if (btn.dataset.mode === mode) {
                btn.classList.add('mode-active');
            }
        });
        
        updateDisplay();
        updateModeLabel();
    }

    // 开始计时器
    function startTimer() {
        if (isRunning) return;
        
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
        totalSeconds = timeConfig[currentMode] * 60;
        updateDisplay();
    }

    // 计时器完成
    function timerComplete() {
        pauseTimer();
        
        // 播放提示音（如果浏览器支持）
        playNotificationSound();
        
        // 如果是工作模式，更新统计
        if (currentMode === 'work') {
            pomodoroCount++;
            totalWorkMinutes += timeConfig['work'];
            updateStats();
        }
        
        // 显示完成消息
        alert(`时间到！${currentMode === 'work' ? '工作时间结束，休息一下吧！' : '休息时间结束，准备开始下一个番茄钟！'}`);
        
        // 自动切换到下一个模式
        if (currentMode === 'work') {
            // 每4个番茄钟后是长休息
            if (pomodoroCount % 4 === 0) {
                switchMode('long-break');
            } else {
                switchMode('short-break');
            }
        } else {
            switchMode('work');
        }
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
    
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            switchMode(btn.dataset.mode);
        });
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
