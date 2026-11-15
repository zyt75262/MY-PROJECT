import csv
import json

from common import PROCESSED_DIR, load_config

day_counts = load_config("analysis_settings.json")["meal_day_counts"]
order = load_config("k2_lexicon.json")["ingredient_order"]

with open(PROCESSED_DIR / "k1_ingredient_counts.json", encoding="utf-8") as f:
    k1_counts = json.load(f)
with open(PROCESSED_DIR / "k2_ingredient_counts.json", encoding="utf-8") as f:
    k2_counts = json.load(f)

rows = []
for name in order:
    c1 = k1_counts[name]
    c2 = k2_counts[name]
    f1 = c1 / day_counts["k1"] * 100
    f2 = c2 / day_counts["k2"] * 100
    rows.append([name, c1, "%.2f%%" % f1, c2, "%.3f%%" % f2])

out_path = PROCESSED_DIR / "ingredient_frequency_table.csv"
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow([
        "ingredient", "k1_count", "k1_frequency",
        "k2_count", "k2_frequency",
    ])
    writer.writerows(rows)

for row in rows:
    print(row[0], row[1], row[2], row[3], row[4])
print("\nsaved", out_path.name)
