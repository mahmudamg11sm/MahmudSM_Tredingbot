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

        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            print("API ERROR:", r.status_code, r.text)
            return None

        data = r.json()

        if not isinstance(data, list):
            print("INVALID DATA:", data)
            return None

        return data

    except Exception as e:
        print("FETCH ERROR:", e)
        return None
