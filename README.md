# Input Context Transparency in Multi-Agent Hidden-Profile Decisions

This repository contains the simulation and analysis code for a study of how input context transparency affects hidden-profile decision making in a multi-agent system. Three panel agents jointly select a candidate while receiving different private information. The experiment varies the discussion context visible to agents and whether they use an explicit shared-mental-model (SMM) memory.

The four experimental cells are:

| Cell | Prompt-visible context | Explicit SMM memory |
|---|---|---|
| Moderate baseline | Full public discussion and tool exchanges | No |
| Low treatment | No raw public discussion or tool-exchange history | Yes |
| Moderate treatment | Full public discussion and tool exchanges | Yes |
| High treatment | Full public discussion, tool exchanges, and stored model thoughts when available | Yes |

Transparency changes agents' input context only. All conditions use the same public-output format, candidate information, and rule that mediated agent-tool questions and answers are public. Model thoughts are never written to the public transcript.

## Repository structure

```text
01_data/
  final/                 Archived simulation runs used for reporting
  processed/             Flat analysis-ready CSV files
  raw/simulations/       Output location for newly executed runs
02_code/
  multi_agent_system/    Google ADK agents, orchestration, prompts, and tasks
  simulation_scripts/    Batch launchers
  metrics_evaluation/    Python metric builders and R analyses
03_report/
  appendix/              Generated appendix documents
  graphs/                Generated PDF figures
  tables/                Generated statistical and descriptive tables
requirements.txt         Pinned Python dependencies
bachelor_thesis.Rproj    RStudio project
```

## 1. Reproduce the software environment

All commands below assume the repository root is the working directory. The simulation environment was built with Python 3.12 and Google ADK 1.31.1. The reporting code requires R 4.x.

### Python

Create and activate a virtual environment, then install the pinned dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

A Conda environment can be used instead:

```bash
conda create -n adk python=3.12 -y
conda activate adk
python -m pip install -r requirements.txt
```

### R

Install the packages used by the analyses, figures, and Word exports:

```bash
Rscript -e 'install.packages(c("tidyverse", "scales", "ggtext", "cowplot", "lmtest", "sandwich", "modelsummary", "flextable", "officer", "jsonlite"), repos = "https://cloud.r-project.org")'
```

The report artifacts in this checkout were most recently generated with R 4.5.2 and the following main package versions: `tidyverse` 2.0.0, `scales` 1.4.0, `ggtext` 0.1.2, `cowplot` 1.2.0, `lmtest` 0.9-40, `sandwich` 3.1-1, `modelsummary` 2.6.0, `flextable` 0.9.12, `officer` 0.7.5, and `jsonlite` 2.0.0.

### Model and embedding endpoints

The simulation uses an OpenAI-compatible endpoint through LiteLLM. Configure `02_code/multi_agent_system/.env` with:

```dotenv
NIM_BASE_URL=https://your-openai-compatible-endpoint/v1
NVIDIA_API_KEY=your-api-key
OPEN_MODEL=your-litellm-model-name
```

The reported `final_200_gpt_oss_120b` snapshot was produced for the GPT-OSS 120B analysis and the repository configuration identifies the LiteLLM model as `openai/gpt-oss-120b`.

SMM similarity and quality recomputation additionally requires an embedding endpoint in the same file:

```dotenv
EMBEDDING_API_KEY=your-embedding-api-key
EMBEDDING_API_BASE=https://your-embedding-endpoint/v1
SIMILARITY_EMBEDDING_MODEL=your-litellm-embedding-model-name
EMBEDDING_INPUT_TYPE=passage
```

The repository configuration used for the reported SMM metrics selects `nvidia/llama-nemotron-embed-1b-v2` with `EMBEDDING_INPUT_TYPE=passage`.

Use the input type expected by the selected embedding provider. Do not commit live credentials. Exact numerical replication of newly generated simulations also requires the same model, endpoint implementation, and model revision used for the original runs.

Batch defaults may be placed in `02_code/simulation_scripts/.env`. Command-line environment variables override the corresponding values in that file.

## 2. Run the simulations

The batch launcher writes every run to:

```text
01_data/raw/simulations/<condition>/<run_id>/
```

Each completed run contains `metadata.json`, the public transcript `chat.md`, a session log, and—under treatment—archived SMM memory files.

