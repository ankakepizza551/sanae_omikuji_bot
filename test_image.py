import os
import sys

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.image_generator import generate_omikuji_image

def test():
    print("Testing image generator...")
    try:
        path = generate_omikuji_image(
            user_name="テストユーザー",
            fortune="奇跡 (Miracle)",
            commentary="常識にとらわれてはいけないのですね！今日あなたにはとてつもない奇跡が起こるでしょう。守矢の神々の加護があなたと共にあります！",
            item="緑色の髪飾り",
            action="近くの神社でお祈りをしてから、常識を捨て去る。",
            favorability=350
        )
        print(f"Success! Image generated at: {path}")
        # 画像が存在するか確認
        if os.path.exists(path):
            print(f"File size: {os.path.getsize(path)} bytes")
        else:
            print("File does not exist!")
    except Exception as e:
        print(f"Error occurred during image generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
