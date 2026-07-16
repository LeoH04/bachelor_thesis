# ============================================================
# Appendix B: Prompt Conditions
#
# Creates a Word document containing:
#   Table B1: Prompt-visible input context by experimental condition
#
# Output:
#   03_report/appendix/appendix_B_prompt_conditions.docx
# ============================================================

# ------------------------------------------------------------
# 0. Setup
# ------------------------------------------------------------

rm(list = ls())

# Install once if necessary:
# install.packages(c("flextable", "officer"))

library(flextable)
library(officer)

path <- getwd()

output_dir <- file.path(
  path,
  "03_report",
  "appendix"
)

output_file <- file.path(
  output_dir,
  "appendix_B_prompt_conditions.docx"
)

cm_to_in <- function(x) {
  x / 2.54
}

thesis_section <- prop_section(
  page_size = page_size(
    width = cm_to_in(21.0),
    height = cm_to_in(29.7),
    orient = "portrait",
    unit = "in"
  ),
  
  page_margins = page_mar(
    top = cm_to_in(3.0),
    bottom = cm_to_in(2.0),
    left = cm_to_in(2.5),
    right = cm_to_in(2.5),
    header = cm_to_in(1.5),
    footer = cm_to_in(1.25)
  )
)

dir.create(
  output_dir,
  recursive = TRUE,
  showWarnings = FALSE
)

# ------------------------------------------------------------
# 1. Create Table B1: Prompt-visible input context
# ------------------------------------------------------------

condition_table <- data.frame(
  Condition = c(
    "Low treatment",
    "Moderate treatment",
    "High treatment",
    "Moderate baseline"
  ),
  `Explicit SMM memory` = c(
    "Yes",
    "Yes",
    "Yes",
    "No"
  ),
  `Public discussion and tool history visible` = c(
    "No raw history",
    "Full public history",
    "Full public history",
    "Full public history"
  ),
  `Model-thought history visible` = c(
    "No",
    "No",
    "Yes, when available",
    "No"
  ),
  check.names = FALSE,
  stringsAsFactors = FALSE
)

# ------------------------------------------------------------
# 2. Minimal LaTeX-style formatting
# ------------------------------------------------------------

thin_line <- fp_border(
  color = "black",
  style = "solid",
  width = 0.75
)

double_line <- fp_border(
  color = "black",
  style = "double",
  width = 1
)

prompt_conditions_table <- flextable(condition_table)

prompt_conditions_table <- add_footer_lines(
  prompt_conditions_table,
  values = paste(
    "Note:",
    "The public-output template, public transcript format, candidate facts,",
    "and structured vote metadata requirement were held constant across",
    "conditions."
  )
)

prompt_conditions_table <- border_remove(prompt_conditions_table)

prompt_conditions_table <- hline_top(
  prompt_conditions_table,
  border = double_line,
  part = "header"
)

prompt_conditions_table <- hline_bottom(
  prompt_conditions_table,
  border = thin_line,
  part = "header"
)

prompt_conditions_table <- hline_bottom(
  prompt_conditions_table,
  border = thin_line,
  part = "body"
)

prompt_conditions_table <- font(
  prompt_conditions_table,
  fontname = "Times New Roman",
  part = "all"
)

prompt_conditions_table <- fontsize(
  prompt_conditions_table,
  size = 11,
  part = "all"
)

prompt_conditions_table <- fontsize(
  prompt_conditions_table,
  size = 10,
  part = "footer"
)

prompt_conditions_table <- bold(
  prompt_conditions_table,
  part = "header"
)

prompt_conditions_table <- bold(
  prompt_conditions_table,
  j = 1,
  part = "body"
)

prompt_conditions_table <- align(
  prompt_conditions_table,
  align = "center",
  part = "header"
)

prompt_conditions_table <- align(
  prompt_conditions_table,
  j = 1,
  align = "left",
  part = "body"
)

prompt_conditions_table <- align(
  prompt_conditions_table,
  j = 2:4,
  align = "center",
  part = "body"
)

prompt_conditions_table <- align(
  prompt_conditions_table,
  align = "left",
  part = "footer"
)

prompt_conditions_table <- valign(
  prompt_conditions_table,
  valign = "center",
  part = "all"
)

prompt_conditions_table <- padding(
  prompt_conditions_table,
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "header"
)

prompt_conditions_table <- padding(
  prompt_conditions_table,
  padding.top = 3,
  padding.bottom = 3,
  padding.left = 2,
  padding.right = 2,
  part = "body"
)

prompt_conditions_table <- padding(
  prompt_conditions_table,
  padding.top = 2,
  padding.bottom = 2,
  padding.left = 2,
  padding.right = 2,
  part = "footer"
)

prompt_conditions_table <- width(
  prompt_conditions_table,
  j = 1,
  width = 1.45
)

prompt_conditions_table <- width(
  prompt_conditions_table,
  j = 2,
  width = 1.10
)

prompt_conditions_table <- width(
  prompt_conditions_table,
  j = 3,
  width = 2.25
)

prompt_conditions_table <- width(
  prompt_conditions_table,
  j = 4,
  width = 1.25
)

prompt_conditions_table <- set_table_properties(
  prompt_conditions_table,
  layout = "fixed",
  opts_word = list(
    split = TRUE,
    repeat_headers = FALSE
  )
)

# ------------------------------------------------------------
# 3. Export to Word
# ------------------------------------------------------------

save_as_docx(
  prompt_conditions_table,
  path = output_file,
  pr_section = thesis_section,
  align = "center"
)

cat(
  "\nAppendix B prompt-condition table exported to:\n",
  output_file,
  "\n",
  sep = ""
)
