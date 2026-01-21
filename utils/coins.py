import requests

def fetch_top_coins():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"

        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 5,
            "page": 1,
            "sparkline": "false"
        }

        headers = {
            "User-Agent": "Mozilla/5.0"  # <-- yana taimaka wa Render kada API ta ƙi request
        }

        r = requests.get(url, params=params, headers=headers, timeout=15)

        if r.status_code != 200:
            print("API ERROR:", r.status_code, r.text)
            return None

        data = r.json()

        if not isinstance(data, list) or len(data) == 0:
            print("INVALID DATA:", data)
            return None

        # Mun rage data zuwa abubuwan da muke bukata
        coins = []
        for coin in data:
            coins.append({
                "name": coin.get("name"),
                "symbol": coin.get("symbol"),
                "price": coin.get("current_price"),  # ✅ GASKIYAR FIELD
                "market_cap": coin.get("market_cap")
            })

        return coins

    except Exception as e:
        print("FETCH ERROR:", e)
        return None
