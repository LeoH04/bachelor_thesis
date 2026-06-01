# ============================================================
# Minimal outlier check for plotted simulation metrics
# ============================================================

options(width = 220, scipen = 999)

# ------------------------------------------------------------
# 1. Load data
# ------------------------------------------------------------

input_file <- "01_data/processed/simulation_metrics_20260530_091120.csv"

if (!file.exists(input_file)) {
  stop(paste("Metrics file not found:", input_file))
}

simulation_metrics <- read.csv(
  input_file,
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

# ------------------------------------------------------------
# 2. Create plotting condition
# ------------------------------------------------------------

simulation_metrics$plot_condition <- NA_character_
simulation_metrics$plot_condition[simulation_metrics$smm_mode == "baseline"] <- "Baseline"
simulation_metrics$plot_condition[
  simulation_metrics$smm_mode == "treatment" &
    simulation_metrics$context_transparency_condition == "low"
] <- "Low"
simulation_metrics$plot_condition[
  simulation_metrics$smm_mode == "treatment" &
    simulation_metrics$context_transparency_condition == "moderate"
] <- "Moderate"
simulation_metrics$plot_condition[
  simulation_metrics$smm_mode == "treatment" &
    simulation_metrics$context_transparency_condition == "high"
] <- "High"

simulation_metrics$plot_condition <- factor(
  simulation_metrics$plot_condition,
  levels = c("Baseline", "Low", "Moderate", "High")
)

# ------------------------------------------------------------
# 3. Define metrics to check
# ------------------------------------------------------------

metrics_to_check <- c(
  "rounds",
  "total_messages",
  "total_tokens",
  "runtime_seconds",
  "mean_pairwise_memory_similarity"
)

metrics_to_check <- intersect(metrics_to_check, names(simulation_metrics))

# ------------------------------------------------------------
# 4. Detect within-condition IQR outliers
# ------------------------------------------------------------

outlier_rows <- list()

for (metric in metrics_to_check) {
  simulation_metrics[[metric]] <- as.numeric(simulation_metrics[[metric]])

  for (condition in levels(simulation_metrics$plot_condition)) {
    condition_rows <- which(simulation_metrics$plot_condition == condition)
    values <- simulation_metrics[[metric]][condition_rows]
    complete_rows <- condition_rows[!is.na(values)]
    complete_values <- values[!is.na(values)]

    if (length(complete_values) == 0) {
      next
    }

    quartiles <- quantile(
      complete_values,
      probs = c(0.25, 0.75),
      na.rm = TRUE,
      names = FALSE
    )
    iqr_value <- IQR(complete_values, na.rm = TRUE)
    lower_bound <- quartiles[1] - 1.5 * iqr_value
    upper_bound <- quartiles[2] + 1.5 * iqr_value

    flagged_rows <- complete_rows[
      complete_values < lower_bound | complete_values > upper_bound
    ]

    if (length(flagged_rows) == 0) {
      next
    }

    outlier_rows[[length(outlier_rows) + 1]] <- data.frame(
      run_id = simulation_metrics$run_id[flagged_rows],
      condition = as.character(simulation_metrics$plot_condition[flagged_rows]),
      metric = metric,
      value = simulation_metrics[[metric]][flagged_rows],
      lower_bound = lower_bound,
      upper_bound = upper_bound,
      stringsAsFactors = FALSE
    )
  }
}

# ------------------------------------------------------------
# 5. Print results
# ------------------------------------------------------------

cat("\nOutlier check:", input_file, "\n")
cat("Rule: within-condition 1.5 * IQR\n")
cat("No rows were removed and no files were written.\n\n")

if (length(outlier_rows) == 0) {
  cat("No outliers found.\n")
} else {
  outliers <- do.call(rbind, outlier_rows)
  outliers <- outliers[order(outliers$metric, outliers$condition, outliers$value), ]

  summary_table <- aggregate(
    run_id ~ metric + condition,
    data = outliers,
    FUN = length
  )
  names(summary_table)[names(summary_table) == "run_id"] <- "outlier_count"

  cat("Summary:\n")
  print(summary_table, row.names = FALSE)

  cat("\nFlagged rows:\n")
  print(outliers, row.names = FALSE, digits = 6)
}
