from dataclasses import dataclass,field

TIER_1_OFFICIAL = [".gov", ".gov.in", ".nic.in", "mca.gov.in", ".edu"]
TIER_2_ESTABLISHED_MEDIA = ["reuters.com", "apnews.com", "bloomberg.com",
                            "economictimes.indiatimes.com", "livemint.com", "business-standard.com"]
TIER_3_BUSINESS_DATA = ["thecompanycheck.com", "mycorporateinfo.com", "zaubacorp.com",
                         "tofler.in", "crunchbase.com"]

def source_reliability(url: str) -> float:
    if any(d in url for d in TIER_1_OFFICIAL):
        return 1.0
    if any(d in url for d in TIER_2_ESTABLISHED_MEDIA):
        return 0.8
    if any(d in url for d in TIER_3_BUSINESS_DATA):
        return 0.65
    return 0.4

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

    def confidence(self) -> float:
        relevant = [e for e in self.evidence if e.relevance not in ("irrelevant", "ambiguous_entity")]
        if not relevant:
            return 0.0
        supporting = [e for e in relevant if e.relevance == "supports"]
        contradicting = [e for e in relevant if e.relevance == "contradicts"]
        support_score = sum(source_reliability(e.source_url) for e in supporting)
        contradict_score = sum(source_reliability(e.source_url) for e in contradicting)
        total = support_score + contradict_score
        return round(support_score / total, 2) if total else 0.0