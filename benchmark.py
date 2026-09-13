from dotenv import load_dotenv
load_dotenv()

from src.agent import investigate
from src.report import generate_report

BENCHMARK_SUBJECTS = [
    ("Tata Consultancy Services", "company", "supported"),
    ("Acme Logistics Pvt Ltd", "company", "insufficient_evidence"), 
    ("OpenAI released GPT-5 in 2024", "claim", "contradicted"),
]

def run_benchmark():
    for subject, subject_type in BENCHMARK_SUBJECTS:
        print(f"\nInvestigating: {subject}")
        tracker, reflection, narrative, metrics = investigate(subject, subject_type=subject_type)
        path = generate_report(subject, subject_type, tracker, reflection, narrative, metrics)
        print(f"  -> verdict={tracker.verdict()} | confidence={tracker.confidence()} | "
              f"reward={metrics.reward} | tokens={metrics.total_tokens} | report={path}")

if __name__ == "__main__":
    run_benchmark()