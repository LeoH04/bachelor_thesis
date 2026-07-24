# ============================================================
# Appendix A: Experimental Task Materials
#
# Creates a Word document containing:
#   Table A2: Candidate facts and information distribution
#
# Input:
#   02_code/multi_agent_system/config/hidden_profile_task.json
#
# Output:
#   03_report/tables/appendix_A_experimental_task_materials.docx
# ============================================================

# ------------------------------------------------------------
# 0. Setup
# ------------------------------------------------------------

rm(list = ls())

# Install once if necessary:
# install.packages(c("jsonlite", "flextable", "officer"))

library(jsonlite)
library(flextable)
library(officer)

path <- getwd()

json_file <- file.path(
  path,
  "02_code",
  "multi_agent_system",
  "config", 
  "hidden_profile_task.json"
)

output_dir <- file.path(
  path,
  "03_report",
  "tables"
)

output_file <- file.path(
  output_dir,
  "appendix_A_experimental_task_materials.docx"
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

if (!file.exists(json_file)) {
  stop(
    paste0(
      "The task-materials JSON file was not found at:\n",
      json_file
    )
  )
}

# ------------------------------------------------------------
# 1. Load experimental task materials
# ------------------------------------------------------------

materials <- fromJSON(
  json_file,
  simplifyVector = FALSE
)

required_elements <- c(
  "candidates",
  "public_information",
  "private_information"
)

missing_elements <- setdiff(
  required_elements,
  names(materials)
)

if (length(missing_elements) > 0) {
  stop(
    paste(
      "The JSON file is missing:",
      paste(missing_elements, collapse = ", ")
    )
  )
}

candidates <- unlist(
  materials$candidates,
  use.names = FALSE
)

if (length(candidates) == 0) {
  stop("The task-materials JSON file does not define any candidates.")
}

agent_short_labels <- c(
  "agent_1" = "Anna Keller - Agent 1",
  "agent_2" = "Markus Weber - Agent 2",
  "agent_3" = "Sofia Brandt - Agent 3",
  "anna_keller" = "Anna Keller - Agent 1",
  "markus_weber" = "Markus Weber - Agent 2",
  "sofia_brandt" = "Sofia Brandt - Agent 3"
)

# ------------------------------------------------------------
# 2. Helper functions
# ------------------------------------------------------------

facts_for_candidate <- function(facts, candidate) {
  
  facts <- unlist(
    facts,
    use.names = FALSE
  )
  
  candidate_pattern <- paste0(
    "^",
    gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", candidate),
    "\\b"
  )
  
  facts[grepl(candidate_pattern, facts)]
}

no_break_text <- function(items) {
  
  gsub(
    " ",
    intToUtf8(160),
    items,
    fixed = TRUE
  )
}

strip_candidate_prefix <- function(facts, candidate) {
  
  candidate_pattern <- paste0(
    "^",
    gsub("([][{}()+*^$|\\\\?.])", "\\\\\\1", candidate),
    "\\s+"
  )
  
  gsub(
    candidate_pattern,
    "",
    facts
  )
}

shared_facts_for_candidate <- function(materials, candidate) {
  
  strip_candidate_prefix(
    facts_for_candidate(
      materials$public_information,
      candidate
    ),
    candidate
  )
}

private_facts_for_candidate <- function(facts, candidate) {
  
  strip_candidate_prefix(
    facts_for_candidate(
      facts,
      candidate
    ),
    candidate
  )
}

append_fact_group <- function(
    fact_chunks,
    label,
    facts,
    label_style,
    fact_style,
    add_blank_line = TRUE) {
  
  if (length(facts) == 0) {
    return(fact_chunks)
  }

  facts <- sub("\\.$", "", facts)
  
  fact_chunks[[length(fact_chunks) + 1]] <- as_chunk(
    paste0(label, "\n"),
    props = label_style
  )
  
  for (fact_index in seq_along(facts)) {
    line_end <- ifelse(
      fact_index < length(facts) || add_blank_line,
      "\n",
      ""
    )
    
    fact_chunks[[length(fact_chunks) + 1]] <- as_chunk(
      paste0("- ", facts[[fact_index]], line_end),
      props = fact_style
    )
  }
  
  if (add_blank_line) {
    fact_chunks[[length(fact_chunks) + 1]] <- as_chunk(
      "\n",
      props = fact_style
    )
  }
  
  fact_chunks
}

fact_paragraph_for_candidate <- function(materials, candidate) {
  
  shared_facts <- shared_facts_for_candidate(
    materials,
    candidate
  )
  
  fact_chunks <- list()
  regular_style <- fp_text(
    font.family = "Times New Roman",
    font.size = 11,
    bold = FALSE
  )
  label_style <- fp_text(
    font.family = "Times New Roman",
    font.size = 11,
    bold = TRUE
  )
  
  fact_chunks <- append_fact_group(
    fact_chunks,
    "Shared information",
    shared_facts,
    label_style,
    regular_style
  )
  
  private_keys <- names(materials$private_information)
  
  fact_chunks[[length(fact_chunks) + 1]] <- as_chunk(
    "Private information\n",
    props = label_style
  )
  
  for (agent_index in seq_along(private_keys)) {
    agent_key <- private_keys[[agent_index]]
    agent_label <- agent_short_labels[[agent_key]]
    
    if (is.null(agent_label)) {
      agent_label <- agent_key
    }
    
    agent_facts <- private_facts_for_candidate(
      materials$private_information[[agent_key]],
      candidate
    )
    
    fact_chunks <- append_fact_group(
      fact_chunks,
      agent_label,
      agent_facts,
      label_style,
      regular_style,
      add_blank_line = agent_index < length(private_keys)
    )
  }
  
  do.call(
    as_paragraph,
    fact_chunks
  )
}

format_appendix_table <- function(ft) {
  
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
  
  ft <- border_remove(ft)
  
  ft <- hline_top(
    ft,
    border = double_line,
    part = "header"
  )
  
  ft <- hline_bottom(
    ft,
    border = thin_line,
    part = "header"
  )
  
  ft <- hline_bottom(
    ft,
    border = thin_line,
    part = "body"
  )
  
  ft <- font(
    ft,
    fontname = "Times New Roman",
    part = "all"
  )
  
  ft <- fontsize(
    ft,
    size = 11,
    part = "header"
  )
  
  ft <- fontsize(
    ft,
    size = 11,
    part = "body"
  )
  
  ft <- bold(
    ft,
    part = "header"
  )
  
  ft <- align(
    ft,
    align = "center",
    part = "header"
  )
  
  ft <- align(
    ft,
    align = "left",
    part = "body"
  )
  
  ft <- valign(
    ft,
    valign = "top",
    part = "all"
  )
  
  ft <- padding(
    ft,
    padding.top = 2,
    padding.bottom = 2,
    padding.left = 2,
    padding.right = 2,
    part = "header"
  )
  
  ft <- padding(
    ft,
    padding.top = 2,
    padding.bottom = 2,
    padding.left = 2,
    padding.right = 2,
    part = "body"
  )
  
  ft <- set_table_properties(
    ft,
    layout = "fixed",
    opts_word = list(
      split = TRUE,
      repeat_headers = FALSE
    )
  )
  
  ft
}

# ------------------------------------------------------------
# 3. Create Table A2: Candidate-fact overview table
# ------------------------------------------------------------

candidate_overview_table <- data.frame(
  Left = c(
    no_break_text(candidates[[1]]),
    "",
    no_break_text(candidates[[3]]),
    ""
  ),
  Right = c(
    no_break_text(candidates[[2]]),
    "",
    no_break_text(candidates[[4]]),
    ""
  ),
  check.names = FALSE,
  stringsAsFactors = FALSE
)

candidate_overview_ft <- flextable(candidate_overview_table)
candidate_overview_ft <- delete_part(
  candidate_overview_ft,
  part = "header"
)
candidate_overview_ft <- format_appendix_table(candidate_overview_ft)
candidate_overview_ft <- hline_top(
  candidate_overview_ft,
  border = fp_border(
    color = "black",
    style = "double",
    width = 1
  ),
  part = "body"
)
candidate_overview_ft <- bold(
  candidate_overview_ft,
  i = c(1, 3),
  part = "body"
)
candidate_overview_ft <- align(
  candidate_overview_ft,
  i = c(1, 3),
  align = "center",
  part = "body"
)
candidate_overview_ft <- align(
  candidate_overview_ft,
  i = c(2, 4),
  align = "left",
  part = "body"
)

candidate_overview_ft <- compose(
  candidate_overview_ft,
  i = 2,
  j = 1,
  value = fact_paragraph_for_candidate(
    materials,
    candidates[[1]]
  ),
  part = "body"
)

candidate_overview_ft <- compose(
  candidate_overview_ft,
  i = 2,
  j = 2,
  value = fact_paragraph_for_candidate(
    materials,
    candidates[[2]]
  ),
  part = "body"
)

candidate_overview_ft <- compose(
  candidate_overview_ft,
  i = 4,
  j = 1,
  value = fact_paragraph_for_candidate(
    materials,
    candidates[[3]]
  ),
  part = "body"
)

candidate_overview_ft <- compose(
  candidate_overview_ft,
  i = 4,
  j = 2,
  value = fact_paragraph_for_candidate(
    materials,
    candidates[[4]]
  ),
  part = "body"
)

candidate_overview_ft <- width(
  candidate_overview_ft,
  j = 1:2,
  width = 3.15
)

# ------------------------------------------------------------
# 4. Create Word document
# ------------------------------------------------------------

doc <- read_docx()

doc <- body_add_flextable(
  doc,
  value = candidate_overview_ft
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
  "\nAppendix A Word document exported to:\n",
  output_file,
  "\n",
  sep = ""
)
