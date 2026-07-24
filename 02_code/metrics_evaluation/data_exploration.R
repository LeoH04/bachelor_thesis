# ============================================================
# Data exploration of generated simulation data
# Baseline as separate fourth column:
# Baseline | Low | Moderate | High
# ============================================================

# Empty workspace
if (!is.null(dev.list())) dev.off()
rm(list = ls())

library(tidyverse)
options(scipen = 999)

path <- getwd()
source(paste0(path, "/02_code/metrics_evaluation/price_calculator.R"))

# ------------------------------------------------------------
# 1. LOAD DATA
# ------------------------------------------------------------

simulation_metrics <- read.csv(
  "01_data/processed/simulation_metrics_final_200_gpt_oss_120b.csv",
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

# ------------------------------------------------------------
# 1a. Type conversion
# ------------------------------------------------------------

simulation_metrics$context_transparency_condition <- factor(
  simulation_metrics$context_transparency_condition,
  levels = c("low", "moderate", "high"),
  ordered = TRUE
)

simulation_metrics$smm_mode <- factor(
  simulation_metrics$smm_mode,
  levels = c("baseline", "treatment")
)

simulation_metrics$status <- factor(simulation_metrics$status)
simulation_metrics$decision_method <- factor(simulation_metrics$decision_method)
simulation_metrics$final_candidate <- factor(simulation_metrics$final_candidate)
simulation_metrics$correct_candidate <- factor(simulation_metrics$correct_candidate)

simulation_metrics$timestamp <- as.POSIXct(
  simulation_metrics$timestamp,
  format = "%Y%m%d_%H%M%S",
  tz = "Europe/Berlin"
)

simulation_metrics$completed_at <- as.POSIXct(
  simulation_metrics$completed_at,
  format = "%Y-%m-%dT%H:%M:%S%z",
  tz = "Europe/Berlin"
)

integer_columns <- c(
  "rounds",
  "agent_turns",
  "agent_tool_calls",
  "agent_tool_messages",
  "memory_updates",
  "total_messages",
  "input_tokens",
  "output_tokens",
  "total_tokens",
  "decision_correct",
  grep("^votes_", names(simulation_metrics), value = TRUE)
)

integer_columns <- intersect(integer_columns, names(simulation_metrics))

simulation_metrics[integer_columns] <- lapply(
  simulation_metrics[integer_columns],
  as.integer
)

numeric_columns <- c(
  "runtime_seconds",
  "team_process_score",
  "team_process_communication",
  "team_process_cooperation"
)

numeric_columns <- intersect(numeric_columns, names(simulation_metrics))

simulation_metrics[numeric_columns] <- lapply(
  simulation_metrics[numeric_columns],
  as.numeric
)

# ------------------------------------------------------------
# 1b. Create plotting condition
# ------------------------------------------------------------
# This collapses all baseline runs into one reference condition.
# Treatment runs remain separated by context transparency condition.

simulation_metrics <- simulation_metrics %>%
  mutate(
    plot_condition = case_when(
      smm_mode == "baseline" ~ "baseline",
      smm_mode == "treatment" ~ as.character(context_transparency_condition),
      TRUE ~ NA_character_
    ),
    plot_condition = factor(
      plot_condition,
      levels = c("baseline", "low", "moderate", "high"),
      labels = c("Baseline", "Low", "Moderate", "High")
    )
  )

# ------------------------------------------------------------
# 2. Calculate costs
# ------------------------------------------------------------

total_number_input_tokens <- sum(simulation_metrics$input_tokens, na.rm = TRUE)
total_number_output_tokens <- sum(simulation_metrics$output_tokens, na.rm = TRUE)

costs <- calculate_costs(
  input_tokens = total_number_input_tokens,
  output_tokens = total_number_output_tokens,
  context = "short"
)

print(costs)

output_token_weight <- 5

# ------------------------------------------------------------
# PLOT THEME
# ------------------------------------------------------------

plot_theme <- theme_minimal(base_size = 13) +
  theme(
    plot.title = element_text(
      face = "bold",
      size = 15,
      hjust = 0,
      margin = margin(b = 12)
    ),
    plot.subtitle = element_text(
      size = 11,
      margin = margin(b = 10)
    ),
    axis.title = element_text(
      face = "bold",
      size = 12
    ),
    axis.text = element_text(
      color = "black",
      size = 11
    ),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_line(linewidth = 0.3),
    legend.position = "none",
    plot.margin = margin(10, 15, 10, 10)
  )

# ------------------------------------------------------------
# Helper function for four-column plots
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

save_four_column_plot <- function(
    plot_data,
    y_var,
    y_label,
    title,
    filename,
    digits = 2,
    y_limits = NULL,
    as_percent = FALSE
) {
  
  plot_data <- plot_data %>%
    filter(!is.na(plot_condition)) %>%
    mutate(
      plot_group = if_else(
        as.character(plot_condition) == "Baseline",
        "Baseline",
        "Treatment"
      ),
      plot_label = if (as_percent) {
        paste0(round(.data[[y_var]] * 100, digits), "%")
      } else {
        as.character(round(.data[[y_var]], digits))
      }
    )
  
  if (is.null(y_limits)) {
    y_max <- max(plot_data[[y_var]], na.rm = TRUE)

    if (!is.finite(y_max) || y_max == 0) {
      y_max <- 1
    }

    y_limits <- c(0, y_max * 1.15)
  }
  
  y_scale <- if (as_percent) {
    scale_y_continuous(
      limits = y_limits,
      expand = expansion(mult = c(0, 0)),
      labels = function(x) paste0(round(x * 100), "%")
    )
  } else {
    scale_y_continuous(
      limits = y_limits,
      expand = expansion(mult = c(0, 0))
    )
  }
  
  four_column_plot <- ggplot(
    plot_data,
    aes(x = plot_condition, y = .data[[y_var]], fill = plot_group)
  ) +
    geom_col(
      width = 0.65
    ) +
    geom_text(
      aes(label = plot_label),
      vjust = -0.4,
      size = 3.6
    ) +
    scale_fill_manual(
      values = c(
        "Baseline" = "grey70",
        "Treatment" = "grey35"
      )
    ) +
    y_scale +
    labs(
      x = "Condition",
      y = y_label,
      title = title
    ) +
    plot_theme +
    theme(
      legend.position = "none"
    )
  
  if (interactive()) print(four_column_plot)
  
  ggsave(
    filename = paste0(path, "/03_report/graphs/", filename),
    plot = four_column_plot,
    width = 8,
    height = 5
  )
}

# ------------------------------------------------------------
# 3a. Correct candidate choices
# Baseline | Low | Moderate | High
# ------------------------------------------------------------
# Use shares instead of raw counts because collapsed baseline may contain
# a different number of runs than each treatment condition.

correct_candidate_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    correct_choices = sum(decision_correct, na.rm = TRUE),
    correct_share = correct_choices / total_runs,
    .groups = "drop"
  )

