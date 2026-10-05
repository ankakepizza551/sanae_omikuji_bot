import functools
import io
import os
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from utils.database import get_today

FONT_DIR = "assets/fonts"
# 先頭のフォントを基本とし、収録されていない文字だけ後ろのフォントで補う
# (Sawarabi Minchoは「賽」「祓」や半角カナ、一部の漢字、絵文字を収録していないため)
FONT_FILES = [
    "SawarabiMincho-Regular.ttf",
    "NotoSerifJP-Regular.otf",
    "NotoEmoji.ttf",
]
# 単独では描画しない文字 (絵文字の異体字セレクタ・結合子)
INVISIBLE_CHARS = {"︎", "️", "‍"}

@functools.lru_cache(maxsize=None)
def _charsets():
    """各フォントが収録している文字コードの集合"""
    charsets = []
    for name in FONT_FILES:
        font = TTFont(os.path.join(FONT_DIR, name), lazy=True)
        charsets.append(frozenset(font.getBestCmap()))
        font.close()
    return charsets

@functools.lru_cache(maxsize=None)
def _font(index: int, size: int):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONT_FILES[index]), size)

def _split_runs(text: str):
    """テキストを、同じフォントで描ける文字のまとまりに分割する"""
    charsets = _charsets()
    runs = []
    for char in text:
        if char in INVISIBLE_CHARS:
            continue
        # どのフォントにも無い文字は基本フォントに任せる (豆腐になる)
        index = next((i for i, chars in enumerate(charsets) if ord(char) in chars), 0)
        if runs and runs[-1][0] == index:
            runs[-1][1] += char
        else:
            runs.append([index, char])
    return runs

def text_length(draw, text: str, size: int) -> float:
    """テキストの描画幅を返す"""
    return sum(draw.textlength(chunk, font=_font(index, size)) for index, chunk in _split_runs(text))

def draw_text(draw, xy, text: str, size: int, fill):
    """テキストを描画する。xyは基本フォントで描いた場合の左上の座標"""
    x, y = xy
    # フォントごとに字の高さが違うので、基本フォントのベースラインに揃える
    baseline = y + _font(0, size).getmetrics()[0]
    for index, chunk in _split_runs(text):
        font = _font(index, size)
        draw.text((x, baseline), chunk, font=font, fill=fill, anchor="ls")
        x += draw.textlength(chunk, font=font)

def wrap_text(text, size, max_width, draw):
    """テキストを指定されたピクセル幅に収まるように折り返す"""
    lines = []
    current_line = ""
    for char in text:
        if char == "\n":
            lines.append(current_line)
            current_line = ""
            continue

        test_line = current_line + char
        width = text_length(draw, test_line, size)
        if width <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines

def generate_omikuji_image(user_name: str, fortune: str, commentary: str, item: str, action: str, favorability: int) -> io.BytesIO:
    """おみくじ画像を生成し、PNGデータを返す"""
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

    # フォントサイズ
    size_title = 32
    size_subtitle = 18
    size_body = 16
    size_bold = 18

    # 1. ヘッダー (守矢神社おみくじ)
    header_text = "守矢神社 奇跡のおみくじ"
    header_w = text_length(draw, header_text, size_title)
    draw_text(draw, ((width - header_w) // 2, 35), header_text, size_title, sanae_green)

    # 仕切り線 (波線か二重線)
    draw.line([30, 85, width - 30, 85], fill=gold_color, width=2)

    # 2. ユーザー名と日付
    today = get_today().strftime("%Y年%m月%d日")
    user_info = f"参拝者: {user_name} 殿   ({today})"
    user_info_w = text_length(draw, user_info, size_subtitle)
    # 長い名前は枠内に収まるまで末尾を省略する
    shown_name = user_name
    while user_info_w > width - 60 and len(shown_name) > 1:
        shown_name = shown_name[:-1]
        user_info = f"参拝者: {shown_name}… 殿   ({today})"
        user_info_w = text_length(draw, user_info, size_subtitle)
    draw_text(draw, ((width - user_info_w) // 2, 100), user_info, size_subtitle, sanae_blue)

    # 3. 運勢表示エリア (大きな木札風)
    # 木札の背景 (左右のマージンを120pxに広げて幅を確保)
    wood_bg = (245, 235, 220)
    draw.rectangle([120, 140, width - 120, 230], fill=wood_bg, outline=sanae_green, width=2)

    # 運勢テキストの長さによってフォントサイズと描画高さを動的に変更
    fortune_len = len(fortune)
    if fortune_len >= 5:
        size_fortune = 24
        fortune_y = 170
    elif fortune_len >= 4:
        size_fortune = 32
        fortune_y = 165
    else:
        size_fortune = 48
        fortune_y = 152

    # 運勢テキストの描画
    fortune_w = text_length(draw, fortune, size_fortune)
    draw_text(draw, ((width - fortune_w) // 2, fortune_y), fortune, size_fortune, (180, 20, 20) if "凶" in fortune else sanae_green)

    # 4. 早苗の託宣 (コメント)
    draw.line([30, 250, width - 30, 250], fill=gold_color, width=1)

    oracle_title = "◆ 早苗の託宣"
    draw_text(draw, (40, 265), oracle_title, size_bold, sanae_blue)

    # 右端マージン(435px)に収まるよう折り返し幅を390pxに制限 (開始位置45px)
    wrapped_commentary = wrap_text(commentary, size_body, 390, draw)
    y_cursor = 295
    for line in wrapped_commentary:
        draw_text(draw, (45, y_cursor), line, size_body, text_color)
        y_cursor += 24

    # 5. ラッキー項目
    y_cursor = max(y_cursor + 15, 390)
    draw.line([30, y_cursor, width - 30, y_cursor], fill=gold_color, width=1)

    y_cursor += 15
    draw_text(draw, (40, y_cursor), "◆ 幸運の導き", size_bold, sanae_blue)

    y_cursor += 30
    draw_text(draw, (45, y_cursor), "ラッキーアイテム:", size_body, sanae_green)
    draw_text(draw, (180, y_cursor), item, size_body, text_color)

    y_cursor += 30
    draw_text(draw, (45, y_cursor), "ラッキーアクション:", size_body, sanae_green)
    # 右端マージン(435px)に収まるよう折り返し幅を240pxに制限 (開始位置195px)
    wrapped_action = wrap_text(action, size_body, 240, draw)
    for i, line in enumerate(wrapped_action):
        draw_text(draw, (195, y_cursor + (i * 22)), line, size_body, text_color)

    # 6. 好感度 (信仰度)
    y_cursor = max(y_cursor + len(wrapped_action) * 22 + 15, 560)
    draw.line([30, y_cursor, width - 30, y_cursor], fill=gold_color, width=1)

    y_cursor += 15
    draw_text(draw, (40, y_cursor), "◆ 守矢の信仰度 (早苗の好感度)", size_bold, sanae_blue)

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

    draw_text(draw, (50, gauge_y + 22), f"信仰値: {favorability_clamped} / 1000", size_body, text_color)

    # 7. フッター
    draw.line([30, height - 60, width - 30, height - 60], fill=gold_color, width=1)
    footer_text = "※常識に囚われない奇跡をあなたに。"
    footer_w = text_length(draw, footer_text, size_body)
    draw_text(draw, ((width - footer_w) // 2, height - 45), footer_text, size_body, sanae_blue)

    # PNGとしてメモリ上に書き出す
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
