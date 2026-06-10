import os
import requests
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "assets/fonts"
FONT_PATH = os.path.join(FONT_DIR, "SawarabiMincho-Regular.ttf")
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/sawarabimincho/SawarabiMincho-Regular.ttf"

def ensure_font():
    """フォントファイルをダウンロードして保存する。失敗した場合は例外を投げる。"""
    if not os.path.exists(FONT_PATH):
        os.makedirs(FONT_DIR, exist_ok=True)
        print("Sawarabi Minchoフォントをダウンロード中...")
        response = requests.get(FONT_URL, timeout=10)
        if response.status_code == 200:
            with open(FONT_PATH, "wb") as f:
                f.write(response.content)
            print("フォントダウンロード完了。")
        else:
            raise Exception(f"HTTP Error: {response.status_code}")
    return FONT_PATH

def get_font(size):
    """フォントオブジェクトを取得する (自動的にフォールバックを実行)"""
    try:
        ensure_font()
        return ImageFont.truetype(FONT_PATH, size)
    except Exception as e:
        print(f"フォントダウンロードまたは読み込みに失敗しました: {e}。システムフォントを使用します。")
        # Windowsの日本語標準フォントを探索
        for fallback in [
            "C:\\Windows\\Fonts\\msmincho.ttc",
            "C:\\Windows\\Fonts\\msgothic.ttc",
            "C:\\Windows\\Fonts\\yumin.ttf",
            "arial.ttf"
        ]:
            if os.path.exists(fallback):
                try:
                    return ImageFont.truetype(fallback, size)
                except Exception as ex:
                    print(f"フォールバックフォント {fallback} の読み込み失敗: {ex}")
                    continue
        return ImageFont.load_default()

def wrap_text(text, font, max_width, draw):
    """テキストを指定されたピクセル幅に収まるように折り返す"""
    lines = []
    current_line = ""
    for char in text:
        if char == "\n":
            lines.append(current_line)
            current_line = ""
            continue
            
        test_line = current_line + char
        # draw.textlength は Pillow 10+ で利用可能
        width = draw.textlength(test_line, font=font)
        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines

