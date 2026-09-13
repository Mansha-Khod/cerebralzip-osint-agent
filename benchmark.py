from dotenv import load_dotenv
load_dotenv()

from src.agent import investigate
from src.report import generate_report

BENCHMARK_SUBJECTS = [
    ("Tata Consultancy Services", "company", "supported"),
    ("Acme Logistics Pvt Ltd", "company", "insufficient_evidence"),
    ("OpenAI released GPT-5 in 2024", "claim", "contradicted"),
    ("Sundar Pichai is the CEO of Google", "person", "supported"),
    ("Satya Nadella", "person", "supported"),
    ("Electric vehicles are cheaper to own than gas cars over their lifetime", "claim", "inconclusive"),
    ("Rabindranath Tagore was a pre-eminent Bengali poet and cultural figure", "claim", "supported"),
    ("Apple Inc. is a United States-based multinational technology company founded in 1976", "claim", "supported"),
]

def run_benchmark():
    correct = 0
    for subject, subject_type, expected_verdict in BENCHMARK_SUBJECTS:
        print(f"\nInvestigating: {subject}")
        tracker, reflection, narrative, metrics = investigate(
            subject, subject_type=subject_type, expected_verdict=expected_verdict
        )
        path = generate_report(subject, subject_type, tracker, reflection, narrative, metrics)
        is_correct = tracker.verdict() == expected_verdict
        correct += int(is_correct)
        print(f"  -> verdict={tracker.verdict()} (expected={expected_verdict}, correct={is_correct}) | "
              f"confidence={tracker.confidence()} | reward={metrics.reward} | "
              f"tokens={metrics.total_tokens} | report={path}")

    accuracy = round(correct / len(BENCHMARK_SUBJECTS), 2)
    print(f"\n=== Benchmark accuracy: {correct}/{len(BENCHMARK_SUBJECTS)} = {accuracy} ===")

if __name__ == "__main__":
    run_benchmark()