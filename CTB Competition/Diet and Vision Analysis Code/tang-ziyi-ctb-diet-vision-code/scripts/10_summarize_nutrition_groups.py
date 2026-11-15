import json

from common import PROCESSED_DIR, load_config

groups_cfg = load_config("nutrition_groups.json")
day_counts = load_config("analysis_settings.json")["meal_day_counts"]

with open(PROCESSED_DIR / "k1_ingredient_counts.json", encoding="utf-8") as f:
    k1_counts = json.load(f)
with open(PROCESSED_DIR / "k2_ingredient_counts.json", encoding="utf-8") as f:
    k2_counts = json.load(f)

data = {"k1": k1_counts, "k2": k2_counts}
result = {}

for group, items in groups_cfg["groups"].items():
    row = {}
    for site in ("k1", "k2"):
        count = sum(data[site].get(item, 0) for item in items)
        row[site] = [count, count / day_counts[site]]
    result[group] = row

for group in groups_cfg["groups"]:
    c1, r1 = result[group]["k1"]
    c2, r2 = result[group]["k2"]
    print(
        "%-18s k1 %4d  per-day %.4f | k2 %4d  per-day %.4f"
        % (group, c1, r1, c2, r2)
    )

out_path = PROCESSED_DIR / "nutrition_group_totals.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=1)

print("\nsaved", out_path.name)