print(correct_candidate_overview)

save_four_column_plot(
  plot_data = correct_candidate_overview,
  y_var = "correct_share",
  y_label = "Share of correct choices",
  title = "Correct candidate choices by condition",
  filename = "correct_candidate_overview_plot.pdf",
  digits = 1,
  y_limits = c(0, 1),
  as_percent = TRUE
)

# ------------------------------------------------------------
# 3b. NA final candidates
# Baseline | Low | Moderate | High
# ------------------------------------------------------------
# Again use shares instead of raw counts.

na_candidate_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    na_candidates = sum(is.na(final_candidate)),
    na_share = na_candidates / total_runs,
    .groups = "drop"
  )

print(na_candidate_overview)

save_four_column_plot(
  plot_data = na_candidate_overview,
  y_var = "na_share",
  y_label = "Share of runs without final candidate",
  title = "Runs without a final candidate by condition",
  filename = "na_candidate_overview_plot.pdf",
  digits = 1,
  y_limits = c(0, 1),
  as_percent = TRUE
)

# ------------------------------------------------------------
# 4a. Team process
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

team_process_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_team_process = mean(team_process_score, na.rm = TRUE),
    .groups = "drop"
  )

print(team_process_overview)

save_four_column_plot(
  plot_data = team_process_overview,
  y_var = "mean_team_process",
  y_label = "Mean team process score",
  title = "Mean team process score by condition",
  filename = "team_process_overview_plot.pdf",
  digits = 3,
  y_limits = c(0, 1)
)

# ------------------------------------------------------------
# 4b. Team process communication
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

team_process_dimensions_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_team_process_communication = mean(team_process_communication, na.rm = TRUE),
    mean_team_process_cooperation = mean(team_process_cooperation, na.rm = TRUE),
    .groups = "drop"
  )

print(team_process_dimensions_overview)

save_four_column_plot(
  plot_data = team_process_dimensions_overview,
  y_var = "mean_team_process_communication",
  y_label = "Mean communication score",
  title = "Mean team process communication by condition",
  filename = "team_process_communication_overview_plot.pdf",
  digits = 3,
  y_limits = c(0, 1)
)