### Small reproduction batch

Run five replications in each treatment cell and five moderate-baseline replications:

```bash
SIM_SMM_MODE=treatment SIM_COUNT=5 \
  ./02_code/simulation_scripts/run_all_conditions.sh

SIM_SMM_MODE=baseline SIM_COUNT=5 \
  ./02_code/simulation_scripts/run_all_conditions.sh
```

The split invocation is intentional: it is unaffected by an `SIM_SMM_MODE` default in the batch `.env` file. The launcher retries failures up to three times and skips already completed run IDs by default.

### Full 200-run-per-cell experiment

```bash
SIM_SMM_MODE=treatment SIM_COUNT=200 SIM_BATCH_ID=my_reproduction \
  ./02_code/simulation_scripts/run_all_conditions.sh

SIM_SMM_MODE=baseline SIM_COUNT=200 SIM_BATCH_ID=my_reproduction \
  ./02_code/simulation_scripts/run_all_conditions.sh
```

Speaker order is deterministically seeded from the condition, SMM mode, and replication index. Set `SIM_SKIP_COMPLETED=0` to rerun IDs whose completed metadata already exists.

### Select a task definition

The default task is `hidden_profile_task.json`. A label-rotated A/C task is also available:

```bash
SIM_TASK_FILE=hidden_profile_task_rotation.json \
SIM_SMM_MODE=treatment SIM_COUNT=5 \
  ./02_code/simulation_scripts/run_all_conditions.sh
```

Task files must be located in `02_code/multi_agent_system/config/`.

### Run one cell manually

Google ADK must be launched from `02_code` so that it can resolve the `multi_agent_system` package:

```bash
cd 02_code
SIM_CONDITION=moderate \
SIM_SMM_MODE=treatment \
SIM_RUN_ID=moderate_treatment_manual_001 \
SIM_RANDOM_SEED=moderate_treatment_001 \
adk run multi_agent_system --replay multi_agent_system/config/replay.json
cd ..
```

Valid simulation cells are `low/treatment`, `moderate/treatment`, `high/treatment`, and `moderate/baseline`.

## 3. Build analysis data from new runs

The Python preprocessing scripts update derived metrics inside each run's `metadata.json`; copy or archive raw runs before forcing a recomputation if the original metadata must remain immutable.

For runs using the default task, execute:

```bash
python 02_code/metrics_evaluation/efficiency.py \
  --input-root 01_data/raw/simulations

python 02_code/metrics_evaluation/calculate_team_process.py \
  --input-root 01_data/raw/simulations

python 02_code/metrics_evaluation/smm_quality.py \
  --input-root 01_data/raw/simulations

python 02_code/metrics_evaluation/build_metadata_table.py \
  --input-root 01_data/raw/simulations \
  --output 01_data/processed/simulation_metrics_reproduction.csv
```

For runs generated with `hidden_profile_task_rotation.json`, use the label-aware wrappers for the two task-dependent metrics:

```bash
python 02_code/metrics_evaluation/calculate_team_process_rotation.py \
  --input-root 01_data/raw/simulations

python 02_code/metrics_evaluation/smm_quality_rotation.py \
  --input-root 01_data/raw/simulations
```

Use `--dry-run` with either metric calculator to inspect eligibility without changing metadata. Add `--force` only when existing derived values should be overwritten. `build_metadata_table.py` includes completed runs by default; pass `--include-incomplete` only for diagnostics.

The R reporting scripts use fixed snapshot paths to make reported results stable. To analyze a new CSV, either copy it to the snapshot filename expected by the relevant script or change that script's `data_file`/`data_path` value explicitly.

## 4. Reproduce the reported analyses

The checked-in reporting snapshot is:

```text
01_data/processed/simulation_metrics_final_200_gpt_oss_120b.csv
```

It contains 800 completed simulations: 200 moderate-baseline runs and 200 runs in each of the low, moderate, and high treatment conditions. Use this checked-in CSV—not the changing `01_data/raw/` directory—to reproduce the reported results.

Run the main exploratory and statistical analyses from the repository root:

```bash
Rscript 02_code/metrics_evaluation/data_exploration.R
Rscript 02_code/metrics_evaluation/statistical_effects_team_process.R
```

