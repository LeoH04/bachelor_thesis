# Simulation Refinement Plan: Context Transparency Conditions

## Summary
Refine the simulation so low, moderate, and high transparency differ in both public communication and shared-memory construction. The target design is: low is too sparse, moderate gives the best decision-focused compression, and high adds legitimate transparency overhead without simply giving agents more useful candidate evidence. Do not change task data, metadata schema, max rounds, tool-call behavior, or speaker randomization.

## Key Changes
- Add condition-specific memory-update instructions in `02_code/multi_agent_system/config/prompts.py`.
- Keep the existing memory schema and output sections unchanged.
- Do not add new metadata fields.
- Do not enable raw model thoughts.
- Do not change the current randomized speaker order.

## Transparency Design
- Low transparency:
  - Public messages stay short: recommendation plus at most one brief fact or concern.
  - Memory updates stay sparse and literal.
  - Avoid rich synthesis, candidate comparison, and group-view interpretation.
  - Preserve fragmentation.

- Moderate transparency:
  - Public messages share compact candidate-linked reasons.
  - Memory updates create the cleanest shared mental model.
  - Prioritize decision-relevant facts, concise candidate comparison, latest votes, and one main unresolved issue.
  - This is the “best compression” condition.

- High transparency:
  - Public messages add source/provenance, uncertainty, prior-discussion references, alternatives, and decision-change conditions.
  - High should add contextual detail, not simply more candidate facts.
  - Memory updates preserve more provenance, repeated rationale, uncertainty, vote-history context, and unresolved alternatives.
  - Do not label this as “noise” in prompts; define these as high-transparency context elements.

## Diagnostic Parity Rule
Use a soft diagnostic parity rule between moderate and high.

- Moderate and high should surface comparable amounts of decision-diagnostic candidate evidence.
- High may be longer, but the added length should come from contextual transparency elements:
  - source/provenance
  - own vs others’ information
  - prior discussion references
  - uncertainty/confidence
  - alternative interpretations
  - unresolved questions
  - what would change the vote
- Avoid hard numeric fact caps except where low already uses one.
- Prompt wording should say high adds “contextual detail” or “expanded transparency context,” never “noise.”

## Memory Update Rules
Revise `build_memory_update_instruction()` so it injects condition-specific memory guidance.

- Low memory:
  - Record only facts explicitly stated in public discussion.
  - Keep candidate evaluation minimal.
  - Track latest votes, but avoid strong synthesis.
  - Use “insufficient evidence” when little has been shared.

- Moderate memory:
  - Integrate decision-relevant candidate facts compactly.
  - Keep one concise row per candidate.
  - Highlight the most important tradeoff and current blocker.
  - Prefer concise synthesis over exhaustive provenance.

- High memory:
  - Preserve all moderate content plus high-transparency context.
  - Include provenance, repeated arguments, confidence/uncertainty, vote changes, prior-context references, and unresolved alternatives.
  - Allow memory to become longer and less compressed.
  - Still avoid raw hidden chain-of-thought.

## Test Plan
- Static prompt checks:
  - Confirm `SIM_CONDITION=low|moderate|high` changes memory-update instructions.
  - Confirm no metadata schema additions.
  - Confirm raw model thoughts remain disabled.
  - Confirm speaker randomization is untouched.

- Pilot run:
  - Run a small treatment-only pilot, for example 5 runs per condition.
  - Inspect `chat.md` and `shared_mental_models/*.md`.
  - Check that low is sparse, moderate is compact/diagnostic, and high is longer due to contextual transparency rather than more useful candidate facts.

- Acceptance criteria:
  - Moderate memories are cleaner and more compressed than high memories.
  - High memories contain more provenance, uncertainty, prior-context references, and unresolved alternatives.
  - High does not gain a clear advantage by listing substantially more unique diagnostic candidate facts than moderate.
  - Existing metrics and run outputs remain compatible.
