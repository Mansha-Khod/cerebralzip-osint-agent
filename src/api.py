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
    <html><body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
        <h2>OSINT Investigation Harness</h2>
        <form onsubmit="return submitForm(event)">
            <input id="subject" placeholder="Subject to investigate" style="width:100%;padding:8px;" required>
            <br><br>
            <select id="subject_type" style="padding:8px;">
                <option value="company">Company</option>
                <option value="person">Person</option>
                <option value="claim">Claim</option>
            </select>
            <br><br>
            <button type="submit" style="padding:8px 16px;">Investigate</button>
        </form>
        <pre id="result" style="white-space: pre-wrap; margin-top: 20px;"></pre>
        <script>
        async function submitForm(e) {
            e.preventDefault();
            document.getElementById('result').innerText = 'Investigating... this can take 30-60s';
            const res = await fetch('/investigate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    subject: document.getElementById('subject').value,
                    subject_type: document.getElementById('subject_type').value
                })
            });
            const data = await res.json();
            document.getElementById('result').innerText = JSON.stringify(data, null, 2);
            return false;
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
        "evidence_count": len(tracker.evidence),
        "reflection": reflection,
        "report_file": report_path,
        "metrics": metrics.__dict__,
    }