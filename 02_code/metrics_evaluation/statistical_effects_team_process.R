# ============================================================
# Statistical tests for team-process simulation metrics
#
# Communication is decisive evidence uptake and cooperation is response
# integration, as calculated by calculate_team_process.py.
# ============================================================

# ------------------------------------------------------------
# 0. Setup
# ------------------------------------------------------------

if (!is.null(dev.list())) dev.off()
rm(list = ls())

library(lmtest)
library(sandwich)

path <- getwd()
output_token_weight <- 5

# ------------------------------------------------------------
# 1. Load data
# ------------------------------------------------------------

simulation_metrics <- read.csv(paste0(path,
  "/01_data/processed/simulation_metrics_final_100_gpt_oss_120b.csv"),
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

required_variables <- c(
  "smm_mode",
  "context_transparency_condition",
  "decision_correct",
  "team_process_communication",
  "team_process_cooperation",
  "input_tokens",
  "output_tokens"
)

missing_variables <- setdiff(required_variables, names(simulation_metrics))
if (length(missing_variables) > 0) {
  stop(paste0(
    "Missing required variables: ",
    paste(missing_variables, collapse = ", ")
  ))
}

# ------------------------------------------------------------
# 2. H1a/H1b: Average SMM treatment communication/cooperation versus baseline
# ------------------------------------------------------------

h1a_data <- subset(
  simulation_metrics,
  smm_mode %in% c("baseline", "treatment") &
    !is.na(team_process_communication) &
    !is.na(team_process_cooperation)
)

h1a_data$smm_treatment <- factor(
  ifelse(h1a_data$smm_mode == "treatment", "treatment", "baseline"),
  levels = c("baseline", "treatment")
)

h1a_data$team_process_communication <- as.numeric(
  h1a_data$team_process_communication
)
h1a_data$team_process_cooperation <- as.numeric(
  h1a_data$team_process_cooperation
)

h1a <- lm(
  team_process_communication ~ smm_treatment,
  data = h1a_data
)

h1b <- lm(
  team_process_cooperation ~ smm_treatment,
  data = h1a_data
)

# ------------------------------------------------------------
# 3. Prepare treatment data
# ------------------------------------------------------------

treatment_data <- subset(
  simulation_metrics,
  smm_mode == "treatment"
)

# Moderate is the reference group; coefficients are Low vs Moderate and High vs Moderate.
treatment_data$condition <- factor(
  treatment_data$context_transparency_condition,
  levels = c("moderate", "low", "high")
)

treatment_data$team_process_communication <- as.numeric(
  treatment_data$team_process_communication
)
treatment_data$team_process_cooperation <- as.numeric(
  treatment_data$team_process_cooperation
)

# H4a-H5b use moderate treatment as the omitted context-configuration group.
# The three indicators below therefore reproduce Baseline, Low, and High on
# the slide while retaining all four cells in the run matrix.
d <- simulation_metrics
d$baseline <- as.numeric(d$smm_mode == "baseline")
d$low <- as.numeric(
  d$smm_mode == "treatment" & d$context_transparency_condition == "low"
)
d$high <- as.numeric(
  d$smm_mode == "treatment" & d$context_transparency_condition == "high"
)
d$team_process_communication <- as.numeric(d$team_process_communication)
d$team_process_cooperation <- as.numeric(d$team_process_cooperation)
d$Effectiveness <- as.numeric(d$decision_correct)
d$input_tokens <- as.numeric(d$input_tokens)
d$output_tokens <- as.numeric(d$output_tokens)

d$coordination_cost <- d$input_tokens +
  output_token_weight * d$output_tokens

d$Efficiency <- d$coordination_cost / 1000000
d$input_tokens_million <- d$input_tokens / 1000000
d$output_tokens_million <- d$output_tokens / 1000000

d <- d[complete.cases(d[, c(
  "team_process_communication",
  "team_process_cooperation",
  "baseline",
  "low",
  "high",
  "Efficiency",
  "input_tokens_million",
  "output_tokens_million",
  "Effectiveness"
)]), ]

if (!all(d$Effectiveness %in% c(0, 1))) {
  stop("Effectiveness must contain only 0 and 1.")
}

# ------------------------------------------------------------
# 4. Fit regression models
# ------------------------------------------------------------

# H2a/H3a and H2b/H3b: transparency -> communication/cooperation within SMM treatment.
h2a_h3a <- lm(
  team_process_communication ~ condition,
  data = treatment_data
)

h2b_h3b <- lm(
  team_process_cooperation ~ condition,
  data = treatment_data
)

# H4a/H5a: communication and cooperation -> Efficiency, controlling for the
# agent context configuration and for each other.
# Operationalization: weighted token cost = input tokens + 5 * output tokens.
# The dependent variable is scaled to millions of weighted tokens.
# Higher weighted token cost means lower coordination efficiency.
h4a_h5a <- lm(
  Efficiency ~ team_process_communication + team_process_cooperation +
    baseline + low + high,
  data = d
)

# H4b/H5b: communication and cooperation -> Effectiveness, controlling for the
# agent context configuration and for each other.
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

robust_vcov <- list(
  vcovHC(h1a, type = "HC3"),
  vcovHC(h1b, type = "HC3"),
  vcovHC(h2a_h3a, type = "HC3"),
  vcovHC(h2b_h3b, type = "HC3"),
  vcovHC(h4a_h5a, type = "HC3"),
  vcovHC(h4b_h5b, type = "HC3")
)

names(robust_vcov) <- names(models)

robust_results <- Map(
  function(model, robust_se) coeftest(model, vcov. = robust_se),
  models,
  robust_vcov
)

cat("\nH1a regression: average SMM treatment -> communication (HC3 robust standard errors)\n")
print(robust_results[[1]])

cat("\nH1b regression: average SMM treatment -> cooperation (HC3 robust standard errors)\n")
print(robust_results[[2]])

cat("\nH2a/H3a regression: transparency -> communication (HC3 robust standard errors)\n")
print(robust_results[[3]])

cat("\nH2b/H3b regression: transparency -> cooperation (HC3 robust standard errors)\n")
print(robust_results[[4]])

cat("\nH4a/H5a regression: communication and cooperation -> Efficiency (HC3 robust standard errors)\n")
print(robust_results[[5]])

cat("\nH4b/H5b logistic regression: communication and cooperation -> Effectiveness (HC3 robust standard errors)\n")
print(robust_results[[6]])

# ------------------------------------------------------------
# 5. Table helpers
# ------------------------------------------------------------

significance_marker <- function(p_value) {
  if (is.na(p_value)) return("")
  if (p_value < 0.001) return("***")
  if (p_value < 0.01) return("**")
  if (p_value < 0.05) return("*")
  if (p_value < 0.1) return("+")
  ""
}

format_estimate_cell <- function(result, term) {
  if (!term %in% rownames(result)) return("")
  paste0(
    sprintf("%.3f", result[term, 1]),
    significance_marker(result[term, 4])
  )
}

format_se_cell <- function(result, term) {
  if (!term %in% rownames(result)) return("")
  paste0("(", sprintf("%.3f", result[term, 2]), ")")
}

render_table <- function(
  title,
  subtitle,
  rows,
  filename,
  source_note = NULL,
  column_x = NULL,
  width = 2000,
  min_height = 900,
  title_y = 0.94,
  subtitle_y = 0.89,
  table_top = 0.80
) {
  row_count <- nrow(rows) + 1
  height <- max(min_height, 250 + row_count * 58 + if (is.null(source_note)) 0 else 70)

  if (tolower(tools::file_ext(filename)) == "pdf") {
    grDevices::cairo_pdf(
      filename,
      width = width / 200,
      height = height / 200,
      family = "serif",
      bg = "white"
    )
  } else {
    png(filename, width = width, height = height, res = 200, bg = "white")
  }
  on.exit(dev.off(), add = TRUE)

  par(mar = c(0, 0, 0, 0), family = "serif")
  plot.new()
  plot.window(xlim = c(0, 1), ylim = c(0, 1))

  text(0.5, title_y, title, cex = 1.55, font = 2)
  text(0.5, subtitle_y, subtitle, cex = 1.0)

  table_bottom <- if (is.null(source_note)) 0.09 else 0.16
  row_height <- (table_top - table_bottom) / row_count
  header_height <- row_height * 2.2
  body_row_height <- (
    table_top - table_bottom - header_height
  ) / nrow(rows)
  header_y <- table_top - header_height / 2

  segments(0.03, table_top, 0.97, table_top, lwd = 2)
  segments(
    0.03,
    table_top - header_height,
    0.97,
    table_top - header_height,
    lwd = 1
  )
  segments(0.03, table_bottom, 0.97, table_bottom, lwd = 2)

  headers <- names(rows)
  if (is.null(column_x)) {
    column_x <- seq(0.04, 0.94, length.out = length(headers))
  }
  for (col_index in seq_along(headers)) {
    text(
      column_x[col_index],
      header_y,
      headers[col_index],
      adj = if (col_index == 1) 0 else 0.5,
      cex = 0.95,
      font = 2
    )
  }

  for (row_index in seq_len(nrow(rows))) {
    row_y <- table_top - header_height - body_row_height * (row_index - 0.5)
    for (col_index in seq_along(rows)) {
      text(
        column_x[col_index],
        row_y,
        as.character(rows[row_index, col_index]),
        adj = if (col_index == 1) 0 else 0.5,
        cex = 0.88
      )
    }
  }

  if (!is.null(source_note)) {
    text(0.04, 0.08, source_note, adj = 0, cex = 0.8)
  }
}

# ------------------------------------------------------------
# 6. Export PowerPoint-ready tables
# ------------------------------------------------------------

dir.create("03_report/tables", recursive = TRUE, showWarnings = FALSE)

coef_map <- c(
  "(Intercept)" = "Intercept",
  "smm_treatmenttreatment" = "SMM treatment",
  "conditionlow" = "Low transparency",
  "conditionhigh" = "High transparency",
  "team_process_communication" = "Communication",
  "team_process_cooperation" = "Cooperation",
  "baseline" = "Baseline",
  "low" = "Low transparency",
  "high" = "High transparency"
)

regression_rows <- data.frame(
  Term = character(),
  "H1a:\nCommunication" = character(),
  "H1b:\nCooperation" = character(),
  "H2a/H3a:\nCommunication" = character(),
  "H2b/H3b:\nCooperation" = character(),
  "H4a/H5a:\nEfficiency" = character(),
  "H4b/H5b:\nEffectiveness" = character(),
  check.names = FALSE
)

for (term in names(coef_map)) {
  regression_rows <- rbind(
    regression_rows,
    data.frame(
      Term = coef_map[[term]],
      "H1a:\nCommunication" = format_estimate_cell(robust_results[[1]], term),
      "H1b:\nCooperation" = format_estimate_cell(robust_results[[2]], term),
      "H2a/H3a:\nCommunication" = format_estimate_cell(robust_results[[3]], term),
      "H2b/H3b:\nCooperation" = format_estimate_cell(robust_results[[4]], term),
      "H4a/H5a:\nEfficiency" = format_estimate_cell(robust_results[[5]], term),
      "H4b/H5b:\nEffectiveness" = format_estimate_cell(robust_results[[6]], term),
      check.names = FALSE
    ),
    data.frame(
      Term = "",
      "H1a:\nCommunication" = format_se_cell(robust_results[[1]], term),
      "H1b:\nCooperation" = format_se_cell(robust_results[[2]], term),
      "H2a/H3a:\nCommunication" = format_se_cell(robust_results[[3]], term),
      "H2b/H3b:\nCooperation" = format_se_cell(robust_results[[4]], term),
      "H4a/H5a:\nEfficiency" = format_se_cell(robust_results[[5]], term),
      "H4b/H5b:\nEffectiveness" = format_se_cell(robust_results[[6]], term),
      check.names = FALSE
    )
  )
}

regression_rows <- rbind(
  regression_rows,
  data.frame(
    Term = "Observations",
    "H1a:\nCommunication" = nobs(h1a),
    "H1b:\nCooperation" = nobs(h1b),
    "H2a/H3a:\nCommunication" = nobs(h2a_h3a),
    "H2b/H3b:\nCooperation" = nobs(h2b_h3b),
    "H4a/H5a:\nEfficiency" = nobs(h4a_h5a),
    "H4b/H5b:\nEffectiveness" = nobs(h4b_h5b),
    check.names = FALSE
  )
)

render_table(
  title = "Regression Results: Team Process H1-H5",
  subtitle = "Efficiency is weighted-token cost in millions; HC3 standard errors",
  rows = regression_rows,
  filename = "03_report/tables/regression_results_team_process_h1_h5.pdf",
  source_note = "+p < .10, *p < .05, **p < .01, ***p < .001",
  column_x = c(0.03, 0.21, 0.36, 0.51, 0.66, 0.81, 0.94),
  width = 2000,
  min_height = 860
)
