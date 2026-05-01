class SandboxApp {
    constructor() {
        this.currentSessionId = null;
        this.currentSession = null;
        this.sessions = [];
        this.apiBase = '';
        this._modalConfirmHandler = null;
        this._creatingSessionId = null;
        this._isCreatingSession = false;
        this._installingPackage = false;
        this._statsRefreshInterval = null;
        
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
        this.pauseSessionBtn = document.getElementById('pauseSessionBtn');
        this.resumeSessionBtn = document.getElementById('resumeSessionBtn');
        this.restartSessionBtn = document.getElementById('restartSessionBtn');
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

        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');

        this.imageTagInput = document.getElementById('imageTagInput');

        this.refreshStatsBtn = document.getElementById('refreshStatsBtn');
        this.containerDetailsEl = document.getElementById('containerDetails');
        this.containerStatsEl = document.getElementById('containerStats');
        this.containerConfigEl = document.getElementById('containerConfig');

        this.packageNameInput = document.getElementById('packageNameInput');
        this.packageVersionInput = document.getElementById('packageVersionInput');
        this.installPackageBtn = document.getElementById('installPackageBtn');
        this.refreshPackagesBtn = document.getElementById('refreshPackagesBtn');
        this.packagesListEl = document.getElementById('packagesList');

        this.logsTimestampsEl = document.getElementById('logsTimestamps');
        this.logsTailEl = document.getElementById('logsTail');
        this.refreshLogsBtn = document.getElementById('refreshLogsBtn');
        this.logsContentEl = document.getElementById('logsContent');
    }

    initEventListeners() {
        this.newSessionBtn.addEventListener('click', () => this.showCreateSessionModal());
        this.clearAllBtn.addEventListener('click', () => this.confirmClearAll());
        this.runBtn.addEventListener('click', () => this.runCode());
        this.pauseSessionBtn.addEventListener('click', () => this.confirmPauseSession());
        this.resumeSessionBtn.addEventListener('click', () => this.resumeSession());
        this.restartSessionBtn.addEventListener('click', () => this.confirmRestartSession());
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

        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });

        if (this.refreshStatsBtn) {
            this.refreshStatsBtn.addEventListener('click', () => this.loadStats());
        }

        if (this.installPackageBtn) {
            this.installPackageBtn.addEventListener('click', () => this.installPackage());
        }
        if (this.refreshPackagesBtn) {
            this.refreshPackagesBtn.addEventListener('click', () => this.loadPackages(true));
        }

        if (this.refreshLogsBtn) {
            this.refreshLogsBtn.addEventListener('click', () => this.loadLogs());
        }
    }

    switchTab(tabName) {
        this.tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });
        this.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tabName}`);
        });

        if (this.currentSessionId) {
            if (tabName === 'details') {
                this.loadDetails();
                this.loadStats();
            } else if (tabName === 'packages') {
                this.loadPackages(false);
            } else if (tabName === 'logs') {
                this.loadLogs();
            }
        }
    }

    loadDefaultCode() {
        const language = this.languageSelectEl.value;
        if (language === 'python') {
            this.codeEditorEl.value = '# Python 示例代码\nprint("Hello, World!")\n\n# 简单计算\nresult = 1 + 1\nprint(f"1 + 1 = {result}")\n\n# 循环\nfor i in range(5):\n    print(f"迭代 {i}")\n';
        } else if (language === 'javascript') {
            this.codeEditorEl.value = '// JavaScript 示例代码\nconsole.log("Hello, World!");\n\n// 简单计算\nconst result = 1 + 1;\nconsole.log(`1 + 1 = ${result}`);\n\n// 循环\nfor (let i = 0; i < 5; i++) {\n    console.log(`迭代 ${i}`);\n}\n';
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
        let allSessions = [...this.sessions];
        
        if (this._isCreatingSession && this._creatingSessionId) {
            allSessions.unshift({
                id: this._creatingSessionId,
                language: this._creatingLanguage || 'python',
                status: 'creating',
                isCreating: true
            });
        }

        if (allSessions.length === 0) {
            this.sessionListEl.innerHTML = '<div class="empty-message">暂无运行中的会话</div>';
            return;
        }

        const html = allSessions.map(session => {
            const isActive = session.id === this.currentSessionId;
            const isRunning = session.status === 'running';
            const isPaused = session.status === 'paused';
            const isCreating = session.isCreating === true;
            
            let statusClass = 'stopped';
            let statusText = this.formatStatus(session.status);
            let dotClass = 'stopped';
            
            if (isCreating) {
                statusClass = 'creating';
                statusText = '创建中';
                dotClass = 'creating';
            } else if (isPaused) {
                statusClass = 'paused';
                statusText = '已暂停';
                dotClass = 'paused';
            } else if (isRunning) {
                statusClass = 'running';
                statusText = '运行中';
                dotClass = 'running';
            }
            
            return `
                <div class="session-item ${isActive ? 'active' : ''} ${isCreating ? 'creating' : ''}" data-session-id="${session.id}">
                    <div class="session-id">${isCreating ? '新建会话...' : (session.id.substring(0, 12) + '...')}</div>
                    <div class="session-language">${this.formatLanguage(session.language)}</div>
                    <div class="session-status ${statusClass}">
                        <span class="status-dot ${dotClass}"></span>
                        ${isCreating ? '<span class="creating-animation"></span>' : ''}
                        ${statusText}
                    </div>
                </div>
            `;
        }).join('');

        this.sessionListEl.innerHTML = html;

        this.sessionListEl.querySelectorAll('.session-item:not(.creating)').forEach(item => {
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
            'stopped': '已停止',
            'paused': '已暂停'
        };
        return statusMap[status] || status;
    }

    showCreateSessionModal() {
        if (this._isCreatingSession) {
            this.addOutput('info', '正在创建会话中，请稍候...');
            return;
        }
        
        this.showLanguageSelectModal();
    }

    showLanguageSelectModal() {
        const modalHtml = `
            <div class="language-select-modal">
                <p class="modal-instruction">请选择要运行的代码语言：</p>
                <div class="language-options">
                    <button class="language-option" data-language="python">
                        <div class="language-icon python-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                                <path d="M9 9h6v6H9z"/>
                            </svg>
                        </div>
                        <div class="language-name">Python</div>
                        <div class="language-desc">适用于 Python 代码</div>
                    </button>
                    <button class="language-option" data-language="javascript">
                        <div class="language-icon js-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                                <path d="M9 8h6v2H9z"/>
                                <path d="M9 14h6v2H9z"/>
                            </svg>
                        </div>
                        <div class="language-name">JavaScript</div>
                        <div class="language-desc">适用于 Node.js 代码</div>
                    </button>
                </div>
            </div>
        `;
        
        this.modalTitleEl.textContent = '新建会话 - 选择语言';
        this.modalBodyEl.innerHTML = modalHtml;
        this.modalConfirmBtn.classList.add('hidden');
        this.modalCancelBtn.classList.add('hidden');
        
        if (this._modalConfirmHandler) {
            this.modalConfirmBtn.removeEventListener('click', this._modalConfirmHandler);
            this._modalConfirmHandler = null;
        }
        
        this.modalEl.classList.remove('hidden');
        
        const languageOptions = this.modalBodyEl.querySelectorAll('.language-option');
        languageOptions.forEach(option => {
            option.addEventListener('click', () => {
                const language = option.dataset.language;
                this.showImageConfigModal(language);
            });
        });
    }

    showImageConfigModal(language) {
        const languageName = this.formatLanguage(language);
        const defaultTag = language === 'python' ? '3.11' : '20';
        const hintText = language === 'python' 
            ? 'Python: 如 <code>3.11</code>, <code>3.10-alpine</code>, <code>3.9-slim</code>'
            : 'Node.js: 如 <code>20</code>, <code>18-alpine</code>, <code>16-slim</code>';
        
        const quickTags = language === 'python'
            ? ['3.11', '3.10', '3.9', '3.11-alpine']
            : ['20', '18', '16', '20-alpine'];
        
        const modalHtml = `
            <div class="image-config-modal">
                <div class="selected-language-info">
                    <div class="selected-language-icon ${language}-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                            <path d="M9 9h6v6H9z"/>
                        </svg>
                    </div>
                    <div>
                        <div class="selected-language-name">${languageName}</div>
                        <div class="selected-language-desc">配置 ${languageName} 镜像参数</div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="modalImageTagInput">镜像 Tag (可选):</label>
                    <div class="quick-tags">
                        ${quickTags.map(tag => `
                            <button type="button" class="quick-tag-btn" data-tag="${tag}">${tag}</button>
                        `).join('')}
                    </div>
                    <input type="text" id="modalImageTagInput" class="form-input" placeholder="例如: ${defaultTag}">
                    <p class="form-hint">
                        ${hintText}<br>
                        留空则使用默认镜像
                    </p>
                </div>
                
                <div class="form-note">
                    <p><strong>提示：</strong></p>
                    <ul>
                        <li>首次创建时可能需要拉取镜像，请耐心等待</li>
                        <li>使用 <code>-alpine</code> 后缀的镜像通常体积更小</li>
                    </ul>
                </div>
            </div>
        `;
        
        this.modalTitleEl.textContent = '新建会话 - 配置镜像';
        this.modalBodyEl.innerHTML = modalHtml;
        this.modalConfirmBtn.classList.remove('hidden');
        this.modalCancelBtn.classList.remove('hidden');
        this.modalConfirmBtn.textContent = '创建会话';
        
        if (this._modalConfirmHandler) {
            this.modalConfirmBtn.removeEventListener('click', this._modalConfirmHandler);
        }
        
        this._modalConfirmHandler = async () => {
            const imageTagInput = document.getElementById('modalImageTagInput');
            const imageTag = imageTagInput.value.trim() || null;
            
            this.closeModal();
            await this.createSession(language, imageTag);
        };
        
        this.modalConfirmBtn.addEventListener('click', this._modalConfirmHandler);
        
        const quickTagBtns = this.modalBodyEl.querySelectorAll('.quick-tag-btn');
        const imageTagInput = this.modalBodyEl.querySelector('#modalImageTagInput');
        
        quickTagBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                quickTagBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                imageTagInput.value = btn.dataset.tag;
            });
        });
        
        setTimeout(() => {
            if (imageTagInput) {
                imageTagInput.focus();
            }
        }, 100);
    }

    async createSession(language, imageTag = null) {
        if (this._isCreatingSession) {
            this.addOutput('info', '正在创建会话中，请稍候...');
            return;
        }
        
        this._isCreatingSession = true;
        this._creatingSessionId = 'creating-' + Date.now();
        this._creatingLanguage = language;
        
        this.newSessionBtn.disabled = true;
        
        let createMessage = `正在创建 ${this.formatLanguage(language)} 会话...`;
        if (imageTag) {
            createMessage = `正在创建 ${this.formatLanguage(language)} 会话 (Tag: ${imageTag})...`;
        }
        this.addOutput('info', createMessage);
        
        this.renderSessionList();
        
        try {
            const body = { language };
            if (imageTag) {
                body.image_tag = imageTag;
            }
            
            const response = await fetch(`${this.apiBase}/api/sessions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(body)
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
        } finally {
            this._isCreatingSession = false;
            this._creatingSessionId = null;
            this._creatingLanguage = null;
            this.newSessionBtn.disabled = false;
            this.renderSessionList();
        }
    }

    selectSession(sessionId) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (!session) {
            return;
        }

        this.currentSessionId = sessionId;
        this.currentSession = session;
        this.currentSessionEl.innerHTML = `<span class="session-id">${sessionId.substring(0, 12)}...</span>`;
        
        this.languageSelectEl.value = session.language;
        
        const isRunning = session.status === 'running';
        const isPaused = session.status === 'paused';
        
        this.runBtn.disabled = !isRunning;
        this.pauseSessionBtn.disabled = !isRunning;
        this.resumeSessionBtn.disabled = !isPaused;
        this.restartSessionBtn.disabled = session.status === 'stopped';
        this.stopSessionBtn.disabled = session.status === 'stopped';

        this.tabBtns.forEach(btn => {
            const tab = btn.dataset.tab;
            if (tab === 'code') {
                btn.disabled = false;
            } else if (tab === 'packages') {
                btn.disabled = session.language !== 'python';
            } else {
                btn.disabled = false;
            }
        });
        
        this.renderSessionList();
        
        if (isRunning) {
            this.addOutput('info', `已选择会话: ${sessionId.substring(0, 12)}... (${this.formatLanguage(session.language)})`);
        } else if (isPaused) {
            this.addOutput('info', `已选择已暂停的会话: ${sessionId.substring(0, 12)}...`);
        } else {
            this.addOutput('info', `已选择的会话已停止运行: ${sessionId.substring(0, 12)}...`);
        }

        const activeTab = document.querySelector('.tab-btn.active');
        if (activeTab) {
            this.switchTab(activeTab.dataset.tab);
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

    confirmPauseSession() {
        if (!this.currentSessionId) {
            return;
        }

        this.showModal(
            '暂停会话',
            `<p>确定要暂停当前会话吗？</p><p>会话ID: ${this.currentSessionId.substring(0, 12)}...</p>`,
            () => this.pauseSession()
        );
    }

    async pauseSession() {
        if (!this.currentSessionId) {
            return;
        }

        this.addOutput('info', `正在暂停会话: ${this.currentSessionId.substring(0, 12)}...`);

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}/pause`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '暂停会话失败');
            }

            this.addOutput('success', '会话已暂停');
            
            await this.loadSessions();
            this.selectSession(this.currentSessionId);

        } catch (error) {
            this.addOutput('error', `暂停会话失败: ${error.message}`);
        }
    }

    async resumeSession() {
        if (!this.currentSessionId) {
            return;
        }

        this.addOutput('info', `正在恢复会话: ${this.currentSessionId.substring(0, 12)}...`);

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}/resume`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '恢复会话失败');
            }

            this.addOutput('success', '会话已恢复');
            
            await this.loadSessions();
            this.selectSession(this.currentSessionId);

        } catch (error) {
            this.addOutput('error', `恢复会话失败: ${error.message}`);
        }
    }

    confirmRestartSession() {
        if (!this.currentSessionId) {
            return;
        }

        this.showModal(
            '重启会话',
            `<p>确定要重启当前会话吗？</p><p>会话ID: ${this.currentSessionId.substring(0, 12)}...</p>`,
            () => this.restartSession()
        );
    }

    async restartSession() {
        if (!this.currentSessionId) {
            return;
        }

        this.addOutput('info', `正在重启会话: ${this.currentSessionId.substring(0, 12)}...`);

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}/restart`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || '重启会话失败');
            }

            this.addOutput('success', '会话已重启');
            
            await this.loadSessions();
            this.selectSession(this.currentSessionId);

        } catch (error) {
            this.addOutput('error', `重启会话失败: ${error.message}`);
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
            this.currentSession = null;
            this.currentSessionEl.textContent = '未选择会话';
            this.runBtn.disabled = true;
            this.pauseSessionBtn.disabled = true;
            this.resumeSessionBtn.disabled = true;
            this.restartSessionBtn.disabled = true;
            this.stopSessionBtn.disabled = true;

            this.tabBtns.forEach(btn => {
                btn.disabled = btn.dataset.tab !== 'code';
            });
            
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
            this.currentSession = null;
            this.currentSessionEl.textContent = '未选择会话';
            this.runBtn.disabled = true;
            this.pauseSessionBtn.disabled = true;
            this.resumeSessionBtn.disabled = true;
            this.restartSessionBtn.disabled = true;
            this.stopSessionBtn.disabled = true;
            
            setTimeout(() => this.loadSessions(), 1000);

        } catch (error) {
            this.addOutput('error', `清空容器失败: ${error.message}`);
        }
    }

    async loadDetails() {
        if (!this.currentSessionId) return;

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}/details`);
            if (!response.ok) {
                throw new Error('获取容器详情失败');
            }
            const data = await response.json();

            const details = {
                '会话 ID:': data.session_id ? data.session_id.substring(0, 20) + '...' : '-',
                '容器 ID:': data.container_id ? data.container_id.substring(0, 20) + '...' : '-',
                '容器名称:': data.container_name || '-',
                '镜像:': data.image || '-',
                '状态:': data.status || '-',
                '创建时间:': data.created_at ? new Date(data.created_at).toLocaleString('zh-CN') : '-',
                '语言:': this.formatLanguage(data.language)
            };

            let html = '';
            for (const [label, value] of Object.entries(details)) {
                html += `
                    <div class="detail-item">
                        <span class="detail-label">${label}</span>
                        <span class="detail-value">${this.escapeHtml(value)}</span>
                    </div>
                `;
            }
            this.containerDetailsEl.innerHTML = html;

            const config = {
                '内存限制:': this.formatBytes(data.config?.memory || 0),
                'CPU 限制:': data.config?.cpus || '-',
                '网络模式:': data.config?.network_mode || '-'
            };

            let configHtml = '';
            for (const [label, value] of Object.entries(config)) {
                configHtml += `
                    <div class="config-item">
                        <span class="config-label">${label}</span>
                        <span class="config-value">${this.escapeHtml(value.toString())}</span>
                    </div>
                `;
            }
            this.containerConfigEl.innerHTML = configHtml;

        } catch (error) {
            this.addOutput('error', `加载容器详情失败: ${error.message}`);
        }
    }

    async loadStats() {
        if (!this.currentSessionId) return;

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}/stats`);
            if (!response.ok) {
                throw new Error('获取容器统计失败');
            }
            const data = await response.json();

            const cpuPercent = data.cpu_usage || 0;
            const memPercent = data.memory_percentage || 0;

            const cpuBar = this.containerStatsEl.querySelector('.stat-item:first-child .stat-bar-fill');
            if (cpuBar) {
                cpuBar.style.width = `${Math.min(cpuPercent, 100)}%`;
            }
            const cpuValue = this.containerStatsEl.querySelector('.stat-item:first-child .stat-value');
            if (cpuValue) {
                cpuValue.textContent = `${cpuPercent.toFixed(2)}%`;
            }

            const memBar = this.containerStatsEl.querySelector('.stat-item:nth-child(2) .stat-bar-fill');
            if (memBar) {
                memBar.style.width = `${Math.min(memPercent, 100)}%`;
            }
            const memValue = this.containerStatsEl.querySelector('.stat-item:nth-child(2) .stat-value');
            if (memValue) {
                memValue.textContent = `${this.formatBytes(data.memory_usage || 0)} / ${this.formatBytes(data.memory_limit || 0)}`;
            }

            const netValue = this.containerStatsEl.querySelector('.stat-item:nth-child(3) .stat-value');
            if (netValue) {
                netValue.textContent = `${this.formatBytes(data.network_rx || 0)} / ${this.formatBytes(data.network_tx || 0)}`;
            }

            const blockValue = this.containerStatsEl.querySelector('.stat-item:nth-child(4) .stat-value');
            if (blockValue) {
                blockValue.textContent = `${this.formatBytes(data.block_read || 0)} / ${this.formatBytes(data.block_write || 0)}`;
            }

            const pidsValue = this.containerStatsEl.querySelector('.stat-item:nth-child(5) .stat-value');
            if (pidsValue) {
                pidsValue.textContent = data.pids || 0;
            }

        } catch (error) {
            this.addOutput('error', `加载资源统计失败: ${error.message}`);
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async loadPackages(refresh = false) {
        if (!this.currentSessionId) return;

        if (this.currentSession && this.currentSession.language !== 'python') {
            this.packagesListEl.innerHTML = '<div class="empty-message">包管理仅支持 Python 会话</div>';
            return;
        }

        this.packagesListEl.innerHTML = '<div class="empty-message">加载中...</div>';

        try {
            const url = refresh 
                ? `${this.apiBase}/api/sessions/${this.currentSessionId}/packages?refresh=true`
                : `${this.apiBase}/api/sessions/${this.currentSessionId}/packages`;
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('获取包列表失败');
            }
            const data = await response.json();

            if (!data.packages || data.packages.length === 0) {
                this.packagesListEl.innerHTML = '<div class="empty-message">暂无已安装的包</div>';
                return;
            }

            const html = data.packages.map(pkg => `
                <div class="package-item">
                    <div class="package-info">
                        <span class="package-name">${this.escapeHtml(pkg.name)}</span>
                        <span class="package-version">${this.escapeHtml(pkg.version)}</span>
                    </div>
                    <button class="btn btn-danger btn-small uninstall-btn" data-package="${this.escapeHtml(pkg.name)}">卸载</button>
                </div>
            `).join('');

            this.packagesListEl.innerHTML = html;

            this.packagesListEl.querySelectorAll('.uninstall-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const packageName = btn.dataset.package;
                    this.confirmUninstallPackage(packageName);
                });
            });

        } catch (error) {
            this.packagesListEl.innerHTML = `<div class="empty-message">加载失败: ${this.escapeHtml(error.message)}</div>`;
            this.addOutput('error', `加载包列表失败: ${error.message}`);
        }
    }

    async installPackage() {
        if (!this.currentSessionId) {
            this.addOutput('error', '请先选择一个 Python 会话');
            return;
        }

        const packageName = this.packageNameInput.value.trim();
        const version = this.packageVersionInput.value.trim();

        if (!packageName) {
            this.addOutput('error', '请输入包名');
            return;
        }

        if (this._installingPackage) {
            this.addOutput('info', '正在安装包，请稍候...');
            return;
        }

        this._installingPackage = true;
        this.installPackageBtn.disabled = true;
        
        const displayName = version ? `${packageName}==${version}` : packageName;
        this.addOutput('info', `正在安装包: ${displayName}...`);

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}/packages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    package_name: packageName,
                    version: version || null
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || '安装包失败');
            }

            this.addOutput('success', `包安装成功: ${data.package_name} ${data.version}`);
            this.packageNameInput.value = '';
            this.packageVersionInput.value = '';
            this.loadPackages(true);

        } catch (error) {
            this.addOutput('error', `安装包失败: ${error.message}`);
        } finally {
            this._installingPackage = false;
            this.installPackageBtn.disabled = false;
        }
    }

    confirmUninstallPackage(packageName) {
        this.showModal(
            '卸载包',
            `<p>确定要卸载包 "${this.escapeHtml(packageName)}" 吗？</p>`,
            () => this.uninstallPackage(packageName)
        );
    }

    async uninstallPackage(packageName) {
        if (!this.currentSessionId) return;

        this.addOutput('info', `正在卸载包: ${packageName}...`);

        try {
            const response = await fetch(`${this.apiBase}/api/sessions/${this.currentSessionId}/packages/${packageName}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || '卸载包失败');
            }

            this.addOutput('success', `包卸载成功: ${packageName}`);
            this.loadPackages(true);

        } catch (error) {
            this.addOutput('error', `卸载包失败: ${error.message}`);
        }
    }

    async loadLogs() {
        if (!this.currentSessionId) return;

        const tail = this.logsTailEl.value;
        const timestamps = this.logsTimestampsEl.checked;

        this.logsContentEl.innerHTML = '<div class="empty-message">加载中...</div>';

        try {
            const url = `${this.apiBase}/api/sessions/${this.currentSessionId}/logs?tail=${tail}&timestamps=${timestamps}`;
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('获取日志失败');
            }
            const data = await response.json();

            if (!data.logs || data.logs.trim() === '') {
                this.logsContentEl.innerHTML = '<div class="empty-message">暂无日志</div>';
                return;
            }

            this.logsContentEl.innerHTML = `<pre class="logs-text">${this.escapeHtml(data.logs)}</pre>`;
            this.logsContentEl.scrollTop = this.logsContentEl.scrollHeight;

        } catch (error) {
            this.logsContentEl.innerHTML = `<div class="empty-message">加载失败: ${this.escapeHtml(error.message)}</div>`;
            this.addOutput('error', `加载日志失败: ${error.message}`);
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
        
        if (this._modalConfirmHandler) {
            this.modalConfirmBtn.removeEventListener('click', this._modalConfirmHandler);
        }
        
        this._modalConfirmHandler = () => {
            this.closeModal();
            if (onConfirm) {
                onConfirm();
            }
        };
        
        this.modalConfirmBtn.addEventListener('click', this._modalConfirmHandler);
        this.modalEl.classList.remove('hidden');
    }

    closeModal() {
        this.modalEl.classList.add('hidden');
        if (this._modalConfirmHandler) {
            this.modalConfirmBtn.removeEventListener('click', this._modalConfirmHandler);
            this._modalConfirmHandler = null;
        }
    }
}

function initSandboxApp() {
    window.sandboxApp = new SandboxApp();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSandboxApp);
} else {
    initSandboxApp();
}
