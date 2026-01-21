import requests

def fetch_top_coins(limit=10):
    """
    Fetch top cryptocurrencies by market cap from CoinGecko API.

    Args:
        limit (int): Number of top coins to fetch. Default is 10.

    Returns:
        list of dicts: Each dict contains 'name', 'symbol', 'price'
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit,
        "page": 1,
        "sparkline": "false"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise error if API fails
        data = response.json()

        coins = []
        for coin in data:
            coins.append({
                "name": coin.get("name"),
                "symbol": coin.get("symbol", "").upper(),
                "price": coin.get("current_price")
            })

        return coins

    except requests.RequestException as e:
        print("ERROR fetching coins:", e)
        return []
