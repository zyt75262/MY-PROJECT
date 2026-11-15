import pandas as pd

from common import PROJECT_ROOT, PROCESSED_DIR, RAW_DIR, load_config

source_columns = load_config("vision_fields.json")["source_columns"]

workbooks = sorted((RAW_DIR / "kindergarten1_vision").rglob("*.xlsx"))
print("workbooks found:", len(workbooks))

frames = []
for path in workbooks:
    frame = pd.read_excel(path, header=1)
    frame["source_file"] = path.name
    frames.append(frame)

records = pd.concat(frames, ignore_index=True)
records = records.rename(
    columns={chinese: english for english, chinese in source_columns.items()}
)

records["exam_date"] = pd.to_datetime(records["exam_date"])
records["year"] = records["exam_date"].dt.year

keep = [
    "exam_date", "class", "gender", "source_file", "year",
    "right_sphere", "left_sphere", "right_vision", "left_vision",
    "clinical_impression",
]
records = records[keep]

print("\nrecords by year:")
print(records["year"].value_counts().sort_index())
print("\ntotal records:", len(records))

out_path = PROCESSED_DIR / "kindergarten1_vision_records.csv"
records.to_csv(out_path, index=False, encoding="utf-8-sig")
print("\nsaved", out_path.relative_to(PROJECT_ROOT))
