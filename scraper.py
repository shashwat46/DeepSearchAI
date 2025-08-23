import requests
from bs4 import BeautifulSoup
from schemas import ProfileData

def scrape_github_profile(username: str) -> ProfileData:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(f'https://github.com/{username}', headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        name_elem = soup.select_one('[itemprop="name"]')
        bio_elem = soup.select_one('[data-bio-text]')
        location_elem = soup.select_one('[itemprop="homeLocation"]')
        
        followers_elem = soup.select_one('a[href$="/followers"] .text-bold')
        following_elem = soup.select_one('a[href$="/following"] .text-bold')
        
        return ProfileData(
            name=name_elem.get_text(strip=True) if name_elem else None,
            bio=bio_elem.get_text(strip=True) if bio_elem else None,
            location=location_elem.get_text(strip=True) if location_elem else None,
            followers=int(followers_elem.get_text().replace(',', '')) if followers_elem else None,
            following=int(following_elem.get_text().replace(',', '')) if following_elem else None
        )
    
    except Exception:
        return ProfileData()