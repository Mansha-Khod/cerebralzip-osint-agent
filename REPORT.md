# Investigation Harness, Design Report

## Design Choices and Rationale

**Architecture.** The core is a plain loop in agent.py, not an agent framework. At each step, one LLM call decides whether to search again or conclude, based on everything found so far. Whatever it decides gets executed, and the result gets folded back into the context for the next decision. No LangGraph or similar library was used. For a 48 hour assignment that says it cares about demonstrated judgment more than spec following, a plain loop that stays fully readable in one file was worth more than a framework that would have hidden the actual decision making behind abstractions.

**Search: Exa over Tavily, SerpAPI, Brave, Firecrawl, Linkup, Valyu.** This was picked against the real constraints of the project, a solo build with a hard 48 hour clock and a lot of expected trial and error, not against a feature checklist. Exa's free credit model gave more room for repeated failed test runs than Tavily's smaller fixed quota would have. Firecrawl solves full page to Markdown conversion, which a plain requests plus BeautifulSoup fetch already handled well enough at this scope. Linkup's benchmark numbers looked good but it's a less established API, and an unfamiliar API under time pressure is its own risk. Valyu's specialty data (SEC filings, PubMed) didn't match the kinds of subjects this project investigates.

**LLM: Groq's free tier over a paid API.** Each investigation makes dozens of model calls, one per evidence judgment plus one per planning step, so a paid API wasn't realistic for a student project on a deadline. The model name lives as a single constant because two different Groq models got deprecated mid project (llama-3.3-70b-versatile, then llama-3.3-70b-specdec). That happened twice, so the fix was to make it a one line change instead of a hardcoded string scattered everywhere.

**Verdict and confidence kept as separate fields.** An earlier version of the confidence formula only measured supporting evidence over total evidence, which meant a claim that was clearly and correctly disproven, for example "OpenAI released GPT-5 in 2024", scored 0.0 confidence. That reads as "we don't know" when the system actually had a clear answer, the claim is false. The fix splits this into two things: verdict (supported, contradicted, inconclusive, or insufficient_evidence) carries the direction, and confidence measures how strongly the evidence leans that way regardless of which direction it is. This turned out to be the most important correctness fix in the whole project, since it changes what the confidence number is actually claiming.

**Tiered, hostname-based source reliability.** Sources are scored by parsed domain, not by checking whether a string appears anywhere in the URL, since substring checks can false match (a URL containing "reuters.com" as part of an unrelated domain would incorrectly score as trustworthy). Four tiers are used: government and official records score 1.0, established media like Reuters or the Economic Times score 0.8, Wikipedia is scored separately at 0.6 as a reference source rather than grouped with primary journalism, business data aggregators like company registries score 0.65, and everything else, including a company's own website, scores 0.4. Self description is treated as the weakest evidence available on purpose, since it's the least independent source there is.

**Four way evidence classification.** Evidence is labeled supports, contradicts, irrelevant, or ambiguous_entity, not just supports or contradicts. Irrelevant and ambiguous_entity are both excluded from the confidence math. This came directly from testing on "Acme Logistics", a deliberately generic name, where early runs kept mixing evidence about what looked like several unrelated real companies sharing that name into one confidence score.

**Reward redesigned around correctness, not just confidence.** The original reward formula rewarded high final confidence minus a small penalty for steps and tokens used. That formula had a real flaw: it would reward a confident wrong answer the same way it rewards a confident correct one. The benchmark cases now carry an expected verdict, and the reward function checks whether the agent's actual verdict matches it. A correct verdict is rewarded roughly as before. An incorrect verdict is penalized in proportion to how confident the agent was, so a confidently wrong conclusion scores worse than an honest, low confidence "I don't know." This is a genuine design choice with a real justification, not a formula picked to make the numbers look good after the fact, and it was updated after noticing the earlier formula would have rewarded exactly the kind of overconfident mistake the earlier Acme Logistics run produced.

## Key Findings

**1. Confidence and verdict direction are not the same thing.** Documented above. Before the fix, "OpenAI released GPT-5 in 2024" scored 0.0 confidence despite two clear, matching sources proving it false. After the fix, it correctly scores confidence 1.0 with verdict contradicted.

**2. Long term memory can bias the investigation itself, not just save time.** In the logs, after recalling a prior investigation of Acme Logistics that had ended at 0.0 confidence, the next planning step reasoned that it needed to "assess potential wrongdoing" and started searching specifically for fraud and legal issues, with no new evidence prompting that shift. The low prior confidence alone pushed the agent toward a specific hypothesis. This is a real example of memory changing what the agent looks for, not just what it already knows, and it happened without being designed for.

**3. Large, well known subjects were sometimes harder to investigate than small, obscure ones, which is the opposite of what you'd expect.** Tata Consultancy Services initially returned close to no usable evidence, seventeen tool calls and zero confidence, because tcs.com sits behind CDN and bot protection that a plain scraper cannot get past. A much smaller and more ambiguous company returned plenty of usable text. This is a structural weakness of any lightweight scraping approach, not something specific to this codebase.

**4. The reflection step catches real problems, not generic hedging.** In one Acme Logistics run, reflection correctly flagged that a "supporting" source was actually a company's own marketing copy about its reporting service, containing no real facts about the company, even though the confidence formula had scored it as full support. The self critique step did real analytical work there.

