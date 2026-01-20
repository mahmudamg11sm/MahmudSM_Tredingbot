import requests

def fetch_top_coins(limit=10):
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false"
        }

        r = requests.get(url, params=params, timeout=20)

        if r.status_code != 200:
            print("CoinGecko error:", r.status_code, r.text)
            return []

        data = r.json()

        coins = []
        for c in data:
            coins.append({
                "name": c.get("name"),
                "symbol": c.get("symbol", "").upper(),
                "price": c.get("current_price"),
                "change": c.get("price_change_percentage_24h")
            })

        return coins

    except Exception as e:
        print("ERROR in fetch_top_coins:", e)
        return []
