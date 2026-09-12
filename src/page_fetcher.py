import requests
from bs4 import BeautifulSoup

def fetch_page(url:str,max_chars:int=3000):
    try:
        response=requests.get(url,timeout=8)
        soup=BeautifulSoup(response.text,"html.parser")
        text=" ".join(p.get_text() for p in soup.find_all("p"))
        return text[:max_chars]
    except Exception as e:
        return f"Could not fetch page : {e}"
    