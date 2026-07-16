# ============================================================
# Figure: Share of correct decisions by experimental condition
# Baseline | Low | Moderate | High
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
# 2. Prepare four experimental conditions
# ------------------------------------------------------------

correct_decision_data <- simulation_metrics %>%
  mutate(
    smm_mode = tolower(trimws(as.character(smm_mode))),
    
    context_transparency_condition = factor(
      context_transparency_condition,
      levels = c("low", "moderate", "high")
    ),
    
    decision_correct = as.integer(decision_correct),
    
    plot_condition = case_when(
      smm_mode == "baseline" ~ "Baseline",
      smm_mode == "treatment" &
        context_transparency_condition == "low" ~ "Low\ndiscussion\ncontext",
      smm_mode == "treatment" &
        context_transparency_condition == "moderate" ~ "Moderate\ndiscussion\ncontext",
      smm_mode == "treatment" &
        context_transparency_condition == "high" ~ "High\ndiscussion\ncontext",
      TRUE ~ NA_character_
    ),
    
    plot_condition = factor(
      plot_condition,
      levels = c(
        "Baseline",
        "Low\ndiscussion\ncontext",
        "Moderate\ndiscussion\ncontext",
        "High\ndiscussion\ncontext"
      )
    )
  ) %>%
  filter(
    !is.na(plot_condition),
    !is.na(decision_correct)
  )

# ------------------------------------------------------------
# 3. Calculate correct-decision shares and 95% normal-approximation CIs
# ------------------------------------------------------------

z_value <- qnorm(0.975)

correct_decision_summary <- correct_decision_data %>%
  group_by(plot_condition) %>%
  summarise(
    n = n(),
    correct_decisions = sum(decision_correct),
    correct_share = mean(decision_correct),
    .groups = "drop"
  ) %>%
  mutate(
    standard_error = sqrt(
      correct_share * (1 - correct_share) / n
    ),
    ci_lower = pmax(
      0,
      correct_share - z_value * standard_error
    ),
    ci_upper = pmin(
      1,
      correct_share + z_value * standard_error
    ),
    percentage_label = percent(correct_share, accuracy = 1)
  )

print(correct_decision_summary)

# Creates x-axis labels dynamically, so n is correct even if group sizes change
# The invisible second line under Baseline aligns all n labels vertically
condition_axis_labels <- setNames(
  vapply(
    as.character(correct_decision_summary$plot_condition),
    function(condition) {
      
      condition_label <- gsub("\n", "<br>", condition)
      
      # Give Baseline an invisible second line to match the treatment labels
      if (!grepl("<br>", condition_label)) {
        condition_label <- paste0(condition_label, "<br>&nbsp;")
      }
      
      paste0(
        "<b>",
        condition_label,
        "</b><br><br>",
        "<i><span style='font-size:9pt; color:#555555;'>",
        "n = ",
        correct_decision_summary$n[
          as.character(correct_decision_summary$plot_condition) == condition
        ],
        "</span></i>"
      )
    },
    character(1)
  ),
  as.character(correct_decision_summary$plot_condition)
)

# ------------------------------------------------------------
# 4. Create figure
# ------------------------------------------------------------

correct_decision_plot <- ggplot(
  correct_decision_summary,
  aes(
    x = plot_condition,
    y = correct_share,
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
      y = ci_upper + 0.06,
      label = percentage_label
    ),
    fontface = "bold",
    colour = "black",
    size = 3.9
  ) +
  scale_fill_manual(
    values = c(
      "Baseline" = "#B0B0B0",
      "Low\ndiscussion\ncontext" = "#D8E5EE",
      "Moderate\ndiscussion\ncontext" = "#7FA9C4",
      "High\ndiscussion\ncontext" = "#315F7D"
    ),
    guide = "none"
  ) +
  scale_x_discrete(
    labels = condition_axis_labels
  ) +
  scale_y_continuous(
    limits = c(0, 1.15),
    breaks = seq(0, 1, by = 0.25),
    labels = percent_format(accuracy = 1),
    expand = expansion(mult = c(0, 0))
  ) +
  coord_cartesian(
    clip = "off"
  ) +
  labs(
    x = "Experimental condition",
    y = "Share of simulations selecting\nthe correct candidate (%)"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold"),
    axis.title.y = element_text(margin = margin(r = 12)),
    axis.title.x = element_text(margin = margin(t = 12)),
    axis.text.x = ggtext::element_markdown(
      size = 10.5,
      margin = margin(t = 8),
      lineheight = 1.12
    ),
    axis.text.y = element_text(colour = "black"),
    plot.margin = margin(t = 25, r = 15, b = 10, l = 15)
  )

print(correct_decision_plot)

# ------------------------------------------------------------
# 5. Save figure
# ------------------------------------------------------------

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_correct_decisions_by_condition.pdf"
  ),
  plot = correct_decision_plot,
  width = 5.5,
  height = 4.8,
  units = "in"
)

ggsave(
  filename = file.path(
    output_dir,
    "thesis_figure_correct_decisions_by_condition.svg"
  ),
  plot = correct_decision_plot,
  width = 5.5,
  height = 4.8,
  units = "in"
)
