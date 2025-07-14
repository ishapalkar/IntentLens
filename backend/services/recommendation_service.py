import requests

def get_recommendations(items, token):
    headers = {"Authorization": f"Bearer {token}"}
    recommendations = {}

    for item in items:
        if not item.strip():
            continue
        query = item.replace(" ", "+")
        url = f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={query}"
        res = requests.get(url, headers=headers)

        if res.status_code == 200:
            results = res.json().get("itemSummaries", [])[:3]
            recommendations[item] = [{
                "title": r.get("title"),
                "price": r.get("price", {}).get("value"),
                "link": r.get("itemWebUrl")
            } for r in results if "title" in r and "price" in r]

    return recommendations
