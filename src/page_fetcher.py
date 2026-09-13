import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def fetch_page(url: str, max_chars: int = 3000) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=8, verify=False)
    except requests.exceptions.SSLError:
        fallback_url = url.replace("https://", "http://")
        try:
            response = requests.get(fallback_url, headers=HEADERS, timeout=8)
        except Exception as e:
            return f"Could not fetch page : {e}"
    except Exception as e:
        return f"Could not fetch page : {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    text = " ".join(p.get_text() for p in soup.find_all("p"))
    return text[:max_chars]