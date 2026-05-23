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
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    if "schema.org/InStock" in resp.text:
        return True, "schema.org/InStock"
    if "schema.org/OutOfStock" in resp.text:
        return False, "schema.org/OutOfStock"

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
