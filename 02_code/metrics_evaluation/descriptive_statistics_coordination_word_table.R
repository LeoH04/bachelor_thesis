# ============================================================
# Descriptive statistics Word table for coordination outcomes
#
# Reports the outcomes shown in the interaction-rounds,
# messages, tool-calls, and runtime overview plots.
# ============================================================


# ------------------------------------------------------------
# 0. Setup
# ------------------------------------------------------------

if (!is.null(dev.list())) {
  dev.off()
}

rm(list = ls())

library(dplyr)
library(tidyr)
library(flextable)
library(officer)

path <- getwd()


# ------------------------------------------------------------
# 1. File paths
# ------------------------------------------------------------

data_file <- file.path(
  path,
  "01_data",
  "processed",
  "simulation_metrics_final_200_gpt_oss_120b.csv"
)

output_dir <- file.path(
  path,
  "03_report",
  "tables"
)

output_file <- file.path(
  output_dir,
  "descriptive_statistics_coordination.docx"
)

cm_to_in <- function(x) {
  x / 2.54
}

thesis_section <- prop_section(
  page_size = page_size(
    width = cm_to_in(21.0),
    height = cm_to_in(29.7),
    orient = "portrait",
    unit = "in"
  ),
  page_margins = page_mar(
    top = cm_to_in(3.0),
    bottom = cm_to_in(2.0),
    left = cm_to_in(2.5),
    right = cm_to_in(2.5),
    header = cm_to_in(1.5),
    footer = cm_to_in(1.25)
  )
)

dir.create(
  output_dir,
  recursive = TRUE,
  showWarnings = FALSE
)


# ------------------------------------------------------------
# 2. Load and validate data
# ------------------------------------------------------------

