from dataclasses import dataclass, field

@dataclass
class InvestigationMetrics:
    steps_taken: int = 0
    tool_calls: int = 0
    total_tokens: int = 0
    latency_seconds: float = 0.0
    confidence_progression: list = field(default_factory=list)
    final_confidence: float = 0.0
    reward: float = 0.0
    converged: bool = False

    def step_rewards(self):
        """Per-step reward = change in confidence from the previous step.
        Measures whether a given step actually moved the investigation forward,
        rather than just adding noise."""
        progression = [0.0] + self.confidence_progression
        return [round(progression[i + 1] - progression[i], 3) for i in range(len(progression) - 1)]

def compute_episode_reward(metrics: "InvestigationMetrics", verdict: str = None, expected_verdict: str = None) -> float:
    """
    Episode reward = final confidence, penalized for inefficiency, with correctness
    taking priority over raw confidence when a ground-truth verdict is available.

    Rationale: a confident, well-supported conclusion is the goal, but an agent that
    reaches a WRONG conclusion confidently is worse than one that honestly says it
    isn't sure. When expected_verdict is provided, a correct verdict is rewarded
    using confidence as before; an incorrect verdict is penalized in proportion to
    how confident the agent was in that wrong answer. Without ground truth, the
    formula falls back to confidence-only scoring, which is a weaker signal and
    should be read as such.
    """
    step_penalty = 0.02 * metrics.steps_taken
    token_penalty = metrics.total_tokens / 100_000

    if expected_verdict is None or verdict is None:
        reward = metrics.final_confidence - step_penalty - token_penalty
    elif verdict == expected_verdict:
        reward = metrics.final_confidence - step_penalty - token_penalty
    else:
        reward = -metrics.final_confidence - step_penalty - token_penalty

    return round(max(reward, -1.5), 3)

def has_converged(confidence_progression: list, threshold: float = 0.05) -> bool:
    if len(confidence_progression) < 3:
        return False
    return abs(confidence_progression[-1] - confidence_progression[-2]) < threshold
