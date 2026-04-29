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
- Updates memory after each round
- Produces both textual and structured outputs

## 5. Communication Structure

### 5.1 Orchestration
Communication is:
- Content-decentralized (agents generate their own reasoning)
- Execution-centralized (controlled by orchestrator)

- Agents do not directly communicate with each other
- All interaction is mediated through an orchestrator

### 5.2 Discussion Loop
Each round follows a fixed sequence:
1. Agent 1 speaks
2. Agent 2 speaks
3. Agent 3 speaks
4. Agent 4 speaks

During each turn, an agent:
- Reads:
  - Full discussion history
  - Its internal memory
- Updates:
  - Internal understanding
  - Memory state
- Produces:
  - A message
  - Structured metadata

### 5.3 Agent Output Structure
Each agent contribution includes:
- Message (natural language reasoning)
- Preferred candidate
- Confidence level
- Decision readiness (boolean)
- Remaining uncertainties

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
- Update agent memories continuously

### 7.3 Decision Phase
After each round, perform a decision check.

Termination Criteria:
- At least 3 out of 4 agents agree on the same candidate, AND
- At least 3 agents indicate readiness to decide

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
- After each discussion turn
- Based on new inputs

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
- No direct agent-to-agent calls
- All communication via orchestrator

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