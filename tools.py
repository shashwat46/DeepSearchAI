from scraper import scrape_github_profile
import os
import requests


def get_real_github_data(username: str) -> dict:
    print(f"TOOL: Scraping GitHub for {username}…")
    profile = scrape_github_profile(username)
    return {
        "source": "GitHub",
        "raw_data": profile.model_dump(),
    }


def get_phone_number_info(phone_number: str) -> dict:
    print(f"TOOL: Querying Numverify API for {phone_number}…")
    api_key = os.getenv("NUMVERIFY_API_KEY")
    if not api_key:
        return {"source": "Numverify", "raw_data": {"error": "API key not configured."}}

    url = f"http://apilayer.net/api/validate?access_key={api_key}&number={phone_number}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return {"source": "Numverify", "raw_data": resp.json()}
    except Exception as e:
        return {"source": "Numverify", "raw_data": {"error": str(e)}}
