import json

from common import PROCESSED_DIR, load_config

reference = load_config("reference_counts.json")

with open(PROCESSED_DIR / "k1_ingredient_counts.json", encoding="utf-8") as f:
    k1_counts = json.load(f)
with open(PROCESSED_DIR / "k2_ingredient_counts.json", encoding="utf-8") as f:
    k2_counts = json.load(f)

bad = 0
for name in reference["k1"]:
    if k1_counts.get(name) != reference["k1"][name]:
        bad += 1
        print("k1 mismatch", name, k1_counts.get(name),
              "expected", reference["k1"][name])
    if k2_counts.get(name) != reference["k2"][name]:
        bad += 1
        print("k2 mismatch", name, k2_counts.get(name),
              "expected", reference["k2"][name])

print("verification done, mismatches:", bad)
