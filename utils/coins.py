import requests

def fetch_top_coins(limit=5):
    """
    Fetch top crypto coins by market cap from CoinGecko API
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": False
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        coins = []
        for coin in data:
            coins.append({
                "name": coin["name"],
                "symbol": coin["symbol"].upper(),
                "price": coin["current_price"]
            })
        return coins

    except requests.RequestException as e:
        print("Error fetching coins:", e)
        return []
