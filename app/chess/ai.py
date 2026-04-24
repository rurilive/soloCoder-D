import random
from typing import Tuple, Optional, List, Dict
from enum import Enum
from dataclasses import dataclass
from app.chess.board import Board
from app.chess.pieces import Color, PieceType, Piece


class Difficulty(Enum):
    EASY = 'easy'
    MEDIUM = 'medium'
    HARD = 'hard'


PIECE_VALUES = {
    PieceType.GENERAL: 10000,
    PieceType.CHARIOT: 900,
    PieceType.HORSE: 400,
    PieceType.CANNON: 450,
    PieceType.ELEPHANT: 200,
    PieceType.ADVISOR: 200,
    PieceType.SOLDIER: 100,
}


@dataclass
class TTEntry:
    value: float
    depth: int
    flag: str
    best_move: Optional[Tuple[int, int, int, int]]


class AI:
    _pos_tables_initialized = False
    _soldier_pos_red = [[0] * 9 for _ in range(10)]
    _soldier_pos_black = [[0] * 9 for _ in range(10)]
    _horse_pos = [[0] * 9 for _ in range(10)]
    _cannon_pos = [[0] * 9 for _ in range(10)]

    def __init__(self, color: Color, difficulty: Difficulty = Difficulty.MEDIUM):
        self.color = color
        self.difficulty = difficulty
        self.transposition_table: Dict[int, TTEntry] = {}
        self._set_depth_and_randomness()
        self._init_pos_tables()

    @classmethod
    def _init_pos_tables(cls):
        if cls._pos_tables_initialized:
            return

        for row in range(10):
            for col in range(9):
                if row <= 4:
                    cls._soldier_pos_red[row][col] = 30
                elif row <= 6:
                    cls._soldier_pos_red[row][col] = 20
                else:
                    cls._soldier_pos_red[row][col] = 10

                if row >= 5:
                    cls._soldier_pos_black[row][col] = 30
                elif row >= 3:
                    cls._soldier_pos_black[row][col] = 20
                else:
                    cls._soldier_pos_black[row][col] = 10

                if 3 <= row <= 6 and 3 <= col <= 5:
                    cls._horse_pos[row][col] = 20
                if col == 0 or col == 8:
                    cls._horse_pos[row][col] -= 10

                if row == 7 or row == 2:
                    cls._cannon_pos[row][col] = 10

        cls._pos_tables_initialized = True

    def _set_depth_and_randomness(self):
        if self.difficulty == Difficulty.EASY:
            self.max_depth = 1
            self.randomness = 0.6
            self.position_weight = 0.3
        elif self.difficulty == Difficulty.MEDIUM:
            self.max_depth = 2
            self.randomness = 0.2
            self.position_weight = 0.7
        else:
            self.max_depth = 3
            self.randomness = 0.05
            self.position_weight = 1.0

    def clear_tt(self):
        self.transposition_table.clear()

    def get_best_move(self, board: Board) -> Optional[Tuple[int, int, int, int]]:
        all_moves = board.get_all_valid_moves(self.color)
        if not all_moves:
            return None

        self.clear_tt()

        if self.difficulty == Difficulty.EASY:
            return self._easy_move(board, all_moves)
        elif self.difficulty == Difficulty.MEDIUM:
            return self._medium_move(board, all_moves)
        else:
            return self._hard_move(board, all_moves)

    def _easy_move(self, board: Board, all_moves: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        if random.random() < self.randomness:
            return random.choice(all_moves)

        capture_moves = []
        for move in all_moves:
            from_row, from_col, to_row, to_col = move
            target = board.get_piece(to_row, to_col)
            if target:
                capture_moves.append(move)

        if capture_moves and random.random() < 0.7:
            return random.choice(capture_moves)

        return random.choice(all_moves)

    def _medium_move(self, board: Board, all_moves: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        if random.random() < self.randomness:
            return random.choice(all_moves)

        sorted_moves = self._order_moves_mvvlva(board, all_moves)

        best_score = float('-inf')
        best_moves = []

        for move in sorted_moves:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._negamax_tt(board, self.max_depth - 1, float('-inf'), float('inf'), False)
            board.undo_move()

            score += random.uniform(-10, 10)

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return random.choice(best_moves) if best_moves else random.choice(all_moves)

    def _hard_move(self, board: Board, all_moves: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        if random.random() < self.randomness:
            return random.choice(all_moves)

        sorted_moves = self._order_moves_mvvlva(board, all_moves)

        best_score = float('-inf')
        best_moves = []

        for move in sorted_moves:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._negamax_tt(board, self.max_depth - 1, float('-inf'), float('inf'), True)
            board.undo_move()

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return random.choice(best_moves) if best_moves else random.choice(all_moves)

    def _order_moves_mvvlva(self, board: Board, moves: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        scored_moves = []
        for move in moves:
            from_row, from_col, to_row, to_col = move
            score = 0

            target = board.get_piece(to_row, to_col)
            from_piece = board.get_piece(from_row, from_col)

            if target and from_piece:
                score += PIECE_VALUES[target.piece_type] * 10 - PIECE_VALUES[from_piece.piece_type]
            elif target:
                score += PIECE_VALUES[target.piece_type] * 10

            if from_piece and from_piece.piece_type in [PieceType.HORSE, PieceType.CANNON, PieceType.CHARIOT]:
                score += 100

            scored_moves.append((score, move))

        scored_moves.sort(reverse=True, key=lambda x: x[0])
        return [move for _, move in scored_moves]

    def _negamax_tt(self, board: Board, depth: int, alpha: float, beta: float, use_quiescence: bool) -> float:
        alpha_orig = alpha

        if board.move_history:
            from_row, from_col, to_row, to_col, captured = board.move_history[-1]
            moved_piece = board.get_piece(to_row, to_col)
            if moved_piece:
                color = moved_piece.color
            else:
                color = self.color
        else:
            color = self.color

        if depth == 0:
            if use_quiescence:
                return self._quiescence(board, alpha, beta)
            return self._evaluate_fast(board, color)

        all_moves = board.get_all_valid_moves(color)
        moves = self._order_moves_mvvlva(board, all_moves)

        if not moves:
            if board.is_in_check(color):
                return float('-inf') + (self.max_depth - depth)
            return 0

        best_move = None
        for move in moves:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._negamax_tt(board, depth - 1, -beta, -alpha, use_quiescence)
            board.undo_move()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                best_move = move

        return alpha

    def _quiescence(self, board: Board, alpha: float, beta: float) -> float:
        if board.move_history:
            from_row, from_col, to_row, to_col, captured = board.move_history[-1]
            moved_piece = board.get_piece(to_row, to_col)
            if moved_piece:
                color = moved_piece.color
            else:
                color = self.color
        else:
            color = self.color

        stand_pat = self._evaluate_fast(board, color)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        all_moves = board.get_all_valid_moves(color)

        capture_moves = []
        for move in all_moves:
            from_row, from_col, to_row, to_col = move
            target = board.get_piece(to_row, to_col)
            if target:
                capture_moves.append(move)

        sorted_captures = self._order_moves_mvvlva(board, capture_moves)

        for move in sorted_captures:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._quiescence(board, -beta, -alpha)
            board.undo_move()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def _evaluate_fast(self, board: Board, current_color: Color) -> float:
        opponent_color = Color.BLACK if current_color == Color.RED else Color.RED

        score = 0.0

        my_pieces = board._red_pieces if current_color == Color.RED else board._black_pieces
        opp_pieces = board._red_pieces if opponent_color == Color.RED else board._black_pieces

        for piece in my_pieces:
            score += PIECE_VALUES[piece.piece_type]
            score += self._get_pos_score_fast(piece) * self.position_weight

        for piece in opp_pieces:
            score -= PIECE_VALUES[piece.piece_type]
            score -= self._get_pos_score_fast(piece) * self.position_weight

        if board.is_in_check(opponent_color):
            score += 100

        if board.is_in_check(current_color):
            score -= 100

        return score

    def _get_pos_score_fast(self, piece: Piece) -> int:
        row, col = piece.row, piece.col

        if piece.piece_type == PieceType.GENERAL:
            return 0

        if piece.piece_type == PieceType.SOLDIER:
            if piece.color == Color.RED:
                return self._soldier_pos_red[row][col]
            else:
                return self._soldier_pos_black[row][col]

        if piece.piece_type == PieceType.HORSE:
            return self._horse_pos[row][col]

        if piece.piece_type == PieceType.CANNON:
            return self._cannon_pos[row][col]

        return 0

    def _evaluate(self, board: Board) -> float:
        if board.move_history:
            from_row, from_col, to_row, to_col, captured = board.move_history[-1]
            moved_piece = board.get_piece(to_row, to_col)
            if moved_piece:
                current_color = moved_piece.color
            else:
                current_color = self.color
        else:
            current_color = self.color

        return self._evaluate_fast(board, current_color)

    def _get_position_score(self, piece: Piece) -> int:
        return self._get_pos_score_fast(piece)

    def _order_moves(self, board: Board, moves: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        return self._order_moves_mvvlva(board, moves)

    def _negamax(self, board: Board, depth: int, alpha: float, beta: float, use_quiescence: bool) -> float:
        return self._negamax_tt(board, depth, alpha, beta, use_quiescence)
