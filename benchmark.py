from dotenv import load_dotenv
load_dotenv()

from src.agent import investigate
from src.report import generate_report

BENCHMARK_SUBJECTS = [
    ("Tata Consultancy Services", "company"),
    ("CerebralZip Technologies Private Limited ", "company"),
    ("OpenAI released GPT-5 in 2024", "claim"),
]

def run_benchmark():
    for subject, subject_type in BENCHMARK_SUBJECTS:
        print(f"\nInvestigating: {subject}")
        tracker, reflection = investigate(subject)
        path = generate_report(subject, subject_type, tracker, reflection)
        print(f"  -> confidence={tracker.confidence()} | report={path}")

if __name__ == "__main__":
    run_benchmark()