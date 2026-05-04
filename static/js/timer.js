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

    // 快速时间按钮
    const quickTimeBtns = document.querySelectorAll('.quick-time-btn');
    
    // 时间输入框
    const customMinutesInput = document.getElementById('custom-minutes');
    const customSecondsInput = document.getElementById('custom-seconds');

    // 自定义时间相关元素（番茄工作法预设）
    const customWorkTimeInput = document.getElementById('custom-work-time');
    const customShortBreakInput = document.getElementById('custom-short-break');
    const customLongBreakInput = document.getElementById('custom-long-break');
    const applyCustomTimeBtn = document.getElementById('apply-custom-time');
    const resetDefaultTimeBtn = document.getElementById('reset-default-time');

    // 默认时间配置（分钟）
    const defaultTimeConfig = {
        'work': 25,
        'short-break': 5,
        'long-break': 15
    };

    // 当前时间配置
    let timeConfig = {
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
    
    // 保存初始时间，用于重置
    let initialSeconds = totalSeconds;
    
    // 标记是否使用了自定义时间（非番茄工作法模式）
    let isCustomTimeMode = false;

    // 初始化
    updateDisplay();
    updateStats();
    updateModeLabel();

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
            'long-break': '长休息时间',
            'custom': '自定义时间'
        };
        timerLabel.textContent = labels[currentMode] || '自定义时间';
    }

    // 更新模式按钮上的时间文本
    function updateModeButtonTexts() {
        const workModeBtn = document.getElementById('work-mode');
        const shortBreakModeBtn = document.getElementById('short-break-mode');
        const longBreakModeBtn = document.getElementById('long-break-mode');
        
        if (workModeBtn) workModeBtn.textContent = `工作 (${timeConfig['work']}分钟)`;
        if (shortBreakModeBtn) shortBreakModeBtn.textContent = `短休息 (${timeConfig['short-break']}分钟)`;
        if (longBreakModeBtn) longBreakModeBtn.textContent = `长休息 (${timeConfig['long-break']}分钟)`;
    }

    // 应用自定义番茄工作法时间
    function applyCustomPomadoroTime() {
        const workTime = parseInt(customWorkTimeInput.value);
        const shortBreakTime = parseInt(customShortBreakInput.value);
        const longBreakTime = parseInt(customLongBreakInput.value);

        if (isNaN(workTime) || workTime < 1 || workTime > 60) {
            alert('工作时间必须是1-60分钟之间的数字');
            return;
        }
        if (isNaN(shortBreakTime) || shortBreakTime < 1 || shortBreakTime > 30) {
            alert('短休息时间必须是1-30分钟之间的数字');
            return;
        }
        if (isNaN(longBreakTime) || longBreakTime < 1 || longBreakTime > 60) {
            alert('长休息时间必须是1-60分钟之间的数字');
            return;
        }

        timeConfig['work'] = workTime;
        timeConfig['short-break'] = shortBreakTime;
        timeConfig['long-break'] = longBreakTime;

        updateModeButtonTexts();

        if (isRunning) {
            pauseTimer();
        }
        
        // 如果当前是番茄工作法模式，更新时间
        if (!isCustomTimeMode) {
            totalSeconds = timeConfig[currentMode] * 60;
            initialSeconds = totalSeconds;
            updateDisplay();
        }

        alert('自定义番茄工作法时间已应用！');
    }

    // 恢复默认番茄工作法时间
    function resetDefaultPomadoroTime() {
        timeConfig['work'] = defaultTimeConfig['work'];
        timeConfig['short-break'] = defaultTimeConfig['short-break'];
        timeConfig['long-break'] = defaultTimeConfig['long-break'];

        customWorkTimeInput.value = defaultTimeConfig['work'];
        customShortBreakInput.value = defaultTimeConfig['short-break'];
        customLongBreakInput.value = defaultTimeConfig['long-break'];

        updateModeButtonTexts();

        if (isRunning) {
            pauseTimer();
        }
        
        // 如果当前是番茄工作法模式，更新时间
        if (!isCustomTimeMode) {
            totalSeconds = timeConfig[currentMode] * 60;
            initialSeconds = totalSeconds;
            updateDisplay();
        }

        alert('已恢复默认番茄工作法时间设置！');
    }

    // 设置时间（通用方法，用于快速按钮和时间输入框）
    function setTime(minutes, seconds = 0) {
        if (isRunning) {
            pauseTimer();
        }
        
        // 验证输入
        minutes = Math.max(0, Math.min(120, parseInt(minutes) || 0));
        seconds = Math.max(0, Math.min(59, parseInt(seconds) || 0));
        
        // 确保总时间至少为 1 秒
        totalSeconds = minutes * 60 + seconds;
        if (totalSeconds <= 0) {
            totalSeconds = 1;
            seconds = 1;
        }
        initialSeconds = totalSeconds;
        
        // 更新输入框
        customMinutesInput.value = minutes;
        customSecondsInput.value = seconds;
        
        // 标记为自定义时间模式
        isCustomTimeMode = true;
        currentMode = 'custom';
        
        // 更新模式按钮样式
        modeBtns.forEach(btn => {
            btn.classList.remove('mode-active');
        });
        
        updateDisplay();
        updateModeLabel();
    }

    // 切换番茄工作法模式
    function switchMode(mode) {
        if (isRunning) {
            pauseTimer();
        }
        
        currentMode = mode;
        isCustomTimeMode = false;
        totalSeconds = timeConfig[currentMode] * 60;
        initialSeconds = totalSeconds;
        
        // 更新时间输入框
        customMinutesInput.value = timeConfig[currentMode];
        customSecondsInput.value = 0;
        
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
        
        // 如果总秒数为0，先从输入框获取时间
        if (totalSeconds <= 0) {
            const minutes = parseInt(customMinutesInput.value) || 0;
            const seconds = parseInt(customSecondsInput.value) || 0;
            totalSeconds = minutes * 60 + seconds;
            // 确保总时间至少为 1 秒
            if (totalSeconds <= 0) {
                totalSeconds = 1;
            }
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
        const minutes = parseInt(customMinutesInput.value);
        const seconds = parseInt(customSecondsInput.value) || 0;
        // 如果分钟是 NaN（空值或无效值），使用默认值 25，否则使用输入值（允许 0）
        totalSeconds = (isNaN(minutes) ? 25 : minutes) * 60 + seconds;
        // 确保总时间至少为 1 秒
        if (totalSeconds <= 0) {
            totalSeconds = 1;
        }
        initialSeconds = totalSeconds;
        
        updateDisplay();
    }

    // 计时器完成
    function timerComplete() {
        pauseTimer();
        
        // 播放提示音（如果浏览器支持）
        playNotificationSound();
        
        // 更新统计
        if (currentMode === 'work' || currentMode === 'custom') {
            pomodoroCount++;
            totalWorkMinutes += Math.ceil(initialSeconds / 60);
            updateStats();
        }
        
        // 显示完成消息
        let message = '时间到！';
        if (currentMode === 'work') {
            message += ' 工作时间结束，休息一下吧！';
        } else if (currentMode === 'short-break' || currentMode === 'long-break') {
            message += ' 休息时间结束，准备开始下一个番茄钟！';
        } else {
            message += ' 倒计时结束！';
        }
        alert(message);
        
        // 自动切换到下一个模式（仅番茄工作法模式）
        if (!isCustomTimeMode) {
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
    
    // 番茄工作法模式按钮点击事件
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            switchMode(btn.dataset.mode);
        });
    });
    
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
    
    // 自定义番茄工作法时间按钮事件
    if (applyCustomTimeBtn) {
        applyCustomTimeBtn.addEventListener('click', applyCustomPomadoroTime);
    }
    if (resetDefaultTimeBtn) {
        resetDefaultTimeBtn.addEventListener('click', resetDefaultPomadoroTime);
    }

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