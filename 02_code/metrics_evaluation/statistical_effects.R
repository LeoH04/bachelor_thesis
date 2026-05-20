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
  "/01_data/processed/simulation_metrics_20260519_074043.csv"),
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)

# Keep only runs where shared-memory metrics exist.
d <- subset(simulation_metrics, smm_mode == "treatment")
# ------------------------------------------------------------
# 2. Conduct statistical tests
# ------------------------------------------------------------

# Moderate is the reference group; coefficients are Low vs Moderate and High vs Moderate.
d$condition <- factor(d$condition, levels = c("moderate", "low", "high"))
d$context_consistency <- d$mean_pairwise_memory_similarity
d$coordination_efficiency <- -d$total_messages
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

cat("\nH1a/H1b regression\n")
print(summary(h1))

cat("\nH2 regression\n")
print(summary(h2))

cat("\nH3 logistic regression\n")
print(summary(h3))
