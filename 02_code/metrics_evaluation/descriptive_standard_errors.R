# ============================================================
# Descriptive means, standard deviations, and standard errors
#
# Covers the outcomes discussed alongside Figures 3 and 4 and
# the coordination-efficiency statistics reported in Appendix E.
# ============================================================

rm(list = ls())

library(dplyr)
library(tidyr)

project_path <- getwd()

data_file <- file.path(
  project_path,
  "01_data",
  "processed",
  "simulation_metrics_final_200_gpt_oss_120b.csv"
)

output_dir <- file.path(project_path, "03_report", "tables")
output_file <- file.path(output_dir, "descriptive_standard_errors.csv")

output_token_weight <- 5
weighted_token_scale <- 1000000

simulation_metrics <- read.csv(
  data_file,
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

required_variables <- c(
  "smm_mode",
  "context_transparency_condition",
  "team_process_communication",
  "team_process_cooperation",
  "decision_correct",
  "input_tokens",
  "output_tokens",
  "rounds",
  "total_messages",
  "agent_tool_calls",
  "runtime_seconds"
)

missing_variables <- setdiff(required_variables, names(simulation_metrics))

if (length(missing_variables) > 0) {
  stop(
    paste0(
      "Missing required variables: ",
      paste(missing_variables, collapse = ", ")
    )
  )
}

analysis_data <- simulation_metrics %>%
  mutate(
    smm_mode = tolower(trimws(as.character(smm_mode))),
    condition = case_when(
      smm_mode == "baseline" ~ "Baseline",
      smm_mode == "treatment" &
        context_transparency_condition == "low" ~ "Low",
      smm_mode == "treatment" &
        context_transparency_condition == "moderate" ~ "Moderate",
      smm_mode == "treatment" &
        context_transparency_condition == "high" ~ "High",
      TRUE ~ NA_character_
    ),
    condition = factor(
      condition,
      levels = c("Baseline", "Low", "Moderate", "High")
    ),
    across(
      all_of(required_variables[3:length(required_variables)]),
      as.numeric
    ),
    weighted_total_tokens_million =
      (input_tokens + output_token_weight * output_tokens) /
        weighted_token_scale
  ) %>%
  filter(!is.na(condition))

# Continuous and count outcomes report the sample SD. The SE is retained because
# it is used to construct the 95% confidence intervals in Figures 3 and 4.
continuous_summary <- analysis_data %>%
  select(
    condition,
    team_process_communication,
    team_process_cooperation,
    weighted_total_tokens_million,
    rounds,
    total_messages,
    agent_tool_calls,
    runtime_seconds
  ) %>%
  pivot_longer(
    cols = -condition,
    names_to = "measure",
    values_to = "value"
  ) %>%
  group_by(measure, condition) %>%
  summarise(
    n = sum(!is.na(value)),
    mean = mean(value, na.rm = TRUE),
    standard_deviation = sd(value, na.rm = TRUE),
    standard_error = standard_deviation / sqrt(n),
    .groups = "drop"
  )

# Match Figure 4: retain observations with both decision and token data.
# The decision mean, SD, and SE are expressed in percentage points. The sample
# SD describes variation in the binary outcome; the binomial SE matches Figure 4.
decision_summary <- analysis_data %>%
  filter(
    !is.na(decision_correct),
    !is.na(weighted_total_tokens_million)
  ) %>%
  group_by(condition) %>%
  summarise(
    n = n(),
    proportion = mean(decision_correct),
    standard_deviation = 100 * sd(decision_correct),
    .groups = "drop"
  ) %>%
  transmute(
    measure = "correct_decision_percent",
    condition,
    n,
    mean = 100 * proportion,
    standard_deviation,
    standard_error = 100 * sqrt(proportion * (1 - proportion) / n)
  )

descriptive_summary <- bind_rows(
  continuous_summary,
  decision_summary
) %>%
  mutate(
    measure = factor(
      measure,
      levels = c(
        "team_process_communication",
        "team_process_cooperation",
        "correct_decision_percent",
        "weighted_total_tokens_million",
        "rounds",
        "total_messages",
        "agent_tool_calls",
        "runtime_seconds"
      )
    )
  ) %>%
  arrange(measure, condition)

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
write.csv(descriptive_summary, output_file, row.names = FALSE)

print(descriptive_summary, n = Inf)
message("Saved descriptive summary to: ", output_file)
