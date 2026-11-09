# ============================================================
# Figure: Decision effectiveness versus weighted token use
# Six context configurations: Low, Moderate, and High access,
# with and without explicit Memory
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
# 2. Prepare the six access-by-memory configurations
# ------------------------------------------------------------

output_token_weight <- 5
weighted_token_scale <- 1000000

figure_data <- simulation_metrics %>%
  mutate(
    smm_mode = tolower(trimws(as.character(smm_mode))),
    context_transparency_condition = tolower(
      trimws(as.character(context_transparency_condition))
    ),
    input_tokens = as.numeric(input_tokens),
    output_tokens = as.numeric(output_tokens),
    decision_correct = as.integer(decision_correct),
    weighted_tokens_million =
      (input_tokens + output_token_weight * output_tokens) /
        weighted_token_scale,
    plot_condition = case_when(
      smm_mode == "baseline" & context_transparency_condition == "low" ~
        "Low access - No memory",
      smm_mode == "baseline" & context_transparency_condition == "moderate" ~
        "Moderate access - No memory",
      smm_mode == "baseline" & context_transparency_condition == "high" ~
        "High access - No memory",
      smm_mode == "treatment" &
        context_transparency_condition == "low" ~
        "Low access - Memory",
      smm_mode == "treatment" &
        context_transparency_condition == "moderate" ~
        "Moderate access - Memory",
      smm_mode == "treatment" &
        context_transparency_condition == "high" ~
        "High access - Memory",
      TRUE ~ NA_character_
    ),
    memory_condition = if_else(
      smm_mode == "treatment",
      "Memory",
      "No memory"
    )
  ) %>%
  filter(
    !is.na(plot_condition),
    !is.na(decision_correct),
    !is.na(weighted_tokens_million)
  )

condition_order <- c(
  "Low access - No memory",
  "Moderate access - No memory",
  "High access - No memory",
  "Low access - Memory",
  "Moderate access - Memory",
  "High access - Memory"
)

# ------------------------------------------------------------
# 3. Condition means
# ------------------------------------------------------------

condition_summary <- figure_data %>%
  group_by(plot_condition, memory_condition) %>%
  summarise(
    n = n(),
    mean_tokens = mean(weighted_tokens_million),
    correct_share = mean(decision_correct),
    .groups = "drop"
  ) %>%
  mutate(
    plot_condition = factor(plot_condition, levels = condition_order),
    percentage_label = sub("\\.0%$", "%", sprintf("%.1f%%", 100 * correct_share)),
    point_label = paste0(
      "(", number(mean_tokens, accuracy = 0.001), ", ", percentage_label, ")"
    )
  ) %>%
  arrange(plot_condition)

if (nrow(condition_summary) != 6L) {
  stop("Expected six access-by-memory configurations; check the source data.")
}

# A point is on the descriptive frontier when no other condition uses no more
# tokens and achieves at least as many correct decisions, with one strict gain.
condition_summary <- condition_summary %>%
  rowwise() %>%
  mutate(
    pareto_frontier = !any(
      condition_summary$mean_tokens <= mean_tokens &
        condition_summary$correct_share >= correct_share &
        (condition_summary$mean_tokens < mean_tokens |
           condition_summary$correct_share > correct_share)
    )
  ) %>%
  ungroup()

print(condition_summary)

# ------------------------------------------------------------
# 4. Label positions and plot styling
# ------------------------------------------------------------

label_positions <- tibble(
  plot_condition = factor(condition_order, levels = condition_order),
  label_x = c(0.115, 0.105, 0.015, 0.565, 0.555, 0.620),
  label_name_y = c(37.5, 46.3, 57.0, 78.2, 69.2, 58.0),
  label_value_y = c(34.3, 43.1, 53.8, 74.9, 66.0, 54.8)
)

plot_data <- condition_summary %>%
  left_join(label_positions, by = "plot_condition") %>%
  mutate(
    condition_label = as.character(plot_condition),
    pareto_status = factor(
      if_else(pareto_frontier, "Pareto frontier", "Dominated"),
      levels = c("Pareto frontier", "Dominated")
    )
  )

frontier_data <- plot_data %>%
  filter(pareto_frontier) %>%
  arrange(mean_tokens)