**5. The agent needed a hard rule against concluding with no evidence.** Early runs occasionally had the planning step choose to conclude on its very first turn, before a single search happened, almost certainly answering from the model's own training knowledge instead of anything actually investigated. A rule was added so the agent cannot conclude while zero evidence has been gathered, no matter what the model thinks it already knows. Every verdict now has to trace back to something retrieved during that specific run.

**6. Source reliability had a real matching bug.** The original implementation checked whether a trusted domain name appeared anywhere inside a URL string, which can misfire on lookalike or subdomain tricks. It's been switched to parsing the actual hostname and matching against that, which is the correct way to do domain based trust scoring.

## Metrics: Formulas and Justification

**Confidence.** 
confidence = max(sum of reliability over supporting sources, sum of reliability over contradicting sources) divided by the sum of both.
Irrelevant and ambiguous_entity evidence is excluded entirely, since evidence that doesn't actually bear on the subject shouldn't move the number in either direction.

**Verdict.** Determined by which side, supporting or contradicting, has the higher reliability weighted total. Equal weight on both sides is called inconclusive. No usable evidence at all is called insufficient_evidence.

**Episode reward.**
If the verdict matches the expected ground truth verdict for that benchmark case: reward = final_confidence minus (0.02 times steps taken) minus (total_tokens divided by 100,000).
If the verdict does not match: reward = negative final_confidence minus the same two penalty terms.
The reasoning is direct: a confident correct conclusion should score well, and steps or tokens spent inefficiently should cost a little, but a confident wrong conclusion needs to score worse than an honest uncertain one, since rewarding confident wrongness is a worse outcome for a system meant to be trusted than rewarding honest uncertainty.

**Step level signal.** Change in confidence from one step to the next. A positive change means that step's search actually moved the investigation forward. A value near zero across several steps in a row suggests the agent has converged, or is stuck adding noise without new information.

**Convergence.** An investigation is marked converged once the confidence change between two consecutive steps drops below 0.05. On the Tata Consultancy Services run, confidence moved 0.0, 0.0, then jumped to 1.0 and stayed there for the rest of the run, flat, then a real jump, then a stable plateau. That shape is what a genuinely convergent investigation should look like, as opposed to confidence bouncing around step to step, which would suggest a confused or unstable agent.

**Benchmark accuracy.** Each benchmark case now carries an expected verdict decided in advance. Accuracy is the fraction of cases where the agent's actual verdict matches that expected verdict. This number is printed directly from running benchmark.py, not written in by hand.

## Limitations and What Was Scoped Out

Some things in a more complete version of this project were deliberately left out given the 48 hour window, and are listed here honestly rather than attempted badly under time pressure:

- **Formal memory ablation across none, short, long, and short plus long configurations, run on the same set of cases for a controlled comparison.** The current system demonstrates one clear memory effect qualitatively, the Acme Logistics bias described above, but doesn't yet run every case under every memory configuration to produce a full comparison table.
- **Confidence calibration using something like a Brier score against ground truth verdicts**, to check whether a stated 0.8 confidence actually corresponds to being right about 80% of the time across many runs. This needs more benchmark cases and more repeated runs than time allowed.
- **Human evaluation with more than one reviewer** on a larger set of cases, judging things like citation correctness and report usefulness. This project's evaluation is currently automated and based on ground truth verdicts the author defined, not independent human judgment, and that distinction matters and should not be blurred.
- **Claim type aware reliability**, where a company's own statement would be treated as reasonably strong evidence for basic facts about itself (like its founding date) but weak evidence against allegations made about it.
- **Decomposing a company or person investigation into separate factual subclaims**, each with its own verdict, instead of one overall verdict for the whole subject.
- **Repeating benchmark cases multiple times and reporting variance**, since these are LLM driven and not fully deterministic, a single run of each case is a snapshot, not a stable measurement.
- **JS rendered and bot walled pages remain inaccessible.** A plain requests and BeautifulSoup fetch cannot run JavaScript, so sites like tcs.com or Cloudflare protected pages return bot challenge text or CDN error pages instead of real content. The system detects known failure signatures and a minimum content length, but this is a list of known shapes, not a real solution, and a proper fix would need a headless browser like Playwright.
- **Content emptiness filtering in general is a list of patterns that were found by hitting them, not a general solution.** Over the course of building this, five different disguises of "this looks like real text but contains no actual information" were found and patched one at a time: SSL failure messages, soft 404 pages, CDN error pages, bot wall messages, and marketing copy that mentions the subject without saying anything about it. Each fix caught the shape already seen and nothing guarantees the next one is covered.

- **`subject_type` (company/person/claim) currently only affects report labeling, not investigation strategy.** The agent uses the same prompts and logic regardless of whether the subject is a company, a person, or a claim. A more complete system might check different things depending on type: registration and filings for a company, public role and notable affiliations for a person, direct source verification for a claim. This was noticed when a benchmark "person" case was phrased as a full factual sentence rather than just a name, effectively making it behave like a claim case rather than a genuine person investigation.

-  **Deduplication normalizes case and trailing slashes, but not all URL variations** (e.g. `www.` prefixes, tracking query parameters). A small remaining category of near-duplicate sources could still be counted as independent evidence.

None of the above is claimed as done. They are named specifically so it's clear what a more thorough version would need, rather than left unmentioned.

## A Note on What Reflection Is and Isn't

The reflection step is an LLM critiquing its own confidence score, and it caught real, specific problems during development. It is not a substitute for ground truth, and it is not being treated as one anywhere in this project's accuracy numbers. Benchmark accuracy is measured against the expected_verdict values defined in benchmark.py, decided in advance by the author, not against anything the reflection step said about itself.