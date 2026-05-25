import os
import time
import json
import requests

PRODUCTS = [
    {"name": "CD-30 農機用ディーゼルオイル 4L", "url": "https://www.monotaro.com/p/0537/2377/"},
    {"name": "CD-30 農機用ディーゼルオイル 20L", "url": "https://www.monotaro.com/p/0537/2386/"},
    {"name": "EP-2Kカートリッジグリース 400g×1本", "url": "https://www.monotaro.com/p/7019/1845/"},
    {"name": "EP-2Kカートリッジグリース 400g×20本", "url": "https://www.monotaro.com/p/7026/3306/"},
]

STATE_FILE = "stock_state.json"

PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
PUSHOVER_USER = os.environ["PUSHOVER_USER"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


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

    previous_state = load_state()
    current_state = {}

    notified_any = False

    for product in PRODUCTS:
        time.sleep(2)

        name = product["name"]
        url = product["url"]

        try:
            in_stock, reason = check_stock(url)

            current_state[url] = {
                "name": name,
                "in_stock": in_stock,
                "reason": reason,
            }

            status = "✅ 在庫あり" if in_stock else "❌ 在庫なし"
            print(f"{status} | {name} | {reason}")

            previous = previous_state.get(url)
            previous_in_stock = previous.get("in_stock") if previous else None

            if previous_in_stock is None:
                print(f"初回記録のみ | {name} | 通知なし")

            elif previous_in_stock is False and in_stock is True:
                notified_any = True
                print(f"通知対象 | {name} | 在庫なし → 在庫あり")

                notify(
                    title=f"🛒 在庫復活: {name}",
                    message=f"MonotaROに在庫が入りました。\n判定: {reason}",
                    url=url,
                )

            elif previous_in_stock is True and in_stock is True:
                print(f"通知なし | {name} | 前回も在庫あり")

            elif previous_in_stock is True and in_stock is False:
                print(f"在庫切れに変化 | {name} | 在庫あり → 在庫なし")

            else:
                print(f"通知なし | {name} | 前回も在庫なし")

        except Exception as e:
            print(f"エラー: {name} → {e}")

            current_state[url] = previous_state.get(url, {
                "name": name,
                "in_stock": False,
                "reason": f"エラー: {e}",
            })

    save_state(current_state)

    if not notified_any:
        print("今回通知する商品なし。")


if __name__ == "__main__":
    main()
