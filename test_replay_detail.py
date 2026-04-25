from app.chess.board import Board
from app.chess.notation import Notation
from app.chess.pieces import Color, PieceType

share_code = "red|medium|炮八进七|卒5进一|马八进二|车1进二|兵五进一|马8进二|兵五进一|将5进一|炮二平五|将5平4|兵七进一|士4进一|马七进二|炮8进一|炮五平六|士5进一|马六进二|将4平5|马七进一|将5进一|车九平八|炮2退一|马九进一|将5平6|车八进七|马7退一|车八平六|象7进二|车六平五|象3进二|兵五进一|炮8退二|兵五进一|将6退一|马七退二|炮8进三|炮八平九|炮8进一|炮九平一|炮2进三|马二进二|炮2退三|兵七进一|炮2进七|兵三进一|炮2退七|马三进二|炮2进二|马二进二|马9进一|马六进二|炮2进五|车一平二|炮2退七|车二进八"

print("=" * 70)
print("详细分析复盘问题")
print("=" * 70)

notations = Notation.decode_game_history(share_code.split('|', 2)[2])
print(f"总步数: {len(notations)}")
print()

temp_board = Board()
current_color = Color.RED

print("-" * 70)
print("步骤分析：")
print("-" * 70)

for i, notation in enumerate(notations):
    step_num = i + 1
    
    print(f"\n第 {step_num:2d} 步 [{current_color.value}]: {notation}")
    
    moves = Notation.notation_to_moves(temp_board, notation, current_color)
    
    if not moves:
        other_color = Color.BLACK if current_color == Color.RED else Color.RED
        moves = Notation.notation_to_moves(temp_board, notation, other_color)
    
    if moves:
        from_row, from_col, to_row, to_col = moves[0]
        piece = temp_board.get_piece(from_row, from_col)
        piece_name = piece.name if piece else '未知'
        
        generated = Notation.move_to_notation(temp_board, from_row, from_col, to_row, to_col)
        match = "✓" if generated == notation else f"✗ (生成: {generated})"
        
        print(f"  解析: ({from_row},{from_col})→({to_row},{to_col}) [{piece_name}] {match}")
        
        temp_board.move_piece(from_row, from_col, to_row, to_col)
    else:
        print(f"  解析失败!")
        print(f"  调试信息:")
        
        piece_char = notation[0]
        if notation[0] in ['前', '后'] or notation[0] in ['一', '二', '三', '四', '五', '六', '七', '八', '九']:
            piece_char = notation[1]
        
        from_col_char_idx = 1 if notation[0] in ['前', '后'] or notation[0] in ['一', '二', '三', '四', '五', '六', '七', '八', '九'] else 1
        
        if len(notation) >= 2:
            from_col_char = notation[1] if notation[0] not in ['前', '后'] else notation[2]
            print(f"    - 棋子字符: '{piece_char}'")
            print(f"    - 起始列字符: '{from_col_char}'")
            
            from_col_red = Notation._parse_col_char(from_col_char, Color.RED)
            from_col_black = Notation._parse_col_char(from_col_char, Color.BLACK)
            print(f"    - 解析为红方起始列: {from_col_red}")
            print(f"    - 解析为黑方起始列: {from_col_black}")
        
        print(f"    - 当前颜色 {current_color.value} 的 {piece_char} 位置:")
        piece_type = Notation._parse_piece_char(piece_char, current_color)
        
        if piece_type:
            for row in range(10):
                for col in range(9):
                    p = temp_board.get_piece(row, col)
                    if p and p.piece_type == piece_type and p.color == current_color:
                        col_char = Notation._get_col_char(col, current_color)
                        print(f"      ({row},{col}) - {p.name} (列字符: '{col_char}')")
                        
                        valid_moves = temp_board.get_valid_moves(row, col)
                        for to_row, to_col in valid_moves:
                            generated = Notation.move_to_notation(temp_board, row, col, to_row, to_col)
                            print(f"        可能走法: ({row},{col})→({to_row},{to_col}) → 记法: '{generated}'")
    
    current_color = Color.BLACK if current_color == Color.RED else Color.RED

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)
