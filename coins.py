import requests

def fetch_top_coins(limit=10):
    try:
        url = "https://min-api.cryptocompare.com/data/top/mktcapfull"
        params = {
            "limit": limit,
            "tsym": "USD"
        }

        r = requests.get(url, params=params, timeout=20)

        print("CryptoCompare status:", r.status_code)

        if r.status_code != 200:
            print("CryptoCompare error:", r.text)
            return []

        data = r.json()

        if "Data" not in data:
            print("Bad response:", data)
            return []

        coins = []

        for c in data["Data"]:
            info = c["CoinInfo"]
            raw = c["RAW"]["USD"]

            coins.append({
                "name": info["Name"],
                "symbol": info["FullName"],
                "price": raw["PRICE"],
                "change": raw["CHANGEPCT24HOUR"]
            })

        print("Loaded coins:", coins[:2])

        return coins

    except Exception as e:
        print("ERROR in fetch_top_coins:", e)
        return []
