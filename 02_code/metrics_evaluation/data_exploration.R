# ============================================================
# Data exploration of generated simulation data
# ============================================================

# Empty workspace
if (!is.null(dev.list())) dev.off()
rm(list = ls())

library(tidyverse)
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
  "01_data/processed/simulation_metrics_20260508_080303.csv",
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
  levels = c("treatment", "baseline")
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
  "mean_gold_standard_memory_similarity",
  "min_gold_standard_memory_similarity",
  "max_gold_standard_memory_similarity",
  "context_alignment",
  grep("^similarity_", names(simulation_metrics), value = TRUE),
  grep("^gold_similarity_", names(simulation_metrics), value = TRUE)
)

simulation_metrics[numeric_columns] <- lapply(
  simulation_metrics[numeric_columns],
  as.numeric
)

# ------------------------------------------------------------
# 2. Calculate costs
# ------------------------------------------------------------
total_number_input_tokens = sum(simulation_metrics$input_tokens)
total_number_output_tokens = sum(simulation_metrics$output_tokens)

costs <- calculate_costs(
  input_tokens = total_number_input_tokens,
  output_tokens = total_number_output_tokens,
  context = "short"
)
print(costs)

condition_colors <- c(
  "low" = "#7BAF9E",
  "moderate" = "#D98C5F",
  "high" = "#6F84B8"
)

# ------------------------------------------------------------
# PLOT THEME
# ------------------------------------------------------------
plot_theme <- theme_minimal(base_size = 13) +
  theme(
    # Title
    plot.title = element_text(
      face = "bold",
      size = 15,
      hjust = 0, 
      margin = margin(b = 12)
    ),
    
    # Axis labels
    axis.title = element_text(
      face = "bold",
      size = 12
    ),
    
    # Axis text
    axis.text = element_text(
      color = "black",
      size = 11
    ),
    
    # Grid
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_line(linewidth = 0.3),
    
    # Legend
    legend.position = "none",
    
    # Plot spacing
    plot.margin = margin(10, 15, 10, 10)
  )

