# ============================================================
# Figure: Communication and cooperation by experimental condition
# Baseline | Low discussion context | Moderate discussion context | High discussion context
# Bars + trend line + 95% confidence intervals
# ============================================================

rm(list = ls())

library(tidyverse)
library(scales)
library(ggtext)

options(scipen = 999)

# ------------------------------------------------------------
# 1. Paths and data
# ------------------------------------------------------------

project_path <- getwd()

data_path <- file.path(
  project_path,
  "01_data/processed/simulation_metrics_final_100_gpt_oss_120b.csv"
)

output_dir <- file.path(project_path, "03_report/graphs")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

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
        context_transparency_condition == "low" ~ "Low\ndiscussion context",
      smm_mode == "treatment" &
        context_transparency_condition == "moderate" ~ "Moderate\ndiscussion context",
      smm_mode == "treatment" &
        context_transparency_condition == "high" ~ "High\ndiscussion context",
      TRUE ~ NA_character_
    ),
    
    plot_condition = factor(
      plot_condition,
      levels = c(
        "Baseline",
        "Low\ndiscussion context",
        "Moderate\ndiscussion context",
        "High\ndiscussion context"
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
    percentage_label = percent(mean_score, accuracy = 1)
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
      
      # Ensure every condition title occupies exactly two lines
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
        condition_n$n[as.character(condition_n$plot_condition) == condition],
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

team_process_plot <- ggplot(
  team_process_summary,
  aes(
    x = plot_condition,
    y = mean_score,
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
    size = 4.6,
    colour = "black",
    stroke = 0.65
  ) +
  geom_text(
    aes(
      y = label_y,
      label = percentage_label
    ),
    fontface = "bold",
    colour = "black",
    size = 3.9
  ) +
  scale_fill_manual(
    values = c(
      "Baseline" = "#B0B0B0",
      "Low\ndiscussion context" = "#D8E5EE",
      "Moderate\ndiscussion context" = "#7FA9C4",
      "High\ndiscussion context" = "#315F7D"
    ),
    guide = "none"
  ) +
  scale_x_discrete(
    labels = condition_axis_labels
  ) +
  scale_y_continuous(
    limits = c(0, 1.13),
    breaks = seq(0, 1, by = 0.25),
    labels = percent_format(accuracy = 1),
    expand = expansion(mult = c(0, 0))
  ) +
  facet_wrap(
    ~ process_dimension,
    ncol = 2
  ) +
  coord_cartesian(
    clip = "off"
  ) +
  labs(
    x = "Experimental condition",
    y = "Mean score per simulation"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold"),
    
    axis.title.y = element_text(
      margin = margin(r = 12)
    ),
    
    axis.title.x = element_text(
      margin = margin(t = 12)
    ),
    
    axis.text.x = ggtext::element_markdown(
      size = 10.5,
      margin = margin(t = 8),
      lineheight = 1.12
    ),
    
    axis.text.y = element_text(
      colour = "black"
    ),
    
    strip.background = element_blank(),
    
    strip.text = element_text(
      face = "bold",
      size = 12,
      margin = margin(t = 4, b = 8)
    ),
    
    panel.spacing.x = grid::unit(1.8, "lines"),
    
    plot.margin = margin(
      t = 25,
      r = 30,
      b = 10,
      l = 15
    )
  )

print(team_process_plot)

# ------------------------------------------------------------
# 6. Save figure
# ------------------------------------------------------------

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_communication_cooperation_by_condition.pdf"
  ),
  plot = team_process_plot,
  width = 16,
  height = 5.6,
  units = "in"
)