class ReplayPlayer {
    constructor() {
        this.steps = [];
        this.currentStep = 0;
        this.init();
    }

    async init() {
        await this.loadReplayData();
        this.setupEventListeners();
        this.renderCurrentStep();
    }

    async loadReplayData() {
        const shareCode = window.location.pathname.split('/').pop();
        if (!shareCode) return;

        try {
            const response = await fetch(`/api/replay/${shareCode}`);
            const data = await response.json();
            
            if (data.steps) {
                this.steps = data.steps;
            }
        } catch (error) {
            console.error('Failed to load replay:', error);
        }
    }

    setupEventListeners() {
        const playBtn = document.getElementById('playBtn');
        if (playBtn) {
            playBtn.addEventListener('click', () => this.playAll());
        }

        const pauseBtn = document.getElementById('pauseBtn');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.pause());
        }

        const prevBtn = document.getElementById('prevBtn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.prevStep());
        }

        const nextBtn = document.getElementById('nextBtn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextStep());
        }

        const firstBtn = document.getElementById('firstBtn');
        if (firstBtn) {
            firstBtn.addEventListener('click', () => this.goToStep(0));
        }

        const lastBtn = document.getElementById('lastBtn');
        if (lastBtn) {
            lastBtn.addEventListener('click', () => this.goToStep(this.steps.length - 1));
        }

        const continueBtn = document.getElementById('continueBtn');
        if (continueBtn) {
            continueBtn.addEventListener('click', () => this.continueGame());
        }
    }

    renderCurrentStep() {
        if (!this.steps.length) return;

        const step = this.steps[this.currentStep];
        this.renderBoard(step);
        this.updateStepInfo(step);
    }

    renderBoard(step) {
        const piecesLayer = document.querySelector('.pieces-layer');
        if (!piecesLayer) return;

        piecesLayer.innerHTML = '';

        const board = step.board;
        const cellSize = 50;

        for (let row = 0; row < 10; row++) {
            for (let col = 0; col < 9; col++) {
                const piece = board[row][col];
                if (piece) {
                    const x = col * cellSize;
                    const y = row * cellSize;

                    const cell = document.createElement('div');
                    cell.className = 'intersection';
                    cell.style.left = x + 'px';
                    cell.style.top = y + 'px';

                    const pieceEl = document.createElement('div');
                    pieceEl.className = `piece ${piece.color}`;
                    pieceEl.textContent = piece.name;

                    cell.appendChild(pieceEl);
                    piecesLayer.appendChild(cell);
                }
            }
        }

        this.renderLastMove(step.last_move);
    }

    renderLastMove(lastMove) {
        const piecesLayer = document.querySelector('.pieces-layer');
        if (!piecesLayer || !lastMove) return;

        const cellSize = 50;
        const [fromRow, fromCol, toRow, toCol] = lastMove;

        [[fromRow, fromCol], [toRow, toCol]].forEach(([row, col]) => {
            const x = col * cellSize;
            const y = row * cellSize;

            const moveEl = document.createElement('div');
            moveEl.className = 'last-move-highlight';
            moveEl.style.left = x + 'px';
            moveEl.style.top = y + 'px';
            piecesLayer.appendChild(moveEl);
        });
    }

    updateStepInfo(step) {
        const stepText = document.getElementById('stepText');
        if (stepText) {
            stepText.textContent = `${step.name} (${this.currentStep + 1}/${this.steps.length})`;
        }
    }

    nextStep() {
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.renderCurrentStep();
        }
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.renderCurrentStep();
        }
    }

    goToStep(stepIndex) {
        if (stepIndex >= 0 && stepIndex < this.steps.length) {
            this.currentStep = stepIndex;
            this.renderCurrentStep();
        }
    }

    playAll() {
        this.isPlaying = true;
        this.playInterval = setInterval(() => {
            if (this.currentStep < this.steps.length - 1) {
                this.nextStep();
            } else {
                this.pause();
            }
        }, 1000);
    }

    pause() {
        this.isPlaying = false;
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }

    async continueGame() {
        const shareCode = window.location.pathname.split('/').pop();
        if (!shareCode) return;

        try {
            const response = await fetch('/api/continue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ share_code: shareCode })
            });

            if (response.ok) {
                window.location.href = '/game';
            }
        } catch (error) {
            console.error('Failed to continue game:', error);
            alert('继续游戏失败');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ReplayPlayer();
});
