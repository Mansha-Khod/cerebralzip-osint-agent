import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_page(url: str, max_chars: int = 3000):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=8, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        return text[:max_chars]
    except Exception as e:
        return f"Could not fetch page : {e}"