simulation_metrics <- read.csv(
  data_file,
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

required_variables <- c(
  "smm_mode",
  "context_transparency_condition",
  "rounds",
  "total_messages",
  "agent_tool_calls",
  "runtime_seconds"
)

missing_variables <- setdiff(
  required_variables,
  names(simulation_metrics)
)

if (length(missing_variables) > 0) {
  stop(
    paste0(
      "Missing required variables: ",
      paste(missing_variables, collapse = ", ")
    )
  )
}


# ------------------------------------------------------------
# 3. Prepare experimental conditions and measures
# ------------------------------------------------------------

simulation_metrics <- simulation_metrics %>%
  mutate(
    smm_mode = tolower(trimws(as.character(smm_mode))),
    plot_condition = case_when(
      smm_mode == "baseline" ~ "Baseline",
      smm_mode == "treatment" &
        context_transparency_condition == "low" ~ "Low",
      smm_mode == "treatment" &
        context_transparency_condition == "moderate" ~ "Moderate",
      smm_mode == "treatment" &
        context_transparency_condition == "high" ~ "High",
      TRUE ~ NA_character_
    ),
    plot_condition = factor(
      plot_condition,
      levels = c("Baseline", "Low", "Moderate", "High")
    ),
    rounds = as.numeric(rounds),
    total_messages = as.numeric(total_messages),
    agent_tool_calls = as.numeric(agent_tool_calls),
    runtime_seconds = as.numeric(runtime_seconds)
  ) %>%
  filter(!is.na(plot_condition))

long_data <- simulation_metrics %>%
  select(
    plot_condition,
    rounds,
    total_messages,
    agent_tool_calls,
    runtime_seconds
  ) %>%
  pivot_longer(
    cols = -plot_condition,
    names_to = "measure",
    values_to = "value"
  ) %>%
  mutate(
    measure = factor(
      measure,
      levels = c(
        "rounds",
        "total_messages",
        "agent_tool_calls",
        "runtime_seconds"
      ),
      labels = c(
        "Interaction rounds",
        "Total public messages",
        "Tool calls",
        "Runtime (seconds)"
      )
    )
  )


# ------------------------------------------------------------
# 4. Calculate descriptive statistics
# ------------------------------------------------------------

descriptive_summary <- long_data %>%
  group_by(measure, plot_condition) %>%
  summarise(
    observations = sum(!is.na(value)),
    mean = mean(value, na.rm = TRUE),
    standard_deviation = sd(value, na.rm = TRUE),
    .groups = "drop"
  )

print(descriptive_summary)

formatted_statistics <- descriptive_summary %>%
  mutate(
    statistic = sprintf(
      "%.2f\n(%.2f)",
      mean,
      standard_deviation
    )
  ) %>%
  select(measure, plot_condition, statistic) %>%
  pivot_wider(
    names_from = plot_condition,
    values_from = statistic
  ) %>%
  arrange(measure) %>%
  rename(Measure = measure)

observations_row <- descriptive_summary %>%
  group_by(plot_condition) %>%
  summarise(
    observations = sprintf("%d", min(observations)),
    .groups = "drop"
  ) %>%
  select(plot_condition, observations) %>%
  pivot_wider(
    names_from = plot_condition,
    values_from = observations
  ) %>%
  mutate(Measure = "Observations", .before = 1)

table_data <- bind_rows(
  formatted_statistics,
  observations_row
)


# ------------------------------------------------------------
# 5. Create table
# ------------------------------------------------------------

descriptive_table <- flextable(table_data)

header_map <- data.frame(
  col_keys = descriptive_table$col_keys,
  condition = c(
    "Condition",
    "Baseline",
    "Low",
    "Moderate",
    "High"
  ),
  statistic = c(
    "Statistic",
    "Mean (SD)",
    "Mean (SD)",
    "Mean (SD)",
    "Mean (SD)"
  ),
  check.names = FALSE,
  stringsAsFactors = FALSE
)

descriptive_table <- set_header_df(
  descriptive_table,
  mapping = header_map,
  key = "col_keys"
)

descriptive_table <- add_footer_lines(
  descriptive_table,
  values = "Note:\u00A0Cells report means with standard deviations in parentheses."
)


# ------------------------------------------------------------
# 6. Minimal LaTeX-style formatting
# ------------------------------------------------------------

thin_line <- fp_border(
  color = "black",
  style = "solid",
  width = 0.75
)

double_line <- fp_border(
  color = "black",
  style = "double",
  width = 1
)

descriptive_table <- border_remove(descriptive_table)

descriptive_table <- hline_top(
  descriptive_table,
  border = double_line,
  part = "header"
)

descriptive_table <- hline_bottom(
  descriptive_table,
  border = thin_line,
  part = "header"
)

descriptive_table <- hline(
  descriptive_table,
  i = 1,
  border = thin_line,
  part = "header"
)

descriptive_table <- hline_bottom(
  descriptive_table,
  border = thin_line,
  part = "body"
)

observations_row_index <- which(
  descriptive_table$body$dataset[[1]] == "Observations"
)

descriptive_table <- hline(
  descriptive_table,
  i = observations_row_index - 1,
  border = thin_line,
  part = "body"
)

descriptive_table <- font(
  descriptive_table,
  fontname = "Times New Roman",
  part = "all"
)

descriptive_table <- fontsize(
  descriptive_table,
  size = 11,
  part = "all"
)

descriptive_table <- bold(
  descriptive_table,
  part = "header"
)

descriptive_table <- bold(
  descriptive_table,
  j = 1,
  part = "body"
)

descriptive_table <- align(
  descriptive_table,
  align = "center",
  part = "all"
)

descriptive_table <- align(
  descriptive_table,
  j = 1,
  align = "left",
  part = "header"
)

descriptive_table <- align(
  descriptive_table,
  j = 1,
  align = "left",
  part = "body"
)

descriptive_table <- valign(
  descriptive_table,
  valign = "center",
  part = "all"
)

descriptive_table <- align(
  descriptive_table,
  align = "left",
  part = "footer"
)

descriptive_table <- fontsize(
  descriptive_table,
  size = 10,
  part = "footer"
)

descriptive_table <- padding(
  descriptive_table,
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "header"
)

descriptive_table <- padding(
  descriptive_table,
  padding.top = 3,
  padding.bottom = 3,
  padding.left = 2,
  padding.right = 2,
  part = "body"
)

descriptive_table <- padding(
  descriptive_table,
  i = observations_row_index,
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "body"
)

descriptive_table <- padding(
  descriptive_table,
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "footer"
)

descriptive_table <- set_table_properties(
  descriptive_table,
  layout = "autofit",
  width = 1,
  opts_word = list(
    split = TRUE,
    repeat_headers = FALSE
  )
)


# ------------------------------------------------------------
# 7. Export to Word
# ------------------------------------------------------------

save_as_docx(
  descriptive_table,
  path = output_file,
  pr_section = thesis_section,
  align = "center"
)

cat(
  "\nDescriptive-statistics table exported to:\n",
  output_file,
  "\n",
  sep = ""
)
