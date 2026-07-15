"""API key validation against Finnhub's REST API."""
import httpx

QUOTE_URL = "https://finnhub.io/api/v1/quote"


async def check_api_key(key: str) -> tuple[bool, str]:
    key = (key or "").strip()
    if not key:
        return False, "API key is empty."

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(QUOTE_URL, params={"symbol": "AAPL", "token": key})
    except Exception as e:
        return False, f"Could not reach Finnhub: {e}"

    if resp.status_code == 401:
        return False, "Invalid API key (Finnhub rejected it)."
    if resp.status_code == 429:
        return False, "Finnhub rate limit hit — the key may still be valid, try again shortly."
    if resp.status_code != 200:
        return False, f"Finnhub returned an unexpected error (HTTP {resp.status_code})."

    data = resp.json()
    if isinstance(data, dict) and "c" in data:
        return True, "API key is valid and working."
    return False, "Unexpected response from Finnhub."
