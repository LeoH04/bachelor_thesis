# Shared Mental Models in Generative AI-Based Multi-Agent Systems

This repository contains the simulation, data, and analysis code for the bachelor thesis **“Shared Mental Models in Generative AI-Based Multi-Agent Systems: A Simulation Study Grounded in Human Team Cognition Theory.”**

The study examines whether an SMM-inspired structured memory mechanism improves efficiency and effectiveness in a generative AI-based multi-agent system, and whether its effects depend on agents’ access to prior discussion history. Three agents solve a hidden-profile personnel-selection task by combining shared and privately distributed information.

The analysis covers 800 independent simulations (200 per configuration):

| Configuration | Structured memory | Prior discussion available to agents |
|---|---:|---|
| Baseline | No | Full public history |
| Low transparency | Yes | Latest speaker turn |
| Moderate transparency | Yes | Full public history |
| High transparency | Yes | Full public history and stored reasoning traces |

Transparency changes the agents’ input context, not their public-output format. Tool questions and answers are public; stored reasoning traces are never included in `chat.md`.

The submitted thesis is available at [`03_report/thesis/Bachelor_Arbeit_Hegemann.pdf`](03_report/thesis/Bachelor_Arbeit_Hegemann.pdf).

## Repository structure

```text
01_data/
  final/                 Archived simulation runs
  processed/             Analysis-ready datasets
  raw/simulations/       Output from new simulation runs
02_code/
  multi_agent_system/    Agents, orchestration, prompts, and task definitions
  simulation_scripts/    Batch launchers
  metrics_evaluation/    Metric calculation and statistical analysis
03_report/
  graphs/                Generated thesis figures
  tables/                Generated tables and appendix material
  thesis/                Thesis and bibliography
```

## Setup

The simulation uses Python 3.12, Google ADK, and an OpenAI-compatible model endpoint. The analysis requires R 4.x.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

Rscript -e 'install.packages(c("tidyverse", "scales", "cowplot", "sandwich", "modelsummary", "flextable", "officer", "jsonlite"), repos = "https://cloud.r-project.org")'
```

Create `02_code/multi_agent_system/.env`:

```dotenv
NIM_BASE_URL=https://your-openai-compatible-endpoint/v1
NVIDIA_API_KEY=your-api-key
OPEN_MODEL=your-litellm-model-name
```

The reported simulations used the self-hosted `gpt-oss-120b` model with temperature 0. Do not commit credentials.

## Reproduce the reported results

Run all commands from the repository root. The frozen analysis dataset is:

```text
01_data/processed/simulation_metrics_final_200_gpt_oss_120b.csv
```

It contains the 800 completed runs used in the thesis. The main thesis artifacts can be regenerated with:

```bash
# Figure 3: communication and cooperation
Rscript 02_code/metrics_evaluation/team_process_thesis_figure.R

# Figure 4: correct decisions and weighted token usage
Rscript 02_code/metrics_evaluation/weighted_tokens_correct_share_thesis_figure.R

# Table 1: regression results
Rscript 02_code/metrics_evaluation/statistical_effects_team_process_word_table.R

# Appendix A and Appendix E source tables
Rscript 02_code/metrics_evaluation/task_materials_word_table.R
Rscript 02_code/metrics_evaluation/descriptive_statistics_coordination_word_table.R
Rscript 02_code/metrics_evaluation/descriptive_standard_errors.R
```

Outputs are written to `03_report/graphs/` and `03_report/tables/`.

## Run new simulations

The default batch contains the three structured-memory configurations and the moderate baseline:

```bash
SIM_COUNT=5 ./02_code/simulation_scripts/run_all_conditions.sh
```

For 200 new runs per configuration:

```bash
SIM_COUNT=200 SIM_BATCH_ID=reproduction \
  ./02_code/simulation_scripts/run_all_conditions.sh
```

New runs are stored under `01_data/raw/simulations/<condition>/<run_id>/`. Each completed run contains its metadata, public transcript, session log, and—where applicable—archived structured memories. Hosted-model changes may prevent bit-for-bit replication even though speaker order is deterministically seeded.

To build an analysis-ready CSV from new runs:

```bash
python 02_code/metrics_evaluation/calculate_team_process.py \
  --input-root 01_data/raw/simulations

python 02_code/metrics_evaluation/build_metadata_table.py \
  --input-root 01_data/raw/simulations \
  --output 01_data/processed/simulation_metrics_reproduction.csv
```

The reporting scripts intentionally read the frozen thesis dataset. Change their `data_path` or `data_file` only when analysing a newly generated CSV.

## Core implementation

- `02_code/multi_agent_system/agent.py`: discussion workflow
- `02_code/multi_agent_system/config/context_transparency.py`: context configurations
- `02_code/multi_agent_system/config/history.py`: public and reasoning-trace history
- `02_code/multi_agent_system/config/prompts.py`: agent prompts
- `02_code/multi_agent_system/agents/control/vote_checker.py`: group-decision rules
- `02_code/simulation_scripts/run_all_conditions.sh`: batch execution
