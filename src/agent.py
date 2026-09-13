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

BLOCKED_DOMAINS = ["linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com"]

def is_blocked_domain(url: str) -> bool:
    return any(d in url for d in BLOCKED_DOMAINS)


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


def judge_evidence(subject: str, url: str, text: str) -> tuple[str, str]:
    prompt = f"""Subject under investigation: {subject}Text found at {url}:{text[:500]}Does this text refer to the SAME specific entity as "{subject}" (not just a similarly-named company)? Minor formatting differences (e.g. "Pvt Ltd" vs "Private Limited" vs the name alone) do NOT count as a mismatch — but a different registration, location, founding date, or industry suggests a DIFFERENT entity with the same name.Respond ONLY with JSON, no other text:{{"relevance": "supports" or "contradicts" or "irrelevant" or "ambiguous_entity", "reason": "one short sentence"}}"""
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_json_response(response.choices[0].message.content)
        return result["relevance"], result.get("reason", "")
    except (ValueError, KeyError) as e:
        log_step("judgment_error", f"url={url} | {e}")
        return "irrelevant", f"[judgment failed: {e}]"


def investigate(subject: str, max_steps: int = 6) -> ClaimTracker:
    tracker = ClaimTracker(claim=subject)
    findings_log = ""
    seen_urls = set()

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
            if r["url"] in seen_urls:
                continue
            seen_urls.add(r["url"])

            if is_blocked_domain(r["url"]):
                log_step("skip", f"url={r['url']} | known scraper-blocked domain, skipped without fetching")
                continue

            text = fetch_page(r["url"])
            FAILURE_SIGNATURES = ["could not fetch page", "could not be found", "edgesuite.net", "reference #"]
            if not text.strip() or any(sig in text.lower()[:300] for sig in FAILURE_SIGNATURES):
                log_step("skip", f"url={r['url']} | no usable content, excluded from evidence")
                continue

            relevance, reason = judge_evidence(subject, r["url"], text)
            tracker.add_evidence(r["url"], relevance=relevance, snippet=text[:200])
            findings_log += f"\n- From {r['url']}: {text[:200]}"
            log_step("fetch", f"url={r['url']} | relevance={relevance} | reason={reason}")

    reflection = reflect_on_findings(subject, tracker)
    log_step("reflection", reflection)
    return tracker, reflection

def reflect_on_findings(subject: str, tracker: "ClaimTracker") -> str:
    evidence_summary = "\n".join(
        f"- [{e.relevance}] {e.source_url}: {e.text_snippet[:150]}" for e in tracker.evidence
    ) or "(no usable evidence gathered)"
    prompt = f"""Subject investigated: {subject}Evidence gathered:{evidence_summary}Computed confidence: {tracker.confidence()} Critically review this investigation. Is the confidence score well-supported by the evidence, or is it based on too little / too ambiguous / too duplicated data? Note any concerns a human analyst should be aware of before trusting this verdict. Respond in 2-3 plain sentences, no JSON."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    result = investigate("Acme Logistics Pvt Ltd", max_steps=3)
    print("Steps taken, confidence:", result.confidence())
    print("Evidence gathered:", len(result.evidence))
    for e in result.evidence:
        print(f"\n[{e.relevance}] {e.source_url}\n{e.text_snippet[:150]}")
        