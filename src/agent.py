import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from src.search_tool import search_web
from src.page_fetcher import fetch_page
from src.logger import log_step
from src.claim_tracker import ClaimTracker
from src.memory import get_past_investigation, save_investigation
from src.metrics import InvestigationMetrics, compute_episode_reward

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL_NAME = "openai/gpt-oss-120b"
BLOCKED_DOMAINS = ["linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com"]

FAILURE_SIGNATURES = [
    "could not fetch page", "could not be found", "edgesuite.net", "reference #",
    "all rights reserved", "enable js", "enable javascript", "unsupported browser",
    "install a current version", "click the box below", "not a robot",
    "content is not available in your region", "disable any ad blocker",
]


def is_blocked_domain(url: str) -> bool:
    return any(d in url for d in BLOCKED_DOMAINS)

def is_unusable_content(text: str) -> bool:
    stripped = text.strip()
    if not stripped or len(stripped) < 250:
        return True
    return any(sig in stripped.lower()[:400] for sig in FAILURE_SIGNATURES)

def parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        raise ValueError("Model returned an empty response")
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in: {raw[:200]}")
    return json.loads(raw[start:end + 1])


def _get_tokens(response):
    usage = getattr(response, "usage", None)
    return getattr(usage, "total_tokens", 0) if usage else 0

def decide_next_step(subject: str, findings_so_far: str) -> tuple[dict, int]:
    prompt = f"""You are investigating: {subject}Findings gathered so far:{findings_so_far if findings_so_far else "(nothing yet)"}
    Respond ONLY with JSON, no other text:{{"action": "search" or "conclude", "query": "next search query if action is search, else empty string", "reason": "why"}}"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return parse_json_response(response.choices[0].message.content), _get_tokens(response)


def judge_evidence(subject: str, url: str, text: str) -> tuple[str, str, int]:
    prompt = f"""Subject under investigation: {subject}Text found at {url}:{text[:500]}
    Does this text refer to the SAME specific entity as "{subject}" (not just a similarly-named company)? Minor formatting differences (e.g. "Pvt Ltd" vs "Private Limited" vs the name alone) do NOT count as a mismatch — but a different registration, location, founding date, or industry suggests a DIFFERENT entity with the same name.

    Respond ONLY with JSON, no other text:
    {{"relevance": "supports" or "contradicts" or "irrelevant" or "ambiguous_entity", "reason": "one short sentence"}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
        result = parse_json_response(response.choices[0].message.content)
        return result["relevance"], result.get("reason", ""), _get_tokens(response)
    except (ValueError, KeyError) as e:
        log_step("judgment_error", f"url={url} | {e}")
        return "irrelevant", f"[judgment failed: {e}]", 0

def write_narrative(subject: str, subject_type: str, tracker: ClaimTracker) -> tuple[str, int]:
    supporting = [e for e in tracker.evidence if e.relevance == "supports"]
    contradicting = [e for e in tracker.evidence if e.relevance == "contradicts"]
    excluded = [e for e in tracker.evidence if e.relevance in ("irrelevant", "ambiguous_entity")]

    evidence_block = "\n".join(
        f"- [{e.relevance}] {e.source_url}: {e.text_snippet[:300]}" for e in tracker.evidence
    ) or "(no usable evidence)"

    prompt = f"""You are writing the findings section of an investigation report for a human analyst.
    Subject: {subject} (type: {subject_type})
    Verdict so far: {tracker.verdict()}, confidence: {tracker.confidence()}
    Evidence gathered:
    {evidence_block}

    Write a plain-English findings narrative in exactly three short paragraphs:
    1. What was investigated and the overall conclusion, in one or two sentences.
    2. What the evidence actually shows, synthesizing the supporting and contradicting points together (not just restating each source) — {len(supporting)} sources support, {len(contradicting)} contradict.
    3. What could NOT be verified or was excluded, and why that matters ({len(excluded)} sources were excluded as irrelevant/ambiguous).

    Do not use bullet points. Do not repeat raw URLs. Write as a human analyst would."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip(), _get_tokens(response)


def reflect_on_findings(subject: str, tracker: ClaimTracker) -> tuple[str, int]:
    evidence_summary = "\n".join(
        f"- [{e.relevance}] {e.source_url}: {e.text_snippet[:150]}" for e in tracker.evidence
    ) or "(no usable evidence gathered)"

    prompt = f"""Subject investigated: {subject}
    Evidence gathered:
    {evidence_summary}
    Computed verdict: {tracker.verdict()}, confidence: {tracker.confidence()}

    Critically review this investigation. Is the confidence score well-supported by the evidence, or is it based on too little / too ambiguous / too duplicated data? Note any concerns a human analyst should be aware of before trusting this verdict.

    Respond in 2-3 plain sentences, no JSON."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip(), _get_tokens(response)


def investigate(subject: str, subject_type: str = "claim", max_steps: int = 6, use_memory: bool = True):
    tracker = ClaimTracker(claim=subject)
    findings_log = ""
    seen_urls = set()
    metrics = InvestigationMetrics()
    start_time = time.time()

    if use_memory:
        past = get_past_investigation(subject)
        if past:
            findings_log += (f"\n[MEMORY] A prior investigation on {past['timestamp']} "
                              f"reached confidence={past['confidence']}. Summary: {past['summary']}")
            log_step("memory_recall", f"subject={subject} | prior_confidence={past['confidence']}")

    steps_used = 0
    for step in range(max_steps):
        steps_used = step + 1
        decision, tok = decide_next_step(subject, findings_log)
        metrics.total_tokens += tok
        log_step("decision", json.dumps(decision))

        if decision["action"] == "conclude":
            if not tracker.evidence:
                log_step("forced_continue", "Model tried to conclude with zero evidence gathered; forcing at least one search")
                decision["action"] = "search"
                decision["query"] = subject
            else:
                log_step("stop", decision["reason"])
                break
        query = decision["query"]
        results = search_web(query)
        metrics.tool_calls += 1
        log_step("search", f"query='{query}' | {len(results)} results")

        for r in results[:3]:
            if r["url"] in seen_urls:
                continue
            seen_urls.add(r["url"])

            if is_blocked_domain(r["url"]):
                log_step("skip", f"url={r['url']} | known scraper-blocked domain, skipped without fetching")
                continue

            text = fetch_page(r["url"])
            metrics.tool_calls += 1

            if is_unusable_content(text):
                log_step("skip", f"url={r['url']} | no usable content, excluded from evidence")
                continue

            relevance, reason, tok = judge_evidence(subject, r["url"], text)
            metrics.total_tokens += tok
            tracker.add_evidence(r["url"], relevance=relevance, snippet=text[:400])
            findings_log += f"\n- From {r['url']}: {text[:200]}"
            log_step("fetch", f"url={r['url']} | relevance={relevance} | reason={reason}")

        metrics.confidence_progression.append(tracker.confidence())

    narrative, tok = write_narrative(subject, subject_type, tracker)
    metrics.total_tokens += tok
    log_step("narrative", narrative)

    reflection, tok = reflect_on_findings(subject, tracker)
    metrics.total_tokens += tok

    metrics.steps_taken = steps_used
    metrics.latency_seconds = round(time.time() - start_time, 2)
    metrics.final_confidence = tracker.confidence()
    metrics.reward = compute_episode_reward(metrics)

    log_step("reflection", reflection)
    log_step("metrics", json.dumps(metrics.__dict__))

    if use_memory:
        save_investigation(subject, tracker.confidence(), reflection[:300])

    return tracker, reflection, narrative, metrics