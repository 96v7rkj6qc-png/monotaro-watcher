import os
import time
import requests

PRODUCTS = [
    {"name": "CD-30 農機用ディーゼルオイル 4L", "url": "https://www.monotaro.com/p/0537/2377/"},
    {"name": "CD-30 農機用ディーゼルオイル 20L", "url": "https://www.monotaro.com/p/0537/2386/"},
    {"name": "EP-2Kカートリッジグリース 400g×1本", "url": "https://www.monotaro.com/p/7019/1845/"},
    {"name": "EP-2Kカートリッジグリース 400g×20本", "url": "https://www.monotaro.com/p/7026/3306/"},
]

PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
PUSHOVER_USER = os.environ["PUSHOVER_USER"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def check_stock(url: str) -> tuple[bool, str]:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    html = resp.text

    if "schema.org/OutOfStock" in html:
        return False, "schema.org/OutOfStock"

    if "schema.org/InStock" in html:
        return True, "schema.org/InStock"

    return False, "判定不明（在庫なしとして扱う）"


def notify(title: str, message: str, url: str) -> None:
    resp = requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "title": title,
            "message": message,
            "url": url,
            "url_title": "MonotaROで開く",
            "priority": 1,
        },
        timeout=10,
    )
    resp.raise_for_status()


def main() -> None:
    print("MonotaRO 在庫チェック開始")

    found_any = False

    for product in PRODUCTS:
        time.sleep(2)

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
