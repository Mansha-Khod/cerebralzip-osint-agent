from dotenv import load_dotenv
load_dotenv() 
import argparse
from src.search_tool import search_web
from src.page_fetcher import fetch_page
from src.logger import log_step

def main():
    parser=argparse.ArgumentParser(description="OSINT investigation harness")
    parser.add_argument("--subject",required=True,help='What to investigate')
    parser.add_argument("--type",choices=['company','person','claim'],required=True)# only these three for now fill expand later
    args=parser.parse_args()

    log_step("start", f"Investigating {args.type}: {args.subject}")

    results = search_web(args.subject)
    log_step("search", f"query='{args.subject}' | {len(results)} results")

    for r in results[:3]:
        text = fetch_page(r["url"])
        log_step("fetch", f"url={r['url']} | {len(text)} chars")
        print(f"\n--- {r['title']} ---\n{r['url']}\n{text[:300]}...\n")

if __name__ == "__main__":
    main()