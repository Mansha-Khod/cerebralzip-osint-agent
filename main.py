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
    parser.add_argument("--no-memory", action="store_true", help="Disable long-term memory recall/save")
    args = parser.parse_args()

    log_step("start", f"Investigating {args.type}: {args.subject}")
    tracker, reflection, narrative, metrics = investigate(args.subject, args.type)
    report_path = generate_report(args.subject, args.type, tracker, reflection, narrative, metrics)
    print(f"\nReport saved to: {report_path}")
    print(f"Confidence: {tracker.confidence()}")
    print(f"Steps: {metrics.steps_taken} | Tool calls: {metrics.tool_calls} | Tokens: {metrics.total_tokens} | Latency: {metrics.latency_seconds}s")
    print(f"Episode reward: {metrics.reward}")

if __name__ == "__main__":
    main()