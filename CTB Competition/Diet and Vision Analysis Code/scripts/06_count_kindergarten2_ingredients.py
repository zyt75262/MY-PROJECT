import datetime
import json
import re

import openpyxl

from common import (
    PROCESSED_DIR,
    RAW_DIR,
    count_ingredients,
    load_config,
)

layout = load_config("k2_recipe_layout.json")
lexicon = load_config("k2_lexicon.json")
date_re = re.compile(layout["date_pattern"])
noise = set(layout["allergy_meal_noise"])
columns = layout["meal_columns"]
date_column = layout["date_column"]


def get_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value
    match = date_re.search(str(value))
    if match:
        return datetime.datetime(*(int(group) for group in match.groups()))
    return None


workbook = openpyxl.load_workbook(
    RAW_DIR / "kindergarten2_recipe.xlsx",
    read_only=True,
    data_only=True,
)
sheet = workbook.active

a_pieces = []
d_pieces = []
day_count = 0

for row in sheet.iter_rows(min_row=1, values_only=True):
    if get_date(row[date_column]) is None:
        fruit_index = columns["fruit"]
        if len(row) > fruit_index and row[fruit_index] is not None:
            d_pieces.append(str(row[fruit_index]))
        continue

    day_count += 1
    a_indexes = [
        columns["morning_snack"],
        columns["lunch"],
        columns["afternoon_snack"],
    ]
    a_pieces.append(
        " ".join(
            str(row[c]) for c in a_indexes
            if c < len(row) and row[c] is not None
        )
    )

    one_day = []
    for c in (
        columns["morning_snack"],
        columns["lunch"],
        columns["allergy_meal"],
        columns["afternoon_snack"],
    ):
        if c < len(row) and row[c] is not None:
            text = str(row[c]).strip()
            if text in noise:
                continue
            one_day.append(text)
    d_pieces.append(" ".join(one_day))

    fruit_index = columns["fruit"]
    if len(row) > fruit_index and row[fruit_index] is not None:
        d_pieces.append(str(row[fruit_index]))

workbook.close()

pools = {
    "a": "\n".join(a_pieces),
    "d": "\n".join(d_pieces),
}
print("meal days:", day_count)

counts = count_ingredients(lexicon, pools)

out_path = PROCESSED_DIR / "k2_ingredient_counts.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(counts, f, indent=1)

for name in lexicon["ingredient_order"]:
    print(name, counts[name])
print("\ningredients:", len(counts), "| saved", out_path.name)
