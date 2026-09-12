import os
import json
from groq import Groq

from dotenv import load_dotenv  # 1. Move this import up here

load_dotenv()  

from src.search_tool import search_web
from src.page_fetcher import fetch_page
from src.logger import log_step
from src.claim_tracker import ClaimTracker

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def decide_next_step(subject: str, findings_so_far: str) -> dict:
    prompt = f"""You are investigating: {subject}
Findings gathered so far:
{findings_so_far if findings_so_far else "(nothing yet)"}

Respond ONLY with JSON, no other text: {{"action": "search" or "conclude", "query": "next search query if action is search, else empty string", "reason": "why"}}"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)

def investigate(subject: str, max_steps: int = 6) -> ClaimTracker:
    tracker = ClaimTracker(claim=subject)
    findings_log = ""

    for step in range(max_steps):
        decision = decide_next_step(subject, findings_log)
        log_step("decision", json.dumps(decision))

        if decision["action"] == "conclude":
            log_step("stop", decision["reason"])
            break

        query = decision["query"]
        results = search_web(query)
        log_step("search", f"query='{query}' | {len(results)} results")

        for r in results[:2]:
            text = fetch_page(r["url"])
            tracker.add_evidence(r["url"], supports=True, snippet=text[:200])
            findings_log += f"\n- From {r['url']}: {text[:200]}"
            log_step("fetch", f"url={r['url']}")

    return tracker

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = investigate("Acme Logistics Pvt Ltd", max_steps=3)
    print("Steps taken, confidence:", result.confidence())
    print("Evidence gathered:", len(result.evidence))