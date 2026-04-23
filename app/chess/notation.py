from typing import List, Tuple, Optional
from app.chess.board import Board
from app.chess.pieces import Color, PieceType, Piece


class Notation:
    RED_COLS = ['九', '八', '七', '六', '五', '四', '三', '二', '一']
    BLACK_COLS = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
    NUMS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']

    @staticmethod
    def move_to_notation(board: Board, from_row: int, from_col: int, to_row: int, to_col: int) -> str:
        piece = board.get_piece(from_row, from_col)
        if not piece:
            return ''

        color = piece.color
        piece_name = Notation._get_piece_notation_name(piece)
        from_col_char = Notation._get_col_char(from_col, color)

        same_col_pieces = Notation._count_same_type_col_pieces(board, piece, from_col)
        prefix = Notation._get_prefix(board, piece, from_row, from_col, same_col_pieces)

        if from_row == to_row:
            action = '平'
            to_char = Notation._get_col_char(to_col, color)
        elif color == Color.RED:
            if to_row < from_row:
                action = '进'
            else:
                action = '退'
            to_char = Notation._get_row_diff_char(abs(to_row - from_row))
        else:
            if to_row > from_row:
                action = '进'
            else:
                action = '退'
            to_char = Notation._get_row_diff_char(abs(to_row - from_row))

        return f"{prefix}{piece_name}{from_col_char}{action}{to_char}"

    @staticmethod
    def _get_piece_notation_name(piece: Piece) -> str:
        if piece.color == Color.RED:
            names = {
                PieceType.GENERAL: '帅',
                PieceType.ADVISOR: '仕',
                PieceType.ELEPHANT: '相',
                PieceType.HORSE: '马',
                PieceType.CHARIOT: '车',
                PieceType.CANNON: '炮',
                PieceType.SOLDIER: '兵',
            }
        else:
            names = {
                PieceType.GENERAL: '将',
                PieceType.ADVISOR: '士',
                PieceType.ELEPHANT: '象',
                PieceType.HORSE: '马',
                PieceType.CHARIOT: '车',
                PieceType.CANNON: '炮',
                PieceType.SOLDIER: '卒',
            }
        return names.get(piece.piece_type, '')

    @staticmethod
    def _get_col_char(col: int, color: Color) -> str:
        if color == Color.RED:
            return Notation.RED_COLS[col]
        else:
            return Notation.BLACK_COLS[col]

    @staticmethod
    def _get_row_diff_char(diff: int) -> str:
        if 0 <= diff < len(Notation.NUMS):
            return Notation.NUMS[diff]
        return str(diff)

    @staticmethod
    def _count_same_type_col_pieces(board: Board, piece: Piece, col: int) -> int:
        count = 0
        for row in range(Board.ROWS):
            p = board.get_piece(row, col)
            if p and p.piece_type == piece.piece_type and p.color == piece.color:
                count += 1
        return count

    @staticmethod
    def _get_prefix(board: Board, piece: Piece, row: int, col: int, same_col_count: int) -> str:
        if same_col_count <= 1:
            return ''

        color = piece.color
        same_type_pieces = []

        for r in range(Board.ROWS):
            p = board.get_piece(r, col)
            if p and p.piece_type == piece.piece_type and p.color == color:
                same_type_pieces.append(r)

        if color == Color.RED:
            same_type_pieces.sort(reverse=True)
        else:
            same_type_pieces.sort()

        idx = same_type_pieces.index(row)

        if len(same_type_pieces) == 2:
            return '前' if idx == 0 else '后'
        else:
            return Notation.NUMS[idx + 1]

    @staticmethod
    def notation_to_moves(board: Board, notation: str, color: Color) -> List[Tuple[int, int, int, int]]:
        try:
            return Notation._parse_notation(board, notation, color)
        except:
            return []

    @staticmethod
    def _parse_notation(board: Board, notation: str, color: Color) -> List[Tuple[int, int, int, int]]:
        if len(notation) < 4:
            return []

        prefix = ''
        idx = 0
        if notation[0] in ['前', '后']:
            prefix = notation[0]
            idx = 1
        elif notation[0] in Notation.NUMS[1:]:
            prefix = notation[0]
            idx = 1

        piece_char = notation[idx]
        from_col_char = notation[idx + 1]
        action = notation[idx + 2]
        to_char = notation[idx + 3]

        from_col = Notation._parse_col_char(from_col_char, color)
        if from_col is None:
            return []

        piece_type = Notation._parse_piece_char(piece_char, color)
        if piece_type is None:
            return []

        candidates = []
        for row in range(Board.ROWS):
            p = board.get_piece(row, from_col)
            if p and p.piece_type == piece_type and p.color == color:
                candidates.append((row, from_col))

        if not candidates:
            for col in range(Board.COLS):
                for row in range(Board.ROWS):
                    p = board.get_piece(row, col)
                    if p and p.piece_type == piece_type and p.color == color:
                        col_char = Notation._get_col_char(col, color)
                        if col_char == from_col_char:
                            candidates.append((row, col))

        if prefix:
            if color == Color.RED:
                candidates.sort(key=lambda x: -x[0])
            else:
                candidates.sort(key=lambda x: x[0])

            if prefix == '前':
                candidates = [candidates[0]] if candidates else []
            elif prefix == '后':
                candidates = [candidates[-1]] if len(candidates) >= 2 else []
            else:
                idx = Notation.NUMS.index(prefix) - 1
                if idx < len(candidates):
                    candidates = [candidates[idx]]
                else:
                    candidates = []

        moves = []
        for from_row, fc in candidates:
            from_col = fc
            valid_moves = board.get_valid_moves(from_row, from_col)

            for to_row, to_col in valid_moves:
                generated = Notation.move_to_notation(board, from_row, from_col, to_row, to_col)
                if generated == notation:
                    moves.append((from_row, from_col, to_row, to_col))

        return moves

    @staticmethod
    def _parse_col_char(col_char: str, color: Color) -> Optional[int]:
        if color == Color.RED:
            if col_char in Notation.RED_COLS:
                return Notation.RED_COLS.index(col_char)
        else:
            if col_char in Notation.BLACK_COLS:
                return Notation.BLACK_COLS.index(col_char)
        return None

    @staticmethod
    def _parse_piece_char(piece_char: str, color: Color) -> Optional[PieceType]:
        red_map = {
            '帅': PieceType.GENERAL,
            '仕': PieceType.ADVISOR,
            '相': PieceType.ELEPHANT,
            '马': PieceType.HORSE,
            '车': PieceType.CHARIOT,
            '炮': PieceType.CANNON,
            '兵': PieceType.SOLDIER,
        }
        black_map = {
            '将': PieceType.GENERAL,
            '士': PieceType.ADVISOR,
            '象': PieceType.ELEPHANT,
            '马': PieceType.HORSE,
            '车': PieceType.CHARIOT,
            '炮': PieceType.CANNON,
            '卒': PieceType.SOLDIER,
        }

        if color == Color.RED:
            return red_map.get(piece_char)
        else:
            if piece_char in black_map:
                return black_map[piece_char]
            if piece_char in red_map and red_map[piece_char] == PieceType.HORSE:
                return PieceType.HORSE
            if piece_char in red_map and red_map[piece_char] == PieceType.CHARIOT:
                return PieceType.CHARIOT
            if piece_char in red_map and red_map[piece_char] == PieceType.CANNON:
                return PieceType.CANNON
        return None

    @staticmethod
    def encode_game_history(move_history: List[Tuple[int, int, int, int, Optional[Piece]]],
                            board: Board) -> str:
        notations = []
        temp_board = board.copy()

        for move in move_history:
            from_row, from_col, to_row, to_col, captured = move
            notation = Notation.move_to_notation(temp_board, from_row, from_col, to_row, to_col)
            notations.append(notation)
            temp_board.move_piece(from_row, from_col, to_row, to_col)

        return '|'.join(notations)

    @staticmethod
    def decode_game_history(encoded: str) -> List[str]:
        if not encoded:
            return []
        return [n for n in encoded.split('|') if n]
