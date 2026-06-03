# Multi-Agent Simulation: Input Context Transparency Study

## 1. Objective
This simulation studies how different levels of input context transparency affect
multi-agent hidden-profile decision making.

The main outcomes are:
- Context consistency, measured through similarity between agent memories
- Coordination efficiency, measured through rounds, messages, tool calls, token
  use, and runtime
- Decision quality, measured by whether the group selects the correct candidate

The current experimental setup compares three treatment conditions against one
moderate baseline. Transparency now changes what agents can see as input, not
what agents are asked to disclose in their public output.

## 2. Task Design
The task is a hidden-profile HR selection scenario for a long-distance pilot
position at a fictional airline.

Key properties:
- Three panel agents receive shared public candidate information.
- Each panel agent also receives private, incomplete candidate information.
- No agent can solve the task reliably alone.
- The best decision requires agents to combine distributed evidence through
  discussion and targeted questions.

## 3. Agents
The active discussion agents are:
- `sarah_mitchell`: Sarah Mitchell, HR Selection Specialist for Flight Operations
- `james_carter`: James Carter, Pilot Assessment Specialist
- `emily_brooks`: Emily Brooks, Recruiting Specialist for Cockpit Personnel

Each discussion agent:
- Has private candidate notes
- Sees public task information
- Can call the other agents through mediated ADK agent tools
- Produces a public message and structured vote metadata
- Does not directly edit memory during its own speaking turn

Each agent also has a tool-agent variant used for targeted questions from other
agents. Tool-agent responses are concise answers to the caller's question.

## 4. Orchestration
The workflow is centralized by the ADK orchestration layer.

Important implementation points:
- Speaker order is randomized at the start of each discussion round.
- Randomization is seeded by `SIM_RANDOM_SEED` when provided, otherwise by
  `RUN_ID`.
- Agent-to-agent tool calls are mediated through `LoggingAgentTool`.
- Tool calls are not private side channels. The public question and answer are
  appended to the public discussion history.
- The vote checker runs after every full round.

One discussion round follows this structure:
1. Shuffle the three speakers.
2. For each speaker in shuffled order:
   - Run the speaker.
   - If `SIM_SMM_MODE=treatment`, run the parallel memory-update stage for all
     agent memories.
3. Run the vote checker.

The main workflow is defined in `02_code/multi_agent_system/agent.py`.

## 5. SMM Modes
The shared mental model mode is controlled by `SIM_SMM_MODE`.

### 5.1 Treatment
`SIM_SMM_MODE=treatment`

Treatment runs use explicit structured SMM memory. The memories are initialized
at the start of the run and updated after each public speaker turn.

The passive memory updater receives:
- The target agent's current structured memory
- Shared public candidate information
- The target agent's own private notes
- The prompt-visible discussion history for the active transparency condition

Memory updates are private. They are not added to the public transcript.

### 5.2 Baseline
`SIM_SMM_MODE=baseline`

Baseline runs do not use explicit SMM memory updates. Agents rely on their normal
prompt context and the prompt-visible discussion history.

The current run matrix includes only the moderate baseline.

## 6. Input Context Transparency Conditions
The transparency condition is controlled by `SIM_CONDITION`.

The implementation lives in
`02_code/multi_agent_system/config/context_transparency.py`.

### 6.1 Low
`SIM_CONDITION=low`

Agents do not see raw public discussion or tool-exchange history in prompts.

Low treatment keeps explicit SMM memory across the full meeting. The structured
memory is not reset between rounds.

Low never includes stored model thoughts.

### 6.2 Moderate
`SIM_CONDITION=moderate`

Agents see the full public discussion and tool-exchange history from the run.

Moderate treatment keeps explicit SMM memory across the full meeting.

Moderate never includes stored model thoughts.

### 6.3 High
`SIM_CONDITION=high`

Agents see the full public discussion and tool-exchange history from the run.
When ADK/model response parts contain `part.thought == true`, those stored model
thoughts are attached to the relevant history entry and rendered into future
prompt history.

High treatment keeps explicit SMM memory across the full meeting.

Model thoughts are experimental input context only. They are not public
transcript content and should not be treated as independent candidate evidence.

## 7. Public History and Thought History
Public discussion history is managed in
`02_code/multi_agent_system/config/history.py`.

The public history records:
- Scheduled speaker messages
- Mediated agent-tool questions and answers

For normal speaker turns:
- Visible text is extracted from non-thought response parts.
- Public output is appended to the public discussion state.
- Public output is written to `chat.md`.
- In high only, thought parts are stored alongside the history item.

