# ============================================================
# Figure: Mean weighted tokens by experimental condition
# Baseline | Low | Moderate | High
# Weighted tokens = input tokens + 5 × output tokens
# ============================================================

rm(list = ls())

library(tidyverse)
library(scales)

options(scipen = 999)

# ------------------------------------------------------------
# 1. Paths and data
# ------------------------------------------------------------

project_path <- getwd()

data_path <- file.path(
  project_path,
  "01_data/processed/simulation_metrics_final_200_gpt_oss_120b.csv"
)

output_dir <- file.path(project_path, "03_report/graphs")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

figure_width <- 3.35
figure_height <- 3.55

simulation_metrics <- read_csv(
  data_path,
  na = c("", "NA"),
  show_col_types = FALSE
)

# ------------------------------------------------------------
# 2. Prepare four experimental conditions and weighted tokens
# ------------------------------------------------------------

output_token_weight <- 5
weighted_token_scale <- 1000000

weighted_tokens_data <- simulation_metrics %>%
  mutate(
    smm_mode = tolower(trimws(as.character(smm_mode))),
    
    context_transparency_condition = factor(
      context_transparency_condition,
      levels = c("low", "moderate", "high")
    ),
    
    input_tokens = as.numeric(input_tokens),
    output_tokens = as.numeric(output_tokens),
    
    weighted_total_tokens_million =
      (input_tokens + output_token_weight * output_tokens) /
        weighted_token_scale,
    
    plot_condition = case_when(
      smm_mode == "baseline" ~ "Baseline",
      smm_mode == "treatment" &
        context_transparency_condition == "low" ~ "Low\ntransparency",
      smm_mode == "treatment" &
        context_transparency_condition == "moderate" ~ "Moderate\ntransparency",
      smm_mode == "treatment" &
        context_transparency_condition == "high" ~ "High\ntransparency",
      TRUE ~ NA_character_
    ),
    
    plot_condition = factor(
      plot_condition,
      levels = c(
        "Baseline",
        "Low\ntransparency",
        "Moderate\ntransparency",
        "High\ntransparency"
      )
    )
  ) %>%
  filter(
    !is.na(plot_condition),
    !is.na(weighted_total_tokens_million)
  )

# ------------------------------------------------------------
# 3. Calculate mean weighted tokens and 95% confidence intervals
# ------------------------------------------------------------

weighted_tokens_summary <- weighted_tokens_data %>%
  group_by(plot_condition) %>%
  summarise(
    n = n(),
    mean_weighted_tokens = mean(weighted_total_tokens_million),
    standard_deviation = sd(weighted_total_tokens_million),
    standard_error = standard_deviation / sqrt(n),
    .groups = "drop"
  ) %>%
  mutate(
    t_value = qt(0.975, df = n - 1),
    ci_lower = pmax(
      0,
      mean_weighted_tokens - t_value * standard_error
    ),
    ci_upper =
      mean_weighted_tokens + t_value * standard_error,
    weighted_token_label = number(
      mean_weighted_tokens,
      accuracy = 0.001
    )
  )

print(weighted_tokens_summary)

# Creates x-axis labels dynamically, so n is correct even if group sizes change
# Invisible lines under Baseline align all n labels vertically
condition_axis_labels <- setNames(
  vapply(
    as.character(weighted_tokens_summary$plot_condition),
    function(condition) {
      
      condition_label <- gsub("\n", "<br>", condition)
      condition_label <- sub(
        "transparency",
        "trans-<br>parency",
        condition_label,
        fixed = TRUE
      )
      
      # Give Baseline invisible lines to match treatment labels
      if (!grepl("<br>", condition_label)) {
        condition_label <- paste0(
          condition_label,
          "<br>&nbsp;<br>&nbsp;"
        )
      }
      
      paste0(
        "<b>",
        condition_label,
        "</b><br><br>",
        "<i><span style='font-size:7pt; color:#555555;'>",
        "n = ",
        weighted_tokens_summary$n[
          as.character(weighted_tokens_summary$plot_condition) == condition
        ],
        "</span></i>"
      )
    },
    character(1)
  ),
  as.character(weighted_tokens_summary$plot_condition)
)

# ------------------------------------------------------------
# 4. Create figure
# ------------------------------------------------------------

y_upper_limit <- max(weighted_tokens_summary$ci_upper) * 1.15

weighted_tokens_summary <- weighted_tokens_summary %>%
  mutate(
    label_y = ci_upper + y_upper_limit * if_else(
      plot_condition == "Baseline",
      0.23,
      0.035
    )
  )

weighted_tokens_plot <- ggplot(
  weighted_tokens_summary,
  aes(
    x = plot_condition,
    y = mean_weighted_tokens,
    fill = plot_condition
  )
) +
  geom_col(
    width = 0.60,
    colour = "black",
    linewidth = 0.35
  ) +
  geom_line(
    aes(group = 1),
    colour = "black",
    linewidth = 0.65
  ) +
  geom_errorbar(
    aes(
      ymin = ci_lower,
      ymax = ci_upper
    ),
    width = 0.08,
    linewidth = 0.7,
    colour = "black"
  ) +
  geom_point(
    shape = 21,
    size = 3.5,
    colour = "black",
    stroke = 0.65
  ) +
  geom_text(
    aes(
      y = label_y,
      label = weighted_token_label
    ),
    fontface = "bold",
    colour = "black",
    size = 3.1
  ) +
  scale_fill_manual(
    values = c(
      "Baseline" = "#B0B0B0",
      "Low\ntransparency" = "#D8E5EE",
      "Moderate\ntransparency" = "#7FA9C4",
      "High\ntransparency" = "#315F7D"
    ),
    guide = "none"
  ) +
  scale_x_discrete(
    labels = condition_axis_labels
  ) +
  scale_y_continuous(
    limits = c(0, y_upper_limit),
    labels = label_number(accuracy = 0.1),
    expand = expansion(mult = c(0, 0))
  ) +
  coord_cartesian(
    clip = "off"
  ) +
  labs(
    x = "Experimental condition",
    y = "Mean weighted tokens per\nsimulation (millions)"
  ) +
  theme_classic(base_size = 10) +
  theme(
    axis.title = element_text(face = "bold"),
    axis.title.y = element_text(margin = margin(r = 6)),
    axis.title.x = element_text(margin = margin(t = 7)),
    axis.text.x = ggtext::element_markdown(
      size = 7.2,
      margin = margin(t = 5),
      lineheight = 1.00
    ),
    axis.text.y = element_text(colour = "black"),
    plot.margin = margin(t = 12, r = 5, b = 3, l = 5)
  )

print(weighted_tokens_plot)

# ------------------------------------------------------------
# 5. Save figure
# ------------------------------------------------------------

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_weighted_tokens_by_condition.pdf"
  ),
  plot = weighted_tokens_plot,
  width = figure_width,
  height = figure_height,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_weighted_tokens_by_condition.svg"
  ),
  plot = weighted_tokens_plot,
  width = figure_width,
  height = figure_height,
  units = "in"
)
