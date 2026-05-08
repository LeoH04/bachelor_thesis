# Gold Standard Shared Mental Model

Reference artifact for the hidden-profile pilot-selection task.

Source task: `02_code/multi_agent_system/config/hidden_profile_task.json`

State represented: the shared mental model an agent should hold after a perfect interaction round, where all public and private candidate information has been exchanged, attributed, integrated, and evaluated against the role requirements.

## Task Summary

Goal
Choose the best candidate for a long-distance pilot position at an airline.

Candidates
- Candidate A
- Candidate B
- Candidate C
- Candidate D

Ground-truth decision
- Candidate C

## Role Criteria

The best candidate should be judged by the combined fit for:
- Reliability and responsibility
- Calmness under pressure
- Technical and cognitive competence
- Attention and decision quality
- Cooperation and cockpit teamwork
- Suitability for high-responsibility long-distance flights

Repeated direct cooperation negatives are safety-relevant in this task and should be weighted heavily.

## Candidate Summary Table

| Candidate | Evidence For | Evidence Against | Fit for Role | Notes |
| --- | --- | --- | --- | --- |
| Candidate A | Anticipates dangerous situations; sees complex connections; has excellent spatial vision; has very good leadership qualities. | Sometimes not good at taking criticism; can be unorganized; regarded as a show-off; not open to new ideas; unfriendly; eats unhealthily. | Strong cognitive, spatial, anticipation, and leadership evidence, but weak cooperation, adaptability, and organization. | Not optimal because several agents' private information reveals direct interpersonal and adaptability concerns. |
| Candidate B | Very conscientious; handles stress very well; good at assessing weather conditions; has excellent computer skills. | Can be grumpy; can be uncooperative; has a relatively weak memory for numbers; makes nasty remarks about colleagues; regarded as pretentious; sometimes adopts the wrong tone when communicating. | Strong reliability, stress tolerance, weather assessment, and computer evidence, but repeated direct cooperation and communication negatives plus a numeric-memory weakness. | Plausible from public information alone, but not optimal once private information is shared. |
| Candidate C | Makes correct decisions quickly; is known to be 100% reliable; creates a positive atmosphere with crew; keeps calm in a crisis; understands complicated technology; puts concern for others above everything; has excellent attention skills. | Has difficulty communicating ideas; is regarded as egocentric; is not very willing to further his education. | Best balanced fit: reliability, calmness, technical understanding, attention, quick correct decisions, and crew-oriented cooperation are all supported by explicit evidence. | Correct candidate. Public drawbacks remain relevant, but the full group evidence gives Candidate C the broadest and strongest overall role fit. |
| Candidate D | Responds to unexpected events adequately; can concentrate very well; solves problems extremely well; takes responsibility seriously. | Regarded as arrogant; has relatively weak leadership skills; regarded as a know-it-all; has a hot temper; considered moody; regarded as a loner. | Strong concentration, problem-solving, responsibility, and response to unexpected events, but poor cooperation, weak leadership, and emotional/interpersonal risk. | Not optimal because safety-critical teamwork evidence is substantially weaker than Candidate C's. |

## Full Evidence Inventory by Source

Public information
- Candidate A can anticipate dangerous situations.
- Candidate A is able to see complex connections.
- Candidate A has excellent spatial vision.
- Candidate A has very good leadership qualities.
- Candidate B is very conscientious.
- Candidate B handles stress very well.
- Candidate B is good at assessing weather conditions.
- Candidate B has excellent computer skills.
- Candidate C can make correct decisions quickly.
- Candidate C has difficulty communicating ideas.
- Candidate C is regarded as egocentric.
- Candidate C is not very willing to further his education.
- Candidate D responds to unexpected events adequately.
- Candidate D can concentrate very well.
- Candidate D solves problems extremely well.
- Candidate D takes responsibility seriously.

