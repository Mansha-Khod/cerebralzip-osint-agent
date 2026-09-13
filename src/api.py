from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from src.agent import investigate
from src.report import generate_report

app = FastAPI(title="OSINT Investigation Harness")


class InvestigateRequest(BaseModel):
    subject: str
    subject_type: str


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html><head><style>
        body { font-family: -apple-system, sans-serif; max-width: 640px; margin: 60px auto; padding: 0 20px; color: #1a1a1a; }
        h2 { font-weight: 600; }
        input, select, button { font-size: 15px; padding: 10px; border-radius: 6px; border: 1px solid #ccc; }
        input { width: 100%; box-sizing: border-box; margin-bottom: 12px; }
        button { background: #1a1a1a; color: white; border: none; cursor: pointer; margin-top: 12px; }
        button:hover { background: #333; }
        #result { margin-top: 24px; }
        .card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
        .verdict { font-size: 18px; font-weight: 600; text-transform: capitalize; }
        .supported { color: #16794c; } .contradicted { color: #b3261e; }
        .inconclusive, .insufficient_evidence { color: #8a6d00; }
        .label { font-size: 12px; color: #777; text-transform: uppercase; letter-spacing: 0.05em; }
        .evidence-item { border-left: 3px solid #ddd; padding-left: 10px; margin: 10px 0; font-size: 14px; }
        .loading { color: #777; font-style: italic; }
    </style></head>
    <body>
        <h2>OSINT Investigation Harness</h2>
        <form onsubmit="return submitForm(event)">
            <input id="subject" placeholder="Subject to investigate" required>
            <select id="subject_type" style="width:100%; margin-bottom:12px;">
                <option value="company">Company</option>
                <option value="person">Person</option>
                <option value="claim">Claim</option>
            </select>
            <button type="submit">Investigate</button>
        </form>
        <div id="result"></div>
        <script>
        async function submitForm(e) {
            e.preventDefault();
            document.getElementById('result').innerHTML = '<p class="loading">Investigating... this can take 30-60s</p>';
            try {
                const res = await fetch('/investigate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        subject: document.getElementById('subject').value,
                        subject_type: document.getElementById('subject_type').value
                    })
                });
                const d = await res.json();
                document.getElementById('result').innerHTML = `
                    <div class="card">
                        <div class="label">Verdict</div>
                        <div class="verdict ${d.verdict}">${d.verdict.replace('_',' ')}</div>
                        <div class="label" style="margin-top:8px;">Confidence: ${d.confidence}</div>
                    </div>
                    <div class="card">
                        <div class="label">Findings</div>
                        <p>${d.narrative.replace(/\\n/g, '<br><br>')}</p>
                    </div>
                    <div class="card">
                        <div class="label">Analyst Notes</div>
                        <p>${d.reflection}</p>
                    </div>
                    <div class="card">
                        <div class="label">Metrics</div>
                        <p>Steps: ${d.metrics.steps_taken} · Tool calls: ${d.metrics.tool_calls} · Tokens: ${d.metrics.total_tokens} · Reward: ${d.metrics.reward}</p>
                    </div>
                    <div class="card">
                        <div class="label">Evidence (${d.evidence.length} sources)</div>
                        ${d.evidence.map(e => `
                            <div class="evidence-item">
                                <strong class="${e.relevance}">[${e.relevance}]</strong><br>
                                <a href="${e.url}" target="_blank" style="font-size:12px; word-break:break-all;">${e.url}</a>
                                <p style="font-size:13px; color:#555;">${e.snippet}...</p>
                            </div>
                        `).join('')}
                    </div>
                `;
            } catch (err) {
                document.getElementById('result').innerHTML = `<p style="color:#b3261e;">Error: ${err.message}</p>`;
            }
        }
        </script>
    </body></html>
    """


@app.post("/investigate")
def run_investigation(req: InvestigateRequest):
    tracker, reflection, narrative, metrics = investigate(req.subject, subject_type=req.subject_type)
    report_path = generate_report(req.subject, req.subject_type, tracker, reflection, narrative, metrics)
    return {
        "verdict": tracker.verdict(),
        "confidence": tracker.confidence(),
        "narrative": narrative,
        "reflection": reflection,
        "evidence": [
            {"relevance": e.relevance, "url": e.source_url, "snippet": e.text_snippet[:200]}
            for e in tracker.evidence
        ],
        "report_file": report_path,
        "metrics": metrics.__dict__,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)