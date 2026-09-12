from dataclasses import dataclass,field

TRUSTED_DOMAINS=['.gov',".edu", "reuters.com", "apnews.com"]

@dataclass
class Evidence:
    source_url: str
    relevance: str 
    text_snippet: str

@dataclass
class ClaimTracker:
    claim: str
    evidence: list[Evidence] = field(default_factory=list)

    def add_evidence(self, url: str, relevance: str, snippet: str):
        self.evidence.append(Evidence(url, relevance, snippet))

    def source_reliability(self, url: str) -> float:
        return 1.0 if any(d in url for d in TRUSTED_DOMAINS) else 0.5

    def confidence(self) -> float:
        relevant = [e for e in self.evidence if e.relevance != "irrelevant"]
        if not relevant:
            return 0.0  
        supporting = [e for e in relevant if e.relevance == "supports"]
        contradicting = [e for e in relevant if e.relevance == "contradicts"]
        support_score = sum(self.source_reliability(e.source_url) for e in supporting)
        contradict_score = sum(self.source_reliability(e.source_url) for e in contradicting)
        total = support_score + contradict_score
        return round(support_score / total, 2) if total else 0.0