import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_config(name):
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def count_ingredients(lexicon, pools):
    counts = {}
    for name in lexicon["ingredient_order"]:
        spec = lexicon["ingredients"][name]
        if "fixed" in spec:
            counts[name] = spec["fixed"]
            continue
        total = sum(
            pools[rule["pool"]].count(rule["keyword"])
            for rule in spec["rules"]
        )
        counts[name] = total + spec.get("offset", 0)
    return counts
