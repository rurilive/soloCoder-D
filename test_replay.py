from app.chess.board import Board
from app.chess.notation import Notation
from app.chess.pieces import Color, PieceType

share_code = "red|medium|炮八进七|卒5进一|马八进二|车1进二|兵五进一|马8进二|兵五进一|将5进一|炮二平五|将5平4|兵七进一|士4进一|马七进二|炮8进一|炮五平六|士5进一|马六进二|将4平5|马七进一|将5进一|车九平八|炮2退一|马九进一|将5平6|车八进七|马7退一|车八平六|象7进二|车六平五|象3进二|兵五进一|炮8退二|兵五进一|将6退一|马七退二|炮8进三|炮八平九|炮8进一|炮九平一|炮2进三|马二进二|炮2退三|兵七进一|炮2进七|兵三进一|炮2退七|马三进二|炮2进二|马二进二|马9进一|马六进二|炮2进五|车一平二|炮2退七|车二进八"

print("=" * 60)
print("测试复盘解析")
print("=" * 60)

notations = Notation.decode_game_history(share_code.split('|', 2)[2])
print(f"总步数: {len(notations)}")
print()

temp_board = Board()
current_color = Color.RED

failed_steps = []

for i, notation in enumerate(notations):
    step_num = i + 1
    
    moves = Notation.notation_to_moves(temp_board, notation, current_color)
    
    if not moves:
        other_color = Color.BLACK if current_color == Color.RED else Color.RED
        moves = Notation.notation_to_moves(temp_board, notation, other_color)
    
    if moves:
        from_row, from_col, to_row, to_col = moves[0]
        piece = temp_board.get_piece(from_row, from_col)
        piece_name = piece.name if piece else '未知'
        print(f"  第 {step_num:2d} 步 [{current_color.value}]: {notation} → ({from_row},{from_col})→({to_row},{to_col}) [{piece_name}]")
        temp_board.move_piece(from_row, from_col, to_row, to_col)
    else:
        print(f"! 第 {step_num:2d} 步 [{current_color.value}]: {notation} → 解析失败!")
        failed_steps.append((step_num, notation, current_color.value))
        
        print(f"  调试信息:")
        print(f"    - 当前颜色: {current_color.value}")
        
        piece_char = notation[0]
        if notation[0] in ['前', '后'] or notation[0] in ['一', '二', '三', '四', '五', '六', '七', '八', '九']:
            piece_char = notation[1]
        
        print(f"    - 棋子字符: '{piece_char}'")
        print(f"    - 记法: {notation}")
        
        piece_type = Notation._parse_piece_char(piece_char, current_color)
        print(f"    - 解析的棋子类型 ({current_color.value}): {piece_type}")
        
        if len(notation) >= 2:
            from_col_char = notation[1] if notation[0] not in ['前', '后'] else notation[2]
            from_col = Notation._parse_col_char(from_col_char, current_color)
            print(f"    - 起始列字符: '{from_col_char}'")
            print(f"    - 解析的起始列 ({current_color.value}): {from_col}")
        
        print(f"    - 当前棋盘上 {current_color.value} 的棋子:")
        for row in range(10):
            for col in range(9):
                p = temp_board.get_piece(row, col)
                if p and p.color == current_color:
                    col_char = Notation._get_col_char(col, current_color)
                    print(f"      ({row},{col}) - {p.name} (列字符: '{col_char}')")
        
        print()
    
    current_color = Color.BLACK if current_color == Color.RED else Color.RED

print()
print("=" * 60)
if failed_steps:
    print(f"失败的步骤 ({len(failed_steps)} 个):")
    for step_num, notation, color in failed_steps:
        print(f"  第 {step_num} 步 ({color}): {notation}")
else:
    print("所有步骤解析成功!")
print("=" * 60)
