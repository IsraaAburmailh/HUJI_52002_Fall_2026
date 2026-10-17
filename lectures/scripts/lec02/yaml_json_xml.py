"""Lecture 2 benchmark: covid.csv -> covid_python.yml, covid_python.json, covid_python.xml, then read them back and query them.

It uses only the first N = 25,000 rows of covid.csv, because YAML and XML are slow on the whole file.

Run it in the folder that holds covid.csv:
    python3 ~/workspace/HUJI_52002_Fall_2026/lectures/scripts/lec02/yaml_json_xml.py
Needs pandas and PyYAML (pip install pandas pyyaml). The json library is part of Python.
"""
import json, os, platform, time
import xml.etree.ElementTree as ET
import pandas as pd
import yaml

N = 25_000   # use only the first N rows of covid.csv
REPS = 100   # a single query takes only milliseconds, so each query is run 100 times and the total is timed
times = {}   # (step, format) -> seconds

def timed(step, fmt, f):
    """Run f(), remember how long it took, and return its result."""
    start = time.perf_counter()
    out = f()
    times[(step, fmt)] = time.perf_counter() - start
    print(f"{step:6s} {fmt:5s} {times[(step, fmt)]:8.2f} s", flush=True)
    return out

# ---- 0. read the first N rows of the CSV into a pandas DataFrame
# (fips is read as text, so that codes with a leading zero, like Alaska's 02020, keep it)
df = timed("read", "csv", lambda: pd.read_csv("covid.csv", nrows=N, dtype={"fips": str}))

# ---- 1. write: from the DataFrame to a file
# JSON and YAML libraries want a list of dicts (one dict per row), so those two start with df.to_dict("records")
def write_json():
    with open("covid_python.json", "w") as f:
        json.dump(df.to_dict("records"), f)

def write_yaml():
    with open("covid_python.yml", "w") as f:
        yaml.dump(df.to_dict("records"), f, Dumper=yaml.CSafeDumper)  # PyYAML's fast C version of the safe dumper

def write_xml():
    df.to_xml("covid_python.xml", parser="etree", index=False, root_name="rows", row_name="row")  # etree: no extra package needed

timed("write", "yaml", write_yaml)
timed("write", "json", write_json)
timed("write", "xml", write_xml)

# ---- 2. read: from the file back into memory
def read_json():
    with open("covid_python.json") as f:
        return json.load(f)

def read_yaml():
    with open("covid_python.yml") as f:
        return yaml.load(f, Loader=yaml.CSafeLoader)  # like yaml.safe_load, but the fast C version

def read_xml():
    return ET.parse("covid_python.xml").getroot()

data = {
    "yaml": timed("read", "yaml", read_yaml),
    "json": timed("read", "json", read_json),
    "xml": timed("read", "xml", read_xml),
}

# ---- 3. query: the total of the cases column over the Texas rows, from the data in memory, run REPS times
def repeat(f):
    for _ in range(REPS):
        answer = f()
    return answer

def query_list(d):
    return sum(r["cases"] for r in d if r["state"] == "Texas")

def query_xml(d):
    return sum(int(r.find("cases").text) for r in d if r.find("state").text == "Texas")

answers = {
    "csv": timed("query", "csv", lambda: repeat(lambda: int(df.loc[df["state"] == "Texas", "cases"].sum()))),
    "yaml": timed("query", "yaml", lambda: repeat(lambda: query_list(data["yaml"]))),
    "json": timed("query", "json", lambda: repeat(lambda: query_list(data["json"]))),
    "xml": timed("query", "xml", lambda: repeat(lambda: query_xml(data["xml"]))),
}

# ---- summary
print(f"\nPython {platform.python_version()} | pandas {pd.__version__} | first {len(df):,} rows of covid.csv | file sizes:",
      ", ".join(f"{n} {os.path.getsize(n) / 1e6:.0f} MB" for n in ["covid_python.yml", "covid_python.json", "covid_python.xml"]))
print("All four queries agree:", len(set(answers.values())) == 1, "| answer:", answers["csv"])
print(f"\nformat   write    read   query (x{REPS})")
for fmt in ["csv", "yaml", "json", "xml"]:
    cells = [times.get((s, fmt)) for s in ["write", "read", "query"]]
    print(f"{fmt:6s}", *(f"{c:7.2f}" if c is not None else "      -" for c in cells))