frontier_colour <- "#C83E4D"
dominated_colour <- "#666666"
dominated_fill <- "#F7D9DD"
plot_x_max <- 0.85
plot_y_min <- 30

dominated_region <- bind_rows(
  frontier_data %>%
    transmute(x = mean_tokens, y = 100 * correct_share),
  tibble(
    x = c(plot_x_max, plot_x_max, min(frontier_data$mean_tokens)),
    y = c(
      100 * max(frontier_data$correct_share),
      plot_y_min,
      plot_y_min
    )
  )
)

tradeoff_plot <- ggplot(
  plot_data,
  aes(x = mean_tokens, y = 100 * correct_share)
) +
  geom_polygon(
    data = dominated_region,
    aes(x = x, y = y, fill = "Dominated region"),
    inherit.aes = FALSE,
    colour = NA,
    alpha = 0.65
  ) +
  # The line connects observed non-dominated means only.
  geom_line(
    data = frontier_data,
    aes(group = 1),
    colour = frontier_colour,
    linewidth = 0.65,
    linetype = "dashed"
  ) +
  geom_point(
    aes(shape = pareto_status, colour = pareto_status),
    fill = frontier_colour,
    size = 4.0,
    stroke = 0.85
  ) +
  geom_text(
    aes(
      x = label_x,
      y = label_name_y,
      label = condition_label
    ),
    hjust = 0,
    colour = "black",
    fontface = "bold",
    size = 4.0
  ) +
  geom_text(
    aes(
      x = label_x,
      y = label_value_y,
      label = point_label
    ),
    hjust = 0,
    colour = "black",
    size = 3.8
  ) +
  annotate(
    "label",
    x = 0.40,
    y = 63.7,
    label = "Pareto frontier",
    angle = 16,
    label.padding = grid::unit(0.05, "lines"),
    linewidth = 0,
    fill = "white",
    colour = frontier_colour,
    fontface = "italic",
    size = 3.3
  ) +
  scale_shape_manual(
    values = c("Pareto frontier" = 21, "Dominated" = 4),
    name = NULL
  ) +
  scale_fill_manual(
    values = c("Dominated region" = dominated_fill),
    name = NULL
  ) +
  scale_colour_manual(
    values = c(
      "Pareto frontier" = frontier_colour,
      "Dominated" = dominated_colour
    ),
    guide = "none"
  ) +
  guides(
    fill = guide_legend(
      order = 2,
      override.aes = list(alpha = 0.65, colour = NA)
    ),
    shape = guide_legend(
      order = 1,
      override.aes = list(
        fill = c(frontier_colour, NA),
        colour = c(frontier_colour, dominated_colour),
        size = 4.0
      )
    )
  ) +
  scale_x_continuous(
    breaks = seq(0, 0.8, by = 0.1),
    labels = label_number(accuracy = 0.1),
    expand = expansion(mult = c(0, 0))
  ) +
  scale_y_continuous(
    breaks = seq(30, 80, by = 10),
    labels = label_number(suffix = "%"),
    expand = expansion(mult = c(0, 0))
  ) +
  coord_cartesian(
    xlim = c(0, plot_x_max),
    ylim = c(plot_y_min, 80),
    expand = FALSE,
    clip = "off"
  ) +
  labs(
    x = "Weighted token usage per simulation (millions)",
    y = "Correct decisions per simulation (%)"
  ) +
  theme_classic(base_size = 14) +
  theme(
    axis.title = element_text(face = "bold"),
    axis.title.y = element_text(margin = margin(r = 12)),
    axis.text = element_text(colour = "black"),
    plot.margin = margin(t = 20, r = 42, b = 8, l = 15),
    legend.position = "bottom",
    legend.title = element_blank(),
    legend.text = element_text(size = 13),
    legend.key.size = grid::unit(0.8, "lines"),
    legend.spacing.x = grid::unit(0.6, "cm")
  )

# ------------------------------------------------------------
# 5. Save figure
# ------------------------------------------------------------

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_decision_effectiveness_token_tradeoff.pdf"
  ),
  plot = tradeoff_plot,
  width = 10.5,
  height = 6.0,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_decision_effectiveness_token_tradeoff.svg"
  ),
  plot = tradeoff_plot,
  width = 10.5,
  height = 6.0,
  units = "in"
)
