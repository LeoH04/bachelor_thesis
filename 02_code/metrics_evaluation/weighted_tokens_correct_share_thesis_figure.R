# ============================================================
# Figure: Decision quality and weighted tokens by access and memory condition
# Low | Moderate | High access, split by explicit SMM memory
# Bars with mean-value labels
# ============================================================

rm(list = ls())

library(tidyverse)
library(scales)
library(cowplot)

options(scipen = 999)

# ------------------------------------------------------------
# 1. Paths and data
# ------------------------------------------------------------

project_path <- getwd()

data_path <- file.path(
  project_path,
  "01_data/processed/simulation_metrics_final_200_plus_low_high_baseline.csv"
)

output_dir <- file.path(project_path, "03_report/graphs")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

simulation_metrics <- read_csv(
  data_path,
  na = c("", "NA"),
  show_col_types = FALSE
)

# ------------------------------------------------------------
# 2. Prepare conditions and outcome measures
# ------------------------------------------------------------

output_token_weight <- 5
weighted_token_scale <- 1000000

figure_data <- simulation_metrics %>%
  mutate(
    smm_mode = tolower(trimws(as.character(smm_mode))),
    memory_condition = recode(
      smm_mode,
      "baseline" = "No memory",
      "treatment" = "Memory",
      .default = NA_character_
    ),
    memory_condition = factor(
      memory_condition,
      levels = c("No memory", "Memory")
    ),
    input_tokens = as.numeric(input_tokens),
    output_tokens = as.numeric(output_tokens),
    decision_correct = as.integer(decision_correct),
    weighted_total_tokens_million =
      (input_tokens + output_token_weight * output_tokens) /
        weighted_token_scale,
    plot_condition = factor(
      context_transparency_condition,
      levels = c("low", "moderate", "high"),
      labels = c("Low\naccess", "Moderate\naccess", "High\naccess")
    )
  ) %>%
  filter(
    !is.na(plot_condition),
    !is.na(memory_condition),
    !is.na(decision_correct),
    !is.na(weighted_total_tokens_million)
  )

# ------------------------------------------------------------
# 3. Calculate estimates and 95% confidence intervals
# ------------------------------------------------------------

z_value <- qnorm(0.975)

correct_share_summary <- figure_data %>%
  group_by(plot_condition, memory_condition) %>%
  summarise(
    n = n(),
    correct_share = mean(decision_correct),
    .groups = "drop"
  ) %>%
  mutate(
    standard_error = sqrt(correct_share * (1 - correct_share) / n),
    mean_value = 100 * correct_share,
    ci_lower = 100 * pmax(
      0,
      correct_share - z_value * standard_error
    ),
    ci_upper = 100 * pmin(
      1,
      correct_share + z_value * standard_error
    ),
    value_label = percent(correct_share, accuracy = 1),
    figure_dimension = "Correct decisions"
  )

weighted_tokens_summary <- figure_data %>%
  group_by(plot_condition, memory_condition) %>%
  summarise(
    n = n(),
    mean_value = mean(weighted_total_tokens_million),
    standard_error = sd(weighted_total_tokens_million) / sqrt(n),
    .groups = "drop"
  ) %>%
  mutate(
    t_value = qt(0.975, df = n - 1),
    ci_lower = pmax(0, mean_value - t_value * standard_error),
    ci_upper = mean_value + t_value * standard_error,
    value_label = number(mean_value, accuracy = 0.001),
    figure_dimension = "Weighted tokens"
  )

figure_summary <- bind_rows(
  correct_share_summary %>%
    select(
      figure_dimension,
      plot_condition,
      memory_condition,
      n,
      mean_value,
      ci_lower,
      ci_upper,
      value_label
    ),
  weighted_tokens_summary %>%
    select(
      figure_dimension,
      plot_condition,
      memory_condition,
      n,
      mean_value,
      ci_lower,
      ci_upper,
      value_label
    )
) %>%
  mutate(
    figure_dimension = factor(
      figure_dimension,
      levels = c("Correct decisions", "Weighted tokens")
    )
  )

print(figure_summary)

# ------------------------------------------------------------
# 5. Create figure
# ------------------------------------------------------------

condition_colours <- c(
  "No memory" = "#B0B0B0",
  "Memory" = "#4F83A3"
)

