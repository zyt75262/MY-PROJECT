# CTB Diet and Vision Analysis

Code for a China Thinks Big (CTB) research project. The study compares the
weekly menus of two kindergartens against the vision screening results of
their children, to see how dietary patterns relate to early myopia.

The pipeline works with two kindergartens, referred to as K1 and K2:

- K1: vision screenings of 442 children across 6 classes and 3 school years,
  plus 92 days of portion-weighted menus
- K2: 345 days of menus recorded in a single workbook

## What each script does

| Script | Step |
|---|---|
| 01 | loads and combines the K1 vision screening workbooks |
| 02 | parses sphere and naked-eye vision, flags myopic children |
| 03 | extracts the valid meal days from the K2 recipe workbook |
| 04 | converts the K1 legacy `.doc` menus to plain text |
| 05 | counts meal days inside the K1 menu text |
| 06 | counts ingredient occurrences in the K2 menus |
| 07 | counts ingredient occurrences in the K1 menus |
| 08 | builds the combined count and frequency table |
| 09 | estimates total ingredient grams for K1 |
| 10 | groups ingredients into nine nutrition categories |
| 11 | checks every count against the published report figures |

## Layout

```
config/     source column names, keyword lexicons, serving weights, report targets
scripts/    numbered pipeline scripts
data/raw/   source files (not committed)
data/processed/  outputs written by the scripts (not committed)
```

The source spreadsheets use Chinese column names and Chinese ingredient
words. Those literals live in the JSON files under `config/`, so the Python
scripts themselves stay in English.

## Running

Install the dependencies:

```
python -m pip install -r requirements.txt
```

Place the source files as follows:

```
data/raw/kindergarten1_vision/        recursive .xlsx screening files
data/raw/kindergarten1_recipes/       .doc portion-weighted menus
data/raw/kindergarten2_recipe.xlsx
```

Then run the whole pipeline:

```
python run_pipeline.py
```

Scripts can also be run one at a time, in numeric order.

## Notes

- Script 04 automates Microsoft Word through `pywin32`, so it only runs on
  Windows with Word installed. The remaining scripts are plain Python.
- Two children in script 02 have a zero sphere but were marked as having
  poor vision by the clinician. They were reviewed by hand and are listed by
  row number in `config/vision_fields.json`.
- Script 11 must report zero mismatches. It compares the generated counts
  with the figures used in the final report.
