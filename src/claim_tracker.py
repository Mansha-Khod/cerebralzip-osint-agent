from dataclasses import dataclass, field
from urllib.parse import urlparse

TIER_1_OFFICIAL = ["gov", "gov.in", "nic.in", "mca.gov.in", "edu"]
TIER_2_ESTABLISHED_MEDIA = ["reuters.com", "apnews.com", "bloomberg.com", "economictimes.indiatimes.com", "livemint.com", "business-standard.com"]
TIER_2_5_REFERENCE = ["wikipedia.org"]
TIER_3_BUSINESS_DATA = ["thecompanycheck.com", "mycorporateinfo.com", "zaubacorp.com","tofler.in", "crunchbase.com"]

def source_reliability(url: str) -> float:
    host = urlparse(url).netloc.lower().replace("www.", "")
    if any(host == d or host.endswith("." + d) for d in TIER_1_OFFICIAL):
        return 1.0
    if any(host == d for d in TIER_2_ESTABLISHED_MEDIA):
        return 0.8
    if any(host == d for d in TIER_2_5_REFERENCE):
        return 0.6  # reference source, not primary journalism
    if any(host == d for d in TIER_3_BUSINESS_DATA):
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

    def _usable_evidence(self):
        return [e for e in self.evidence if e.relevance not in ("irrelevant", "ambiguous_entity")]

    def verdict(self) -> str:
        relevant = self._usable_evidence()
        if not relevant:
            return "insufficient_evidence"
        support_score = sum(source_reliability(e.source_url) for e in relevant if e.relevance == "supports")
        contradict_score = sum(source_reliability(e.source_url) for e in relevant if e.relevance == "contradicts")
        if support_score == contradict_score:
            return "inconclusive"
        return "supported" if support_score > contradict_score else "contradicted"

    def confidence(self) -> float:
        relevant = self._usable_evidence()
        if not relevant:
            return 0.0
        support_score = sum(source_reliability(e.source_url) for e in relevant if e.relevance == "supports")
        contradict_score = sum(source_reliability(e.source_url) for e in relevant if e.relevance == "contradicts")
        total = support_score + contradict_score
        if total == 0:
            return 0.0
        return round(max(support_score, contradict_score) / total, 2)