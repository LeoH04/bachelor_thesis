# ============================================================
# Statistical tests for simulation metrics
# ============================================================

# Clean workspace
if (!is.null(dev.list())) dev.off()
rm(list = ls())

path <- getwd()

# ------------------------------------------------------------
# 1. Load data
# ------------------------------------------------------------

simulation_metrics <- read.csv(paste0(path,
  "/01_data/processed/simulation_metrics_20260530_091120.csv"),
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

# SMM vs. baseline: compare correct-decision shares.
smm_decisions <- subset(simulation_metrics, smm_mode == "treatment" & !is.na(decision_correct))
baseline_decisions <- subset(simulation_metrics, smm_mode == "baseline" & !is.na(decision_correct))
smm_vs_baseline <- prop.test(
  x = c(sum(smm_decisions$decision_correct), sum(baseline_decisions$decision_correct)),
  n = c(nrow(smm_decisions), nrow(baseline_decisions)),
  alternative = "greater"
)

# Keep only runs where shared-memory metrics exist.
d <- subset(simulation_metrics, smm_mode == "treatment")

# ------------------------------------------------------------
# 2. Conduct statistical tests
# ------------------------------------------------------------

# Moderate is the reference group; coefficients are Low vs Moderate and High vs Moderate.
d$condition <- factor(d$context_transparency_condition, levels = c("moderate", "low", "high"))
d$context_consistency <- d$mean_pairwise_memory_similarity
d$coordination_efficiency <- -d$tokens_per_correct_decision
d$coordination_effectiveness <- d$decision_correct

d <- d[complete.cases(d[, c(
  "condition",
  "context_consistency",
  "coordination_efficiency",
  "coordination_effectiveness"
)]), ]

# H1a/H1b: context transparency -> context consistency
h1 <- lm(context_consistency ~ condition, data = d)

# H2: context consistency -> coordination efficiency, controlling for transparency
h2 <- lm(coordination_efficiency ~ context_consistency + condition, data = d)

# H3: context consistency -> correct decision, controlling for transparency
h3 <- glm(
  coordination_effectiveness ~ context_consistency + condition,
  data = d,
  family = binomial
)

# ------------------------------------------------------------
# 3. Summarize test results
# ------------------------------------------------------------

cat("\nH1a/H1b regression\n")
print(summary(h1))

cat("\nH2 regression\n")
print(summary(h2))

cat("\nH3 logistic regression\n")
print(summary(h3))

cat("\nSMM vs. baseline correct-decision share test\n")
print(smm_vs_baseline)
