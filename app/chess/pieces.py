from enum import Enum

class Color(Enum):
    RED = 'red'
    BLACK = 'black'

class PieceType(Enum):
    GENERAL = 'general'
    ADVISOR = 'advisor'
    ELEPHANT = 'elephant'
    HORSE = 'horse'
    CHARIOT = 'chariot'
    CANNON = 'cannon'
    SOLDIER = 'soldier'

class Piece:
    def __init__(self, color: Color, piece_type: PieceType, row: int, col: int):
        self.color = color
        self.piece_type = piece_type
        self.row = row
        self.col = col
        self.name = self._get_name()

    def _get_name(self) -> str:
        names = {
            (Color.RED, PieceType.GENERAL): '帅',
            (Color.RED, PieceType.ADVISOR): '仕',
            (Color.RED, PieceType.ELEPHANT): '相',
            (Color.RED, PieceType.HORSE): '马',
            (Color.RED, PieceType.CHARIOT): '车',
            (Color.RED, PieceType.CANNON): '炮',
            (Color.RED, PieceType.SOLDIER): '兵',
            (Color.BLACK, PieceType.GENERAL): '将',
            (Color.BLACK, PieceType.ADVISOR): '士',
            (Color.BLACK, PieceType.ELEPHANT): '象',
            (Color.BLACK, PieceType.HORSE): '马',
            (Color.BLACK, PieceType.CHARIOT): '车',
            (Color.BLACK, PieceType.CANNON): '炮',
            (Color.BLACK, PieceType.SOLDIER): '卒',
        }
        return names[(self.color, self.piece_type)]

    def __str__(self) -> str:
        return self.name
