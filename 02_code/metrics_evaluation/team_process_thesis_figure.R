# ============================================================
# Figure: Communication and cooperation by experimental condition
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
    
    context_transparency_condition = factor(
      context_transparency_condition,
      levels = c("low", "moderate", "high")
    ),
    
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
  group_by(process_dimension, plot_condition) %>%
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
# 4. Create dynamic x-axis labels
# ------------------------------------------------------------

condition_n <- team_process_summary %>%
  distinct(plot_condition, n) %>%
  arrange(plot_condition)

condition_axis_labels <- setNames(
  vapply(
    as.character(condition_n$plot_condition),
    function(condition) {
      
      # Wrap the treatment labels compactly and align Baseline to their height
      condition_label <- gsub("\n", "<br>", condition)
      condition_label <- sub(
        "transparency",
        "trans-<br>parency",
        condition_label,
        fixed = TRUE
      )
      
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
        condition_n$n[as.character(condition_n$plot_condition) == condition],
        "</span></i>"
      )
    },
    character(1)
  ),
  as.character(condition_n$plot_condition)
)

# ------------------------------------------------------------
# 5. Create separate figures
# ------------------------------------------------------------

create_team_process_plot <- function(process_name) {
  plot_data <- team_process_summary %>%
    filter(process_dimension == process_name) %>%
    mutate(plot_label_y = label_y)
  y_upper_limit <- if (process_name == "Communication") {
    0.6
  } else {
    max(plot_data$plot_label_y, na.rm = TRUE) * 1.12
  }
  y_breaks <- if (process_name == "Communication") {
    seq(0, 0.6, by = 0.2)
  } else {
    pretty_breaks(n = 4)
  }

  ggplot(
    plot_data,
    aes(
      x = plot_condition,
      y = mean_score,
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
        label = score_label
      ),
      fontface = "bold",
      colour = "black",
      size = 3.1,
      vjust = -2.5
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
      )
    ) +
    theme_classic(base_size = 10) +
    theme(
      axis.title = element_text(face = "bold"),
      axis.title.y = element_text(margin = margin(r = 6)),
      axis.title.x = element_text(margin = margin(t = 7)),
      plot.title = element_text(
        face = "bold",
        size = 12,
        hjust = 0.5,
        margin = margin(t = 4, b = 8)
      ),
      axis.text.x = ggtext::element_markdown(
        size = 7.2,
        margin = margin(t = 5),
        lineheight = 1.00
      ),
      axis.text.y = element_text(colour = "black"),
      plot.margin = margin(t = 12, r = 5, b = 3, l = 5)
    )
}

communication_plot <- create_team_process_plot("Communication")
cooperation_plot <- create_team_process_plot("Cooperation")

combined_panels <- plot_grid(
  communication_plot + labs(x = NULL),
  cooperation_plot + labs(x = NULL),
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
  height = 5.6,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_communication_cooperation_by_condition.svg"
  ),
  plot = combined_plot,
  width = 16,
  height = 5.6,
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
