class ChineseChessGame {
    constructor() {
        this.gameState = null;
        this.selectedPiece = null;
        this.validMoves = [];
        this.isAIThinking = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.renderGridLines();
        this.loadGameState();
        this.setupResizeListener();
    }

    getCellSize() {
        const root = document.documentElement;
        const cellSizeValue = getComputedStyle(root).getPropertyValue('--cell-size');
        return parseFloat(cellSizeValue) || 50;
    }

    renderGridLines() {
        const gridLines = document.getElementById('gridLines');
        if (!gridLines) return;

        gridLines.innerHTML = '';
        const cellSize = this.getCellSize();

        for (let row = 0; row < 10; row++) {
            const line = document.createElement('div');
            line.className = 'grid-line-h';
            line.style.top = (row * cellSize) + 'px';
            gridLines.appendChild(line);
        }

        for (let col = 0; col < 9; col++) {
            const x = col * cellSize;

            if (col === 0 || col === 8) {
                const line = document.createElement('div');
                line.className = 'grid-line-v';
                line.style.left = x + 'px';
                gridLines.appendChild(line);
            } else {
                const topLine = document.createElement('div');
                topLine.className = 'grid-line-v-top';
                topLine.style.left = x + 'px';
                topLine.style.top = '0px';
                gridLines.appendChild(topLine);

                const bottomLine = document.createElement('div');
                bottomLine.className = 'grid-line-v-bottom';
                bottomLine.style.left = x + 'px';
                bottomLine.style.top = (5 * cellSize) + 'px';
                gridLines.appendChild(bottomLine);
            }
        }

        const topPalace = { row: 0, col: 3 };
        const bottomPalace = { row: 7, col: 3 };

        [topPalace, bottomPalace].forEach(palace => {
            const y = palace.row * cellSize;
            const x = palace.col * cellSize;

            const diag1 = document.createElement('div');
            diag1.className = 'palace-diag palace-diag-1';
            diag1.style.left = x + 'px';
            diag1.style.top = y + 'px';
            gridLines.appendChild(diag1);

            const diag2 = document.createElement('div');
            diag2.className = 'palace-diag palace-diag-2';
            diag2.style.left = (x + 2 * cellSize) + 'px';
            diag2.style.top = y + 'px';
            gridLines.appendChild(diag2);
        });
    }

