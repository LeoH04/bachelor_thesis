# ============================================================
# Statistical tests and Word regression table for team process
#
# Mirrors statistical_effects_team_process.R, but exports the
# regression results as a Word table.
# ============================================================


# ------------------------------------------------------------
# 0. Setup
# ------------------------------------------------------------

if (!is.null(dev.list())) {
  dev.off()
}

rm(list = ls())

# Install once if necessary:
# install.packages(c(
#   "lmtest",
#   "sandwich",
#   "modelsummary",
#   "flextable",
#   "officer"
# ))

library(lmtest)
library(sandwich)
library(modelsummary)
library(flextable)
library(officer)

path <- getwd()
output_token_weight <- 5


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
  "regression_results_team_process_h1_h5.docx"
)

dir.create(
  output_dir,
  recursive = TRUE,
  showWarnings = FALSE
)


# ------------------------------------------------------------
# 2. Load data
# ------------------------------------------------------------

simulation_metrics <- read.csv(
  data_file,
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)


# ------------------------------------------------------------
# 3. Check required variables
# ------------------------------------------------------------

required_variables <- c(
  "smm_mode",
  "context_transparency_condition",
  "decision_correct",
  "team_process_communication",
  "team_process_cooperation",
  "input_tokens",
  "output_tokens"
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
# 4. H1a/H1b: SMM configurations versus baseline
# ------------------------------------------------------------

h1a_data <- subset(
  simulation_metrics,
  smm_mode %in% c("baseline", "treatment") &
    !is.na(team_process_communication) &
    !is.na(team_process_cooperation)
)

h1a_data$baseline <- as.numeric(
  h1a_data$smm_mode == "baseline"
)
h1a_data$low <- as.numeric(
  h1a_data$smm_mode == "treatment" &
    h1a_data$context_transparency_condition == "low"
)
h1a_data$moderate <- as.numeric(
  h1a_data$smm_mode == "treatment" &
    h1a_data$context_transparency_condition == "moderate"
)
h1a_data$high <- as.numeric(
  h1a_data$smm_mode == "treatment" &
    h1a_data$context_transparency_condition == "high"
)

h1a_data$team_process_communication <- as.numeric(
  h1a_data$team_process_communication
)

h1a_data$team_process_cooperation <- as.numeric(
  h1a_data$team_process_cooperation
)

h1a <- lm(
  team_process_communication ~ low + moderate + high,
  data = h1a_data
)

h1b <- lm(
  team_process_cooperation ~ low + moderate + high,
  data = h1a_data
)


# ------------------------------------------------------------
# 5. Prepare treatment data
# ------------------------------------------------------------

treatment_data <- subset(
  simulation_metrics,
  smm_mode == "treatment"
)

treatment_data$condition <- factor(
  treatment_data$context_transparency_condition,
  levels = c(
    "moderate",
    "low",
    "high"
  )
)
treatment_data$low <- as.numeric(
  treatment_data$context_transparency_condition == "low"
)
treatment_data$high <- as.numeric(
  treatment_data$context_transparency_condition == "high"
)

treatment_data$team_process_communication <- as.numeric(
  treatment_data$team_process_communication
)

treatment_data$team_process_cooperation <- as.numeric(
  treatment_data$team_process_cooperation
)

# H4a-H5b use moderate treatment as the omitted context-configuration group.
d <- simulation_metrics
d$baseline <- as.numeric(d$smm_mode == "baseline")
d$low <- as.numeric(
  d$smm_mode == "treatment" & d$context_transparency_condition == "low"
)
d$high <- as.numeric(
  d$smm_mode == "treatment" & d$context_transparency_condition == "high"
)
d$team_process_communication <- as.numeric(
  d$team_process_communication
)
d$team_process_cooperation <- as.numeric(
  d$team_process_cooperation
)

d$Effectiveness <- as.numeric(
  d$decision_correct
)

d$input_tokens <- as.numeric(
  d$input_tokens
)

d$output_tokens <- as.numeric(
  d$output_tokens
)

d$coordination_cost <- d$input_tokens +
  output_token_weight * d$output_tokens

d$Efficiency <- d$coordination_cost / 1000000
d$input_tokens_million <- d$input_tokens / 1000000
d$output_tokens_million <- d$output_tokens / 1000000

d <- d[
  complete.cases(
    d[, c(
      "team_process_communication",
      "team_process_cooperation",
      "baseline",
      "low",
      "high",
      "Efficiency",
      "input_tokens_million",
      "output_tokens_million",
      "Effectiveness"
    )]
  ),
]

if (
  !all(
    d$Effectiveness %in% c(0, 1)
  )
) {
  stop(
    paste(
      "Effectiveness must contain",
      "only 0 and 1."
    )
  )
}


# ------------------------------------------------------------
# 6. Fit regression models
# ------------------------------------------------------------

h2a_h3a <- lm(
  team_process_communication ~ low + high,
  data = treatment_data
)

h2b_h3b <- lm(
  team_process_cooperation ~ low + high,
  data = treatment_data
)

h4a_h5a <- lm(
  Efficiency ~ team_process_communication + team_process_cooperation +
    baseline + low + high,
  data = d
)

h4b_h5b <- glm(
  Effectiveness ~ team_process_communication + team_process_cooperation +
    baseline + low + high,
  data = d,
  family = binomial
)

models <- list(
  "H1a: Communication" = h1a,
  "H1b: Cooperation" = h1b,
  "H2a/H3a: Communication" = h2a_h3a,
  "H2b/H3b: Cooperation" = h2b_h3b,
  "H4a/H5a: Efficiency" = h4a_h5a,
  "H4b/H5b: Effectiveness" = h4b_h5b
)


# ------------------------------------------------------------
# 7. HC3 robust covariance matrices
# ------------------------------------------------------------

robust_vcov <- list(
  vcovHC(h1a, type = "HC3"),
  vcovHC(h1b, type = "HC3"),
  vcovHC(h2a_h3a, type = "HC3"),
  vcovHC(h2b_h3b, type = "HC3"),
  vcovHC(h4a_h5a, type = "HC3"),
  vcovHC(h4b_h5b, type = "HC3")
)

names(robust_vcov) <- names(models)


# ------------------------------------------------------------
# 8. Define table rows
# ------------------------------------------------------------

coefficient_map <- c(
  "(Intercept)" = "Intercept",
  "baseline" = "Baseline",
  "low" = "Low\u00A0transparency",
  "moderate" = "Moderate\u00A0transparency",
  "high" = "High\u00A0transparency",
  "team_process_communication" = "Communication",
  "team_process_cooperation" = "Cooperation"
)

goodness_of_fit_map <- data.frame(
  raw = c(
    "nobs",
    "r.squared",
    "adj.r.squared"
  ),
  clean = c(
    "Observations",
    "R²",
    "Adjusted\u00A0R²"
  ),
  fmt = c(
    0,
    3,
    3
  )
)


# ------------------------------------------------------------
# 9. Create table
# ------------------------------------------------------------

regression_table <- modelsummary(
  models,
  vcov = robust_vcov,
  coef_map = coefficient_map,
  gof_map = goodness_of_fit_map,
  fmt = 3,
  estimate = "{estimate}{stars}\n({std.error})",
  statistic = NULL,
  stars = c(
    "+" = 0.10,
    "*" = 0.05,
    "**" = 0.01,
    "***" = 0.001
  ),
  notes = NULL,
  output = "flextable"
)


# Replace the modelsummary header with the three-row structure used in the
# report table. Fixed labels and column widths below keep every header on one
# line; the only intentional line break in the body is before the standard
# error in each coefficient cell.
header_map <- data.frame(
  col_keys = regression_table$col_keys,
  model = c(
    "Model",
    "(1)",
    "(2)",
    "(3)",
    "(4)",
    "(5)",
    "(6)"
  ),
  estimator = c(
    "Estimator",
    "OLS",
    "OLS",
    "OLS",
    "OLS",
    "OLS",
    "Logit"
  ),
  dependent_variable = c(
    "Dependent\u00A0Variable",
    "Communication",
    "Cooperation",
    "Communication",
    "Cooperation",
    "Efficiency",
    "Effectiveness"
  ),
  check.names = FALSE,
  stringsAsFactors = FALSE
)

regression_table <- set_header_df(
  regression_table,
  mapping = header_map,
  key = "col_keys"
)


# ------------------------------------------------------------
# 10. Significance legend
# ------------------------------------------------------------

regression_table <- add_footer_lines(
  regression_table,
  values = paste0(
    "Note:\u00A0Heteroskedasticity-robust\u00A0HC3\u00A0standard\u00A0errors\u00A0in\u00A0parentheses.\u00A0",
    "+\u00A0p\u00A0<\u00A0.10,\u00A0",
    "*\u00A0p\u00A0<\u00A0.05,\u00A0",
    "**\u00A0p\u00A0<\u00A0.01,\u00A0",
    "***\u00A0p\u00A0<\u00A0.001"
  )
)


# ------------------------------------------------------------
# 11. Minimal LaTeX-style formatting
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

regression_table <- border_remove(
  regression_table
)

regression_table <- hline_top(
  regression_table,
  border = double_line,
  part = "header"
)

regression_table <- hline_bottom(
  regression_table,
  border = thin_line,
  part = "header"
)

regression_table <- hline(
  regression_table,
  i = 2,
  border = thin_line,
  part = "header"
)

regression_table <- hline_bottom(
  regression_table,
  border = thin_line,
  part = "body"
)

observations_row <- which(
  regression_table$body$dataset[[1]] == "Observations"
)

regression_table <- hline(
  regression_table,
  i = observations_row - 1,
  border = thin_line,
  part = "body"
)

regression_table <- font(
  regression_table,
  fontname = "Times New Roman",
  part = "all"
)

regression_table <- fontsize(
  regression_table,
  size = 9,
  part = "all"
)

regression_table <- bold(
  regression_table,
  part = "header"
)

regression_table <- bold(
  regression_table,
  j = 1,
  part = "body"
)

regression_table <- align(
  regression_table,
  align = "center",
  part = "all"
)

regression_table <- align(
  regression_table,
  j = 1,
  align = "left",
  part = "body"
)

regression_table <- align(
  regression_table,
  j = 1,
  align = "left",
  part = "header"
)

regression_table <- valign(
  regression_table,
  valign = "center",
  part = "all"
)

regression_table <- align(
  regression_table,
  align = "left",
  part = "footer"
)

regression_table <- fontsize(
  regression_table,
  size = 8,
  part = "footer"
)

regression_table <- padding(
  regression_table,
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "header"
)

regression_table <- padding(
  regression_table,
  padding.top = 3,
  padding.bottom = 3,
  padding.left = 2,
  padding.right = 2,
  part = "body"
)

regression_table <- padding(
  regression_table,
  i = observations_row:nrow(regression_table$body$dataset),
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "body"
)

regression_table <- padding(
  regression_table,
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "footer"
)

regression_table <- set_table_properties(
  regression_table,
  layout = "autofit",
  width = 1,
  opts_word = list(
    split = FALSE,
    repeat_headers = TRUE
  )
)


# ------------------------------------------------------------
# 12. Export to Word
# ------------------------------------------------------------

portrait_section <- prop_section(
  page_size = page_size(
    width = 8.27,
    height = 11.69,
    orient = "portrait",
    unit = "in"
  ),
  page_margins = page_mar(
    top = 0.35,
    bottom = 0.35,
    left = 0.2,
    right = 0.2,
    header = 0.2,
    footer = 0.2
  )
)

save_as_docx(
  regression_table,
  path = output_file,
  pr_section = portrait_section,
  align = "center"
)

cat(
  "\nTeam-process regression table exported to:\n",
  output_file,
  "\n",
  sep = ""
)
