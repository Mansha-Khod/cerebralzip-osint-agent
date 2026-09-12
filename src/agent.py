import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from src.search_tool import search_web
from src.page_fetcher import fetch_page
from src.logger import log_step
from src.claim_tracker import ClaimTracker

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "openai/gpt-oss-120b"


def parse_json_response(raw: str) :
    raw = raw.strip()
    if not raw:
        raise ValueError("Model returned an empty response")
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in: {raw[:200]}")
    return json.loads(raw[start:end + 1])


def decide_next_step(subject: str, findings_so_far: str) -> dict:
    prompt = f"""You are Investigating: {subject}
Findings gathered so far:
{findings_so_far if findings_so_far else "(nothing yet)"}
Respond ONLY with JSON, no other text:
{{"action": "search" or "conclude", "query": "next search query if action is search, else empty string", "reason": "why"}}"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_json_response(response.choices[0].message.content)


def judge_evidence(subject: str, url: str, text: str) -> str:
    prompt = f"""Subject under investigation: {subject}Text found at {url}:{text[:500]}

Does this text actually mention or provide information about "{subject}" specifically?
Respond ONLY with JSON, no other text:
{{"relevance": "supports" or "contradicts" or "irrelevant", "reason": "one short sentence"}}"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    result = parse_json_response(response.choices[0].message.content)
    return result["relevance"]


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

             if not text.strip() or text.startswith("Could not fetch page"):
                log_step("skip", f"url={r['url']} | no usable content, excluded from evidence")
                continue

             relevance = judge_evidence(subject, r["url"], text)
             tracker.add_evidence(r["url"], relevance=relevance, snippet=text[:200])
             findings_log += f"\n- From {r['url']}: {text[:200]}"
             log_step("fetch", f"url={r['url']} | relevance={relevance}")

    return tracker


if __name__ == "__main__":
    result = investigate("Acme Logistics Pvt Ltd", max_steps=3)
    print("Steps taken, confidence:", result.confidence())
    print("Evidence gathered:", len(result.evidence))
    for e in result.evidence:
        print(f"\n[{e.supports}] {e.source_url}\n{e.text_snippet[:150]}")