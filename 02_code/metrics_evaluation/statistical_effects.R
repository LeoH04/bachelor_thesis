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
library(skedastic)

path <- getwd()

# ------------------------------------------------------------
# 1. Load data
# ------------------------------------------------------------

simulation_metrics <- read.csv(paste0(path,
  "/01_data/processed/simulation_metrics_20260530_091120.csv"),
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

# ------------------------------------------------------------
# 2. Test average treatment against baseline
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
smm_vs_baseline <- prop.test(
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

# H1a/H1b adapted to SMM quality:
# context transparency -> SMM quality
h1 <- lm(smm_quality ~ condition, data = d)

# H2: SMM quality -> coordination efficiency, controlling for transparency
h2 <- lm(coordination_efficiency ~ smm_quality + condition, data = d)


# H3 adapted to SMM quality:
# SMM quality -> correct decision, controlling for transparency
h3 <- glm(
  coordination_effectiveness ~ smm_quality + condition,
  data = d,
  family = binomial
)

# ------------------------------------------------------------
# 6. Print descriptive summaries
# ------------------------------------------------------------

cat("\nSMM quality summary by condition\n")
print(aggregate(smm_quality ~ condition, data = d, FUN = mean))

# ------------------------------------------------------------
# 7. Print heteroskedasticity diagnostics
# ------------------------------------------------------------

cat("\nWhite test for heteroskedasticity: H1\n")
print(white(h1, interactions = TRUE))

cat("\nWhite test for heteroskedasticity: H2\n")
print(white(h2, interactions = TRUE))

# ------------------------------------------------------------
# 8. Print regression results
# ------------------------------------------------------------

cat("\nH1a/H1b regression: transparency -> SMM quality (HC3 robust standard errors)\n")
print(coeftest(h1, vcov. = vcovHC(h1, type = "HC3")))

cat("\nH2 regression\n")
print(summary(h2))

cat("\nH3 logistic regression: SMM quality -> correct decision\n")
print(summary(h3))

# ------------------------------------------------------------
# 9. Print baseline comparison
# ------------------------------------------------------------

cat("\nAverage SMM treatment vs. baseline correct-decision share test\n")
print(smm_vs_baseline)
