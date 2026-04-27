class SandboxApp {
    constructor() {
        this.currentSessionId = null;
        this.sessions = [];
        this.apiBase = '';
        
        this.initElements();
        this.initEventListeners();
        this.loadSessions();
        this.loadDefaultCode();
    }

    initElements() {
        this.sessionListEl = document.getElementById('sessionList');
        this.currentSessionEl = document.getElementById('currentSession');
        this.languageSelectEl = document.getElementById('languageSelect');
        this.codeEditorEl = document.getElementById('codeEditor');
        this.outputContentEl = document.getElementById('outputContent');
        this.runBtn = document.getElementById('runBtn');
        this.stopSessionBtn = document.getElementById('stopSessionBtn');
        this.newSessionBtn = document.getElementById('newSessionBtn');
        this.clearAllBtn = document.getElementById('clearAllBtn');
        this.clearOutputBtn = document.getElementById('clearOutputBtn');
        this.modalEl = document.getElementById('modal');
        this.modalTitleEl = document.getElementById('modalTitle');
        this.modalBodyEl = document.getElementById('modalBody');
        this.modalCloseBtn = document.getElementById('modalClose');
        this.modalCancelBtn = document.getElementById('modalCancel');
        this.modalConfirmBtn = document.getElementById('modalConfirm');
    }

    initEventListeners() {
        this.newSessionBtn.addEventListener('click', () => this.createSession());
        this.clearAllBtn.addEventListener('click', () => this.confirmClearAll());
        this.runBtn.addEventListener('click', () => this.runCode());
        this.stopSessionBtn.addEventListener('click', () => this.confirmStopSession());
        this.clearOutputBtn.addEventListener('click', () => this.clearOutput());
        
        this.modalCloseBtn.addEventListener('click', () => this.closeModal());
        this.modalCancelBtn.addEventListener('click', () => this.closeModal());
        
        this.codeEditorEl.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = this.codeEditorEl.selectionStart;
                const end = this.codeEditorEl.selectionEnd;
                this.codeEditorEl.value = this.codeEditorEl.value.substring(0, start) + '    ' + this.codeEditorEl.value.substring(end);
                this.codeEditorEl.selectionStart = this.codeEditorEl.selectionEnd = start + 4;
            }
            
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                if (!this.runBtn.disabled) {
                    this.runCode();
                }
            }
        });

        this.languageSelectEl.addEventListener('change', () => this.loadDefaultCode());
    }

    loadDefaultCode() {
        const language = this.languageSelectEl.value;
        if (language === 'python') {
            this.codeEditorEl.value = `# Python 示例代码
print("Hello, World!")

# 简单计算
result = 1 + 1
print(f"1 + 1 = {result}")

# 循环
for i in range(5):
    print(f"迭代 {i}")
`;
        } else if (language === 'javascript') {
            this.codeEditorEl.value = `// JavaScript 示例代码
console.log("Hello, World!");

// 简单计算
const result = 1 + 1;
console.log(`1 + 1 = ${result}`);

// 循环
for (let i = 0; i < 5; i++) {
    console.log(`迭代 ${i}`);
}
`;
        }
    }

    async loadSessions() {
        try {
            const response = await fetch(`${this.apiBase}/api/sessions`);
            const data = await response.json();
            this.sessions = data.sessions || [];
            this.renderSessionList();
        } catch (error) {
            this.addOutput('error', `加载会话失败: ${error.message}`);
        }
    }

    renderSessionList() {
        if (this.sessions.length === 0) {
            this.sessionListEl.innerHTML = '<div class="empty-message">暂无运行中的会话</div>';
            return;
        }

        const html = this.sessions.map(session => {
            const isActive = session.id === this.currentSessionId;
            const isRunning = session.status === 'running';
            return `
                <div class="session-item ${isActive ? 'active' : ''}" data-session-id="${session.id}">
                    <div class="session-id">${session.id.substring(0, 12)}...</div>
                    <div class="session-language">${this.formatLanguage(session.language)}</div>
                    <div class="session-status ${isRunning ? 'running' : 'stopped'}">
                        <span class="status-dot ${isRunning ? 'running' : 'stopped'}"></span>
                        ${this.formatStatus(session.status)}
                    </div>
                </div>
            `;
        }).join('');

        this.sessionListEl.innerHTML = html;

        this.sessionListEl.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', () => {
                const sessionId = item.dataset.sessionId;
                this.selectSession(sessionId);
            });
        });
    }

    formatLanguage(language) {
        const langMap = {
            'python': 'Python',
            'javascript': 'JavaScript'
        };
        return langMap[language] || language;
    }

    formatStatus(status) {
        const statusMap = {
            'running': '运行中',
            'stopped': '已停止'
        };
        return statusMap[status] || status;
    }

    async createSession() {
        const language = this.languageSelectEl.value;
        this.addOutput('info', `正在创建 ${this.formatLanguage(language)} 会话...`);
        
        try {
            const response = await fetch(`${this.apiBase}/api/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ language })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '创建会话失败');
            }

            const data = await response.json();
            this.addOutput('success', `会话创建成功: ${data.session_id}`);
            
            await this.loadSessions();
            this.selectSession(data.session_id);
            
        } catch (error) {
            this.addOutput('error', `创建会话失败: ${error.message}`);
        }
    }

    selectSession(sessionId) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (!session) {
            return;
        }

        this.currentSessionId = sessionId;
        this.currentSessionEl.innerHTML = `<span class="session-id">${sessionId.substring(0, 12)}...</span>`;
        
        this.languageSelectEl.value = session.language;
        
        const isRunning = session.status === 'running';
        this.runBtn.disabled = !isRunning;
        this.stopSessionBtn.disabled = !isRunning;
        
        this.renderSessionList();
        
        if (isRunning) {
            this.addOutput('info', `已选择会话: ${sessionId.substring(0, 12)}... (${this.formatLanguage(session.language)})`);
        } else {
            this.addOutput('info', `已选择的会话已停止运行: ${sessionId.substring(0, 12)}...`);
        }
    }

    async runCode() {
        if (!this.currentSessionId) {
            this.addOutput('error', '请先选择一个会话');
            return;
        }

        const code = this.codeEditorEl.value;
        if (!code.trim()) {
            this.addOutput('error', '代码不能为空');
            return;
        }

        this.runBtn.disabled = true;
        this.addOutput('info', '正在执行代码...');

        try {
            const response = await fetch(`${this.apiBase}/api/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    code: code,
                    session_id: this.currentSessionId
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '执行失败');
            }

            const result = await response.json();
            
            if (result.output) {
                this.addOutput('stdout', result.output);
            }
            if (result.error) {
                this.addOutput('stderr', result.error);
            }
            
            if (result.exit_code === 0) {
                this.addOutput('success', `执行完成 (退出码: ${result.exit_code})`);
            } else {
                this.addOutput('error', `执行完成 (退出码: ${result.exit_code})`);
            }

        } catch (error) {
            this.addOutput('error', `执行失败: ${error.message}`);
        } finally {
            this.runBtn.disabled = false;
        }
    }

    confirmStopSession() {
        if (!this.currentSessionId) {
            return;
        }

        this.showModal(
            '停止会话',
            `<p>确定要停止当前会话吗？</p><p>会话ID: ${this.currentSessionId.substring(0, 12)}...</p>`,
            () => this.stopCurrentSession()
        );
    }

    async stopCurrentSession() {
        if (!this.currentSessionId) {
            return;
        }

        this.addOutput('info', `正在停止会话: ${this.currentSessionId.substring(0, 12)}...`);

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '停止会话失败');
            }

            this.addOutput('success', '会话已停止');
            
            this.currentSessionId = null;
            this.currentSessionEl.textContent = '未选择会话';
            this.runBtn.disabled = true;
            this.stopSessionBtn.disabled = true;
            
            await this.loadSessions();

        } catch (error) {
            this.addOutput('error', `停止会话失败: ${error.message}`);
        }
    }

    confirmClearAll() {
        this.showModal(
            '清空所有容器',
            '<p>确定要清空所有运行中的容器吗？</p><p style="color: #f44747;">此操作将停止并删除所有容器。</p>',
            () => this.clearAllSessions()
        );
    }

    async clearAllSessions() {
        this.addOutput('info', '正在清空所有容器...');

        try {
            const response = await fetch(`${this.apiBase}/api/clear-all`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '清空容器失败');
            }

            this.addOutput('success', '所有容器正在清空...');
            
            this.currentSessionId = null;
            this.currentSessionEl.textContent = '未选择会话';
            this.runBtn.disabled = true;
            this.stopSessionBtn.disabled = true;
            
            setTimeout(() => this.loadSessions(), 1000);

        } catch (error) {
            this.addOutput('error', `清空容器失败: ${error.message}`);
        }
    }

    addOutput(type, text) {
        const item = document.createElement('div');
        item.className = 'output-item';
        
        const labelMap = {
            'info': '[系统]',
            'stdout': '[输出]',
            'stderr': '[错误]',
            'error': '[错误]',
            'success': '[成功]'
        };
        
        item.innerHTML = `
            <span class="output-label ${type}">${labelMap[type] || '[日志]'}</span>
            <span class="output-text">${this.escapeHtml(text)}</span>
        `;
        
        this.outputContentEl.appendChild(item);
        this.outputContentEl.scrollTop = this.outputContentEl.scrollHeight;
    }

    clearOutput() {
        this.outputContentEl.innerHTML = `
            <div class="output-item">
                <span class="output-label info">[系统]</span>
                <span class="output-text">输出已清空。</span>
            </div>
        `;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showModal(title, bodyHtml, onConfirm) {
        this.modalTitleEl.textContent = title;
        this.modalBodyEl.innerHTML = bodyHtml;
        
        const confirmHandler = () => {
            this.closeModal();
            if (onConfirm) {
                onConfirm();
            }
            this.modalConfirmBtn.removeEventListener('click', confirmHandler);
        };
        
        this.modalConfirmBtn.addEventListener('click', confirmHandler);
        this.modalEl.classList.remove('hidden');
    }

    closeModal() {
        this.modalEl.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.sandboxApp = new SandboxApp();
});
