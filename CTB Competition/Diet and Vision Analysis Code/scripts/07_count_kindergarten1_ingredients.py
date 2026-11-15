import json
import re

from common import PROCESSED_DIR, count_ingredients, load_config

lexicon = load_config("k1_lexicon.json")
text_patterns = load_config("k1_text_patterns.json")
text_dir = PROCESSED_DIR / "kindergarten1_recipe_text"

whole = ""
for path in sorted(text_dir.glob("*.txt")):
    whole += path.read_text(encoding="utf-8") + "\n"

bracket_re = re.compile(text_patterns["bracketed_content"])
weekday_re = re.compile(text_patterns["weekday_label"])

inside_pieces = []
for part in bracket_re.findall(whole):
    if weekday_re.fullmatch(part.strip()):
        continue
    inside_pieces.append(part)
inside = " ".join(inside_pieces)

outside = re.sub(text_patterns["bracket_block"], "", whole)

pools = {
    "whole": whole,
    "inside": inside,
    "outside": outside,
}
counts = count_ingredients(lexicon, pools)

out_path = PROCESSED_DIR / "k1_ingredient_counts.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(counts, f, indent=1)

for name in lexicon["ingredient_order"]:
    print(name, counts[name])
print("\ningredients:", len(counts), "| saved", out_path.name)
