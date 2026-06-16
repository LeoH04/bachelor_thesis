# ============================================================
# Statistical tests for simulation metrics
# ============================================================

# ------------------------------------------------------------
# 0. Setup
# ------------------------------------------------------------

if (!is.null(dev.list())) dev.off()
rm(list = ls())

library(lmtest)
library(sandwich)

path <- getwd()

# ------------------------------------------------------------
# 1. Load data
# ------------------------------------------------------------

simulation_metrics <- read.csv(paste0(path,
  "/01_data/processed/simulation_metrics_20260612_090103.csv"),
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

# ------------------------------------------------------------
# 2. H1: Test matched moderate treatment against baseline
# ------------------------------------------------------------

# SMM vs. baseline: compare average SMM treatment performance against baseline.
smm_decisions <- subset(
  simulation_metrics,
  smm_mode == "treatment" & !is.na(decision_correct)
)
baseline_decisions <- subset(
  simulation_metrics,
  smm_mode == "baseline" & !is.na(decision_correct)
)
h1 <- prop.test(
  x = c(sum(smm_decisions$decision_correct), sum(baseline_decisions$decision_correct)),
  n = c(nrow(smm_decisions), nrow(baseline_decisions)),
  alternative = "greater"
)

# ------------------------------------------------------------
# 3. Prepare treatment data
# ------------------------------------------------------------

# Keep only runs where shared-memory metrics exist.
d <- subset(simulation_metrics, smm_mode == "treatment")

# ------------------------------------------------------------
# 4. Create analysis variables
# ------------------------------------------------------------

# Moderate is the reference group; coefficients are Low vs Moderate and High vs Moderate.
d$condition <- factor(d$context_transparency_condition, levels = c("moderate", "low", "high"))
d$smm_quality <- as.numeric(d$smm_quality)
d$coordination_effectiveness <- as.numeric(d$decision_correct)
d$rounds <- as.numeric(d$rounds)
d$total_messages <- as.numeric(d$total_messages)
d$total_tokens <- as.numeric(d$total_tokens)

d$coordination_efficiency <- -rowMeans(scale(d[, c(
  "rounds",
  "total_messages",
  "total_tokens"
)]))

d <- d[complete.cases(d[, c(
  "condition",
  "smm_quality",
  "coordination_efficiency",
  "coordination_effectiveness"
)]), ]

# ------------------------------------------------------------
# 5. Fit regression models
# ------------------------------------------------------------

# H2a/H2b adapted to SMM quality:
# context transparency -> SMM quality
h2 <- lm(smm_quality ~ condition, data = d)

# H3: SMM quality -> coordination efficiency, controlling for transparency
h3 <- lm(coordination_efficiency ~ smm_quality + condition, data = d)


# H4 adapted to SMM quality:
# SMM quality -> correct decision, controlling for transparency
h4 <- glm(
  coordination_effectiveness ~ smm_quality + condition,
  data = d,
  family = binomial
)

models <- list(
  "H2: Context quality" = h2,
  "H3: Coordination efficiency" = h3,
  "H4: Correct decision" = h4
)

robust_vcov <- list(
  vcovHC(h2, type = "HC3"),
  vcovHC(h3, type = "HC3"),
  vcovHC(h4, type = "HC3")
)

names(robust_vcov) <- names(models)

robust_results <- Map(
  function(model, robust_se) coeftest(model, vcov. = robust_se),
  models,
  robust_vcov
)

cat("\nH1 average SMM treatment vs. baseline correct-decision share test\n")
print(h1)

cat("\nH2 regression: transparency -> Context quality (HC3 robust standard errors)\n")
print(robust_results[[1]])

cat("\nH3 regression: Context quality -> coordination efficiency (HC3 robust standard errors)\n")
print(robust_results[[2]])

cat("\nH4 logistic regression: Context quality -> correct decision (HC3 robust standard errors)\n")
print(robust_results[[3]])

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
  column_x = c(0.04, 0.46, 0.68, 0.88),
  width = 2200,
  min_height = 850,
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

h1_table <- data.frame(
  Hypothesis = "H1",
  Test = "Average SMM treatment vs. baseline",
  Result = paste0(
    round(mean(smm_decisions$decision_correct) * 100, 1),
    "% vs. ",
    round(mean(baseline_decisions$decision_correct) * 100, 1),
    "%"
  ),
  p_value = format.pval(h1$p.value, digits = 3, eps = 0.001)
)

names(h1_table) <- c("Hypothesis", "Test", "Result", "p-value")

render_png_table(
  title = "Hypothesis Test: H1",
  subtitle = "Average decision correctness comparison",
  rows = h1_table,
  filename = "03_report/tables/h1_result.png",
  column_x = c(0.05, 0.28, 0.72, 0.88),
  width = 2000,
  min_height = 560,
  title_y = 0.91,
  subtitle_y = 0.82,
  table_top = 0.68
)

coef_map <- c(
  "(Intercept)" = "Intercept",
  "conditionlow" = "Low transparency",
  "conditionhigh" = "High transparency",
  "context_quality" = "Context quality"
)

regression_rows <- data.frame(
  Term = character(),
  "H2: Context quality" = character(),
  "H3: Coord. efficiency" = character(),
  "H4: Correct decision" = character(),
  check.names = FALSE
)

for (term in names(coef_map)) {
  regression_rows <- rbind(
    regression_rows,
    data.frame(
      Term = coef_map[[term]],
      "H2: Context quality" = format_estimate_cell(robust_results[[1]], term),
      "H3: Coord. efficiency" = format_estimate_cell(robust_results[[2]], term),
      "H4: Correct decision" = format_estimate_cell(robust_results[[3]], term),
      check.names = FALSE
    ),
    data.frame(
      Term = "",
      "H2: Context quality" = format_se_cell(robust_results[[1]], term),
      "H3: Coord. efficiency" = format_se_cell(robust_results[[2]], term),
      "H4: Correct decision" = format_se_cell(robust_results[[3]], term),
      check.names = FALSE
    )
  )
}

regression_rows <- rbind(
  regression_rows,
  data.frame(
    Term = "Observations",
    "H2: Context quality" = nobs(h2),
    "H3: Coord. efficiency" = nobs(h3),
    "H4: Correct decision" = nobs(h4),
    check.names = FALSE
  )
)

render_png_table(
  title = "Regression Results: H2-H4",
  subtitle = "HC3 robust standard errors in parentheses",
  rows = regression_rows,
  filename = "03_report/tables/regression_results_h2_h4.png",
  source_note = "+p < .10, *p < .05, **p < .01, ***p < .001"
)
