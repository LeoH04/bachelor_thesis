# ============================================================
# Data exploration of generated simulation data
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
# simulation_metric_files <- list.files(
#   "01_data/processed",
#   pattern = "^simulation_metrics_.*\\.csv$",
#   full.names = TRUE
# )
# latest_simulation_metric_file <- sort(simulation_metric_files, decreasing = TRUE)[1]
# 
# simulation_metrics <- read.csv(
#   latest_simulation_metric_file,
#   na.strings = c("", "NA"),
#   stringsAsFactors = FALSE
# )

simulation_metrics <- read.csv(
  "01_data/processed/simulation_metrics_20260517_214240.csv",
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

simulation_metrics$condition <- factor(
  simulation_metrics$condition,
  levels = c("low", "moderate", "high"),
  ordered = TRUE
)

simulation_metrics$smm_mode <- factor(
  simulation_metrics$smm_mode,
  levels = c("baseline", "treatment")
)

simulation_metrics$run_tag <- factor(simulation_metrics$run_tag)
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

simulation_metrics[integer_columns] <- lapply(
  simulation_metrics[integer_columns],
  as.integer
)

numeric_columns <- c(
  "runtime_seconds",
  "mean_pairwise_memory_similarity",
  "min_pairwise_memory_similarity",
  "max_pairwise_memory_similarity",
  "mean_gold_standard_alignment",
  "min_gold_standard_alignment",
  "max_gold_standard_alignment",
  "mean_public_facts",
  "mean_public_fact_coverage",
  "mean_own_private_facts",
  "mean_own_private_fact_coverage",
  "mean_other_private_facts",
  "mean_other_private_fact_coverage",
  "context_alignment",
  grep("^similarity_", names(simulation_metrics), value = TRUE),
  grep("^gold_alignment_", names(simulation_metrics), value = TRUE),
  grep("^gold_check_", names(simulation_metrics), value = TRUE)
)

simulation_metrics[numeric_columns] <- lapply(
  simulation_metrics[numeric_columns],
  as.numeric
)

# ------------------------------------------------------------
# 2. Calculate costs
# ------------------------------------------------------------
total_number_input_tokens <- sum(simulation_metrics$input_tokens)
total_number_output_tokens <- sum(simulation_metrics$output_tokens)

costs <- calculate_costs(
  input_tokens = total_number_input_tokens,
  output_tokens = total_number_output_tokens,
  context = "short"
)

print(costs)

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
# Helper function for baseline + treatment comparison plots
# ------------------------------------------------------------
save_comparison_plot <- function(plot_data, y_var, y_label, title, filename, digits = 2) {
  
  y_max <- max(plot_data[[y_var]], na.rm = TRUE)
  
  if (!is.finite(y_max) || y_max == 0) {
    y_max <- 1
  }
  
  comparison_plot <- ggplot(
    plot_data,
    aes(x = condition, y = .data[[y_var]], fill = smm_mode)
  ) +
    geom_col(
      position = position_dodge(width = 0.75),
      width = 0.65
    ) +
    geom_text(
      aes(label = round(.data[[y_var]], digits)),
      position = position_dodge(width = 0.75),
      vjust = -0.4,
      size = 3.6
    ) +
    scale_fill_manual(
      values = c(
        "baseline" = "grey70",
        "treatment" = "grey35"
      ),
      name = NULL,
      labels = c(
        "Baseline",
        "Treatment"
      )
    ) +
    scale_y_continuous(
      limits = c(0, y_max * 1.15),
      expand = expansion(mult = c(0, 0))
    ) +
    labs(
      x = "Condition",
      y = y_label,
      title = title,
    ) +
    plot_theme +
    theme(
      legend.position = "top",
      plot.subtitle = element_text(
        size = 11,
        margin = margin(b = 10)
      )
    )
  
  if (interactive()) print(comparison_plot)
  
  ggsave(
    filename = paste0(path, "/03_report/graphs/", filename),
    plot = comparison_plot,
    width = 8,
    height = 5
  )
}

# ------------------------------------------------------------
# Helper function for treatment-only plots
# ------------------------------------------------------------
save_single_mode_plot <- function(plot_data, y_var, y_label, title, filename, digits = 3, y_limits = NULL) {
  
  if (is.null(y_limits)) {
    y_max <- max(plot_data[[y_var]], na.rm = TRUE)
    
    if (!is.finite(y_max) || y_max == 0) {
      y_max <- 1
    }
    
    y_limits <- c(0, y_max * 1.15)
  }
  
  single_mode_plot <- ggplot(
    plot_data,
    aes(x = condition, y = .data[[y_var]])
  ) +
    geom_col(
      width = 0.65,
      fill = "grey35"
    ) +
    geom_text(
      aes(label = round(.data[[y_var]], digits)),
      vjust = -0.4,
      size = 3.6
    ) +
    scale_y_continuous(
      limits = y_limits,
      expand = expansion(mult = c(0, 0))
    ) +
    labs(
      x = "Condition",
      y = y_label,
      title = title,
      subtitle = "Treatment condition only"
    ) +
    plot_theme +
    theme(
      plot.subtitle = element_text(
        size = 11,
        margin = margin(b = 10)
      )
    )
  
  if (interactive()) print(single_mode_plot)
  
  ggsave(
    filename = paste0(path, "/03_report/graphs/", filename),
    plot = single_mode_plot,
    width = 8,
    height = 5
  )
}
# ------------------------------------------------------------
# 3a. Correct candidate choices: baseline vs treatment
# ------------------------------------------------------------
correct_candidate_overview <- simulation_metrics %>%
  group_by(smm_mode, condition) %>%
  summarise(
    total_runs = n(),
    correct_choices = sum(decision_correct, na.rm = TRUE),
    correct_share = correct_choices / total_runs,
    .groups = "drop"
  )

print(correct_candidate_overview)

save_comparison_plot(
  plot_data = correct_candidate_overview,
  y_var = "correct_choices",
  y_label = "Correct choices",
  title = "Correct candidate choices by condition",
  filename = "correct_candidate_overview_plot.pdf",
  digits = 0
)

# ------------------------------------------------------------
# 3b. NA final candidates: baseline vs treatment
# ------------------------------------------------------------
na_candidate_overview <- simulation_metrics %>%
  group_by(smm_mode, condition) %>%
  summarise(
    total_runs = n(),
    na_candidates = sum(is.na(final_candidate)),
    .groups = "drop"
  )

print(na_candidate_overview)

save_comparison_plot(
  plot_data = na_candidate_overview,
  y_var = "na_candidates",
  y_label = "Number of runs",
  title = "Runs without a final candidate by condition",
  filename = "na_candidate_overview_plot.pdf",
  digits = 0
)

# ------------------------------------------------------------
# 4. Treatment-only metrics
# These cannot be compared to baseline unless baseline has values.
# ------------------------------------------------------------
treatment_metrics <- simulation_metrics %>%
  filter(smm_mode == "treatment")

if (nrow(treatment_metrics) > 0) {
  
  # ------------------------------------------------------------
  # 4a. Semantic similarity across conditions
  # ------------------------------------------------------------
  semantic_similarity_overview <- treatment_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      mean_semantic_similarity = mean(mean_pairwise_memory_similarity, na.rm = TRUE),
      .groups = "drop"
    )
  
  print(semantic_similarity_overview)
  
  save_single_mode_plot(
    plot_data = semantic_similarity_overview,
    y_var = "mean_semantic_similarity",
    y_label = "Mean semantic similarity",
    title = "Mean semantic similarity by condition",
    filename = "semantic_similarity_overview_plot.pdf",
    digits = 3,
    y_limits = c(0, 1)
  )
  
  # ------------------------------------------------------------
  # 4b. Gold standard alignment across conditions
  # ------------------------------------------------------------
  gold_standard_alignment_overview <- treatment_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      mean_gold_standard_alignment = mean(mean_gold_standard_alignment, na.rm = TRUE),
      .groups = "drop"
    )
  
  print(gold_standard_alignment_overview)
  
  save_single_mode_plot(
    plot_data = gold_standard_alignment_overview,
    y_var = "mean_gold_standard_alignment",
    y_label = "Mean gold standard alignment",
    title = "Mean gold standard alignment by condition",
    filename = "gold_standard_alignment_overview_plot.pdf",
    digits = 3,
    y_limits = c(0, 1)
  )
  
  # ------------------------------------------------------------
  # 4c. Context alignment across conditions
  # ------------------------------------------------------------
  context_alignment_overview <- treatment_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      mean_context_alignment = mean(context_alignment, na.rm = TRUE),
      .groups = "drop"
    )
  
  print(context_alignment_overview)
  
  save_single_mode_plot(
    plot_data = context_alignment_overview,
    y_var = "mean_context_alignment",
    y_label = "Mean context alignment",
    title = "Mean context alignment by condition",
    filename = "context_alignment_overview_plot.pdf",
    digits = 3,
    y_limits = c(0, 1)
  )
}

