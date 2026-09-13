from dotenv import load_dotenv
load_dotenv()
import argparse
from src.agent import investigate
from src.logger import log_step
from src.report import generate_report

def main():
    parser = argparse.ArgumentParser(description="OSINT investigation harness")
    parser.add_argument("--subject", required=True, help='What to investigate')
    parser.add_argument("--type", choices=['company', 'person', 'claim'], required=True)
    args = parser.parse_args()

    log_step("start", f"Investigating {args.type}: {args.subject}")
    tracker,reflection = investigate(args.subject)
    report_path = generate_report(args.subject, args.type, tracker, reflection)
    print(f"\nReport saved to: {report_path}")
    print(f"Confidence: {tracker.confidence()}")

    print(f"\n=== FINDINGS FOR: {args.subject} ===")
    print(f"Total evidence collected: {len(tracker.evidence)}")
    print(f"Confidence score: {tracker.confidence()}")
    for e in tracker.evidence:
        label = "SUPPORTS" if e.supports else "CONTRADICTS"
        print(f"\n[{label}] {e.source_url}\n{e.text_snippet}")

if __name__ == "__main__":
    main()