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

library(sandwich)
library(modelsummary)
library(flextable)
library(officer)
library(performance)
library(emmeans)

path <- getwd()
output_token_weight <- 5


# ------------------------------------------------------------
# 1. File paths
# ------------------------------------------------------------

data_file <- file.path(
  path,
  "01_data",
  "processed",
  "simulation_metrics_final_200_plus_low_high_baseline.csv"
)

output_dir <- file.path(
  path,
  "03_report",
  "tables"
)

output_file <- file.path(
  output_dir,
  "regression_results_team_process_h1_h5_extended.docx"
)

h1_effects_output_file <- file.path(
  output_dir,
  "h1_simple_effects_team_process.docx"
)

tool_calls_output_file <- file.path(
  output_dir,
  "regression_tool_calls_mechanism.docx"
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
# 4. H1-H3: hypothesis-specific team-process models
# ------------------------------------------------------------

# H1 uses the full factorial model so the memory effect and its variation by
# access level remain visible. Moderate access is the reference level; the
# interaction terms show whether the memory effect changes at low or high
# access. H2 and H3 use separate treatment-only models below.
h1_data <- subset(
  simulation_metrics,
  smm_mode %in% c("baseline", "treatment") &
    context_transparency_condition %in% c("low", "moderate", "high") &
    !is.na(team_process_communication) &
    !is.na(team_process_cooperation)
)

h1_data$smm_mode <- factor(
  h1_data$smm_mode,
  levels = c("baseline", "treatment")
)

h1_data$context_transparency_condition <- factor(
  h1_data$context_transparency_condition,
  levels = c("moderate", "low", "high")
)

h1a <- lm(
  team_process_communication ~ smm_mode * context_transparency_condition,
  data = h1_data
)

h1b <- lm(
  team_process_cooperation ~ smm_mode * context_transparency_condition,
  data = h1_data
)

# Mechanism model: test whether structured memory and context access are
# associated with the frequency of targeted agent-tool calls. Moderate access
# and baseline runs are the reference categories; the interaction tests
# whether the access effect differs between memory conditions.
tool_calls_data <- subset(
  simulation_metrics,
  !is.na(agent_tool_calls) &
    !is.na(smm_mode) &
    !is.na(context_transparency_condition)
)

tool_calls_data$smm_mode <- factor(
  tool_calls_data$smm_mode,
  levels = c("baseline", "treatment")
)

tool_calls_data$context_transparency_condition <- factor(
  tool_calls_data$context_transparency_condition,
  levels = c("moderate", "low", "high")
)

tool_calls_model <- lm(
  agent_tool_calls ~ smm_mode * context_transparency_condition,
  data = tool_calls_data
)

# H2/H3 compare low and high access with moderate access within treatment
# runs. Moderate is omitted as the reference category, so the low and high
# coefficients are the access contrasts relative to moderate.
treatment_data <- subset(h1_data, smm_mode == "treatment")
treatment_data$low <- as.numeric(
  treatment_data$context_transparency_condition == "low"
)
treatment_data$high <- as.numeric(
  treatment_data$context_transparency_condition == "high"
)

h2a_h3a <- lm(
  team_process_communication ~ low + high,
  data = treatment_data
)

h2b_h3b <- lm(
  team_process_cooperation ~ low + high,
  data = treatment_data
)


# ------------------------------------------------------------
# 5. Prepare data for H4/H5
# ------------------------------------------------------------

# H4a-H5b control for the complete six-cell SMM-by-context-access design.
# Moderate baseline is the reference cell, as in the H1-H3 models.
d <- simulation_metrics
d$smm_mode <- factor(
  d$smm_mode,
  levels = c("baseline", "treatment")
)
d$context_transparency_condition <- factor(
  d$context_transparency_condition,
  levels = c("moderate", "low", "high")
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
      "smm_mode",
      "context_transparency_condition",
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

h4a_h4b <- lm(
  Efficiency ~ team_process_communication + team_process_cooperation +
    smm_mode * context_transparency_condition,
  data = d
)

h5a_h5b <- glm(
  Effectiveness ~ team_process_communication + team_process_cooperation +
    smm_mode * context_transparency_condition,
  data = d,
  family = binomial
)

models <- list(
  "H1a: Communication" = h1a,
  "H1b: Cooperation" = h1b,
  "H2a/H3a: Communication" = h2a_h3a,
  "H2b/H3b: Cooperation" = h2b_h3b,
  "H4a/H4b: Efficiency" = h4a_h4b,
  "H5a/H5b: Effectiveness" = h5a_h5b
)


# ------------------------------------------------------------
# 7. HC3 robust covariance matrices
# ------------------------------------------------------------

robust_vcov <- list(
  vcovHC(h1a, type = "HC3"),
  vcovHC(h1b, type = "HC3"),
  vcovHC(h2a_h3a, type = "HC3"),
  vcovHC(h2b_h3b, type = "HC3"),
  vcovHC(h4a_h4b, type = "HC3"),
  vcovHC(h5a_h5b, type = "HC3")
)

names(robust_vcov) <- names(models)


# ------------------------------------------------------------
# 8. H1 simple effects and average effects
# ------------------------------------------------------------

# The factorial H1 models retain the memory-by-access interaction. These
# contrasts make the memory effect directly readable at each access level.
h1_memory_contrast <- function(model) {
  robust_covariance <- sandwich::vcovHC(model, type = "HC3")
  access_means <- emmeans(
    model,
    ~ smm_mode | context_transparency_condition,
    vcov. = robust_covariance
  )

  contrast(
    access_means,
    method = list("Memory - baseline" = c(-1, 1)),
    infer = c(TRUE, TRUE)
  )
}

h1a_simple_effects <- h1_memory_contrast(h1a)
h1b_simple_effects <- h1_memory_contrast(h1b)

# These marginal contrasts estimate the average memory effect across the three
# balanced access levels. They complement, but do not replace, the simple
# effects above.
h1a_average_effect <- contrast(
  emmeans(
    h1a,
    ~ smm_mode,
    vcov. = sandwich::vcovHC(h1a, type = "HC3")
  ),
  method = list("Average memory - baseline" = c(-1, 1)),
  infer = c(TRUE, TRUE)
)

h1b_average_effect <- contrast(
  emmeans(
    h1b,
    ~ smm_mode,
    vcov. = sandwich::vcovHC(h1b, type = "HC3")
  ),
  method = list("Average memory - baseline" = c(-1, 1)),
  infer = c(TRUE, TRUE)
)

cat("\nH1a simple effects: memory minus baseline by access\n")
print(summary(h1a_simple_effects))
cat("\nH1b simple effects: memory minus baseline by access\n")
print(summary(h1b_simple_effects))
cat("\nH1a average effect across access\n")
print(summary(h1a_average_effect))
cat("\nH1b average effect across access\n")
print(summary(h1b_average_effect))

h1_effects_stars <- function(p_value) {
  if (p_value < 0.001) {
    "***"
  } else if (p_value < 0.01) {
    "**"
  } else if (p_value < 0.05) {
    "*"
  } else if (p_value < 0.10) {
    "+"
  } else {
    ""
  }
}

h1_effects_frame <- function(effect_grid, outcome, hypothesis) {
  effects <- as.data.frame(summary(effect_grid))
  effects <- effects[match(
    c("low", "moderate", "high"),
    as.character(effects$context_transparency_condition)
  ), ]
  data.frame(
    Hypothesis = hypothesis,
    Outcome = outcome,
    Access = factor(
      effects$context_transparency_condition,
      levels = c("low", "moderate", "high"),
      labels = c("Low access", "Moderate access", "High access")
    ),
    Estimate = paste0(
      sprintf("%.3f", effects$estimate),
      vapply(effects$p.value, h1_effects_stars, character(1)),
      "\n(",
      sprintf("%.3f", effects$SE),
      ")"
    ),
    `95% CI` = paste0(
      "[",
      sprintf("%.3f", effects$lower.CL),
      ", ",
      sprintf("%.3f", effects$upper.CL),
      "]"
    ),
    p = ifelse(
      effects$p.value < 0.001,
      "< .001",
      sprintf("%.3f", effects$p.value)
    ),
    check.names = FALSE,
    stringsAsFactors = FALSE
  )
}

h1_effects_data <- rbind(
  h1_effects_frame(
    h1a_simple_effects,
    "Communication",
    "H1a"
  ),
  h1_effects_frame(
    h1b_simple_effects,
    "Cooperation",
    "H1b"
  )
)


# ------------------------------------------------------------
# 9. Define table rows
# ------------------------------------------------------------

coefficient_map <- c(
  "(Intercept)" = "Intercept",
  "smm_modetreatment" = "Memory",
  "context_transparency_conditionlow" = "Low\u00A0access",
  "context_transparency_conditionmoderate" = "Moderate\u00A0access",
  "context_transparency_conditionhigh" = "High\u00A0access",
  "smm_modetreatment:context_transparency_conditionlow" =
    "Memory \u00D7 Low\u00A0access",
  "smm_modetreatment:context_transparency_conditionhigh" =
    "Memory \u00D7 High\u00A0access",
  "baseline" = "Baseline",
  "low" = "Low\u00A0access",
  "high" = "High\u00A0access",
  "team_process_communication" = "Communication",
  "team_process_cooperation" = "Cooperation"
)

format_r_squared <- function(x) {
  sub(
    pattern = "^(-?)0\\.",
    replacement = "\\1.",
    x = sprintf("%.3f", x)
  )
}

goodness_of_fit_map <- list(
  list(raw = "nobs", clean = "Observations", fmt = 0),
  list(raw = "r.squared", clean = "R²", fmt = format_r_squared),
  list(
    raw = "adj.r.squared",
    clean = "Adjusted\u00A0R²",
    fmt = format_r_squared
  ),
  list(
    raw = "mcfadden_r2",
    clean = "McFadden\u00A0R²",
    fmt = format_r_squared
  )
)


# ------------------------------------------------------------
# 10. Create table
# ------------------------------------------------------------

regression_table <- modelsummary(
  models,
  vcov = robust_vcov,
  coef_map = coefficient_map,
  gof_map = goodness_of_fit_map,
  gof_function = function(model) {
    data.frame(
      mcfadden_r2 = if (
        inherits(model, "glm") &&
          family(model)$family == "binomial"
      ) {
        as.numeric(performance::r2_mcfadden(model)$R2)
      } else {
        NA_real_
      }
    )
  },
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

r_squared_rows <- which(
  regression_table$body$dataset[[1]] %in%
    c("R²", "Adjusted\u00A0R²")
)

mcfadden_r2_row <- which(
  regression_table$body$dataset[[1]] == "McFadden\u00A0R²"
)

regression_table <- compose(
  regression_table,
  i = mcfadden_r2_row,
  j = setdiff(
    regression_table$col_keys,
    c(regression_table$col_keys[[1]], "H5a/H5b: Effectiveness")
  ),
  value = as_paragraph("-"),
  part = "body"
)

regression_table <- compose(
  regression_table,
  i = r_squared_rows,
  j = "H5a/H5b: Effectiveness",
  value = as_paragraph("-"),
  part = "body"
)


# Replace the modelsummary header with the four-row structure used in the
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
  hypothesis = c(
    "Hypothesis",
    "H1a",
    "H1b",
    "H2a/H3a",
    "H2b/H3b",
    "H4a/H4b",
    "H5a/H5b"
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
    "Computational effort",
    "Decision effectiveness"
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
# 11. Significance legend
# ------------------------------------------------------------

regression_table <- add_footer_lines(
  regression_table,
  values = paste0(
    "Note:\u00A0HC3\u00A0standard\u00A0errors\u00A0in\u00A0parentheses.\u00A0",
    "+\u00A0p\u00A0<\u00A0.10,\u00A0",
    "*\u00A0p\u00A0<\u00A0.05,\u00A0",
    "**\u00A0p\u00A0<\u00A0.01,\u00A0",
    "***\u00A0p\u00A0<\u00A0.001."
  )
)


# ------------------------------------------------------------
# 12. Minimal LaTeX-style formatting
# ------------------------------------------------------------

thin_line <- fp_border(
  color = "black",
  style = "solid",
  width = 0.75
)

thick_line <- fp_border(
  color = "black",
  style = "solid",
  width = 1.5
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

regression_table <- hline(
  regression_table,
  i = 3,
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
  size = 10,
  part = "all"
)

regression_table <- bold(
  regression_table,
  i = 1:3,
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
  size = 9,
  part = "footer"
)

regression_table <- font(
  regression_table,
  fontname = "Times New Roman",
  part = "footer"
)

regression_table <- padding(
  regression_table,
  padding.top = 0,
  padding.bottom = 0,
  padding.left = 2,
  padding.right = 2,
  part = "header"
)

regression_table <- padding(
  regression_table,
  padding.top = 0,
  padding.bottom = 0,
  padding.left = 2,
  padding.right = 2,
  part = "body"
)

regression_table <- padding(
  regression_table,
  i = observations_row:nrow(regression_table$body$dataset),
  padding.top = 0,
  padding.bottom = 0,
  padding.left = 2,
  padding.right = 2,
  part = "body"
)

regression_table <- padding(
  regression_table,
  padding.top = 0,
  padding.bottom = 0,
  padding.left = 2,
  padding.right = 2,
  part = "footer"
)

regression_table <- line_spacing(
  regression_table,
  space = 0.9,
  part = "all"
)

regression_table <- set_table_properties(
  regression_table,
  layout = "autofit",
  width = 1,
  opts_word = list(
    split = TRUE,
    repeat_headers = FALSE
  )
)


# ------------------------------------------------------------
# 13. Export to Word
# ------------------------------------------------------------

save_as_docx(
  regression_table,
  path = output_file,
  pr_section = thesis_section,
  align = "center"
)


# ------------------------------------------------------------
# 14. Export separate tool-call mechanism table
# ------------------------------------------------------------

tool_calls_table <- modelsummary(
  list("Tool calls" = tool_calls_model),
  vcov = list(vcovHC(tool_calls_model, type = "HC3")),
  coef_map = coefficient_map[
    c(
      "(Intercept)",
      "smm_modetreatment",
      "context_transparency_conditionlow",
      "context_transparency_conditionhigh",
      "smm_modetreatment:context_transparency_conditionlow",
      "smm_modetreatment:context_transparency_conditionhigh"
    )
  ],
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
  notes = "HC3 standard errors in parentheses. Reference categories: baseline and moderate access.",
  output = "flextable"
)

tool_calls_table <- font(
  tool_calls_table,
  fontname = "Times New Roman",
  part = "all"
)
tool_calls_table <- fontsize(
  tool_calls_table,
  size = 10,
  part = "all"
)
tool_calls_table <- align(
  tool_calls_table,
  align = "center",
  part = "all"
)
tool_calls_table <- align(
  tool_calls_table,
  j = 1,
  align = "left",
  part = "all"
)
tool_calls_table <- set_table_properties(
  tool_calls_table,
  layout = "autofit",
  width = 1,
  opts_word = list(
    split = TRUE,
    repeat_headers = FALSE
  )
)

save_as_docx(
  tool_calls_table,
  path = tool_calls_output_file,
  pr_section = thesis_section,
  align = "center"
)


# ------------------------------------------------------------
# 15. Export compact H1 simple-effects table
# ------------------------------------------------------------

h1_effects_table <- flextable(h1_effects_data)
h1_effects_table <- set_header_labels(
  h1_effects_table,
  Hypothesis = "Hypothesis",
  Outcome = "Outcome",
  Access = "Access",
  Estimate = "Memory − baseline",
  `95% CI` = "95% CI",
  p = "p"
)

h1_effects_table <- border_remove(h1_effects_table)
h1_effects_table <- hline_top(
  h1_effects_table,
  border = thick_line,
  part = "header"
)
h1_effects_table <- hline_bottom(
  h1_effects_table,
  border = thin_line,
  part = "header"
)
h1_effects_table <- hline_bottom(
  h1_effects_table,
  border = thin_line,
  part = "body"
)
h1_effects_table <- font(
  h1_effects_table,
  fontname = "Times New Roman",
  part = "all"
)
h1_effects_table <- fontsize(
  h1_effects_table,
  size = 10,
  part = "all"
)
h1_effects_table <- bold(
  h1_effects_table,
  part = "header"
)
h1_effects_table <- align(
  h1_effects_table,
  align = "center",
  part = "all"
)
h1_effects_table <- align(
  h1_effects_table,
  j = c("Hypothesis", "Outcome", "Access"),
  align = "left",
  part = "body"
)
h1_effects_table <- valign(
  h1_effects_table,
  valign = "center",
  part = "all"
)
h1_effects_table <- padding(
  h1_effects_table,
  padding.top = 0,
  padding.bottom = 0,
  padding.left = 2,
  padding.right = 2,
  part = "all"
)
h1_effects_table <- line_spacing(
  h1_effects_table,
  space = 0.9,
  part = "all"
)
h1_effects_table <- add_footer_lines(
  h1_effects_table,
  values = paste0(
    "Note:\u00A0Estimates\u00A0are\u00A0memory\u00A0minus\u00A0baseline.\u00A0",
    "HC3\u00A0standard\u00A0errors\u00A0in\u00A0parentheses.\u00A0",
    "+\u00A0p\u00A0<\u00A0.10,\u00A0",
    "*\u00A0p\u00A0<\u00A0.05,\u00A0",
    "**\u00A0p\u00A0<\u00A0.01,\u00A0",
    "***\u00A0p\u00A0<\u00A0.001."
  )
)
h1_effects_table <- fontsize(
  h1_effects_table,
  size = 9,
  part = "footer"
)
h1_effects_table <- font(
  h1_effects_table,
  fontname = "Times New Roman",
  part = "footer"
)
h1_effects_table <- align(
  h1_effects_table,
  align = "left",
  part = "footer"
)
h1_effects_table <- set_table_properties(
  h1_effects_table,
  layout = "autofit",
  width = 1,
  opts_word = list(
    split = TRUE,
    repeat_headers = FALSE
  )
)

save_as_docx(
  h1_effects_table,
  path = h1_effects_output_file,
  pr_section = thesis_section,
  align = "center"
)

cat(
  "\nTeam-process regression table exported to:\n",
  output_file,
  "\nTool-call mechanism table exported to:\n",
  tool_calls_output_file,
  "\nH1 simple-effects table exported to:\n",
  h1_effects_output_file,
  "\n",
  sep = ""
)