These commands generate the condition overview figures and the team-process regression output. The separate decision/SMM analysis family uses the frozen earlier snapshot `01_data/processed/simulation_metrics_20260612_090103.csv`:

```bash
Rscript 02_code/metrics_evaluation/statistical_effects.R
```

## 5. Generate the reported tables

Run the following from the repository root:

```bash
# Regression table for the decision/SMM analysis family
Rscript 02_code/metrics_evaluation/statistical_effects_word_table.R

# Regression table for communication, cooperation, and decision quality
Rscript 02_code/metrics_evaluation/statistical_effects_team_process_word_table.R

# Descriptive coordination statistics
Rscript 02_code/metrics_evaluation/descriptive_statistics_coordination_word_table.R
```

The generated report files are:

| Script | Output |
|---|---|
| `statistical_effects.R` | `03_report/tables/h1_result.png`; `03_report/tables/regression_results_h2_h4.png` |
| `statistical_effects_word_table.R` | `03_report/tables/regression_results_h2_h4.docx` |
| `statistical_effects_team_process.R` | `03_report/tables/regression_results_team_process_h1_h5.pdf` |
| `statistical_effects_team_process_word_table.R` | `03_report/tables/regression_results_team_process_h1_h5.docx` |
| `descriptive_statistics_coordination_word_table.R` | `03_report/tables/descriptive_statistics_coordination.docx` |

## 6. Generate the reported figures

Generate the thesis figures with:

```bash
Rscript 02_code/metrics_evaluation/correct_share_thesis_figure.R
Rscript 02_code/metrics_evaluation/weighted_tokens_thesis_figure.R
Rscript 02_code/metrics_evaluation/team_process_thesis_figure.R
Rscript 02_code/metrics_evaluation/weighted_tokens_correct_share_thesis_figure.R
```

The scripts write:

| Figure | Output |
|---|---|
| Correct decisions | `03_report/graphs/thesis_figure_correct_decisions_by_condition.pdf` |
| Weighted token use | `03_report/graphs/thesis_figure_weighted_tokens_by_condition.pdf` |
| Communication and cooperation | `03_report/graphs/thesis_figure_communication_cooperation_by_condition.pdf` |
| Decision quality and weighted tokens | `03_report/graphs/thesis_figure_correct_decisions_weighted_tokens_by_condition.pdf` |

`data_exploration.R` additionally regenerates all overview PDFs in `03_report/graphs/`, including decision quality, SMM measures, team-process measures, rounds, messages, tool calls, token use, efficiency, and runtime.

## 7. Generate appendix tables

The appendix documents are generated directly from the task configuration and prompt-condition definitions:

```bash
Rscript 02_code/metrics_evaluation/task_materials_word_table.R
Rscript 02_code/metrics_evaluation/prompt_conditions_word_table.R
```

They write:

```text
03_report/appendix/appendix_A_experimental_task_materials.docx
03_report/appendix/appendix_B_prompt_conditions.docx
```

## Reproducibility notes

- Always run the R scripts from the repository root; they resolve inputs and outputs from `getwd()`.
- `chat.md` is a public transcript and never contains model thoughts. High-condition thought context may appear only in structured state or session logs.
- The archived `01_data/final/` runs and processed CSVs are the provenance record for the reported results. Newly generated API-based simulations may differ if the hosted model or serving stack changes.
- The batch launcher uses deterministic speaker-order seeds, but deterministic orchestration does not guarantee bit-for-bit deterministic model responses.
- `smm_quality.py` calls the configured embedding service. Existing values are skipped unless `--force` is supplied.
- Word outputs are generated with `flextable` and `officer`; open the resulting `.docx` files in Word or LibreOffice for final visual inspection.

## Core implementation files

- `02_code/multi_agent_system/agent.py`: centralized discussion workflow
- `02_code/multi_agent_system/config/context_transparency.py`: low/moderate/high prompt-history scope
- `02_code/multi_agent_system/config/history.py`: public and thought-enriched history handling
- `02_code/multi_agent_system/config/prompts.py`: discussion and memory-update prompts
- `02_code/multi_agent_system/agents/control/vote_checker.py`: consensus and majority decision rules
- `02_code/simulation_scripts/run_all_conditions.sh`: reproducible batch launcher