# ------------------------------------------------------------
# 4c. Team process cooperation: response integration
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

save_four_column_plot(
  plot_data = team_process_dimensions_overview,
  y_var = "mean_team_process_cooperation",
  y_label = "Mean response integration score",
  title = "Mean team process response integration by condition",
  filename = "team_process_cooperation_overview_plot.pdf",
  digits = 3,
  y_limits = c(0, 1)
)

# ------------------------------------------------------------
# 5. Interaction rounds
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

rounds_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_rounds = mean(rounds, na.rm = TRUE),
    .groups = "drop"
  )

print(rounds_overview)

save_four_column_plot(
  plot_data = rounds_overview,
  y_var = "mean_rounds",
  y_label = "Mean rounds",
  title = "Mean interaction rounds by condition",
  filename = "rounds_overview_plot.pdf",
  digits = 2
)

# ------------------------------------------------------------
# 6. Messages
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

messages_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_messages = mean(total_messages, na.rm = TRUE),
    .groups = "drop"
  )

print(messages_overview)

save_four_column_plot(
  plot_data = messages_overview,
  y_var = "mean_messages",
  y_label = "Mean messages",
  title = "Mean messages by condition",
  filename = "messages_overview_plot.pdf",
  digits = 2
)

# ------------------------------------------------------------
# 6a. Tool calls
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

tool_calls_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_tool_calls = mean(agent_tool_calls, na.rm = TRUE),
    .groups = "drop"
  )

print(tool_calls_overview)

save_four_column_plot(
  plot_data = tool_calls_overview,
  y_var = "mean_tool_calls",
  y_label = "Mean tool calls",
  title = "Mean tool calls by condition",
  filename = "tool_calls_overview_plot.pdf",
  digits = 2
)

# ------------------------------------------------------------
# 7. Tokens
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

tokens_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_tokens = mean(total_tokens, na.rm = TRUE),
    .groups = "drop"
  )

print(tokens_overview)

save_four_column_plot(
  plot_data = tokens_overview,
  y_var = "mean_tokens",
  y_label = "Mean tokens",
  title = "Mean tokens by condition",
  filename = "tokens_overview_plot.pdf",
  digits = 0
)

# ------------------------------------------------------------
# 7a. Input tokens
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

input_tokens_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_input_tokens = mean(input_tokens, na.rm = TRUE),
    .groups = "drop"
  )

print(input_tokens_overview)

save_four_column_plot(
  plot_data = input_tokens_overview,
  y_var = "mean_input_tokens",
  y_label = "Mean input tokens",
  title = "Mean input tokens by condition",
  filename = "input_tokens_overview_plot.pdf",
  digits = 0
)

# ------------------------------------------------------------
# 7b. Output tokens
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

output_tokens_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_output_tokens = mean(output_tokens, na.rm = TRUE),
    .groups = "drop"
  )

print(output_tokens_overview)

save_four_column_plot(
  plot_data = output_tokens_overview,
  y_var = "mean_output_tokens",
  y_label = "Mean output tokens",
  title = "Mean output tokens by condition",
  filename = "output_tokens_overview_plot.pdf",
  digits = 0
)

# ------------------------------------------------------------
# 7c. Weighted tokens
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

weighted_tokens_overview <- simulation_metrics %>%
  mutate(weighted_total_tokens = input_tokens + output_token_weight * output_tokens) %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_weighted_tokens = mean(weighted_total_tokens, na.rm = TRUE),
    .groups = "drop"
  )

print(weighted_tokens_overview)

save_four_column_plot(
  plot_data = weighted_tokens_overview,
  y_var = "mean_weighted_tokens",
  y_label = "Mean weighted tokens",
  title = "Mean weighted tokens by condition",
  filename = "weighted_tokens_overview_plot.pdf",
  digits = 0
)

# ------------------------------------------------------------
# 9. Runtime
# Baseline | Low | Moderate | High
# ------------------------------------------------------------

runtime_overview <- simulation_metrics %>%
  group_by(plot_condition) %>%
  summarise(
    total_runs = n(),
    mean_runtime_seconds = mean(runtime_seconds, na.rm = TRUE),
    .groups = "drop"
  )

print(runtime_overview)

save_four_column_plot(
  plot_data = runtime_overview,
  y_var = "mean_runtime_seconds",
  y_label = "Mean runtime in seconds",
  title = "Mean runtime until task completion by condition",
  filename = "runtime_overview_plot.pdf",
  digits = 2
)