# ------------------------------------------------------------
# 5. Messages: baseline vs treatment
# ------------------------------------------------------------
messages_overview <- simulation_metrics %>%
  group_by(smm_mode, condition) %>%
  summarise(
    total_runs = n(),
    mean_messages = mean(total_messages, na.rm = TRUE),
    .groups = "drop"
  )

print(messages_overview)

save_comparison_plot(
  plot_data = messages_overview,
  y_var = "mean_messages",
  y_label = "Mean messages",
  title = "Mean messages by condition",
  filename = "messages_overview_plot.pdf",
  digits = 2
)

# ------------------------------------------------------------
# 6. Tokens: baseline vs treatment
# ------------------------------------------------------------
tokens_overview <- simulation_metrics %>%
  group_by(smm_mode, condition) %>%
  summarise(
    total_runs = n(),
    mean_tokens = mean(total_tokens, na.rm = TRUE),
    .groups = "drop"
  )

print(tokens_overview)

save_comparison_plot(
  plot_data = tokens_overview,
  y_var = "mean_tokens",
  y_label = "Mean tokens",
  title = "Mean tokens by condition",
  filename = "tokens_overview_plot.pdf",
  digits = 0
)

# ------------------------------------------------------------
# 7. Runtime: baseline vs treatment
# ------------------------------------------------------------
runtime_overview <- simulation_metrics %>%
  group_by(smm_mode, condition) %>%
  summarise(
    total_runs = n(),
    mean_runtime_seconds = mean(runtime_seconds, na.rm = TRUE),
    .groups = "drop"
  )

print(runtime_overview)

save_comparison_plot(
  plot_data = runtime_overview,
  y_var = "mean_runtime_seconds",
  y_label = "Mean runtime in seconds",
  title = "Mean runtime until task completion by condition",
  filename = "runtime_overview_plot.pdf",
  digits = 2
)