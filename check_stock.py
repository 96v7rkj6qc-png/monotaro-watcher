import os
import time
import json
import requests

PRODUCTS_FILE = "products.json"
STATE_FILE = "stock_state.json"

PUSHOVER_TOKEN = os.environ["PUSHOVER_TOKEN"]
PUSHOVER_USER = os.environ["PUSHOVER_USER"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}


def load_products() -> list[dict]:
    if not os.path.exists(PRODUCTS_FILE):
        raise FileNotFoundError(f"{PRODUCTS_FILE} が見つかりません")

    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    if not isinstance(products, list):
        raise ValueError(f"{PRODUCTS_FILE} は配列形式にしてください")

    for product in products:
        if "name" not in product or "url" not in product:
            raise ValueError("各商品には name と url が必要です")

    return products


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

    html = resp.content.decode("utf-8", errors="replace")

    ng_words = [
        "取扱停止中",
        "販売終了",
        "取扱い終了",
        "取扱終了",
        "お取り扱いを終了",
        "現在ご注文頂けません",
        "現在ご注文いただけません",
        "ご注文頂けません",
        "ご注文いただけません",
        "現在お取り扱いできません",
        "注文できません",
        "カートに入れることができません",
        "入荷予定はありません",
    ]

    for word in ng_words:
        if word in html:
            return False, f"注文不可文言: {word}"

    if "schema.org/OutOfStock" in html:
        return False, "schema.org/OutOfStock"

    if "在庫数量" in html:
        return True, "在庫数量あり"

    if "バスケットに入れる" in html:
        return True, "バスケットに入れる"

    if "schema.org/InStock" in html:
        return False, "schema.org/InStockのみ検出・注文可否不明"

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

    products = load_products()
    previous_state = load_state()
    current_state = {}

    notified_any = False

    print(f"監視商品数: {len(products)}件")

    for product in products:
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
                    message=f"MonotaROで注文できる可能性があります。\n判定: {reason}",
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
