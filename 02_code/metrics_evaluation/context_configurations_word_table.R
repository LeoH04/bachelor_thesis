# ============================================================
# Context configurations Word table
#
# Creates a Word document describing the four input-context
# configurations used in the multi-agent simulation.
#
# Output:
#   03_report/tables/context_configurations.docx
# ============================================================

if (!is.null(dev.list())) {
  dev.off()
}

rm(list = ls())

# Install once if necessary:
# install.packages(c("flextable", "officer"))

library(flextable)
library(officer)

path <- getwd()

output_dir <- file.path(
  path,
  "03_report",
  "tables"
)

output_file <- file.path(
  output_dir,
  "context_configurations.docx"
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

# The wording describes prompt-visible input context. It does not imply that
# reasoning traces are public transcript content.
context_configurations <- data.frame(
  Configuration = c(
    "Baseline",
    "Low access",
    "Moderate access",
    "High access"
  ),
  `Structured memory mechanism` = c(
    "No",
    "Yes",
    "Yes",
    "Yes"
  ),
  `Interaction history (including targeted Q&A)` = c(
    "Complete history",
    "Immediately preceding agent only",
    "Complete history",
    "Complete history"
  ),
  `Prior reasoning traces` = c(
    "No",
    "No",
    "No",
    "All previous turns"
  ),
  check.names = FALSE,
  stringsAsFactors = FALSE
)

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

configuration_table <- flextable(context_configurations)
configuration_table <- border_remove(configuration_table)
configuration_table <- border_outer(
  configuration_table,
  border = thin_line,
  part = "all"
)
configuration_table <- hline_top(
  configuration_table,
  border = double_line,
  part = "header"
)
configuration_table <- border_inner_h(
  configuration_table,
  border = thin_line,
  part = "all"
)
configuration_table <- border_inner_v(
  configuration_table,
  border = thin_line,
  part = "all"
)
configuration_table <- font(
  configuration_table,
  fontname = "Times New Roman",
  part = "all"
)
configuration_table <- fontsize(
  configuration_table,
  size = 10,
  part = "all"
)
configuration_table <- bold(
  configuration_table,
  part = "header"
)
configuration_table <- align(
  configuration_table,
  align = "center",
  part = "header"
)
configuration_table <- align(
  configuration_table,
  j = 1,
  align = "left",
  part = "body"
)
configuration_table <- align(
  configuration_table,
  j = 2:4,
  align = "center",
  part = "body"
)
configuration_table <- valign(
  configuration_table,
  valign = "top",
  part = "all"
)
configuration_table <- padding(
  configuration_table,
  padding.top = 3,
  padding.bottom = 3,
  padding.left = 2,
  padding.right = 2,
  part = "all"
)
configuration_table <- set_table_properties(
  configuration_table,
  layout = "fixed",
  opts_word = list(
    split = TRUE,
    repeat_headers = TRUE
  )
)
configuration_table <- width(
  configuration_table,
  j = 1,
  width = 1.35
)
configuration_table <- width(
  configuration_table,
  j = 2,
  width = 1.55
)
configuration_table <- width(
  configuration_table,
  j = 3,
  width = 2.05
)
configuration_table <- width(
  configuration_table,
  j = 4,
  width = 1.35
)

doc <- read_docx()
doc <- body_add_flextable(
  doc,
  value = configuration_table
)
doc <- body_set_default_section(
  doc,
  value = thesis_section
)

print(
  doc,
  target = output_file
)

cat(
  "\nContext-configuration Word document exported to:\n",
  output_file,
  "\n",
  sep = ""
)
