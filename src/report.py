import os
from datetime import datetime, UTC
from urllib.parse import urlparse
from src.claim_tracker import ClaimTracker, source_reliability

def generate_report(subject: str, subject_type: str, tracker: ClaimTracker,
                     reflection: str, narrative: str, metrics) -> str:
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"reports/{subject.replace(' ', '_')}_{timestamp}.md"

    lines = [
        f"# Investigation Report: {subject}",
        f"**Type:** {subject_type}  ",
        f"**Date:** {datetime.now(UTC).isoformat()}  ",
        f"**Verdict:** {tracker.verdict()}  ",
        f"**Confidence Score:** {tracker.confidence()}",
        "",
        "## Findings",
        narrative,
        "",
        "## Analyst Notes on Confidence",
        reflection,
        "",
        f"## Evidence Log ({len(tracker.evidence)} usable sources)",
    ]
    for e in tracker.evidence:
        reliability = source_reliability(e.source_url)
        lines.append(f"- **[{e.relevance}]** (reliability: {reliability}) {e.source_url}")
        lines.append(f"  > {e.text_snippet[:400]}")
    if not tracker.evidence:
        lines.append("_No usable evidence was found._")
    unique_domains = len(set(urlparse(e.source_url).netloc.lower().replace("www.", "") for e in tracker.evidence))
    lines += [
        "",
        "## Investigation Metrics",
        f"- Steps taken: {metrics.steps_taken}",
        f"- Tool calls: {metrics.tool_calls}",
        f"- Total tokens used: {metrics.total_tokens}",
        f"- Latency: {metrics.latency_seconds}s",
        f"- Total evidence sources: {len(tracker.evidence)}",
        f"- Unique domains among sources: {unique_domains}",
        f"- Confidence progression across steps: {metrics.confidence_progression}",
        f"- Converged: {metrics.converged}",
        f"- Episode reward: {metrics.reward}",
    ]
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filename