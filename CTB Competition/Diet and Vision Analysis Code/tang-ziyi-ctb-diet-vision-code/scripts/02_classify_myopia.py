import re

import pandas as pd

from common import PROCESSED_DIR, load_config

cfg = load_config("vision_fields.json")
threshold = cfg["vision_threshold"]
manual_rows = cfg["manual_review_rows"]

records = pd.read_csv(PROCESSED_DIR / "kindergarten1_vision_records.csv")


def parse_sphere(value):
    if pd.isna(value):
        return None
    match = re.search(r"([+-]?\d+\.?\d*)D?", str(value).strip())
    if match:
        return float(match.group(1))
    return None


def parse_vision(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text in ("--", "", "/"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


records["right_sphere_d"] = records["right_sphere"].apply(parse_sphere)
records["left_sphere_d"] = records["left_sphere"].apply(parse_sphere)
records["right_vision_d"] = records["right_vision"].apply(parse_vision)
records["left_vision_d"] = records["left_vision"].apply(parse_vision)


def is_myopic(row):
    spheres = [
        v for v in (row["right_sphere_d"], row["left_sphere_d"])
        if pd.notna(v)
    ]
    visions = [
        v for v in (row["right_vision_d"], row["left_vision_d"])
        if pd.notna(v)
    ]
    if not spheres or min(spheres) >= 0:
        return False
    if len(visions) < 2:
        return True
    return min(visions) < threshold


records["rule_myopic"] = records.apply(is_myopic, axis=1)

rule_counts = records[records["rule_myopic"]].groupby("year").size()
print("rule hits by year:")
print(rule_counts)
print("rule total:", int(records["rule_myopic"].sum()))

# two zero-sphere cases flagged by the clinician as poor vision; reviewed by hand
print("\nmanual review rows:")
for i in manual_rows:
    row = records.loc[i]
    print(
        " ", i, "year", row["year"],
        "| sphere", row["right_sphere_d"], row["left_sphere_d"],
        "| vision", row["right_vision_d"], row["left_vision_d"],
        "|", row["clinical_impression"],
    )

records["myopic"] = records["rule_myopic"]
records.loc[manual_rows, "myopic"] = True

final_counts = records[records["myopic"]].groupby("year").size()
print("\nfinal myopic counts by year:")
print(final_counts)

total_n = len(records)
myopic_n = int(records["myopic"].sum())
print("\ntotal children:", total_n)
print("myopic children:", myopic_n)
print("myopia rate: %.2f%%" % (myopic_n / total_n * 100))

out_path = PROCESSED_DIR / "kindergarten1_myopia.csv"
records.to_csv(out_path, index=False, encoding="utf-8-sig")
print("\nsaved", out_path.name)
