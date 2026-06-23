# ============================================================
# Statistical tests for team-process simulation metrics
#
# team_process_score is the simplified Mathieu-style process score from
# calculate_team_process.py: communication = decisive evidence uptake,
# coordination = inquiry network coverage, cooperation = response integration.
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
  "team_process_score",
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
# 2. H1a: Average SMM treatment team process versus baseline
# ------------------------------------------------------------

h1a_data <- subset(
  simulation_metrics,
  smm_mode %in% c("baseline", "treatment") &
    !is.na(team_process_score)
)

h1a_data$smm_treatment <- factor(
  ifelse(h1a_data$smm_mode == "treatment", "treatment", "baseline"),
  levels = c("baseline", "treatment")
)

h1a_data$team_process_score <- as.numeric(h1a_data$team_process_score)

h1a <- lm(
  team_process_score ~ smm_treatment,
  data = h1a_data
)

# ------------------------------------------------------------
# 3. Prepare treatment data
# ------------------------------------------------------------

d <- subset(
  simulation_metrics,
  smm_mode == "treatment"
)

# Moderate is the reference group; coefficients are Low vs Moderate and High vs Moderate.
d$condition <- factor(
  d$context_transparency_condition,
  levels = c("moderate", "low", "high")
)

d$team_process_score <- as.numeric(d$team_process_score)
d$coordination_effectiveness <- as.numeric(d$decision_correct)
d$input_tokens <- as.numeric(d$input_tokens)
d$output_tokens <- as.numeric(d$output_tokens)

d$coordination_cost <- d$input_tokens +
  output_token_weight * d$output_tokens

d$coordination_cost_million <- d$coordination_cost / 1000000
d$input_tokens_million <- d$input_tokens / 1000000
d$output_tokens_million <- d$output_tokens / 1000000

d <- d[complete.cases(d[, c(
  "condition",
  "team_process_score",
  "coordination_cost_million",
  "input_tokens_million",
  "output_tokens_million",
  "coordination_effectiveness"
)]), ]

if (!all(d$coordination_effectiveness %in% c(0, 1))) {
  stop("coordination_effectiveness must contain only 0 and 1.")
}

# ------------------------------------------------------------
# 4. Fit regression models
# ------------------------------------------------------------

# H1b/H1c: transparency -> team process within SMM treatment.
h1bc <- lm(
  team_process_score ~ condition,
  data = d
)

# H2: team process -> coordination efficiency, controlling for transparency.
# Operationalization: weighted token cost = input tokens + 5 * output tokens.
# The dependent variable is scaled to millions of weighted tokens.
# Higher weighted token cost means lower coordination efficiency.
h2 <- lm(
  coordination_cost_million ~ team_process_score + condition,
  data = d
)

# H2 decomposition: input and output token costs separately,
# both scaled to millions of tokens.
h2_input <- lm(
  input_tokens_million ~ team_process_score + condition,
  data = d
)

h2_output <- lm(
  output_tokens_million ~ team_process_score + condition,
  data = d
)

# H3: team process -> correct decision, controlling for transparency.
h3 <- glm(
  coordination_effectiveness ~ team_process_score + condition,
  data = d,
  family = binomial
)

models <- list(
  "H1a: Team process" = h1a,
  "H1b/H1c: Team process" = h1bc,
  "H2: Coordination efficiency" = h2,
  "H2a: Input tokens" = h2_input,
  "H2b: Output tokens" = h2_output,
  "H3: Correct decision" = h3
)

robust_vcov <- list(
  vcovHC(h1a, type = "HC3"),
  vcovHC(h1bc, type = "HC3"),
  vcovHC(h2, type = "HC3"),
  vcovHC(h2_input, type = "HC3"),
  vcovHC(h2_output, type = "HC3"),
  vcovHC(h3, type = "HC3")
)

names(robust_vcov) <- names(models)

robust_results <- Map(
  function(model, robust_se) coeftest(model, vcov. = robust_se),
  models,
  robust_vcov
)

cat("\nH1a regression: average SMM treatment -> team process (HC3 robust standard errors)\n")
print(robust_results[[1]])

cat("\nH1b/H1c regression: transparency -> team process (HC3 robust standard errors)\n")
print(robust_results[[2]])