save_overview_plots <- function(mode_metrics, smm_mode) {
  file_prefix <- if (smm_mode == "treatment") "" else paste0(smm_mode, "_")
  title_suffix <- paste0(" (", smm_mode, ")")

  # ------------------------------------------------------------
  # 3a. Overview of correctly chosen candidates across conditions
  # ------------------------------------------------------------
  correct_candidate_overview <- mode_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      correct_choices = sum(decision_correct, na.rm = TRUE),
      correct_share = correct_choices / total_runs,
      .groups = "drop"
    )

  print(correct_candidate_overview)

  correct_candidate_overview_plot <- ggplot(correct_candidate_overview, aes(x = condition, y = correct_choices, fill = condition)) +
    geom_col() +
    geom_text(aes(label = correct_choices), vjust = -0.5) +
    labs(
      x = "Condition",
      y = "Correct choices",
      title = paste0("Correct candidate choices by condition", title_suffix)
    ) +
    scale_fill_manual(values = condition_colors) +
    plot_theme
  if (interactive()) print(correct_candidate_overview_plot)

  ggsave(
    filename = paste0(path, "/03_report/graphs/", file_prefix, "correct_candidate_overview_plot.pdf"),
    plot = correct_candidate_overview_plot,
    width = 7,
    height = 5
  )

  # ------------------------------------------------------------
  # 3b. Overview of NA final candidates across conditions
  # ------------------------------------------------------------
  na_candidate_overview <- mode_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      na_candidates = sum(is.na(final_candidate)),
      .groups = "drop"
    )

  print(na_candidate_overview)

  na_candidate_overview_plot <- ggplot(na_candidate_overview, aes(x = condition, y = na_candidates, fill = condition)) +
    geom_col() +
    geom_text(aes(label = na_candidates), vjust = -0.5) +
    labs(
      x = "Condition",
      y = "Number of runs",
      title = paste0("Runs without a final candidate by condition", title_suffix)
    ) +
    scale_fill_manual(values = condition_colors) +
    plot_theme
  if (interactive()) print(na_candidate_overview_plot)

  ggsave(
    filename = paste0(path, "/03_report/graphs/", file_prefix, "na_candidate_overview_plot.pdf"),
    plot = na_candidate_overview_plot,
    width = 7,
    height = 5
  )

  if (smm_mode == "treatment") {
    
    # ------------------------------------------------------------
    # 4. Overview of semantic similarity across conditions
    # ------------------------------------------------------------
    semantic_similarity_overview <- mode_metrics %>%
      group_by(condition) %>%
      summarise(
        total_runs = n(),
        mean_semantic_similarity = mean(mean_pairwise_memory_similarity, na.rm = TRUE),
        .groups = "drop"
      )
    
    print(semantic_similarity_overview)
    
    semantic_similarity_overview_plot <- ggplot(
      semantic_similarity_overview,
      aes(x = condition, y = mean_semantic_similarity, fill = condition)
    ) +
      geom_col() +
      geom_text(aes(label = round(mean_semantic_similarity, 3)), vjust = -0.5) +
      labs(
        x = "Condition",
        y = "Mean semantic similarity",
        title = paste0("Mean semantic similarity by condition", title_suffix)
      ) +
      scale_fill_manual(values = condition_colors) +
      plot_theme
    
    if (interactive()) print(semantic_similarity_overview_plot)
    
    ggsave(
      filename = paste0(path, "/03_report/graphs/", file_prefix, "semantic_similarity_overview_plot.pdf"),
      plot = semantic_similarity_overview_plot,
      width = 7,
      height = 5
    )
    
    # ------------------------------------------------------------
    # 4b. Overview of gold standard similarity across conditions
    # ------------------------------------------------------------
    gold_standard_similarity_overview <- mode_metrics %>%
      group_by(condition) %>%
      summarise(
        total_runs = n(),
        mean_gold_standard_similarity = mean(mean_gold_standard_memory_similarity, na.rm = TRUE),
        .groups = "drop"
      )
    
    print(gold_standard_similarity_overview)
    
    gold_standard_similarity_overview_plot <- ggplot(
      gold_standard_similarity_overview,
      aes(x = condition, y = mean_gold_standard_similarity, fill = condition)
    ) +
      geom_col() +
      geom_text(aes(label = round(mean_gold_standard_similarity, 3)), vjust = -0.5) +
      labs(
        x = "Condition",
        y = "Mean gold standard similarity",
        title = paste0("Mean gold standard similarity by condition", title_suffix)
      ) +
      scale_fill_manual(values = condition_colors) +
      plot_theme
    
    if (interactive()) print(gold_standard_similarity_overview_plot)
    
    ggsave(
      filename = paste0(path, "/03_report/graphs/", file_prefix, "gold_standard_similarity_overview_plot.pdf"),
      plot = gold_standard_similarity_overview_plot,
      width = 7,
      height = 5
    )
    
    # ------------------------------------------------------------
    # 4c. Overview of context alignment across conditions
    # ------------------------------------------------------------
    context_alignment_overview <- mode_metrics %>%
      group_by(condition) %>%
      summarise(
        total_runs = n(),
        mean_context_alignment = mean(context_alignment, na.rm = TRUE),
        .groups = "drop"
      )
    
    print(context_alignment_overview)
    
    context_alignment_overview_plot <- ggplot(
      context_alignment_overview,
      aes(x = condition, y = mean_context_alignment, fill = condition)
    ) +
      geom_col() +
      geom_text(aes(label = round(mean_context_alignment, 3)), vjust = -0.5) +
      labs(
        x = "Condition",
        y = "Mean context alignment",
        title = paste0("Mean context alignment by condition", title_suffix)
      ) +
      scale_fill_manual(values = condition_colors) +
      plot_theme
    
    if (interactive()) print(context_alignment_overview_plot)
    
    ggsave(
      filename = paste0(path, "/03_report/graphs/", file_prefix, "context_alignment_overview_plot.pdf"),
      plot = context_alignment_overview_plot,
      width = 7,
      height = 5
    )
  }

  # ------------------------------------------------------------
  # 5. Overview of interaction rounds across conditions
  # ------------------------------------------------------------
  rounds_overview <- mode_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      mean_rounds = mean(rounds, na.rm = TRUE),
      .groups = "drop"
    )

  print(rounds_overview)

  rounds_overview_plot <- ggplot(rounds_overview, aes(x = condition, y = mean_rounds, fill = condition)) +
    geom_col() +
    geom_text(aes(label = round(mean_rounds, 2)), vjust = -0.5) +
    labs(
      x = "Condition",
      y = "Mean rounds",
      title = paste0("Mean interaction rounds by condition", title_suffix)
    ) +
    scale_fill_manual(values = condition_colors) +
    plot_theme
  if (interactive()) print(rounds_overview_plot)

  ggsave(
    filename = paste0(path, "/03_report/graphs/", file_prefix, "rounds_overview_plot.pdf"),
    plot = rounds_overview_plot,
    width = 7,
    height = 5
  )

  # ------------------------------------------------------------
  # 6. Overview of messages across conditions
  # ------------------------------------------------------------
  messages_overview <- mode_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      mean_messages = mean(total_messages, na.rm = TRUE),
      .groups = "drop"
    )

  print(messages_overview)

  messages_overview_plot <- ggplot(messages_overview, aes(x = condition, y = mean_messages, fill = condition)) +
    geom_col() +
    geom_text(aes(label = round(mean_messages, 2)), vjust = -0.5) +
    labs(
      x = "Condition",
      y = "Mean messages",
      title = paste0("Mean messages by condition", title_suffix)
    ) +
    scale_fill_manual(values = condition_colors) +
    plot_theme
  if (interactive()) print(messages_overview_plot)

  ggsave(
    filename = paste0(path, "/03_report/graphs/", file_prefix, "messages_overview_plot.pdf"),
    plot = messages_overview_plot,
    width = 7,
    height = 5
  )

  # ------------------------------------------------------------
  # 7. Overview of tokens across conditions
  # ------------------------------------------------------------
  tokens_overview <- mode_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      mean_tokens = mean(total_tokens, na.rm = TRUE),
      .groups = "drop"
    )

  print(tokens_overview)

  tokens_overview_plot <- ggplot(tokens_overview, aes(x = condition, y = mean_tokens, fill = condition)) +
    geom_col() +
    geom_text(aes(label = round(mean_tokens, 0)), vjust = -0.5) +
    labs(
      x = "Condition",
      y = "Mean tokens",
      title = paste0("Mean tokens by condition", title_suffix)
    ) +
    scale_fill_manual(values = condition_colors) +
    plot_theme
  if (interactive()) print(tokens_overview_plot)

  ggsave(
    filename = paste0(path, "/03_report/graphs/", file_prefix, "tokens_overview_plot.pdf"),
    plot = tokens_overview_plot,
    width = 7,
    height = 5
  )

  # ------------------------------------------------------------
  # 8. Overview of runtime across conditions
  # ------------------------------------------------------------
  runtime_overview <- mode_metrics %>%
    group_by(condition) %>%
    summarise(
      total_runs = n(),
      mean_runtime_seconds = mean(runtime_seconds, na.rm = TRUE),
      .groups = "drop"
    )

  print(runtime_overview)

  runtime_overview_plot <- ggplot(runtime_overview, aes(x = condition, y = mean_runtime_seconds, fill = condition)) +
    geom_col() +
    geom_text(aes(label = round(mean_runtime_seconds, 2)), vjust = -0.5) +
    labs(
      x = "Condition",
      y = "Mean runtime in seconds",
      title = paste0("Mean runtime until task completion by condition", title_suffix)
    ) +
    scale_fill_manual(values = condition_colors) +
    plot_theme
  if (interactive()) print(runtime_overview_plot)

  ggsave(
    filename = paste0(path, "/03_report/graphs/", file_prefix, "runtime_overview_plot.pdf"),
    plot = runtime_overview_plot,
    width = 7,
    height = 5
  )
}

for (current_smm_mode in c("treatment", "baseline")) {
  mode_metrics <- simulation_metrics %>%
    filter(smm_mode == current_smm_mode)

  if (nrow(mode_metrics) > 0) {
    save_overview_plots(mode_metrics, current_smm_mode)
  }
}
