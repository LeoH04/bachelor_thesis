# ============================================================
# Figure: Communication and cooperation by access and memory condition
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

figure_width <- 3.35
figure_height <- 3.55

simulation_metrics <- read_csv(
  data_path,
  na = c("", "NA"),
  show_col_types = FALSE
)

# ------------------------------------------------------------
# 2. Prepare conditions and process measures
# ------------------------------------------------------------

team_process_data <- simulation_metrics %>%
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
    
    context_transparency_condition = factor(
      context_transparency_condition,
      levels = c("low", "moderate", "high")
    ),
    
    plot_condition = factor(
      context_transparency_condition,
      levels = c("low", "moderate", "high"),
      labels = c("Low\naccess", "Moderate\naccess", "High\naccess")
    )
  ) %>%
  pivot_longer(
    cols = c(
      team_process_communication,
      team_process_cooperation
    ),
    names_to = "process_dimension",
    values_to = "score"
  ) %>%
  mutate(
    process_dimension = recode(
      process_dimension,
      "team_process_communication" = "Communication",
      "team_process_cooperation" = "Cooperation"
    ),
    process_dimension = factor(
      process_dimension,
      levels = c("Communication", "Cooperation")
    )
  ) %>%
  filter(
    !is.na(plot_condition),
    !is.na(memory_condition),
    !is.na(score)
  )

# Check that both measures are proportions
if (any(
  team_process_data$score < 0 |
  team_process_data$score > 1,
  na.rm = TRUE
)) {
  stop("Communication or cooperation scores fall outside the expected 0–1 range.")
}

# ------------------------------------------------------------
# 3. Calculate means and 95% confidence intervals
# ------------------------------------------------------------

team_process_summary <- team_process_data %>%
  group_by(process_dimension, plot_condition, memory_condition) %>%
  summarise(
    n = n(),
    mean_score = mean(score),
    standard_error = sd(score) / sqrt(n),
    .groups = "drop"
  ) %>%
  mutate(
    t_value = qt(0.975, df = n - 1),
    ci_lower = pmax(0, mean_score - t_value * standard_error),
    ci_upper = pmin(1, mean_score + t_value * standard_error),
    label_y = pmin(1.10, ci_upper + 0.06),
    score_label = number(mean_score, accuracy = 0.01)
  )

print(team_process_summary)

# ------------------------------------------------------------
# 5. Create separate figures
# ------------------------------------------------------------

create_team_process_plot <- function(process_name) {
  plot_data <- team_process_summary %>%
    filter(process_dimension == process_name) %>%
    mutate(plot_label_y = label_y)
  y_upper_limit <- 0.8
  y_breaks <- seq(0, 0.8, by = 0.2)

  ggplot(
    plot_data,
    aes(
      x = plot_condition,
      y = mean_score,
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
      aes(
        ymin = ci_lower,
        ymax = ci_upper
      ),
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
        label = score_label
      ),
      fontface = "bold",
      colour = "black",
      size = 4.8,
      vjust = -2.5,
      position = position_dodge(width = 0.72)
    ) +
    scale_fill_manual(
      values = c(
        "No memory" = "#B0B0B0",
        "Memory" = "#4F83A3"
      ),
      name = NULL
    ) +
    scale_x_discrete(
      labels = function(x) {
        gsub("\n", "<br>", x)
      }
    ) +
    scale_y_continuous(
      limits = c(0, y_upper_limit),
      breaks = y_breaks,
      labels = number_format(accuracy = 0.1),
      expand = expansion(mult = c(0, 0))
    ) +
    coord_cartesian(
      clip = "off"
    ) +
    labs(
      title = paste0(process_name, " quality"),
      x = "Context configuration",
      y = paste0(
        "Mean ",
        tolower(process_name),
        " quality score\nper simulation"
      ),
      caption = "n = 200 per condition"
    ) +
    theme_classic(base_size = 18) +
    theme(
      axis.title = element_text(face = "bold"),
      axis.title.y = element_text(margin = margin(r = 12)),
      axis.title.x = element_text(margin = margin(t = 7)),
      plot.title = element_text(
        face = "bold",
        size = 20,
        hjust = 0.5,
        margin = margin(t = 4, b = 8)
      ),
      axis.text.x = ggtext::element_markdown(
        size = 16,
        margin = margin(t = 8),
        lineheight = 1.12
      ),
      axis.text.y = element_text(colour = "black"),
      plot.caption = element_text(
        hjust = 0.5,
        colour = "#555555",
        size = 12,
        margin = margin(t = 8)
      ),
      plot.margin = margin(t = 25, r = 15, b = 10, l = 15),
      legend.position = "bottom",
      legend.title = element_blank(),
      legend.text = element_text(size = 18),
      legend.key.size = grid::unit(0.8, "lines"),
      legend.spacing.x = grid::unit(0.6, "cm")
    )
}

communication_plot <- create_team_process_plot("Communication")
cooperation_plot <- create_team_process_plot("Cooperation")

figure_legend <- get_legend(communication_plot)
communication_plot <- communication_plot + theme(legend.position = "none")
cooperation_plot <- cooperation_plot + theme(legend.position = "none")

combined_panels <- plot_grid(
  communication_plot +
    labs(x = NULL) +
    theme(
      plot.title = element_text(size = 20),
      axis.title.y = element_text(size = 18, margin = margin(r = 12)),
      axis.text.y = element_text(size = 16),
      axis.text.x = ggtext::element_markdown(size = 16),
      plot.caption = element_blank(),
      plot.margin = margin(t = 18, r = 18, b = 12, l = 40)
    ),
  cooperation_plot +
    labs(x = NULL) +
    theme(
      plot.title = element_text(size = 20),
      axis.title.y = element_text(size = 18, margin = margin(r = 12)),
      axis.text.y = element_text(size = 16),
      axis.text.x = ggtext::element_markdown(size = 16),
      plot.caption = element_blank(),
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

print(communication_plot)
print(cooperation_plot)
print(combined_plot)

# ------------------------------------------------------------
# 6. Save figures
# ------------------------------------------------------------

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_communication_by_condition.pdf"
  ),
  plot = communication_plot,
  width = figure_width,
  height = figure_height,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_communication_cooperation_by_condition.pdf"
  ),
  plot = combined_plot,
  width = 16,
  height = 5.8,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_communication_cooperation_by_condition.svg"
  ),
  plot = combined_plot,
  width = 16,
  height = 5.8,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_communication_by_condition.svg"
  ),
  plot = communication_plot,
  width = figure_width,
  height = figure_height,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_cooperation_by_condition.pdf"
  ),
  plot = cooperation_plot,
  width = figure_width,
  height = figure_height,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_cooperation_by_condition.svg"
  ),
  plot = cooperation_plot,
  width = figure_width,
  height = figure_height,
  units = "in"
)
