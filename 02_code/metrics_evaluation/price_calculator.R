# ============================================================
# Price calculator for different GPT models
# ============================================================

library(tidyverse)

# ------------------------------------------------------------
# 1. Function
# ------------------------------------------------------------
calculate_costs <- function(input_tokens, output_tokens, context = c("short", "long")) {
  context <- match.arg(context)
  
  prices <- data.frame(
    model = c("gpt-5", "gpt-5-pro", "gpt-4", "gpt-4-mini", "gpt-4-nano", "gpt-4-pro"),
    short_input = c(5.00, 30.00, 2.50, 0.75, 0.20, 30.00),
    short_output = c(30.00, 180.00, 15.00, 4.50, 1.25, 180.00),
    long_input = c(10.00, 60.00, 5.00, NA, NA, 60.00),
    long_output = c(45.00, 270.00, 22.50, NA, NA, 270.00)
  )
  
  input_col <- paste0(context, "_input")
  output_col <- paste0(context, "_output")
  
  result <- data.frame(
    model = prices$model,
    input_cost = (input_tokens / 1e6) * prices[[input_col]],
    output_cost = (output_tokens / 1e6) * prices[[output_col]]
  )
  
  result$total_cost <- result$input_cost + result$output_cost
  
  result <- result[!is.na(result$total_cost), ]
  
  result$input_cost <- round(result$input_cost, 2)
  result$output_cost <- round(result$output_cost, 2)
  result$total_cost <- round(result$total_cost, 2)
  
  result
}