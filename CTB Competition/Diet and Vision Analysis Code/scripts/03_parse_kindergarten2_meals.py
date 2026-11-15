import csv
import datetime
import re

import openpyxl

from common import PROCESSED_DIR, RAW_DIR, load_config

layout = load_config("k2_recipe_layout.json")
date_re = re.compile(layout["date_pattern"])
date_column = layout["date_column"]
meal_columns = layout["meal_columns"]


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.year, value.month, value.day
    match = date_re.search(str(value))
    if match:
        return tuple(int(group) for group in match.groups())
    return None


workbook = openpyxl.load_workbook(
    RAW_DIR / "kindergarten2_recipe.xlsx",
    read_only=True,
    data_only=True,
)
sheet = workbook.active

days = []
for row_index, row in enumerate(
    sheet.iter_rows(min_row=1, values_only=True), start=1
):
    parsed = parse_date(row[date_column])
    if parsed is None:
        continue
    days.append({
        "physical_row": row_index,
        "year": parsed[0],
        "month": parsed[1],
        "day": parsed[2],
        "morning_snack": row[meal_columns["morning_snack"]],
        "lunch": row[meal_columns["lunch"]],
        "allergy_meal": row[meal_columns["allergy_meal"]],
        "afternoon_snack": row[meal_columns["afternoon_snack"]],
        "fruit_check": row[meal_columns["fruit"]],
    })
workbook.close()

print("valid meal days:", len(days))

year_counts = {}
for item in days:
    year_counts[item["year"]] = year_counts.get(item["year"], 0) + 1
print("days by year:", dict(sorted(year_counts.items())))

unique_dates = {(item["year"], item["month"], item["day"]) for item in days}
print("unique dates:", len(unique_dates))

out_path = PROCESSED_DIR / "kindergarten2_meal_days.csv"
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(days[0].keys()))
    writer.writeheader()
    writer.writerows(days)
print("saved", out_path.name)
