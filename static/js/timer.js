document.addEventListener('DOMContentLoaded', function() {
    const minutesDisplay = document.getElementById('minutes');
    const secondsDisplay = document.getElementById('seconds');
    const timerLabel = document.getElementById('timer-label');
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const modeBtns = document.querySelectorAll('.mode-btn');
    const pomodoroCountDisplay = document.getElementById('pomodoro-count');
    const totalTimeDisplay = document.getElementById('total-time');

    const quickTimeBtns = document.querySelectorAll('.quick-time-btn');
    const customMinutesInput = document.getElementById('custom-minutes');
    const customSecondsInput = document.getElementById('custom-seconds');

    const customWorkTimeInput = document.getElementById('custom-work-time');
    const customShortBreakInput = document.getElementById('custom-short-break');
    const customLongBreakInput = document.getElementById('custom-long-break');
    const applyCustomTimeBtn = document.getElementById('apply-custom-time');
    const resetDefaultTimeBtn = document.getElementById('reset-default-time');

    const cycleConfig = document.getElementById('cycle-config');
    const cycleActive = document.getElementById('cycle-active');
    const cyclePomodorosInput = document.getElementById('cycle-pomodoros');
    const cycleNameInput = document.getElementById('cycle-name');
    const createCycleBtn = document.getElementById('create-cycle-btn');
    const cancelCycleBtn = document.getElementById('cancel-cycle-btn');
    const stopCycleBtn = document.getElementById('stop-cycle-btn');
    const pauseCycleBtn = document.getElementById('pause-cycle-btn');
    const activeCycleName = document.getElementById('active-cycle-name');
    const cycleProgress = document.getElementById('cycle-progress');
    const cycleProgressFill = document.getElementById('cycle-progress-fill');
    const cycleSegments = document.getElementById('cycle-segments');
    const cycleHistory = document.getElementById('cycle-history');
    const cycleHistoryList = document.getElementById('cycle-history-list');

    const defaultTimeConfig = {
        'work': 25,
        'short-break': 5,
        'long-break': 15
    };

    let timeConfig = {
        'work': 25,
        'short-break': 5,
        'long-break': 15
    };

    let currentMode = 'work';
    let totalSeconds = timeConfig[currentMode] * 60;
    let timerInterval = null;
    let isRunning = false;
    let pomodoroCount = 0;
    let totalWorkMinutes = 0;
    let initialSeconds = totalSeconds;
    let isCustomTimeMode = false;

    let activeCycle = null;
    let activeCycleSegments = [];
    let currentSegmentIndex = 0;
    let isCycleMode = false;
    let isCyclePaused = false;

    updateDisplay();
    updateStats();
    updateModeLabel();
    loadCycleHistory();

    function updateDisplay() {
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        
        minutesDisplay.textContent = minutes.toString().padStart(2, '0');
        secondsDisplay.textContent = seconds.toString().padStart(2, '0');
    }

    function updateStats() {
        pomodoroCountDisplay.textContent = pomodoroCount;
        totalTimeDisplay.textContent = `${totalWorkMinutes}分钟`;
    }

    function updateModeLabel() {
        const labels = {
            'work': '工作时间',
            'short-break': '短休息时间',
            'long-break': '长休息时间',
            'custom': '自定义时间'
        };
        timerLabel.textContent = labels[currentMode] || '自定义时间';
    }

    function updateModeButtonTexts() {
        const workModeBtn = document.getElementById('work-mode');
        const shortBreakModeBtn = document.getElementById('short-break-mode');
        const longBreakModeBtn = document.getElementById('long-break-mode');
        
        if (workModeBtn) workModeBtn.textContent = `工作 (${timeConfig['work']}分钟)`;
        if (shortBreakModeBtn) shortBreakModeBtn.textContent = `短休息 (${timeConfig['short-break']}分钟)`;
        if (longBreakModeBtn) longBreakModeBtn.textContent = `长休息 (${timeConfig['long-break']}分钟)`;
    }

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
        
        if (!isCustomTimeMode && !isCycleMode) {
            totalSeconds = timeConfig[currentMode] * 60;
            initialSeconds = totalSeconds;
            updateDisplay();
        }

        alert('自定义番茄工作法时间已应用！');
    }

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
        
        if (!isCustomTimeMode && !isCycleMode) {
            totalSeconds = timeConfig[currentMode] * 60;
            initialSeconds = totalSeconds;
            updateDisplay();
        }

        alert('已恢复默认番茄工作法时间设置！');
    }

    function setTime(minutes, seconds = 0) {
        if (isRunning) {
            pauseTimer();
        }
        
        minutes = Math.max(0, Math.min(120, parseInt(minutes) || 0));
        seconds = Math.max(0, Math.min(59, parseInt(seconds) || 0));
        
        totalSeconds = minutes * 60 + seconds;
        if (totalSeconds <= 0) {
            totalSeconds = 1;
            seconds = 1;
        }
        initialSeconds = totalSeconds;
        
        customMinutesInput.value = minutes;
        customSecondsInput.value = seconds;
        
        isCustomTimeMode = true;
        currentMode = 'custom';
        
        modeBtns.forEach(btn => {
            btn.classList.remove('mode-active');
        });
        
        updateDisplay();
        updateModeLabel();
    }

    function switchMode(mode) {
        if (isCycleMode) return;
        
        if (isRunning) {
            pauseTimer();
        }
        
        currentMode = mode;
        isCustomTimeMode = false;
        totalSeconds = timeConfig[currentMode] * 60;
        initialSeconds = totalSeconds;
        
        customMinutesInput.value = timeConfig[currentMode];
        customSecondsInput.value = 0;
        
        modeBtns.forEach(btn => {
            btn.classList.remove('mode-active');
            if (btn.dataset.mode === mode) {
                btn.classList.add('mode-active');
            }
        });
        
        updateDisplay();
        updateModeLabel();
    }

    function startTimer() {
        if (isRunning) return;
        
        if (totalSeconds <= 0) {
            const minutes = parseInt(customMinutesInput.value) || 0;
            const seconds = parseInt(customSecondsInput.value) || 0;
            totalSeconds = minutes * 60 + seconds;
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

    function pauseTimer() {
        if (!isRunning) return;
        
        isRunning = false;
        clearInterval(timerInterval);
        timerInterval = null;
        
        startBtn.style.display = 'inline-block';
        pauseBtn.style.display = 'none';
    }

    function resetTimer() {
        pauseTimer();
        
        const minutes = parseInt(customMinutesInput.value);
        const seconds = parseInt(customSecondsInput.value) || 0;
        totalSeconds = (isNaN(minutes) ? 25 : minutes) * 60 + seconds;
        if (totalSeconds <= 0) {
            totalSeconds = 1;
        }
        initialSeconds = totalSeconds;
        
        updateDisplay();
    }

    async function saveTimerRecord(segmentId = null) {
        try {
            const body = {
                mode: currentMode,
                duration_seconds: initialSeconds,
                note: `模式: ${currentMode}, 时长: ${Math.ceil(initialSeconds / 60)}分钟`
            };
            
            if (segmentId) {
                body.cycle_segment_id = segmentId;
            }
            
            const response = await fetch('/api/records', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(body),
            });
            
            if (!response.ok) {
                console.error('保存记录失败:', response.statusText);
            } else {
                const result = await response.json();
                console.log('记录已保存:', result);
            }
        } catch (error) {
            console.error('保存记录时出错:', error);
        }
    }

    async function completeCycleSegment(segmentId) {
        if (!activeCycle) return;
        
        try {
            const response = await fetch(`/api/cycles/${activeCycle.id}/segments/${segmentId}/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                console.error('完成阶段失败:', response.statusText);
                return null;
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('完成阶段时出错:', error);
            return null;
        }
    }

    async function timerComplete() {
        pauseTimer();
        
        let currentSegmentId = null;
        if (isCycleMode && activeCycleSegments.length > 0 && currentSegmentIndex < activeCycleSegments.length) {
            currentSegmentId = activeCycleSegments[currentSegmentIndex].id;
        }
        
        await saveTimerRecord(currentSegmentId);
        
        playNotificationSound();
        
        if (currentMode === 'work' || currentMode === 'custom') {
            pomodoroCount++;
            totalWorkMinutes += Math.ceil(initialSeconds / 60);
            updateStats();
        }
        
        if (isCycleMode && activeCycle) {
            await handleCycleSegmentComplete();
        } else {
            let message = '时间到！';
            if (currentMode === 'work') {
                message += ' 工作时间结束，休息一下吧！';
            } else if (currentMode === 'short-break' || currentMode === 'long-break') {
                message += ' 休息时间结束，准备开始下一个番茄钟！';
            } else {
                message += ' 倒计时结束！';
            }
            alert(message);
            
            if (!isCustomTimeMode) {
                if (currentMode === 'work') {
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
    }

    async function handleCycleSegmentComplete() {
        if (!activeCycle || activeCycleSegments.length === 0) return;
        
        const currentSegment = activeCycleSegments[currentSegmentIndex];
        
        await completeCycleSegment(currentSegment.id);
        
        currentSegment.is_completed = true;
        updateCycleSegmentsDisplay();
        
        const workSegmentsCompleted = activeCycleSegments.filter(s => s.segment_type === 'work' && s.is_completed).length;
        const totalWorkSegments = activeCycleSegments.filter(s => s.segment_type === 'work').length;
        
        cycleProgress.textContent = `${workSegmentsCompleted}/${totalWorkSegments}`;
        const progressPercent = (workSegmentsCompleted / totalWorkSegments) * 100;
        cycleProgressFill.style.width = `${progressPercent}%`;
        
        currentSegmentIndex++;
        
        if (currentSegmentIndex >= activeCycleSegments.length) {
            alert(`循环 "${activeCycle.name}" 已完成！共完成 ${workSegmentsCompleted} 个番茄钟。`);
            await endCycle();
            return;
        }
        
        const nextSegment = activeCycleSegments[currentSegmentIndex];
        const nextMode = nextSegment.segment_type;
        
        let message = '时间到！';
        if (currentSegment.segment_type === 'work') {
            message += ' 工作时间结束，开始休息！';
        } else {
            message += ' 休息时间结束，准备开始下一个番茄钟！';
        }
        alert(message);
        
        startNextCycleSegment(nextSegment, nextMode);
    }

    function startNextCycleSegment(segment, mode) {
        currentMode = mode;
        isCustomTimeMode = false;
        totalSeconds = segment.duration_seconds;
        initialSeconds = totalSeconds;
        
        customMinutesInput.value = Math.floor(segment.duration_seconds / 60);
        customSecondsInput.value = segment.duration_seconds % 60;
        
        modeBtns.forEach(btn => {
            btn.classList.remove('mode-active');
            if (btn.dataset.mode === mode) {
                btn.classList.add('mode-active');
            }
        });
        
        updateCycleSegmentsDisplay();
        updateDisplay();
        updateModeLabel();
        
        if (!isCyclePaused) {
            startTimer();
        }
    }

    async function createCycle() {
        const pomodoros = parseInt(cyclePomodorosInput.value);
        const name = cycleNameInput.value.trim() || '工作循环';
        
        if (isNaN(pomodoros) || pomodoros < 1 || pomodoros > 20) {
            alert('番茄钟数量必须是1-20之间的数字');
            return;
        }
        
        try {
            const response = await fetch('/api/cycles', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    total_pomodoros: pomodoros,
                    work_duration_minutes: timeConfig['work'],
                    short_break_duration_minutes: timeConfig['short-break'],
                    long_break_duration_minutes: timeConfig['long-break']
                }),
            });
            
            if (!response.ok) {
                const error = await response.json();
                alert('创建循环失败: ' + (error.detail || '未知错误'));
                return;
            }
            
            activeCycle = await response.json();
            activeCycleSegments = activeCycle.segments || [];
            currentSegmentIndex = 0;
            isCycleMode = true;
            isCyclePaused = false;
            
            showCycleActive();
            updateCycleDisplay();
            
            alert(`循环 "${activeCycle.name}" 已创建！点击开始按钮开始第一个番茄钟。`);
            
        } catch (error) {
            console.error('创建循环时出错:', error);
            alert('创建循环失败，请检查网络连接');
        }
    }

    async function endCycle() {
        if (!activeCycle) return;
        
        try {
            await fetch(`/api/cycles/${activeCycle.id}/status`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    status: 'cancelled'
                }),
            });
        } catch (error) {
            console.error('更新循环状态时出错:', error);
        }
        
        pauseTimer();
        isCycleMode = false;
        isCyclePaused = false;
        activeCycle = null;
        activeCycleSegments = [];
        currentSegmentIndex = 0;
        
        showCycleConfig();
        loadCycleHistory();
        
        switchMode('work');
    }

    function showCycleActive() {
        cycleConfig.style.display = 'none';
        cycleActive.style.display = 'block';
    }

    function showCycleConfig() {
        cycleConfig.style.display = 'block';
        cycleActive.style.display = 'none';
    }

    function updateCycleDisplay() {
        if (!activeCycle) return;
        
        activeCycleName.textContent = activeCycle.name;
        
        const workSegments = activeCycleSegments.filter(s => s.segment_type === 'work');
        const completedWorkSegments = workSegments.filter(s => s.is_completed);
        
        cycleProgress.textContent = `${completedWorkSegments.length}/${workSegments.length}`;
        const progressPercent = workSegments.length > 0 ? (completedWorkSegments.length / workSegments.length) * 100 : 0;
        cycleProgressFill.style.width = `${progressPercent}%`;
        
        updateCycleSegmentsDisplay();
    }

    function updateCycleSegmentsDisplay() {
        if (!activeCycleSegments || activeCycleSegments.length === 0) {
            cycleSegments.innerHTML = '<p class="no-segments">暂无阶段</p>';
            return;
        }
        
        let html = '';
        for (let i = 0; i < activeCycleSegments.length; i++) {
            const segment = activeCycleSegments[i];
            const isCurrent = i === currentSegmentIndex;
            const isPast = i < currentSegmentIndex || (segment.is_completed && !isCurrent);
            
            let segmentClass = 'cycle-segment';
            if (isCurrent) segmentClass += ' cycle-segment-current';
            if (segment.is_completed) segmentClass += ' cycle-segment-completed';
            if (isPast && !segment.is_completed) segmentClass += ' cycle-segment-past';
            
            const typeLabels = {
                'work': '工作',
                'short-break': '短休',
                'long-break': '长休'
            };
            
            const typeIcons = {
                'work': '💼',
                'short-break': '☕',
                'long-break': '🌴'
            };
            
            const minutes = Math.floor(segment.duration_seconds / 60);
            
            html += `
                <div class="${segmentClass}" data-index="${i}">
                    <span class="segment-icon">${typeIcons[segment.segment_type] || '⏱️'}</span>
                    <span class="segment-type">${typeLabels[segment.segment_type] || segment.segment_type}</span>
                    <span class="segment-duration">${minutes}分钟</span>
                    ${segment.is_completed ? '<span class="segment-check">✓</span>' : ''}
                </div>
            `;
        }
        
        cycleSegments.innerHTML = html;
    }

    async function loadCycleHistory() {
        try {
            const response = await fetch('/api/cycles?limit=10');
            
            if (!response.ok) {
                console.error('加载历史循环失败:', response.statusText);
                return;
            }
            
            const cycles = await response.json();
            
            if (cycles.length === 0) {
                cycleHistory.style.display = 'none';
                return;
            }
            
            cycleHistory.style.display = 'block';
            
            let html = '';
            for (const cycle of cycles) {
                if (cycle.status === 'running' || cycle.status === 'pending') continue;
                
                const statusLabels = {
                    'completed': '已完成',
                    'cancelled': '已取消'
                };
                
                const statusColors = {
                    'completed': 'status-completed',
                    'cancelled': 'status-cancelled'
                };
                
                const completedWork = cycle.segments ? 
                    cycle.segments.filter(s => s.segment_type === 'work' && s.is_completed).length : 0;
                
                html += `
                    <div class="history-item">
                        <div class="history-header">
                            <span class="history-name">${cycle.name || '未命名循环'}</span>
                            <span class="history-status ${statusColors[cycle.status] || ''}">${statusLabels[cycle.status] || cycle.status}</span>
                        </div>
                        <div class="history-details">
                            <span>完成: ${completedWork}/${cycle.total_pomodoros} 个番茄钟</span>
                            <span>创建时间: ${new Date(cycle.created_at).toLocaleString('zh-CN')}</span>
                        </div>
                    </div>
                `;
            }
            
            cycleHistoryList.innerHTML = html || '<p class="no-history">暂无历史记录</p>';
            
        } catch (error) {
            console.error('加载历史循环时出错:', error);
        }
    }

    function playNotificationSound() {
        try {
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

    startBtn.addEventListener('click', startTimer);
    pauseBtn.addEventListener('click', pauseTimer);
    resetBtn.addEventListener('click', resetTimer);
    
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (!isCycleMode) {
                switchMode(btn.dataset.mode);
            }
        });
    });
    
    quickTimeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (!isCycleMode) {
                const minutes = parseInt(btn.dataset.minutes);
                setTime(minutes, 0);
            }
        });
    });
    
    customMinutesInput.addEventListener('change', () => {
        if (!isCycleMode) {
            const minutes = parseInt(customMinutesInput.value) || 25;
            const seconds = parseInt(customSecondsInput.value) || 0;
            setTime(minutes, seconds);
        }
    });
    
    customSecondsInput.addEventListener('change', () => {
        if (!isCycleMode) {
            const minutes = parseInt(customMinutesInput.value) || 25;
            const seconds = parseInt(customSecondsInput.value) || 0;
            setTime(minutes, seconds);
        }
    });
    
    if (applyCustomTimeBtn) {
        applyCustomTimeBtn.addEventListener('click', applyCustomPomadoroTime);
    }
    if (resetDefaultTimeBtn) {
        resetDefaultTimeBtn.addEventListener('click', resetDefaultPomadoroTime);
    }

    if (createCycleBtn) {
        createCycleBtn.addEventListener('click', createCycle);
    }
    
    if (stopCycleBtn) {
        stopCycleBtn.addEventListener('click', () => {
            if (confirm('确定要结束当前循环吗？')) {
                endCycle();
            }
        });
    }
    
    if (pauseCycleBtn) {
        pauseCycleBtn.addEventListener('click', () => {
            if (isRunning) {
                pauseTimer();
                isCyclePaused = true;
                pauseCycleBtn.textContent = '继续循环';
            } else if (isCyclePaused) {
                isCyclePaused = false;
                pauseCycleBtn.textContent = '暂停循环';
                if (activeCycle && activeCycleSegments.length > 0) {
                    startTimer();
                }
            }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            e.preventDefault();
            if (isRunning) {
                pauseTimer();
            } else {
                startTimer();
            }
        } else if (e.code === 'KeyR') {
            if (!isCycleMode) {
                resetTimer();
            }
        }
    });
});
