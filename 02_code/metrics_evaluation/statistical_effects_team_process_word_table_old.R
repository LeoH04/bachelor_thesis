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
  "simulation_metrics_final_100_gpt_oss_120b.csv"
)

output_dir <- file.path(
  path,
  "03_report",
  "tables"
)

output_file <- file.path(
  output_dir,
  "regression_results_team_process_h1_h3.docx"
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
  "team_process_score",
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
# 4. H1a: Average SMM treatment team process versus baseline
# ------------------------------------------------------------

h1a_data <- subset(
  simulation_metrics,
  smm_mode %in% c("baseline", "treatment") &
    !is.na(team_process_score)
)

h1a_data$smm_treatment <- factor(
  ifelse(
    h1a_data$smm_mode == "treatment",
    "treatment",
    "baseline"
  ),
  levels = c("baseline", "treatment")
)

h1a_data$team_process_score <- as.numeric(
  h1a_data$team_process_score
)

h1a <- lm(
  team_process_score ~ smm_treatment,
  data = h1a_data
)


# ------------------------------------------------------------
# 5. Prepare treatment data
# ------------------------------------------------------------

d <- subset(
  simulation_metrics,
  smm_mode == "treatment"
)

d$condition <- factor(
  d$context_transparency_condition,
  levels = c(
    "moderate",
    "low",
    "high"
  )
)

d$team_process_score <- as.numeric(
  d$team_process_score
)

d$coordination_effectiveness <- as.numeric(
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

d$coordination_cost_million <- d$coordination_cost / 1000000
d$input_tokens_million <- d$input_tokens / 1000000
d$output_tokens_million <- d$output_tokens / 1000000

d <- d[
  complete.cases(
    d[, c(
      "condition",
      "team_process_score",
      "coordination_cost_million",
      "input_tokens_million",
      "output_tokens_million",
      "coordination_effectiveness"
    )]
  ),
]

if (
  !all(
    d$coordination_effectiveness %in% c(0, 1)
  )
) {
  stop(
    paste(
      "coordination_effectiveness must contain",
      "only 0 and 1."
    )
  )
}


# ------------------------------------------------------------
# 6. Fit regression models
# ------------------------------------------------------------

h1bc <- lm(
  team_process_score ~ condition,
  data = d
)

h2 <- lm(
  coordination_cost_million ~ team_process_score + condition,
  data = d
)

h2_input <- lm(
  input_tokens_million ~ team_process_score + condition,
  data = d
)

h2_output <- lm(
  output_tokens_million ~ team_process_score + condition,
  data = d
)

h3 <- glm(
  coordination_effectiveness ~ team_process_score + condition,
  data = d,
  family = binomial
)

models <- list(
  "H1a: Team process" = h1a,
  "H1b/c: Team process" = h1bc,
  "H2: Token cost (m)" = h2,
  "H2a: Input (m)" = h2_input,
  "H2b: Output (m)" = h2_output,
  "H3: Correct decision" = h3
)


# ------------------------------------------------------------
# 7. HC3 robust covariance matrices
# ------------------------------------------------------------

robust_vcov <- list(
  vcovHC(h1a, type = "HC3"),
  vcovHC(h1bc, type = "HC3"),
  vcovHC(h2, type = "HC3"),
  vcovHC(h2_input, type = "HC3"),
  vcovHC(h2_output, type = "HC3"),
  vcovHC(h3, type = "HC3")
)

names(robust_vcov) <- names(models)


# ------------------------------------------------------------
# 8. Define table rows
# ------------------------------------------------------------

coefficient_map <- c(
  "(Intercept)" = "Intercept",
  "smm_treatmenttreatment" = "SMM treatment",
  "conditionlow" = "Low transparency",
  "conditionhigh" = "High transparency",
  "team_process_score" = "Team process"
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
    "Adjusted R²"
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


# ------------------------------------------------------------
# 10. Significance legend
# ------------------------------------------------------------

regression_table <- add_footer_lines(
  regression_table,
  values = paste(
    "+ p < .10, * p < .05, ** p < .01, *** p < .001"
  )
)


# ------------------------------------------------------------
# 11. Minimal LaTeX-style formatting
# ------------------------------------------------------------

thin_line <- fp_border(
  width = 0.5
)

thick_line <- fp_border(
  width = 1
)

regression_table <- border_remove(
  regression_table
)

regression_table <- hline_top(
  regression_table,
  border = thick_line,
  part = "header"
)

regression_table <- hline_bottom(
  regression_table,
  border = thin_line,
  part = "header"
)

regression_table <- hline_bottom(
  regression_table,
  border = thick_line,
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
  padding.top = 3,
  padding.bottom = 3,
  padding.left = 3,
  padding.right = 3,
  part = "all"
)

regression_table <- autofit(
  regression_table
)

regression_table <- set_table_properties(
  regression_table,
  layout = "autofit",
  width = 1
)


# ------------------------------------------------------------
# 12. Export to Word
# ------------------------------------------------------------

save_as_docx(
  regression_table,
  path = output_file
)

cat(
  "\nTeam-process regression table exported to:\n",
  output_file,
  "\n",
  sep = ""
)
