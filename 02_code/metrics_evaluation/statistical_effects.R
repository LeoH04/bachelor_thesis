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
  "/01_data/processed/simulation_metrics_20260508_080303.csv"),
  na.strings = c("", "NA"),
  stringsAsFactors = FALSE
)