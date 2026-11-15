import re

from common import PROCESSED_DIR, load_config

pattern = re.compile(
    load_config("analysis_settings.json")["k1_day_header_pattern"]
)
text_dir = PROCESSED_DIR / "kindergarten1_recipe_text"

total = 0
for path in sorted(text_dir.glob("*.txt")):
    titles = pattern.findall(path.read_text(encoding="utf-8"))
    total += len(titles)
    print(path.name, len(titles))

print("\ntotal meal days:", total)
