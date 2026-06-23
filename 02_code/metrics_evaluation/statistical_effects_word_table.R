# ============================================================
# Statistical tests and minimal Word regression table
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


# ------------------------------------------------------------
# 1. File paths
# ------------------------------------------------------------

data_file <- file.path(
  path,
  "01_data",
  "processed",
  "simulation_metrics_20260612_090103.csv"
)

output_dir <- file.path(
  path,
  "03_report",
  "tables"
)

output_file <- file.path(
  output_dir,
  "regression_results_h2_h4.docx"
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
  "smm_quality",
  "rounds",
  "total_messages",
  "total_tokens"
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
# 4. H1: Moderate treatment versus baseline
# ------------------------------------------------------------

smm_decisions <- subset(
  simulation_metrics,
  smm_mode == "treatment" &
    context_transparency_condition == "moderate" &
    !is.na(decision_correct)
)

baseline_decisions <- subset(
  simulation_metrics,
  smm_mode == "baseline" &
    !is.na(decision_correct)
)

smm_decisions$decision_correct <- as.numeric(
  smm_decisions$decision_correct
)

baseline_decisions$decision_correct <- as.numeric(
  baseline_decisions$decision_correct
)

if (nrow(smm_decisions) == 0) {
  stop("No moderate-treatment observations found.")
}

if (nrow(baseline_decisions) == 0) {
  stop("No baseline observations found.")
}

h1 <- prop.test(
  x = c(
    sum(smm_decisions$decision_correct),
    sum(baseline_decisions$decision_correct)
  ),
  n = c(
    nrow(smm_decisions),
    nrow(baseline_decisions)
  ),
  alternative = "greater"
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

d$smm_quality <- as.numeric(
  d$smm_quality
)

d$coordination_effectiveness <- as.numeric(
  d$decision_correct
)

d$rounds <- as.numeric(
  d$rounds
)

d$total_messages <- as.numeric(
  d$total_messages
)

d$total_tokens <- as.numeric(
  d$total_tokens
)


# ------------------------------------------------------------
# 6. Create coordination-efficiency measure
# ------------------------------------------------------------

efficiency_components <- scale(
  d[, c(
    "rounds",
    "total_messages",
    "total_tokens"
  )]
)

d$coordination_efficiency <- -rowMeans(
  efficiency_components
)

d <- d[
  complete.cases(
    d[, c(
      "condition",
      "smm_quality",
      "coordination_efficiency",
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
# 7. Fit models
# ------------------------------------------------------------

h2 <- lm(
  smm_quality ~ condition,
  data = d
)

h3 <- lm(
  coordination_efficiency ~ smm_quality + condition,
  data = d
)

h4 <- glm(
  coordination_effectiveness ~ smm_quality + condition,
  data = d,
  family = binomial
)

models <- list(
  "H2a/H2b: Context quality" = h2,
  "H3: Coordination efficiency" = h3,
  "H4: Coordination effectiveness" = h4
)


# ------------------------------------------------------------
# 8. HC3 robust covariance matrices
# ------------------------------------------------------------

robust_vcov <- list(
  vcovHC(h2, type = "HC3"),
  vcovHC(h3, type = "HC3"),
  vcovHC(h4, type = "HC3")
)

names(robust_vcov) <- names(models)


# ------------------------------------------------------------
# 9. Console output
# ------------------------------------------------------------

robust_results <- Map(
  function(model, covariance_matrix) {
    coeftest(
      model,
      vcov. = covariance_matrix
    )
  },
  models,
  robust_vcov
)

cat("\nH1: Moderate treatment versus baseline\n")
print(h1)

cat("\nContext quality\n")
print(robust_results[[1]])

cat("\nCoordination efficiency\n")
print(robust_results[[2]])

cat("\nCoordination effectiveness\n")
print(robust_results[[3]])


# ------------------------------------------------------------
# 10. Define table rows
# ------------------------------------------------------------

coefficient_map <- c(
  "(Intercept)" = "Intercept",
  "smm_quality" = "Context quality",
  "conditionlow" = "Low transparency",
  "conditionhigh" = "High transparency"
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
# 11. Create table
# ------------------------------------------------------------

regression_table <- modelsummary(
  models,
  vcov = robust_vcov,
  coef_map = coefficient_map,
  gof_map = goodness_of_fit_map,
  fmt = 3,
  
  # Estimate and robust SE in the same cell
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
# 12. Significance legend
# ------------------------------------------------------------

regression_table <- add_footer_lines(
  regression_table,
  values = "+ p < .10, * p < .05, ** p < .01, *** p < .001"
)


# ------------------------------------------------------------
# 13. Minimal LaTeX-style formatting
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
  size = 10,
  part = "all"
)

regression_table <- bold(
  regression_table,
  part = "header"
)

# Center all table content first
regression_table <- align(
  regression_table,
  align = "center",
  part = "all"
)

# Left-align variable names in the body
regression_table <- align(
  regression_table,
  j = 1,
  align = "left",
  part = "body"
)

# Left-align the first header cell
regression_table <- align(
  regression_table,
  j = 1,
  align = "left",
  part = "header"
)

# Left-align significance legend
regression_table <- align(
  regression_table,
  align = "left",
  part = "footer"
)

regression_table <- fontsize(
  regression_table,
  size = 9,
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
# 14. Export to Word
# ------------------------------------------------------------

save_as_docx(
  regression_table,
  path = output_file
)

cat(
  "\nRegression table exported to:\n",
  output_file,
  "\n",
  sep = ""
)