create_panel <- function(
  panel_data,
  panel_title,
  y_axis_title,
  y_axis_labels
) {
  ggplot(
    panel_data,
    aes(
      x = plot_condition,
      y = mean_value,
      fill = memory_condition,
      group = memory_condition
    )
  ) +
    geom_col(
      width = 0.42,
      position = position_dodge(width = 0.72),
      colour = "black",
      linewidth = 0.5
    ) +
    geom_errorbar(
      aes(ymin = ci_lower, ymax = ci_upper),
      position = position_dodge(width = 0.72),
      width = 0.08,
      linewidth = 0.9,
      colour = "black"
    ) +
    geom_point(
      shape = 21,
      size = 5.8,
      colour = "black",
      stroke = 0.8,
      position = position_dodge(width = 0.72)
    ) +
    geom_text(
      aes(
        label = value_label,
        vjust = if_else(
          figure_dimension == "Weighted tokens" &
            memory_condition == "No memory",
          -3.2,
          -2.5
        )
      ),
      fontface = "bold",
      colour = "black",
      size = 4.8,
      position = position_dodge(width = 0.72)
    ) +
    scale_fill_manual(
      values = condition_colours,
      name = NULL
    ) +
    scale_x_discrete(
      labels = function(x) {
        gsub("\n", "<br>", x)
      }
    ) +
    scale_y_continuous(
      labels = y_axis_labels,
      expand = expansion(mult = c(0, 0.22))
    ) +
    coord_cartesian(clip = "off") +
    labs(
      title = panel_title,
      x = NULL,
      y = y_axis_title
    ) +
  theme_classic(base_size = 18) +
    theme(
      axis.title = element_text(face = "bold"),
      axis.title.y = element_text(margin = margin(r = 12)),
      axis.text.x = ggtext::element_markdown(
        size = 16,
        margin = margin(t = 8),
        lineheight = 1.12
      ),
      axis.text.y = element_text(colour = "black"),
      plot.title = element_text(
        face = "bold",
        size = 20,
        hjust = 0.5,
        margin = margin(t = 4, b = 8)
      ),
      plot.margin = margin(t = 25, r = 15, b = 10, l = 15),
      legend.position = "bottom",
      legend.title = element_blank(),
      legend.text = element_text(size = 18),
      legend.key.size = grid::unit(0.8, "lines"),
      legend.spacing.x = grid::unit(0.6, "cm")
    )
}

correct_decision_plot <- create_panel(
  panel_data = filter(
    figure_summary,
    figure_dimension == "Correct decisions"
  ),
  panel_title = "Decision effectiveness",
  y_axis_title =
    "Share selecting the correct\ncandidate (%)",
  y_axis_labels = label_percent(scale = 1, accuracy = 1)
)

weighted_tokens_plot <- create_panel(
  panel_data = filter(
    figure_summary,
    figure_dimension == "Weighted tokens"
  ),
  panel_title = "Weighted token usage",
  y_axis_title = "Weighted tokens per\nsimulation (millions)",
  y_axis_labels = label_number(accuracy = 0.1)
)

figure_legend <- get_legend(correct_decision_plot)
correct_decision_plot <- correct_decision_plot + theme(legend.position = "none")
weighted_tokens_plot <- weighted_tokens_plot + theme(legend.position = "none")

combined_panels <- plot_grid(
  correct_decision_plot +
    theme(
      axis.title.y = element_text(size = 18, margin = margin(r = 12)),
      axis.text.y = element_text(size = 16),
      axis.text.x = ggtext::element_markdown(size = 16),
      plot.margin = margin(t = 18, r = 18, b = 12, l = 40)
    ),
  weighted_tokens_plot +
    theme(
      axis.title.y = element_text(size = 18, margin = margin(r = 12)),
      axis.text.y = element_text(size = 16),
      axis.text.x = ggtext::element_markdown(size = 16),
      plot.margin = margin(t = 18, r = 18, b = 12, l = 40)
    ),
  ncol = 2,
  align = "h",
  axis = "tb",
  rel_widths = c(1, 1)
)

combined_plot <- plot_grid(
  combined_panels,
  ggdraw() +
    draw_label(
      "n = 200 per condition",
      colour = "#555555",
      size = 14
    ),
  figure_legend,
  ggdraw() +
    draw_label(
      "Context configuration",
      fontface = "bold",
      size = 20
    ),
  ncol = 1,
  rel_heights = c(1, 0.06, 0.10, 0.07)
)

print(combined_plot)

# ------------------------------------------------------------
# 6. Save figure
# ------------------------------------------------------------

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_correct_decisions_weighted_tokens_by_condition.pdf"
  ),
  plot = combined_plot,
  width = 16,
  height = 5.8,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_correct_decisions_weighted_tokens_by_condition.svg"
  ),
  plot = combined_plot,
  width = 16,
  height = 5.8,
  units = "in"
)
