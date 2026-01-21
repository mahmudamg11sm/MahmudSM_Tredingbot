# utils/coins.py

def fetch_top_coins(limit=10):
    # Dummy data for testing (no API)
    coins = [
        {"name": "Bitcoin", "symbol": "BTC", "price": 65000, "change": 1.2},
        {"name": "Ethereum", "symbol": "ETH", "price": 3500, "change": -0.5},
        {"name": "BNB", "symbol": "BNB", "price": 600, "change": 0.3},
        {"name": "Solana", "symbol": "SOL", "price": 150, "change": 2.1},
        {"name": "XRP", "symbol": "XRP", "price": 0.6, "change": -1.0},
    ]

    return coins[:limit]
