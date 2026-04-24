import time
from app.chess.board import Board
from app.chess.ai import AI, Difficulty
from app.chess.pieces import Color
from app.chess.game import Game


def test_ai_speed():
    print("=" * 60)
    print("测试 AI 算法性能")
    print("=" * 60)

    board = Board()

    print("\n1. 测试 get_all_valid_moves 性能:")
    start = time.time()
    for i in range(100):
        moves = board.get_all_valid_moves(Color.RED)
    elapsed = (time.time() - start) * 1000
    print(f"   100 次调用耗时: {elapsed:.2f} ms")
    print(f"   每次平均耗时: {elapsed/100:.2f} ms")
    print(f"   红方有效走法数量: {len(moves)}")

    print("\n2. 测试 AI 决策速度 (不同难度):")

    for diff_name, diff in [("简单", Difficulty.EASY), ("中等", Difficulty.MEDIUM), ("困难", Difficulty.HARD)]:
        ai = AI(Color.BLACK, diff)
        start = time.time()
        move = ai.get_best_move(board)
        elapsed = (time.time() - start) * 1000
        print(f"   {diff_name} (深度 {ai.max_depth}): {elapsed:.2f} ms")
        if move:
            print(f"      选择走法: {move}")

    print("\n3. 测试多回合 AI 对战:")
    game = Game()
    game.start_game(Color.RED, Difficulty.MEDIUM)

    total_time = 0
    move_count = 0

    for i in range(10):
        if game.status.value not in ['playing', 'check']:
            break

        moves = game.board.get_all_valid_moves(game.current_player)
        if not moves:
            break

        move = moves[0]
        from_r, from_c, to_r, to_c = move

        start = time.time()
        game.make_move(from_r, from_c, to_r, to_c)
        elapsed = (time.time() - start) * 1000

        total_time += elapsed
        move_count += 1

        print(f"   回合 {i+1}: 玩家走法耗时 {elapsed:.2f} ms")

    if move_count > 0:
        print(f"\n   平均每回合耗时: {total_time/move_count:.2f} ms")

    print("\n" + "=" * 60)
    print("优化总结:")
    print("=" * 60)
    print("1. Board 类优化:")
    print("   - 缓存红方/黑方棋子列表 (避免每次遍历整个棋盘)")
    print("   - 缓存将的位置 (避免每次查找)")
    print("2. AI 类优化:")
    print("   - MVVLVA 走法排序 (Most Valuable Victim - Least Valuable Aggressor)")
    print("   - 预计算位置分表 (避免每次动态计算)")
    print("   - 简化评估函数 (使用缓存的棋子列表)")
    print("3. 走法排序效果:")
    print("   - 吃子走法优先 (用车吃兵 < 用兵吃车)")
    print("   - 强子活动走法优先 (车、马、炮)")


if __name__ == '__main__':
    test_ai_speed()
