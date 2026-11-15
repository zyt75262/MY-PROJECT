import csv
import json
import re
from collections import Counter

from common import PROCESSED_DIR, load_config

cfg = load_config("serving_weights.json")
text_patterns = load_config("k1_text_patterns.json")
text_dir = PROCESSED_DIR / "kindergarten1_recipe_text"

text = ""
for path in sorted(text_dir.glob("*.txt")):
    text += path.read_text(encoding="utf-8") + "\n"

for old, new in cfg["text_replacements"]:
    text = text.replace(old, new)

pair_re = re.compile(cfg["brace_weight_pattern"])
bracket_re = re.compile(text_patterns["bracketed_content"])
weekday_re = re.compile(text_patterns["weekday_label"])

brace_weight = Counter()
brace_count = Counter()
for part in bracket_re.findall(text):
    if weekday_re.fullmatch(part.strip()):
        continue
    for name, grams in pair_re.findall(part):
        brace_weight[name] += float(grams)
        brace_count[name] += 1

print("weights read from braces:")
for name in sorted(brace_count):
    average = brace_weight[name] / brace_count[name]
    print(" ", name, "x%d" % brace_count[name], "avg %.1f" % average)

with open(PROCESSED_DIR / "k1_ingredient_counts.json", encoding="utf-8") as f:
    frequencies = json.load(f)

per_serving = cfg["per_serving_grams"]
targets = cfg["target_total_grams"]

rows = []
bad = 0
for name in cfg["ingredient_order"]:
    servings = frequencies.get(name, 0)
    total = round(per_serving.get(name, 0) * servings, 1)
    rows.append((name, servings, total))
    if abs(total - targets[name]) > 0.5:
        bad += 1
        print("mismatch", name, "got %.1f" % total,
              "expected %.1f" % targets[name])

grand_total = cfg["grand_total_grams"]
out_path = PROCESSED_DIR / "kindergarten1_ingredient_weights.csv"
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow([
        "ingredient", "servings", "total_grams", "intake_share_pct",
    ])
    for name, servings, total in rows:
        share = round(total / grand_total * 100, 3)
        writer.writerow([name, servings, total, share])

print("\nmismatches:", bad)
print("sum of weights:", round(sum(row[2] for row in rows), 1))
print("saved", out_path.name)
