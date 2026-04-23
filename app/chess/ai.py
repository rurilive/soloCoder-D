import random
from typing import Tuple, Optional, List
from enum import Enum
from app.chess.board import Board
from app.chess.pieces import Color, PieceType


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


class AI:
    def __init__(self, color: Color, difficulty: Difficulty = Difficulty.MEDIUM):
        self.color = color
        self.difficulty = difficulty
        self._set_depth_and_randomness()

    def _set_depth_and_randomness(self):
        if self.difficulty == Difficulty.EASY:
            self.max_depth = 1
            self.randomness = 0.6
            self.position_weight = 0.3
        elif self.difficulty == Difficulty.MEDIUM:
            self.max_depth = 3
            self.randomness = 0.2
            self.position_weight = 0.7
        else:
            self.max_depth = 4
            self.randomness = 0.05
            self.position_weight = 1.0

    def get_best_move(self, board: Board) -> Optional[Tuple[int, int, int, int]]:
        all_moves = board.get_all_valid_moves(self.color)
        if not all_moves:
            return None

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

        best_score = float('-inf')
        best_moves = []

        for move in all_moves:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._negamax(board, self.max_depth - 1, float('-inf'), float('inf'), False)
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

        sorted_moves = self._order_moves(board, all_moves)

        best_score = float('-inf')
        best_moves = []

        for move in sorted_moves:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._negamax(board, self.max_depth - 1, float('-inf'), float('inf'), True)
            board.undo_move()

            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)

        return random.choice(best_moves) if best_moves else random.choice(all_moves)

    def _order_moves(self, board: Board, moves: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        scored_moves = []
        for move in moves:
            from_row, from_col, to_row, to_col = move
            score = 0

            target = board.get_piece(to_row, to_col)
            if target:
                score += PIECE_VALUES[target.piece_type] * 10

            from_piece = board.get_piece(from_row, from_col)
            if from_piece:
                score -= PIECE_VALUES[from_piece.piece_type]

            general = board.find_general(self.color)
            if general:
                dist_before = abs(general.row - from_row) + abs(general.col - from_col)
                dist_after = abs(general.row - to_row) + abs(general.col - to_col)
                if dist_after < dist_before:
                    score += 50

            scored_moves.append((score, move))

        scored_moves.sort(reverse=True, key=lambda x: x[0])
        return [move for _, move in scored_moves]

    def _negamax(self, board: Board, depth: int, alpha: float, beta: float, use_quiescence: bool) -> float:
        if depth == 0:
            if use_quiescence:
                return self._quiescence(board, alpha, beta)
            return self._evaluate(board)

        color = board.move_history[-1][4].color if board.move_history else self.color
        moves = board.get_all_valid_moves(color)

        if not moves:
            if board.is_in_check(color):
                return float('-inf') + (self.max_depth - depth)
            return 0

        for move in moves:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._negamax(board, depth - 1, -beta, -alpha, use_quiescence)
            board.undo_move()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def _quiescence(self, board: Board, alpha: float, beta: float) -> float:
        stand_pat = self._evaluate(board)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        color = board.move_history[-1][4].color if board.move_history else self.color
        all_moves = board.get_all_valid_moves(color)

        capture_moves = []
        for move in all_moves:
            from_row, from_col, to_row, to_col = move
            target = board.get_piece(to_row, to_col)
            if target:
                capture_moves.append(move)

        for move in capture_moves:
            from_row, from_col, to_row, to_col = move
            board.move_piece(from_row, from_col, to_row, to_col)
            score = -self._quiescence(board, -beta, -alpha)
            board.undo_move()

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def _evaluate(self, board: Board) -> float:
        current_color = board.move_history[-1][4].color if board.move_history else self.color
        opponent_color = Color.BLACK if current_color == Color.RED else Color.RED

        score = 0.0

        for piece in board.get_all_pieces(current_color):
            score += PIECE_VALUES[piece.piece_type]
            score += self._get_position_score(piece) * self.position_weight

        for piece in board.get_all_pieces(opponent_color):
            score -= PIECE_VALUES[piece.piece_type]
            score -= self._get_position_score(piece) * self.position_weight

        if board.is_in_check(opponent_color):
            score += 100

        if board.is_in_check(current_color):
            score -= 100

        return score

    def _get_position_score(self, piece) -> int:
        row, col = piece.row, piece.col

        if piece.piece_type == PieceType.GENERAL:
            return 0

        if piece.piece_type == PieceType.SOLDIER:
            if piece.color == Color.RED:
                if row <= 4:
                    return 30
                if row <= 6:
                    return 20
                return 10
            else:
                if row >= 5:
                    return 30
                if row >= 3:
                    return 20
                return 10

        if piece.piece_type == PieceType.HORSE:
            center_bonus = 0
            if 3 <= row <= 6 and 3 <= col <= 5:
                center_bonus = 20
            edge_penalty = 0
            if col == 0 or col == 8:
                edge_penalty = 10
            return center_bonus - edge_penalty

        if piece.piece_type == PieceType.CANNON:
            if row == 7 or row == 2:
                return 10

        return 0