def generate_omikuji_image(user_name: str, fortune: str, commentary: str, item: str, action: str, favorability: int) -> str:
    """おみくじ画像を生成し、その一時ファイルパスを返す"""
    # 画像サイズ: 480 x 760
    width = 480
    height = 760
    
    # 背景色: 和風の鳥の子色 (クリームっぽい白)
    bg_color = (252, 248, 242)
    # 早苗のテーマカラー: 深い緑 (常磐色)
    sanae_green = (15, 125, 66)
    # 早苗のセカンドカラー: 深い青 (瑠璃色)
    sanae_blue = (27, 49, 94)
    # ゴールド/ベージュのアクセント
    gold_color = (212, 175, 55)
    # 文字色: 墨色
    text_color = (30, 30, 30)
    
    # 新しい画像を作成
    image = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # 外枠の描画 (二重枠)
    # 外側の緑の枠
    draw.rectangle([10, 10, width - 10, height - 10], outline=sanae_green, width=3)
    # 内側のゴールドの枠
    draw.rectangle([16, 16, width - 16, height - 16], outline=gold_color, width=1)
    
    # フォントの読み込み
    font_title = get_font(32)
    font_subtitle = get_font(18)
    font_body = get_font(16)
    font_bold = get_font(18)
    
    # 1. ヘッダー (守矢神社おみくじ)
    header_text = "守谷神社 奇跡のおみくじ"
    header_w = draw.textlength(header_text, font=font_title)
    draw.text(((width - header_w) // 2, 35), header_text, font=font_title, fill=sanae_green)
    
    # 仕切り線 (波線か二重線)
    draw.line([30, 85, width - 30, 85], fill=gold_color, width=2)
    
    # 2. ユーザー名と日付
    import datetime
    today = datetime.date.today().strftime("%Y年%m月%d日")
    user_info = f"参拝者: {user_name} 殿   ({today})"
    user_info_w = draw.textlength(user_info, font=font_subtitle)
    draw.text(((width - user_info_w) // 2, 100), user_info, font=font_subtitle, fill=sanae_blue)
    
    # 3. 運勢表示エリア (大きな木札風)
    # 木札の背景 (左右のマージンを120pxに広げて幅を確保)
    wood_bg = (245, 235, 220)
    draw.rectangle([120, 140, width - 120, 230], fill=wood_bg, outline=sanae_green, width=2)
    
    # 運勢テキストの長さによってフォントサイズと描画高さを動的に変更
    fortune_len = len(fortune)
    if fortune_len >= 5:
        font_fortune = get_font(24)
        fortune_y = 170
    elif fortune_len >= 4:
        font_fortune = get_font(32)
        fortune_y = 165
    else:
        font_fortune = get_font(48)
        fortune_y = 152
        
    # 運勢テキストの描画
    fortune_w = draw.textlength(fortune, font=font_fortune)
    draw.text(((width - fortune_w) // 2, fortune_y), fortune, font=font_fortune, fill=(180, 20, 20) if "凶" in fortune else sanae_green)
    
    # 4. 早苗の託宣 (コメント)
    draw.line([30, 250, width - 30, 250], fill=gold_color, width=1)
    
    oracle_title = "◆ 早苗の託宣"
    draw.text((40, 265), oracle_title, font=font_bold, fill=sanae_blue)
    
    # 右端マージン(435px)に収まるよう折り返し幅を390pxに制限 (開始位置45px)
    wrapped_commentary = wrap_text(commentary, font_body, 390, draw)
    y_cursor = 295
    for line in wrapped_commentary:
        draw.text((45, y_cursor), line, font=font_body, fill=text_color)
        y_cursor += 24
        
    # 5. ラッキー項目
    y_cursor = max(y_cursor + 15, 390)
    draw.line([30, y_cursor, width - 30, y_cursor], fill=gold_color, width=1)
    
    y_cursor += 15
    draw.text((40, y_cursor), "◆ 幸運の導き", font=font_bold, fill=sanae_blue)
    
    y_cursor += 30
    draw.text((45, y_cursor), "ラッキーアイテム:", font=font_body, fill=sanae_green)
    draw.text((180, y_cursor), item, font=font_body, fill=text_color)
    
    y_cursor += 30
    draw.text((45, y_cursor), "ラッキーアクション:", font=font_body, fill=sanae_green)
    # 右端マージン(435px)に収まるよう折り返し幅を240pxに制限 (開始位置195px)
    wrapped_action = wrap_text(action, font_body, 240, draw)
    for i, line in enumerate(wrapped_action):
        draw.text((195, y_cursor + (i * 22)), line, font=font_body, fill=text_color)
    
    # 6. 好感度 (信仰度)
    y_cursor = max(y_cursor + len(wrapped_action) * 22 + 15, 560)
    draw.line([30, y_cursor, width - 30, y_cursor], fill=gold_color, width=1)
    
    y_cursor += 15
    draw.text((40, y_cursor), "◆ 守矢の信仰度 (早苗の好感度)", font=font_bold, fill=sanae_blue)
    
    # 信仰度ゲージ
    gauge_max_w = width - 100
    gauge_y = y_cursor + 35
    draw.rectangle([50, gauge_y, 50 + gauge_max_w, gauge_y + 15], outline=sanae_green, width=1)
    
    # ゲージの中身 (好感度は最大1000として割合を描画、最低でも少し表示)
    favorability_clamped = max(0, min(1000, favorability))
    # 枠線の内側に収まるように幅を設定 (左右マージン2pxずつ引く)
    gauge_inner_max_w = gauge_max_w - 4
    gauge_fill_w = int(gauge_inner_max_w * (favorability_clamped / 1000))
    if favorability_clamped > 0 and gauge_fill_w == 0:
        gauge_fill_w = 1
    if gauge_fill_w > 0:
        draw.rectangle([52, gauge_y + 2, 52 + gauge_fill_w, gauge_y + 13], fill=sanae_green)
        
    draw.text((50, gauge_y + 22), f"信仰値: {favorability_clamped} / 1000", font=font_body, fill=text_color)
    
    # 7. フッター
    draw.line([30, height - 60, width - 30, height - 60], fill=gold_color, width=1)
    footer_text = "※常識に囚われない奇跡をあなたに。"
    footer_w = draw.textlength(footer_text, font=font_body)
    draw.text(((width - footer_w) // 2, height - 45), footer_text, font=font_body, fill=sanae_blue)
    
    # 保存
    os.makedirs("data/temp", exist_ok=True)
    temp_path = os.path.join("data/temp", f"omikuji_{user_name}_{int(datetime.datetime.now().timestamp())}.png")
    image.save(temp_path)
    return temp_path