Agent 1 private information
- Candidate A is sometimes not good at taking criticism.
- Candidate A can be unorganized.
- Candidate B can be grumpy.
- Candidate B can be uncooperative.
- Candidate C is known to be 100% reliable.
- Candidate C creates a positive atmosphere with his crew.
- Candidate D is regarded as arrogant.
- Candidate D has relatively weak leadership skills.

Agent 2 private information
- Candidate A is regarded as a show-off.
- Candidate A is regarded as being not open to new ideas.
- Candidate B has a relatively weak memory for numbers.
- Candidate B makes nasty remarks about his colleagues.
- Candidate C keeps calm in a crisis.
- Candidate C understands complicated technology.
- Candidate D is regarded as a know-it-all.
- Candidate D has a hot temper.

Agent 3 private information
- Candidate A is unfriendly.
- Candidate A eats unhealthily.
- Candidate B is regarded as pretentious.
- Candidate B sometimes adopts the wrong tone when communicating.
- Candidate C puts concern for others above everything.
- Candidate C has excellent attention skills.
- Candidate D is considered moody.
- Candidate D is regarded as a loner.

## Current Agent Position

My Last Vote
- Candidate C

My Current Working Favorite
- Candidate C

My Rationale
- Candidate C is the only candidate whose complete evidence set clearly covers the core role requirements in a balanced way: reliability, calmness under pressure, technical competence, attention, decision quality, and crew cooperation.
- Candidate C's public negatives are real and should be retained in memory, but the private evidence adds strong positive indicators across the most safety-relevant dimensions.
- Candidates A, B, and D each have meaningful strengths, but each also has repeated direct cooperation, adaptability, or interpersonal drawbacks that are especially problematic for cockpit teamwork.

Evidence That Could Change My Mind
- Only new valid task evidence showing that Candidate C's communication, egocentrism, or low willingness for further education is more safety-critical than the repeated cooperation risks of the alternatives.

Confidence (percent)
- 90

## Other Agents' Positions

| Agent | Latest Vote | Main Reason | Evidence Shared |
| --- | --- | --- | --- |
| agent_1 | Candidate C | Candidate C adds 100% reliability and positive crew atmosphere to the public quick-decision profile. | Shared C reliability and crew atmosphere; shared A criticism/organization concerns; B grumpy/uncooperative; D arrogance/weak leadership. |
| agent_2 | Candidate C | Candidate C adds calmness in crisis and complicated-technology understanding, while B and D have serious interpersonal risks. | Shared C calmness and technology understanding; shared A show-off/not open; B weak numeric memory/nasty remarks; D know-it-all/hot temper. |
| agent_3 | Candidate C | Candidate C adds concern for others and excellent attention, while A, B, and D have additional cooperation concerns. | Shared C concern for others and attention; shared A unfriendly/unhealthy eating; B pretentious/wrong tone; D moody/loner. |

## Emerging Group View

Group-Leading Candidate
- Candidate C

Important Agreements
- All agents should converge on Candidate C once the full hidden-profile information is shared.
- Candidate C has the strongest combined evidence for reliability, calmness under pressure, technical competence, attention, correct decisions, and positive crew interaction.
- Candidate B looks strong from public information but loses its advantage after private cooperation and numeric-memory concerns are integrated.
- Candidate A and Candidate D have strong technical or cognitive signals, but both carry multiple safety-relevant interpersonal or adaptability drawbacks.

Important Disagreements / Tensions
- Candidate C has public drawbacks: difficulty communicating ideas, egocentrism, and low willingness for further education.
- The core evaluative tension is whether those drawbacks outweigh Candidate C's broad private strengths. In the full evidence set, they do not.

Uncertainties
- No missing candidate information remains within the configured task.
- Residual uncertainty is limited to weighting the known drawbacks, not to factual incompleteness.

## Open Questions

Missing evidence
- None within the configured hidden-profile task.

What would change the decision
- Nothing in the current task evidence. A decision change would require new valid evidence outside the configured information set.

## Next-Step Focus

What to ask or look for next
- No further information exchange is required after the perfect round. The appropriate next step is unanimous selection of Candidate C.
