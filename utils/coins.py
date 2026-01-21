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

        r = requests.get(url, params=params, timeout=10)
        data = r.json()   # 👈 Wannan shi ne json()

        coins = []
        for coin in data:
            coins.append({
                "name": coin["name"],
                "symbol": coin["symbol"].upper(),
                "price": coin["current_price"],
                "change": coin["price_change_percentage_24h"]
            })

        return coins

    except Exception as e:
        print("CoinGecko error:", e)
        return []
