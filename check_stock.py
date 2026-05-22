import os
import requests
from bs4 import BeautifulSoup
import time

# ── 監視対象 ──────────────────────────────────────────────
PRODUCTS = [
    {
        "name": "CD-30 農機用ディーゼルオイル 4L",
        "url": "https://www.monotaro.com/p/0537/2377/",
    },
    {
        "name": "CD-30 農機用ディーゼルオイル 20L",
        "url": "https://www.monotaro.com/p/0537/2386/",
    },
    {
        "name": "EP-2Kカートリッジグリース 400g×1本",
        "url": "https://www.monotaro.com/p/7019/1845/",
    },
    {
        "name": "EP-2Kカートリッジグリース 400g×20本",
        "url": "https://www.monotaro.com/p/7026/3306/",
    },
]

# ── Pushover（GitHub Secretsから取得）────────────────────
PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
PUSHOVER_USER  = os.environ["PUSHOVER_USER"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── 在庫判定 ──────────────────────────────────────────────
def check_stock(url: str) -> tuple[bool, str]:
    """
    戻り値: (在庫あり=True, 判定根拠テキスト)
    """
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # ① カートボタン（在庫あり）
    cart_btn = soup.find("button", string=lambda t: t and "カートに入れる" in t)
    if cart_btn:
        disabled = cart_btn.get("disabled")
        if disabled is None:
            return True, "カートに入れるボタンが有効"

    # ② 品切れテキスト（在庫なし）
    out_keywords = ["品切れ", "在庫なし", "入荷待ち", "販売終了"]
    for kw in out_keywords:
        if kw in resp.text:
            return False, kw

    # ③ 在庫数テキスト（在庫あり）
    in_keywords = ["在庫あり", "在庫：", "即日出荷"]
    for kw in in_keywords:
        if kw in resp.text:
            return True, kw
    
        # デバッグ：HTML断片を出力
        print("--- HTML断片（デバッグ） ---")
        for kw in ["品切れ", "カート", "在庫", "stock", "cart", "sold"]:
            idx = resp.text.lower().find(kw.lower())
            if idx >= 0:
                print(f"[{kw}] ...{resp.text[max(0,idx-30):idx+50]}...")
        print("--- ここまで ---")
    return False, "判定不明（在庫なしとして扱う）"


# ── Pushover通知 ──────────────────────────────────────────
def notify(title: str, message: str, url: str):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token":   PUSHOVER_TOKEN,
            "user":    PUSHOVER_USER,
            "title":   title,
            "message": message,
            "url":     url,
            "url_title": "MonotaROで開く",
            "priority": 1,   # 高優先度（バイブあり）
        },
        timeout=10,
    )


# ── メイン ────────────────────────────────────────────────
def main():
    print("MonotaRO 在庫チェック開始")
    found_any = False

    for product in PRODUCTS:
        time.sleep(2)  # サーバー負荷軽減
        try:
            in_stock, reason = check_stock(product["url"])
            status = "✅ 在庫あり" if in_stock else "❌ 在庫なし"
            print(f"{status} | {product['name']} | {reason}")

            if in_stock:
                found_any = True
                notify(
                    title=f"🛒 在庫復活: {product['name']}",
                    message=f"MonotaROに在庫が入りました。\n判定: {reason}",
                    url=product["url"],
                )
        except Exception as e:
            print(f"エラー: {product['name']} → {e}")

    if not found_any:
        print("在庫ありの商品なし。通知なし。")


if __name__ == "__main__":
    main()
