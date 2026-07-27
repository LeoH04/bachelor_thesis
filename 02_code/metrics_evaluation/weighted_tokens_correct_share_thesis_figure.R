# ============================================================
# Figure: Decision quality and weighted tokens by condition
# Baseline | Low transparency | Moderate transparency | High transparency
# Bars + trend line + 95% confidence intervals
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
  "01_data/processed/simulation_metrics_final_200_gpt_oss_120b.csv"
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
    input_tokens = as.numeric(input_tokens),
    output_tokens = as.numeric(output_tokens),
    decision_correct = as.integer(decision_correct),
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
    !is.na(decision_correct),
    !is.na(weighted_total_tokens_million)
  )

# ------------------------------------------------------------
# 3. Calculate estimates and 95% confidence intervals
# ------------------------------------------------------------

z_value <- qnorm(0.975)

correct_share_summary <- figure_data %>%
  group_by(plot_condition) %>%
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
  group_by(plot_condition) %>%
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
  ) %>%
  group_by(figure_dimension) %>%
  mutate(
    panel_upper_limit = max(ci_upper) * 1.15,
    label_y = ci_upper + panel_upper_limit * if_else(
      figure_dimension == "Weighted tokens" &
        plot_condition == "Baseline",
      0.20,
      0.035
    )
  ) %>%
  ungroup()

print(figure_summary)

# ------------------------------------------------------------
# 4. Create dynamic x-axis labels
# ------------------------------------------------------------

condition_n <- figure_summary %>%
  distinct(plot_condition, n) %>%
  arrange(plot_condition)

condition_axis_labels <- setNames(
  vapply(
    as.character(condition_n$plot_condition),
    function(condition) {
      condition_label <- gsub("\n", "<br>", condition)

      if (!grepl("<br>", condition_label)) {
        condition_label <- paste0(condition_label, "<br>&nbsp;")
      }

      paste0(
        "<b>",
        condition_label,
        "</b><br><br>",
        "<i><span style='font-size:9pt; color:#555555;'>",
        "n = ",
        condition_n$n[
          as.character(condition_n$plot_condition) == condition
        ],
        "</span></i>"
      )
    },
    character(1)
  ),
  as.character(condition_n$plot_condition)
)

# ------------------------------------------------------------
# 5. Create figure
# ------------------------------------------------------------

condition_colours <- c(
  "Baseline" = "#B0B0B0",
  "Low\ntransparency" = "#D8E5EE",
  "Moderate\ntransparency" = "#7FA9C4",
  "High\ntransparency" = "#315F7D"
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
      fill = plot_condition
    )
  ) +
    geom_col(
      width = 0.56,
      colour = "black",
      linewidth = 0.35
    ) +
    geom_line(
      aes(group = 1),
      colour = "black",
      linewidth = 0.65
    ) +
    geom_errorbar(
      aes(ymin = ci_lower, ymax = ci_upper),
      width = 0.08,
      linewidth = 0.7,
      colour = "black"
    ) +
    geom_point(
      shape = 21,
      size = 4.6,
      colour = "black",
      stroke = 0.65
    ) +
    geom_text(
      aes(
        label = value_label,
        vjust = if_else(
          figure_dimension == "Weighted tokens" &
            plot_condition == "Baseline",
          -3.2,
          -2.5
        )
      ),
      fontface = "bold",
      colour = "black",
      size = 3.9
    ) +
    scale_fill_manual(
      values = condition_colours,
      guide = "none"
    ) +
    scale_x_discrete(labels = condition_axis_labels) +
    scale_y_continuous(
      labels = y_axis_labels,
      expand = expansion(mult = c(0, 0.14))
    ) +
    coord_cartesian(clip = "off") +
    labs(
      title = panel_title,
      x = NULL,
      y = y_axis_title
    ) +
    theme_classic(base_size = 12) +
    theme(
      axis.title = element_text(face = "bold"),
      axis.title.y = element_text(margin = margin(r = 12)),
      axis.text.x = ggtext::element_markdown(
        size = 10.5,
        margin = margin(t = 8),
        lineheight = 1.12
      ),
      axis.text.y = element_text(colour = "black"),
      plot.title = element_text(
        face = "bold",
        size = 12,
        hjust = 0.5,
        margin = margin(t = 4, b = 8)
      ),
      plot.margin = margin(t = 25, r = 15, b = 10, l = 15)
    )
}

correct_decision_plot <- create_panel(
  panel_data = filter(
    figure_summary,
    figure_dimension == "Correct decisions"
  ),
  panel_title = "Correct decisions",
  y_axis_title =
    "Share of simulations selecting the correct candidate (%)",
  y_axis_labels = label_percent(scale = 1, accuracy = 1)
)

weighted_tokens_plot <- create_panel(
  panel_data = filter(
    figure_summary,
    figure_dimension == "Weighted tokens"
  ),
  panel_title = "Weighted token usage",
  y_axis_title = "Mean weighted token usage per simulation (millions)",
  y_axis_labels = label_number(accuracy = 0.1)
)

combined_panels <- plot_grid(
  correct_decision_plot,
  weighted_tokens_plot,
  ncol = 2,
  align = "h",
  axis = "tb",
  rel_widths = c(1, 1)
)

combined_plot <- plot_grid(
  combined_panels,
  ggdraw() +
    draw_label(
      "Context configuration",
      fontface = "bold",
      size = 12
    ),
  ncol = 1,
  rel_heights = c(1, 0.07)
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
  height = 5.6,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_correct_decisions_weighted_tokens_by_condition.svg"
  ),
  plot = combined_plot,
  width = 16,
  height = 5.6,
  units = "in"
)
