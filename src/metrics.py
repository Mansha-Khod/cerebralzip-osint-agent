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

    def step_rewards(self):
        """Per-step reward = change in confidence from the previous step.
        Measures whether a given step actually moved the investigation forward,
        rather than just adding noise."""
        progression = [0.0] + self.confidence_progression
        return [round(progression[i + 1] - progression[i], 3) for i in range(len(progression) - 1)]

def compute_episode_reward(metrics: "InvestigationMetrics") -> float:
    """
    Episode reward = final confidence, penalized for inefficiency.

    Rationale: a confident, well-supported conclusion is the actual goal, but an
    agent that burns 20 steps and 50,000 tokens to land on 0.6 confidence is
    objectively worse than one that reaches 0.6 in 3 steps — cost matters, per
    the brief's efficiency requirement. Penalties are kept small relative to
    confidence (max realistic penalty ~0.3-0.4) so they discourage waste without
    letting an efficient-but-wrong investigation outscore a slow-but-correct one.
    """
    step_penalty = 0.02 * metrics.steps_taken
    token_penalty = metrics.total_tokens / 100_000  
    reward = metrics.final_confidence - step_penalty - token_penalty
    return round(max(reward, -1.0), 3)