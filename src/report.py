import os
from datetime import datetime, UTC
from src.claim_tracker import ClaimTracker

def generate_report(subject: str, subject_type: str, tracker: ClaimTracker, reflection: str) -> str:
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"reports/{subject.replace(' ', '_')}_{timestamp}.md"

    lines = [
        f"# Investigation Report: {subject}",
        f"**Type:** {subject_type}  ",
        f"**Date:** {datetime.now(UTC).isoformat()}  ",
        f"**Confidence Score:** {tracker.confidence()}",
        "",
        "## Evidence",
    ]
    for e in tracker.evidence:
        lines.append(f"- **[{e.relevance}]** {e.source_url}")
        lines.append(f"  > {e.text_snippet[:200]}")
    if not tracker.evidence:
        lines.append("_No usable evidence was found._")

    lines += ["", "## Reflection", reflection]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filename