For tool-agent turns:
- In high only, tool-agent thoughts are temporarily stashed.
- When the public tool exchange is logged, the stashed thoughts are attached to
  that tool-exchange history item.

`chat.md` remains a public transcript only. It must not include model thoughts.
Thoughts may appear in structured run state, session logs, and high-condition
prompt-built history.

## 8. Prompt Behavior
Prompt builders are defined in
`02_code/multi_agent_system/config/prompts.py`.

All conditions use the same public-output template. The treatment changes the
input context available to the agents, not the disclosure style requested from
them.

Discussion agents receive:
- Their persona and task role
- Public candidate information
- Their own private candidate notes
- The current discussion round
- Explicit SMM memory when treatment mode is active
- The scoped public discussion history
- Tool-use and evidence-boundary instructions

Memory-update agents receive the same scoped discussion history as discussion
agents. In high, this may include thought-enriched history. In low and moderate,
thought text is not included.

## 9. Decision Logic
The vote checker is defined in
`02_code/multi_agent_system/agents/control/vote_checker.py`.

Decision rules:
- Minimum consensus rounds: 2
- Maximum discussion rounds: 5
- If all agents vote for the same candidate after the minimum round threshold,
  the run ends by consensus.
- If maximum rounds are reached and a majority exists, the run ends by majority
  vote.
- If maximum rounds are reached without a majority, the run ends without a
  selected winner.

Each discussion response must include structured vote metadata in
`METADATA_JSON`.

## 10. Run Matrix
The batch runner is
`02_code/simulation_scripts/run_all_conditions.sh`.

Default matrix:
- `low_treatment`
- `moderate_treatment`
- `high_treatment`
- `moderate_baseline`

The old low and high baselines are no longer part of the default experiment.

Run five simulations for each current matrix cell:

```bash
SIM_COUNT=5 ./02_code/simulation_scripts/run_all_conditions.sh
```

Run only treatment cells:

```bash
SIM_SMM_MODE=treatment SIM_COUNT=5 ./02_code/simulation_scripts/run_all_conditions.sh
```

Run only the moderate baseline:

```bash
SIM_SMM_MODE=baseline SIM_COUNT=5 ./02_code/simulation_scripts/run_all_conditions.sh
```

Single-run examples:

```bash
SIM_CONDITION=low SIM_SMM_MODE=treatment \
adk run multi_agent_system --replay multi_agent_system/config/replay.json

SIM_CONDITION=moderate SIM_SMM_MODE=treatment \
adk run multi_agent_system --replay multi_agent_system/config/replay.json

SIM_CONDITION=high SIM_SMM_MODE=treatment \
adk run multi_agent_system --replay multi_agent_system/config/replay.json

SIM_CONDITION=moderate SIM_SMM_MODE=baseline \
adk run multi_agent_system --replay multi_agent_system/config/replay.json
```

For shell commands that need Google ADK, activate the local Conda environment:

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate adk
cd 02_code
```

## 11. Logs and Metadata
Each run writes under:

```text
01_data/raw/simulations/<condition>/<run_id>/
```

Run IDs use:

```text
{condition}_{smm_mode}_{batch}_{i}
```

Important outputs include:
- `chat.md`: public transcript only
- `metadata.json`: run metadata and metrics
- Session trace/log files: structured events, including thought-history counts
  and high-condition thought entries when available
- Archived SMM memory files for treatment runs

Metadata includes the active context-transparency field:
- `context_transparency_condition`

Related history-scope behavior is derived in
`02_code/multi_agent_system/config/context_transparency.py`; those derived
labels are not currently persisted as separate metadata fields.

## 12. Evaluation
The main evaluation dimensions are:

Context consistency:
- Calculated from archived agent memories in treatment runs
- Uses embedding-based pairwise memory similarity when available

Coordination efficiency:
- Discussion rounds
- Public messages
- Agent-tool calls
- Memory updates
- Token usage
- Runtime

Decision quality:
- Final candidate
- Decision method
- Whether the selected candidate matches the configured correct candidate

## 13. Design Boundary
The most important design boundary is:

Transparency changes prompt-visible input context only.

It should not change:
- The public-output template
- The public transcript format
- The candidate facts available in the task setup
- The rule that tool questions and answers are public
- The rule that model thoughts are not public transcript content

This keeps the experiment focused on input context transparency and explicit SMM
memory rather than output-style differences.