cat("\nH2 regression: team process -> coordination efficiency, measured as weighted token cost in millions (HC3 robust standard errors)\n")
print(robust_results[[3]])

cat("\nH2a decomposition: team process -> input tokens in millions (HC3 robust standard errors)\n")
print(robust_results[[4]])

cat("\nH2b decomposition: team process -> output tokens in millions (HC3 robust standard errors)\n")
print(robust_results[[5]])

cat("\nH3 logistic regression: team process -> correct decision (HC3 robust standard errors)\n")
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

render_png_table <- function(
  title,
  subtitle,
  rows,
  filename,
  source_note = NULL,
  column_x = NULL,
  width = 3200,
  min_height = 900,
  title_y = 0.94,
  subtitle_y = 0.89,
  table_top = 0.80
) {
  row_count <- nrow(rows) + 1
  height <- max(min_height, 250 + row_count * 58 + if (is.null(source_note)) 0 else 70)

  png(filename, width = width, height = height, res = 200, bg = "white")
  on.exit(dev.off(), add = TRUE)

  par(mar = c(0, 0, 0, 0), family = "Times New Roman")
  plot.new()
  plot.window(xlim = c(0, 1), ylim = c(0, 1))

  text(0.5, title_y, title, cex = 1.55, font = 2)
  text(0.5, subtitle_y, subtitle, cex = 1.0)

  table_bottom <- if (is.null(source_note)) 0.09 else 0.16
  row_height <- (table_top - table_bottom) / row_count
  header_y <- table_top - row_height / 2

  segments(0.03, table_top, 0.97, table_top, lwd = 2)
  segments(
    0.03,
    table_top - row_height,
    0.97,
    table_top - row_height,
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
    row_y <- table_top - row_height * (row_index + 0.5)
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
  "team_process_score" = "Team process"
)

regression_rows <- data.frame(
  Term = character(),
  "H1a: Team process" = character(),
  "H1b/c: Team process" = character(),
  "H2: Token cost (m)" = character(),
  "H2a: Input (m)" = character(),
  "H2b: Output (m)" = character(),
  "H3: Correct decision" = character(),
  check.names = FALSE
)

for (term in names(coef_map)) {
  regression_rows <- rbind(
    regression_rows,
    data.frame(
      Term = coef_map[[term]],
      "H1a: Team process" = format_estimate_cell(robust_results[[1]], term),
      "H1b/c: Team process" = format_estimate_cell(robust_results[[2]], term),
      "H2: Token cost (m)" = format_estimate_cell(robust_results[[3]], term),
      "H2a: Input (m)" = format_estimate_cell(robust_results[[4]], term),
      "H2b: Output (m)" = format_estimate_cell(robust_results[[5]], term),
      "H3: Correct decision" = format_estimate_cell(robust_results[[6]], term),
      check.names = FALSE
    ),
    data.frame(
      Term = "",
      "H1a: Team process" = format_se_cell(robust_results[[1]], term),
      "H1b/c: Team process" = format_se_cell(robust_results[[2]], term),
      "H2: Token cost (m)" = format_se_cell(robust_results[[3]], term),
      "H2a: Input (m)" = format_se_cell(robust_results[[4]], term),
      "H2b: Output (m)" = format_se_cell(robust_results[[5]], term),
      "H3: Correct decision" = format_se_cell(robust_results[[6]], term),
      check.names = FALSE
    )
  )
}

regression_rows <- rbind(
  regression_rows,
  data.frame(
    Term = "Observations",
    "H1a: Team process" = nobs(h1a),
    "H1b/c: Team process" = nobs(h1bc),
    "H2: Token cost (m)" = nobs(h2),
    "H2a: Input (m)" = nobs(h2_input),
    "H2b: Output (m)" = nobs(h2_output),
    "H3: Correct decision" = nobs(h3),
    check.names = FALSE
  )
)

render_png_table(
  title = "Regression Results: Team Process H1-H3",
  subtitle = "H2, H2a, and H2b token outcomes are measured in millions; HC3 standard errors",
  rows = regression_rows,
  filename = "03_report/tables/regression_results_team_process_h1_h3.png",
  source_note = "+p < .10, *p < .05, **p < .01, ***p < .001",
  column_x = c(0.04, 0.25, 0.39, 0.53, 0.66, 0.79, 0.92),
  width = 2400,
  min_height = 860
)
