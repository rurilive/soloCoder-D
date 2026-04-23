from typing import Optional, List, Tuple
from enum import Enum
from app.chess.board import Board
from app.chess.pieces import Color, Piece
from app.chess.ai import AI, Difficulty
from app.chess.notation import Notation


class GameStatus(Enum):
    WAITING = 'waiting'
    PLAYING = 'playing'
    CHECK = 'check'
    CHECKMATE = 'checkmate'
    STALEMATE = 'stalemate'
    FINISHED = 'finished'


class Game:
    def __init__(self):
        self.board = Board()
        self.current_player: Color = Color.RED
        self.status: GameStatus = GameStatus.WAITING
        self.player_color: Color = Color.RED
        self.ai_color: Color = Color.BLACK
        self.difficulty: Difficulty = Difficulty.MEDIUM
        self.ai: Optional[AI] = None
        self.move_notations: List[str] = []
        self.selected_piece: Optional[Tuple[int, int]] = None
        self.valid_moves: List[Tuple[int, int]] = []
        self.last_move: Optional[Tuple[int, int, int, int]] = None
        self.winner: Optional[Color] = None

    def start_game(self, player_color: Color = Color.RED, difficulty: Difficulty = Difficulty.MEDIUM):
        self.board = Board()
        self.current_player = Color.RED
        self.status = GameStatus.PLAYING
        self.player_color = player_color
        self.ai_color = Color.BLACK if player_color == Color.RED else Color.RED
        self.difficulty = difficulty
        self.ai = AI(self.ai_color, difficulty)
        self.move_notations = []
        self.selected_piece = None
        self.valid_moves = []
        self.last_move = None
        self.winner = None

        if self.ai_color == Color.RED:
            self._make_ai_move()

    def select_piece(self, row: int, col: int) -> bool:
        if self.status not in [GameStatus.PLAYING, GameStatus.CHECK]:
            return False

        if self.current_player != self.player_color:
            return False

        piece = self.board.get_piece(row, col)
        if piece and piece.color == self.current_player:
            self.selected_piece = (row, col)
            self.valid_moves = list(self.board.get_valid_moves(row, col))
            return True

        return False

    def make_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        if self.status not in [GameStatus.PLAYING, GameStatus.CHECK]:
            return False

        if self.current_player != self.player_color:
            return False

        valid_moves = self.board.get_valid_moves(from_row, from_col)
        if (to_row, to_col) not in valid_moves:
            return False

        notation = Notation.move_to_notation(self.board, from_row, from_col, to_row, to_col)

        self.board.move_piece(from_row, from_col, to_row, to_col)
        self.move_notations.append(notation)
        self.last_move = (from_row, from_col, to_row, to_col)
        self.selected_piece = None
        self.valid_moves = []

        if not self._check_game_end():
            self.current_player = self.ai_color
            self._make_ai_move()

        return True

    def _make_ai_move(self):
        if self.ai is None:
            return

        if self.status not in [GameStatus.PLAYING, GameStatus.CHECK]:
            return

        move = self.ai.get_best_move(self.board)
        if move is None:
            return

        from_row, from_col, to_row, to_col = move
        notation = Notation.move_to_notation(self.board, from_row, from_col, to_row, to_col)

        self.board.move_piece(from_row, from_col, to_row, to_col)
        self.move_notations.append(notation)
        self.last_move = (from_row, from_col, to_row, to_col)

        self._check_game_end()

        if self.status in [GameStatus.PLAYING, GameStatus.CHECK]:
            self.current_player = self.player_color

    def _check_game_end(self) -> bool:
        opponent_color = Color.BLACK if self.current_player == Color.RED else Color.RED

        if self.board.is_in_check(opponent_color):
            if self.board.is_checkmate(opponent_color):
                self.status = GameStatus.CHECKMATE
                self.winner = self.current_player
                return True
            else:
                self.status = GameStatus.CHECK
        elif self.board.is_stalemate(opponent_color):
            self.status = GameStatus.STALEMATE
            return True
        else:
            self.status = GameStatus.PLAYING

        return False

    def get_game_state(self) -> dict:
        board_state = []
        for row in range(Board.ROWS):
            row_data = []
            for col in range(Board.COLS):
                piece = self.board.get_piece(row, col)
                if piece:
                    row_data.append({
                        'row': row,
                        'col': col,
                        'color': piece.color.value,
                        'type': piece.piece_type.value,
                        'name': piece.name
                    })
                else:
                    row_data.append(None)
            board_state.append(row_data)

        return {
            'board': board_state,
            'current_player': self.current_player.value,
            'player_color': self.player_color.value,
            'status': self.status.value,
            'difficulty': self.difficulty.value,
            'move_notations': self.move_notations,
            'selected_piece': self.selected_piece,
            'valid_moves': self.valid_moves,
            'last_move': self.last_move,
            'winner': self.winner.value if self.winner else None
        }

    def get_share_code(self) -> str:
        initial_board = Board()
        notations = Notation.encode_game_history(self.board.move_history, initial_board)

        config = f"{self.player_color.value}|{self.difficulty.value}"
        return f"{config}|{notations}"

    @staticmethod
    def from_share_code(share_code: str) -> Optional['Game']:
        try:
            parts = share_code.split('|', 2)
            if len(parts) < 3:
                return None

            player_color_str, difficulty_str, notations_str = parts

            player_color = Color(player_color_str)
            difficulty = Difficulty(difficulty_str)

            game = Game()
            game.player_color = player_color
            game.ai_color = Color.BLACK if player_color == Color.RED else Color.RED
            game.difficulty = difficulty
            game.ai = AI(game.ai_color, difficulty)

            notations = Notation.decode_game_history(notations_str)
            game.move_notations = notations.copy()

            temp_board = Board()
            current_color = Color.RED

            for notation in notations:
                moves = Notation.notation_to_moves(temp_board, notation, current_color)
                if moves:
                    from_row, from_col, to_row, to_col = moves[0]
                    temp_board.move_piece(from_row, from_col, to_row, to_col)
                    game.last_move = (from_row, from_col, to_row, to_col)
                    current_color = Color.BLACK if current_color == Color.RED else Color.RED

            game.board = temp_board
            game.current_player = current_color

            if game.board.is_in_check(game.current_player):
                if game.board.is_checkmate(game.current_player):
                    game.status = GameStatus.CHECKMATE
                    game.winner = Color.BLACK if game.current_player == Color.RED else Color.RED
                else:
                    game.status = GameStatus.CHECK
            elif game.board.is_stalemate(game.current_player):
                game.status = GameStatus.STALEMATE
            else:
                game.status = GameStatus.PLAYING

            return game
        except Exception:
            return None

    def load_replay(self, share_code: str) -> List[Tuple[str, dict]]:
        try:
            parts = share_code.split('|', 2)
            if len(parts) < 3:
                return []

            player_color_str, difficulty_str, notations_str = parts
            notations = Notation.decode_game_history(notations_str)

            replay_steps = []
            temp_board = Board()
            current_color = Color.RED

            initial_state = self._get_board_state(temp_board)
            replay_steps.append(('初始局面', initial_state))

            for i, notation in enumerate(notations):
                moves = Notation.notation_to_moves(temp_board, notation, current_color)
                if moves:
                    from_row, from_col, to_row, to_col = moves[0]
                    temp_board.move_piece(from_row, from_col, to_row, to_col)

                    step_name = f"第{i+1}步: {notation}"
                    board_state = self._get_board_state(temp_board)
                    board_state['last_move'] = (from_row, from_col, to_row, to_col)
                    replay_steps.append((step_name, board_state))

                    current_color = Color.BLACK if current_color == Color.RED else Color.RED

            return replay_steps
        except Exception:
            return []

    def _get_board_state(self, board: Board) -> dict:
        board_state = []
        for row in range(Board.ROWS):
            row_data = []
            for col in range(Board.COLS):
                piece = board.get_piece(row, col)
                if piece:
                    row_data.append({
                        'row': row,
                        'col': col,
                        'color': piece.color.value,
                        'type': piece.piece_type.value,
                        'name': piece.name
                    })
                else:
                    row_data.append(None)
            board_state.append(row_data)
        return {'board': board_state, 'last_move': None}