    setupEventListeners() {
        const newGameBtn = document.getElementById('newGameBtn');
        if (newGameBtn) {
            newGameBtn.addEventListener('click', () => this.showNewGameModal());
        }

        const shareBtn = document.getElementById('shareBtn');
        if (shareBtn) {
            shareBtn.addEventListener('click', () => this.shareGame());
        }

        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadGameState());
        }

        const modalClose = document.querySelectorAll('.modal-close');
        modalClose.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').classList.remove('show');
            });
        });

        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('show');
                }
            });
        });

        this.setupColorButtons();
        this.setupDifficultyButtons();

        const startBtn = document.getElementById('startGameBtn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startNewGame());
        }

        const copyBtn = document.getElementById('copyShareBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyShareLink());
        }
    }

    setupColorButtons() {
        const colorBtns = document.querySelectorAll('.color-btn');
        colorBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                colorBtns.forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
            });
        });
    }

    setupDifficultyButtons() {
        const diffBtns = document.querySelectorAll('.difficulty-btn');
        diffBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                diffBtns.forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
            });
        });
    }

    setupResizeListener() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.renderGridLines();
                if (this.gameState) {
                    this.renderBoard();
                }
            }, 100);
        });
    }

    showNewGameModal() {
        const modal = document.getElementById('newGameModal');
        if (modal) {
            modal.classList.add('show');
        }
    }

    async startNewGame() {
        const selectedColor = document.querySelector('.color-btn.selected');
        const selectedDiff = document.querySelector('.difficulty-btn.selected');

        const playerColor = selectedColor ? selectedColor.dataset.color : 'red';
        const difficulty = selectedDiff ? selectedDiff.dataset.difficulty : 'medium';

        try {
            const response = await fetch('/api/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ player_color: playerColor, difficulty })
            });

            const data = await response.json();
            this.gameState = data;
            this.renderBoard();
            this.updateGameInfo();

            const modal = document.getElementById('newGameModal');
            if (modal) modal.classList.remove('show');
        } catch (error) {
            console.error('Failed to start game:', error);
        }
    }

    async loadGameState() {
        try {
            const response = await fetch('/api/state');
            const data = await response.json();

            if (data.status !== 'waiting') {
                this.gameState = data;
                this.renderBoard();
                this.updateGameInfo();
            } else {
                this.showNewGameModal();
            }
        } catch (error) {
            console.error('Failed to load game state:', error);
            this.showNewGameModal();
        }
    }

    renderBoard() {
        const piecesLayer = document.querySelector('.pieces-layer');
        if (!piecesLayer || !this.gameState) return;

        piecesLayer.innerHTML = '';

        const board = this.gameState.board;
        const cellSize = this.getCellSize();

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
                    cell.dataset.row = row;
                    cell.dataset.col = col;

                    const pieceEl = document.createElement('div');
                    pieceEl.className = `piece ${piece.color}`;
                    pieceEl.textContent = piece.name;

                    if (this.gameState.selected_piece &&
                        this.gameState.selected_piece[0] === row &&
                        this.gameState.selected_piece[1] === col) {
                        pieceEl.classList.add('selected');
                    }

                    cell.appendChild(pieceEl);
                    cell.addEventListener('click', () => this.handleCellClick(row, col));
                    piecesLayer.appendChild(cell);
                }
            }
        }

        this.renderValidMoves();
        this.renderLastMove();
    }

    renderValidMoves() {
        const piecesLayer = document.querySelector('.pieces-layer');
        if (!piecesLayer || !this.gameState) return;

        const validMoves = this.gameState.valid_moves || [];
        const cellSize = this.getCellSize();

        validMoves.forEach(([row, col]) => {
            const x = col * cellSize;
            const y = row * cellSize;

            const targetPiece = this.gameState.board[row][col];

            const clickArea = document.createElement('div');
            clickArea.className = 'clickable-area';
            clickArea.style.left = x + 'px';
            clickArea.style.top = y + 'px';
            clickArea.addEventListener('click', () => this.handleCellClick(row, col));
            piecesLayer.appendChild(clickArea);

            const moveEl = document.createElement('div');
            if (targetPiece) {
                moveEl.className = 'valid-capture';
            } else {
                moveEl.className = 'valid-move';
            }
            moveEl.style.left = x + 'px';
            moveEl.style.top = y + 'px';
            piecesLayer.appendChild(moveEl);
        });
    }

    renderLastMove() {
        const piecesLayer = document.querySelector('.pieces-layer');
        if (!piecesLayer || !this.gameState) return;

        const lastMove = this.gameState.last_move;
        if (!lastMove) return;

        const cellSize = this.getCellSize();
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

    async handleCellClick(row, col) {
        if (this.isAIThinking) return;
        if (!this.gameState) return;

        const status = this.gameState.status;
        if (status !== 'playing' && status !== 'check') {
            return;
        }

        if (this.gameState.current_player !== this.gameState.player_color) {
            return;
        }

        const clickedPiece = this.gameState.board[row][col];
        const validMoves = this.gameState.valid_moves || [];
        const isInValidMoves = validMoves.some(m => m[0] === row && m[1] === col);

        if (clickedPiece && clickedPiece.color === this.gameState.player_color) {
            await this.selectPiece(row, col);
        } else if (isInValidMoves && this.gameState.selected_piece) {
            const [fromRow, fromCol] = this.gameState.selected_piece;
            await this.makeMove(fromRow, fromCol, row, col);
        }
    }

    async selectPiece(row, col) {
        try {
            const response = await fetch('/api/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ row, col })
            });

            const data = await response.json();
            if (data.success) {
                this.gameState = data.state;
                this.renderBoard();
                this.updateGameInfo();
            }
        } catch (error) {
            console.error('Failed to select piece:', error);
        }
    }

    async makeMove(fromRow, fromCol, toRow, toCol) {
        try {
            const response = await fetch('/api/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ from_row: fromRow, from_col: fromCol, to_row: toRow, to_col: toCol })
            });

            const data = await response.json();
            if (data.success) {
                this.gameState = data.state;
                this.renderBoard();
                this.updateGameInfo();

                this.checkGameEnd();
            }
        } catch (error) {
            console.error('Failed to make move:', error);
        }
    }

    updateGameInfo() {
        if (!this.gameState) return;

        const turnIndicator = document.querySelector('.turn-dot');
        if (turnIndicator) {
            turnIndicator.className = `turn-dot ${this.gameState.current_player}`;
        }

        const turnText = document.getElementById('turnText');
        if (turnText) {
            turnText.textContent = this.gameState.current_player === 'red' ? '红方回合' : '黑方回合';
        }

        const statusText = document.getElementById('statusText');
        if (statusText) {
            const statusMap = {
                'waiting': '等待开始',
                'playing': '游戏进行中',
                'check': '将军！',
                'checkmate': '将死！',
                'stalemate': '困毙！',
                'finished': '游戏结束'
            };
            statusText.textContent = statusMap[this.gameState.status] || this.gameState.status;
            statusText.className = 'status-text';
            if (this.gameState.status === 'check') {
                statusText.classList.add('check');
            }
        }

        const difficultyText = document.getElementById('difficultyText');
        if (difficultyText) {
            const diffMap = { 'easy': '简单', 'medium': '中等', 'hard': '困难' };
            difficultyText.textContent = `难度: ${diffMap[this.gameState.difficulty] || this.gameState.difficulty}`;
        }

        this.updateMoveHistory();
    }

    updateMoveHistory() {
        const moveList = document.getElementById('moveList');
        if (!moveList || !this.gameState) return;

        moveList.innerHTML = '';
        const notations = this.gameState.move_notations || [];

        notations.forEach((notation, index) => {
            const li = document.createElement('li');
            li.className = 'move-item';

            const moveNum = document.createElement('span');
            moveNum.className = 'move-number';
            moveNum.textContent = `${index + 1}.`;

            const moveNotation = document.createElement('span');
            moveNotation.className = 'move-notation';
            moveNotation.textContent = notation;

            li.appendChild(moveNum);
            li.appendChild(moveNotation);
            moveList.appendChild(li);
        });

        moveList.scrollTop = moveList.scrollHeight;
    }

    checkGameEnd() {
        if (!this.gameState) return;

        if (this.gameState.status === 'checkmate') {
            setTimeout(() => {
                const winner = this.gameState.winner === 'red' ? '红方' : '黑方';
                alert(`游戏结束！${winner}获胜！`);
            }, 100);
        } else if (this.gameState.status === 'stalemate') {
            setTimeout(() => {
                alert('游戏结束！困毙！');
            }, 100);
        }
    }

    async shareGame() {
        if (!this.gameState || this.gameState.status === 'waiting') {
            alert('请先开始游戏！');
            return;
        }

        try {
            const response = await fetch('/api/share');
            const data = await response.json();

            const shareUrl = document.getElementById('shareUrl');
            const shareCode = document.getElementById('shareCode');

            if (shareUrl) shareUrl.value = data.share_url;
            if (shareCode) shareCode.value = data.share_code;

            const modal = document.getElementById('shareModal');
            if (modal) modal.classList.add('show');
        } catch (error) {
            console.error('Failed to share game:', error);
            alert('分享失败，请重试');
        }
    }

    async copyShareLink() {
        const shareUrl = document.getElementById('shareUrl');
        if (shareUrl) {
            try {
                await navigator.clipboard.writeText(shareUrl.value);
                alert('分享链接已复制到剪贴板！');
            } catch (error) {
                shareUrl.select();
                document.execCommand('copy');
                alert('分享链接已复制到剪贴板！');
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChineseChessGame();
});
