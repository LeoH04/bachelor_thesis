# Multi-Agent Simulation: Context Transparency Study

## 1. Objective
The objective of this simulation is to analyze how different levels of context transparency influence:
- Context consistency (alignment of shared mental models)
- Coordination efficiency (communication cost and speed)
- Overall system performance (decision accuracy)

The simulation reflects a realistic enterprise-style decision-making process.

## 2. System Overview
The system models a structured multi-agent workflow with:
- Iterative discussion rounds
- Fixed communication order
- Explicit stopping criteria
- Controlled interaction for reproducibility and measurement

## 3. Task Design: Hidden Profile Scenario
- Each agent receives private, incomplete information
- No agent can solve the task independently
- The optimal solution emerges only through information sharing

## 4. Agents
- Total agents: 4

Each agent:
- Has private knowledge
- Maintains an internal memory (shared mental model)
- Can call other agents as mediated tools during its own speaking turn
- Produces a public message and structured vote metadata
- Does not update memory during the speaking turn itself

## 5. Communication Structure

### 5.1 Orchestration
Communication is:
- Content-decentralized (agents generate their own reasoning)
- Execution-centralized (controlled by orchestrator)

- Agents can request information from other agents via orchestrator-mediated tool calls
- Tool calls are not private side channels: the question and answer are recorded in the public discussion history
- All interaction is mediated through the orchestrator

### 5.2 Discussion Loop
Each round follows a fixed sequence:
1. Agent 1 speaks
2. All agent memories are updated in parallel
3. Agent 2 speaks
4. All agent memories are updated in parallel
5. Agent 3 speaks
6. All agent memories are updated in parallel
7. Agent 4 speaks
8. All agent memories are updated in parallel
9. Vote checker evaluates the round

During each speaking turn, an agent:
- Reads:
  - Full discussion history
  - Its internal memory
- May call other agents as tools
- Produces:
  - A public message
  - Structured metadata

During each tool exchange:
- The calling agent asks another agent a specific question
- The called agent answers directly and concisely
- The tool question and answer are appended to the public discussion history
- No memory is updated inside the tool response itself

During each memory-update phase:
- Four passive memory-update agents run in parallel
- Each one updates exactly one agent memory
- Updates use the full public discussion history, including public tool exchanges
- Memory updates are internal and are not added as public discussion messages

### 5.3 Agent Output Structure
Each agent contribution includes:
- Message (natural language reasoning)
- Preferred candidate
- Structured vote metadata in `METADATA_JSON`

The public message may include confidence, uncertainty, and justification depending on the transparency condition.

## 6. Context Transparency Conditions

### 6.1 Low Transparency
- Fragmented information sharing
- No explicit links to candidates
- No evaluation or reasoning

### 6.2 Moderate Transparency
- Information linked to specific candidates
- Concise evaluations included

### 6.3 High Transparency
Includes all of the above plus:
- Sources or justification
- Uncertainty estimates
- References to prior discussion

## 7. Simulation Phases

### 7.1 Initialization Phase
- Assign private information to each agent
- Initialize agent memory
- Define experimental condition

### 7.2 Iterative Discussion Phase
- Execute discussion rounds
- Record public speaker messages and public tool exchanges
- Update all agent memories after every speaker turn

### 7.3 Decision Phase
After each round, perform a decision check.

Termination Criteria:
- All 4 agents agree on the same candidate

### 7.4 Maximum Round Constraint
- A maximum number of rounds is predefined
- If reached without consensus:
  - Final decision is made via majority voting

## 8. Memory and Shared Mental Models
Each agent maintains an internal memory representing:
- Task
- Candidates
- Shared information

Memory is updated:
- After each scheduled speaker turn
- In parallel for all 4 agents
- Based on the public discussion history, including tool exchanges
- Through passive memory-update agents, not during normal speaking turns

## 9. Evaluation Metrics

### 9.1 Context Consistency
Measured as:
- Semantic similarity between agent memories

Method:
- Embeddings
- Cosine similarity

### 9.2 Coordination Efficiency
Measured using:
- Number of rounds
- Number of messages
- Number of agent-tool calls
- Number of memory updates
- Token usage
- Runtime

### 9.3 System Performance
Binary metric:
- 1 = Correct decision
- 0 = Incorrect decision

## 10. System Architecture

### 10.1 Orchestration Layer
Responsible for:
- Execution order
- Loop control
- Termination logic
- State tracking

### 10.2 Agent Layer
- LLM-based agents
- Each agent:
  - Processes inputs
  - Maintains state
  - Generates outputs

### 10.3 Interaction Model
- No unmediated agent-to-agent communication
- Agent-to-agent tool calls are allowed
- Tool exchanges are recorded as public discussion content
- All communication and memory updates are mediated by the orchestrator

## 11. Implementation Options
- Google ADK
- LangGraph
- CrewAI Flows

Support:
- Sequential execution
- Looping
- Conditional logic
- State management

## 12. Design Rationale
Prioritizes:
- Control
- Traceability
- Reproducibility

Reflects enterprise systems where:
- Workflows are structured
- Interactions are monitored
- Decisions must be explainable

## 13. Summary
This simulation studies:
- Impact of context transparency on:
  - Shared mental models
  - Coordination
  - Decision quality

Bridges research and enterprise system design.
