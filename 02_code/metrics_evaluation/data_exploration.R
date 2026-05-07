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
simulation_metrics <- read.csv(
  "01_data/processed/simulation_metrics_20260506_181837.csv",
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

simulation_metrics$condition <- factor(
  simulation_metrics$condition,
  levels = c("low", "moderate", "high"),
  ordered = TRUE
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
  grep("^similarity_", names(simulation_metrics), value = TRUE)
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

# ------------------------------------------------------------
# 3. Overview of correctly chosen candidates across conditions
# ------------------------------------------------------------
correct_candidate_overview <- simulation_metrics %>%
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
    title = "Correct candidate choices by condition"
  ) + 
  scale_fill_manual(
    values = c(
      "low" = "#66C2A5",
      "moderate" = "#FC8D62",
      "high" = "#8DA0CB"
    )) +
  theme_classic()
if (interactive()) print(correct_candidate_overview_plot)

ggsave(
  filename = paste0(path, "/03_report/graphs/correct_candidate_overview_plot.pdf"),
  plot = correct_candidate_overview_plot,
  width = 7,
  height = 5
)

# ------------------------------------------------------------
# 4. Overview of semantic similarity across conditions
# ------------------------------------------------------------
semantic_similarity_overview <- simulation_metrics %>%
  group_by(condition) %>%
  summarise(
    total_runs = n(),
    mean_semantic_similarity = mean(mean_pairwise_memory_similarity, na.rm = TRUE),
    .groups = "drop"
  )

print(semantic_similarity_overview)

semantic_similarity_overview_plot <- ggplot(semantic_similarity_overview, aes(x = condition, y = mean_semantic_similarity, fill = condition)) +
  geom_col() +
  geom_text(aes(label = round(mean_semantic_similarity, 3)), vjust = -0.5) +
  labs(
    x = "Condition",
    y = "Mean semantic similarity",
    title = "Mean semantic similarity by condition"
  ) +
  scale_fill_manual(
    values = c(
      "low" = "#66C2A5",
      "moderate" = "#FC8D62",
      "high" = "#8DA0CB"
    )) +
  theme_classic()
if (interactive()) print(semantic_similarity_overview_plot)

ggsave(
  filename = paste0(path, "/03_report/graphs/semantic_similarity_overview_plot.pdf"),
  plot = semantic_similarity_overview_plot,
  width = 7,
  height = 5
)

# ------------------------------------------------------------
# 5. Overview of interaction rounds across conditions
# ------------------------------------------------------------
rounds_overview <- simulation_metrics %>%
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
    title = "Mean interaction rounds by condition"
  ) +
  scale_fill_manual(
    values = c(
      "low" = "#66C2A5",
      "moderate" = "#FC8D62",
      "high" = "#8DA0CB"
    )) +
  theme_classic()
if (interactive()) print(rounds_overview_plot)

ggsave(
  filename = paste0(path, "/03_report/graphs/rounds_overview_plot.pdf"),
  plot = rounds_overview_plot,
  width = 7,
  height = 5
)

# ------------------------------------------------------------
# 6. Overview of messages across conditions
# ------------------------------------------------------------
messages_overview <- simulation_metrics %>%
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
    title = "Mean messages by condition"
  ) +
  scale_fill_manual(
    values = c(
      "low" = "#66C2A5",
      "moderate" = "#FC8D62",
      "high" = "#8DA0CB"
    )) +
  theme_classic()
if (interactive()) print(messages_overview_plot)

ggsave(
  filename = paste0(path, "/03_report/graphs/messages_overview_plot.pdf"),
  plot = messages_overview_plot,
  width = 7,
  height = 5
)

# ------------------------------------------------------------
# 7. Overview of tokens across conditions
# ------------------------------------------------------------
tokens_overview <- simulation_metrics %>%
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
    title = "Mean tokens by condition"
  ) +
  scale_fill_manual(
    values = c(
      "low" = "#66C2A5",
      "moderate" = "#FC8D62",
      "high" = "#8DA0CB"
    )) +
  theme_classic()
if (interactive()) print(tokens_overview_plot)

ggsave(
  filename = paste0(path, "/03_report/graphs/tokens_overview_plot.pdf"),
  plot = tokens_overview_plot,
  width = 7,
  height = 5
)

# ------------------------------------------------------------
# 8. Overview of runtime across conditions
# ------------------------------------------------------------
runtime_overview <- simulation_metrics %>%
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
    title = "Mean runtime until task completion by condition"
  ) +
  scale_fill_manual(
    values = c(
      "low" = "#66C2A5",
      "moderate" = "#FC8D62",
      "high" = "#8DA0CB"
    )) +
  theme_classic()
if (interactive()) print(runtime_overview_plot)

ggsave(
  filename = paste0(path, "/03_report/graphs/runtime_overview_plot.pdf"),
  plot = runtime_overview_plot,
  width = 7,
  height = 5
)
