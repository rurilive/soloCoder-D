from typing import List, Optional, Tuple, Set
from app.chess.pieces import Color, PieceType, Piece


class Board:
    ROWS = 10
    COLS = 9

    def __init__(self):
        self.grid: List[List[Optional[Piece]]] = [[None for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.move_history: List[Tuple[int, int, int, int, Optional[Piece]]] = []
        self._red_pieces: List[Piece] = []
        self._black_pieces: List[Piece] = []
        self._red_general_pos: Optional[Tuple[int, int]] = None
        self._black_general_pos: Optional[Tuple[int, int]] = None
        self._initialize_board()

    def _initialize_board(self):
        self._red_pieces = []
        self._black_pieces = []
        self._red_general_pos = None
        self._black_general_pos = None

        for row, col, color, piece_type in [
            (0, 0, Color.BLACK, PieceType.CHARIOT),
            (0, 1, Color.BLACK, PieceType.HORSE),
            (0, 2, Color.BLACK, PieceType.ELEPHANT),
            (0, 3, Color.BLACK, PieceType.ADVISOR),
            (0, 4, Color.BLACK, PieceType.GENERAL),
            (0, 5, Color.BLACK, PieceType.ADVISOR),
            (0, 6, Color.BLACK, PieceType.ELEPHANT),
            (0, 7, Color.BLACK, PieceType.HORSE),
            (0, 8, Color.BLACK, PieceType.CHARIOT),
            (2, 1, Color.BLACK, PieceType.CANNON),
            (2, 7, Color.BLACK, PieceType.CANNON),
            (3, 0, Color.BLACK, PieceType.SOLDIER),
            (3, 2, Color.BLACK, PieceType.SOLDIER),
            (3, 4, Color.BLACK, PieceType.SOLDIER),
            (3, 6, Color.BLACK, PieceType.SOLDIER),
            (3, 8, Color.BLACK, PieceType.SOLDIER),
            (9, 0, Color.RED, PieceType.CHARIOT),
            (9, 1, Color.RED, PieceType.HORSE),
            (9, 2, Color.RED, PieceType.ELEPHANT),
            (9, 3, Color.RED, PieceType.ADVISOR),
            (9, 4, Color.RED, PieceType.GENERAL),
            (9, 5, Color.RED, PieceType.ADVISOR),
            (9, 6, Color.RED, PieceType.ELEPHANT),
            (9, 7, Color.RED, PieceType.HORSE),
            (9, 8, Color.RED, PieceType.CHARIOT),
            (7, 1, Color.RED, PieceType.CANNON),
            (7, 7, Color.RED, PieceType.CANNON),
            (6, 0, Color.RED, PieceType.SOLDIER),
            (6, 2, Color.RED, PieceType.SOLDIER),
            (6, 4, Color.RED, PieceType.SOLDIER),
            (6, 6, Color.RED, PieceType.SOLDIER),
            (6, 8, Color.RED, PieceType.SOLDIER),
        ]:
            piece = Piece(color, piece_type, row, col)
            self.grid[row][col] = piece
            if color == Color.RED:
                self._red_pieces.append(piece)
            else:
                self._black_pieces.append(piece)
            if piece_type == PieceType.GENERAL:
                if color == Color.RED:
                    self._red_general_pos = (row, col)
                else:
                    self._black_general_pos = (row, col)

    def get_piece(self, row: int, col: int) -> Optional[Piece]:
        if 0 <= row < self.ROWS and 0 <= col < self.COLS:
            return self.grid[row][col]
        return None

    def set_piece(self, row: int, col: int, piece: Optional[Piece]):
        if 0 <= row < self.ROWS and 0 <= col < self.COLS:
            self.grid[row][col] = piece
            if piece:
                piece.row = row
                piece.col = col

    def move_piece(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        piece = self.get_piece(from_row, from_col)
        if piece is None:
            return False

        target = self.get_piece(to_row, to_col)
        self.move_history.append((from_row, from_col, to_row, to_col, target))

        if target:
            if target.color == Color.RED:
                self._red_pieces.remove(target)
            else:
                self._black_pieces.remove(target)

        self.set_piece(to_row, to_col, piece)
        self.set_piece(from_row, from_col, None)

        if piece.piece_type == PieceType.GENERAL:
            if piece.color == Color.RED:
                self._red_general_pos = (to_row, to_col)
            else:
                self._black_general_pos = (to_row, to_col)

        return True

    def undo_move(self) -> bool:
        if not self.move_history:
            return False

        from_row, from_col, to_row, to_col, captured = self.move_history.pop()
        piece = self.get_piece(to_row, to_col)

        if piece:
            self.set_piece(from_row, from_col, piece)
            if piece.piece_type == PieceType.GENERAL:
                if piece.color == Color.RED:
                    self._red_general_pos = (from_row, from_col)
                else:
                    self._black_general_pos = (from_row, from_col)
        self.set_piece(to_row, to_col, captured)

        if captured:
            if captured.color == Color.RED:
                self._red_pieces.append(captured)
            else:
                self._black_pieces.append(captured)

        return True

    def get_valid_moves(self, row: int, col: int) -> Set[Tuple[int, int]]:
        piece = self.get_piece(row, col)
        if piece is None:
            return set()

        moves = self._get_piece_moves(piece)
        valid_moves = set()

        for to_row, to_col in moves:
            if self._is_valid_move(piece, row, col, to_row, to_col):
                valid_moves.add((to_row, to_col))

        return valid_moves

    def _get_piece_moves(self, piece: Piece) -> Set[Tuple[int, int]]:
        moves = set()
        row, col = piece.row, piece.col

        if piece.piece_type == PieceType.GENERAL:
            moves = self._get_general_moves(piece, row, col)
        elif piece.piece_type == PieceType.ADVISOR:
            moves = self._get_advisor_moves(piece, row, col)
        elif piece.piece_type == PieceType.ELEPHANT:
            moves = self._get_elephant_moves(piece, row, col)
        elif piece.piece_type == PieceType.HORSE:
            moves = self._get_horse_moves(piece, row, col)
        elif piece.piece_type == PieceType.CHARIOT:
            moves = self._get_chariot_moves(piece, row, col)
        elif piece.piece_type == PieceType.CANNON:
            moves = self._get_cannon_moves(piece, row, col)
        elif piece.piece_type == PieceType.SOLDIER:
            moves = self._get_soldier_moves(piece, row, col)

        return moves

    def _is_valid_move(self, piece: Piece, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        target = self.get_piece(to_row, to_col)
        if target and target.color == piece.color:
            return False

        self.move_piece(from_row, from_col, to_row, to_col)
        in_check = self.is_in_check(piece.color)
        self.undo_move()

        return not in_check

    def _get_general_moves(self, piece: Piece, row: int, col: int) -> Set[Tuple[int, int]]:
        moves = set()

        if piece.color == Color.RED:
            row_min, row_max = 7, 9
        else:
            row_min, row_max = 0, 2
        col_min, col_max = 3, 5

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if row_min <= nr <= row_max and col_min <= nc <= col_max:
                target = self.get_piece(nr, nc)
                if target is None or target.color != piece.color:
                    moves.add((nr, nc))

        opponent_color = Color.BLACK if piece.color == Color.RED else Color.RED
        if opponent_color == Color.RED:
            opp_general_pos = self._red_general_pos
        else:
            opp_general_pos = self._black_general_pos

        if opp_general_pos:
            opp_row, opp_col = opp_general_pos
            if opp_col == col:
                min_row, max_row = min(row, opp_row), max(row, opp_row)
                clear = True
                for r in range(min_row + 1, max_row):
                    if self.get_piece(r, col) is not None:
                        clear = False
                        break
                if clear:
                    moves.add((opp_row, col))

        return moves

    def _get_advisor_moves(self, piece: Piece, row: int, col: int) -> Set[Tuple[int, int]]:
        moves = set()

        if piece.color == Color.RED:
            row_min, row_max = 7, 9
        else:
            row_min, row_max = 0, 2
        col_min, col_max = 3, 5

        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nr, nc = row + dr, col + dc
            if row_min <= nr <= row_max and col_min <= nc <= col_max:
                target = self.get_piece(nr, nc)
                if target is None or target.color != piece.color:
                    moves.add((nr, nc))

        return moves

    def _get_elephant_moves(self, piece: Piece, row: int, col: int) -> Set[Tuple[int, int]]:
        moves = set()

        if piece.color == Color.RED:
            row_min, row_max = 5, 9
        else:
            row_min, row_max = 0, 4

        for dr, dc, block_dr, block_dc in [
            (-2, -2, -1, -1), (-2, 2, -1, 1),
            (2, -2, 1, -1), (2, 2, 1, 1)
        ]:
            nr, nc = row + dr, col + dc
            block_r, block_c = row + block_dr, col + block_dc

            if row_min <= nr <= row_max and 0 <= nc < self.COLS:
                if self.get_piece(block_r, block_c) is None:
                    target = self.get_piece(nr, nc)
                    if target is None or target.color != piece.color:
                        moves.add((nr, nc))

        return moves

    def _get_horse_moves(self, piece: Piece, row: int, col: int) -> Set[Tuple[int, int]]:
        moves = set()

        for dr, dc, block_dr, block_dc in [
            (-2, -1, -1, 0), (-2, 1, -1, 0),
            (2, -1, 1, 0), (2, 1, 1, 0),
            (-1, -2, 0, -1), (1, -2, 0, -1),
            (-1, 2, 0, 1), (1, 2, 0, 1)
        ]:
            nr, nc = row + dr, col + dc
            block_r, block_c = row + block_dr, col + block_dc

            if 0 <= nr < self.ROWS and 0 <= nc < self.COLS:
                if self.get_piece(block_r, block_c) is None:
                    target = self.get_piece(nr, nc)
                    if target is None or target.color != piece.color:
                        moves.add((nr, nc))

        return moves

    def _get_chariot_moves(self, piece: Piece, row: int, col: int) -> Set[Tuple[int, int]]:
        moves = set()

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            while 0 <= nr < self.ROWS and 0 <= nc < self.COLS:
                target = self.get_piece(nr, nc)
                if target is None:
                    moves.add((nr, nc))
                else:
                    if target.color != piece.color:
                        moves.add((nr, nc))
                    break
                nr += dr
                nc += dc

        return moves

    def _get_cannon_moves(self, piece: Piece, row: int, col: int) -> Set[Tuple[int, int]]:
        moves = set()

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            jumped = False
            while 0 <= nr < self.ROWS and 0 <= nc < self.COLS:
                target = self.get_piece(nr, nc)
                if not jumped:
                    if target is None:
                        moves.add((nr, nc))
                    else:
                        jumped = True
                else:
                    if target is not None:
                        if target.color != piece.color:
                            moves.add((nr, nc))
                        break
                nr += dr
                nc += dc

        return moves

    def _get_soldier_moves(self, piece: Piece, row: int, col: int) -> Set[Tuple[int, int]]:
        moves = set()

        if piece.color == Color.RED:
            forward = -1
            crossed_river = row <= 4
        else:
            forward = 1
            crossed_river = row >= 5

        nr = row + forward
        if 0 <= nr < self.ROWS:
            target = self.get_piece(nr, col)
            if target is None or target.color != piece.color:
                moves.add((nr, col))

        if crossed_river:
            for dc in [-1, 1]:
                nc = col + dc
                if 0 <= nc < self.COLS:
                    target = self.get_piece(row, nc)
                    if target is None or target.color != piece.color:
                        moves.add((row, nc))

        return moves

    def get_all_pieces(self, color: Optional[Color] = None) -> List[Piece]:
        if color == Color.RED:
            return list(self._red_pieces)
        elif color == Color.BLACK:
            return list(self._black_pieces)
        else:
            return self._red_pieces + self._black_pieces

    def find_general(self, color: Color) -> Optional[Piece]:
        if color == Color.RED:
            pos = self._red_general_pos
        else:
            pos = self._black_general_pos
        if pos:
            return self.get_piece(pos[0], pos[1])
        return None

    def is_in_check(self, color: Color) -> bool:
        if color == Color.RED:
            general_pos = self._red_general_pos
        else:
            general_pos = self._black_general_pos
        if general_pos is None:
            return True
        gen_row, gen_col = general_pos

        opponent_color = Color.BLACK if color == Color.RED else Color.RED
        opponent_pieces = self._black_pieces if opponent_color == Color.BLACK else self._red_pieces

        for piece in opponent_pieces:
            moves = self._get_piece_moves(piece)
            if (gen_row, gen_col) in moves:
                return True

        return False

    def get_all_valid_moves(self, color: Color) -> List[Tuple[int, int, int, int]]:
        moves = []
        pieces = self._red_pieces if color == Color.RED else self._black_pieces
        for piece in pieces:
            valid_moves = self.get_valid_moves(piece.row, piece.col)
            for to_row, to_col in valid_moves:
                moves.append((piece.row, piece.col, to_row, to_col))
        return moves

    def is_checkmate(self, color: Color) -> bool:
        if not self.is_in_check(color):
            return False
        return len(self.get_all_valid_moves(color)) == 0

    def is_stalemate(self, color: Color) -> bool:
        if self.is_in_check(color):
            return False
        return len(self.get_all_valid_moves(color)) == 0

    def copy(self) -> 'Board':
        new_board = Board()
        new_board.grid = [[None for _ in range(self.COLS)] for _ in range(self.ROWS)]
        for row in range(self.ROWS):
            for col in range(self.COLS):
                piece = self.get_piece(row, col)
                if piece:
                    new_board.grid[row][col] = Piece(piece.color, piece.piece_type, row, col)
        new_board.move_history = []
        return new_board
