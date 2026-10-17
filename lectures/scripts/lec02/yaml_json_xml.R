# Lecture 2 benchmark: covid.csv -> covid_r.yml, covid_r.json, covid_r.xml, then read them back and query them.
#
# It uses only the first N = 25,000 rows of covid.csv, because YAML and XML are slow on the whole file.
#
# Run it in the folder that holds covid.csv:
#   Rscript ~/workspace/HUJI_52002_Fall_2026/lectures/scripts/lec02/yaml_json_xml.R
# Needs the packages data.table, jsonlite, yaml and xml2 (install.packages(c("data.table", "jsonlite", "yaml", "xml2"))).
library(data.table)
library(jsonlite)
library(yaml)
library(xml2)

N <- 25000    # use only the first N rows of covid.csv
REPS <- 100   # a single query takes only milliseconds, so each query is run 100 times and the total is timed
times <- list()  # "step format" -> seconds

timed <- function(step, fmt, expr) {
  seconds <- unname(system.time(out <- expr)[["elapsed"]])
  times[[paste(step, fmt)]] <<- seconds
  cat(sprintf("%-6s %-5s %8.2f s\n", step, fmt, seconds))
  out
}

# ---- 0. read the first N rows of the CSV into a data.table (a data frame with extras)
df <- timed("read", "csv", fread("covid.csv", nrows = N))

# ---- 1. write: from the data.table to a file
# YAML and XML want one record per row (a list of rows); the reshaping is part of the cost, so it is timed too.
as_rows <- function(df) unname(do.call(Map, c(f = list, df)))  # a list with one named list per row (unname: Map would name each row by its date)

invisible(timed("write", "yaml", write_yaml(as_rows(df), "covid_r.yml")))
invisible(timed("write", "json", write_json(df, "covid_r.json")))
invisible(timed("write", "xml", {
  rows <- lapply(as_rows(df), function(r) lapply(r, function(v) list(as.character(v))))
  names(rows) <- rep("row", length(rows))
  write_xml(as_xml_document(list(rows = rows)), "covid_r.xml")
}))

# ---- 2. read: from the file back into memory
y <- timed("read", "yaml", read_yaml("covid_r.yml"))
j <- timed("read", "json", fromJSON("covid_r.json"))
x <- timed("read", "xml", read_xml("covid_r.xml"))

# ---- 3. query: the total of the cases column over the Texas rows, from the data in memory, run REPS times
repeat_query <- function(f) { for (i in seq_len(REPS)) answer <- f(); answer }

answers <- c(
  csv  = timed("query", "csv",  repeat_query(function() df[state == "Texas", sum(cases)])),
  yaml = timed("query", "yaml", repeat_query(function() sum(vapply(y, function(r) if (identical(r$state, "Texas")) r$cases else 0, numeric(1))))),
  json = timed("query", "json", repeat_query(function() sum(j$cases[j$state == "Texas"]))),
  xml  = timed("query", "xml",  repeat_query(function() sum(as.numeric(xml_text(xml_find_all(x, "//row[state='Texas']/cases"))))))
)

# ---- summary
sizes <- sapply(c("covid_r.yml", "covid_r.json", "covid_r.xml"), function(n) round(file.size(n) / 1e6))
cat("\n", R.version.string, "| first", format(nrow(df), big.mark = ","), "rows of covid.csv | file sizes (MB):", paste(names(sizes), sizes, collapse = ", "), "\n")
cat("All four queries agree:", length(unique(answers)) == 1, "| answer:", answers[["csv"]], "\n")
cat("\nformat   write    read   query (x", REPS, ")\n", sep = "")
for (fmt in c("csv", "yaml", "json", "xml")) {
  cells <- sapply(c("write", "read", "query"), function(s) times[[paste(s, fmt)]])
  cat(sprintf("%-6s", fmt), vapply(cells, function(v) if (is.null(v)) "      -" else sprintf("%7.2f", v), ""), "\n")
}
