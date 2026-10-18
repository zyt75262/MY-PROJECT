# How meal planning works

Implementation: `community/planner.py`.

## Scope and inputs

The planner selects breakfast, lunch and dinner from known demonstration recipes under budget, allergen labels, plant-based preference and availability constraints. It rewards favorites and discourages repetition across days. It has no calorie, protein-gram or micronutrient targets because validated portions and nutrient data have not been supplied. The category “Protein” is a menu group, not a calculated intake.

Options include a daily per-person CNY `budget` (at most two decimal places), `days` (1, 3 or 7), `allergies`, `vegetarian`, `available_ids`, `preferred_ids` and a reproducible `seed`. Omitted or null availability permits every recipe; an empty list permits none. The UI sends favorite IDs as preferences. Internal category and allergen codes are retained from the earlier edition for compatibility; the UI translates their labels.

## Hard filtering

`normalize_options()` validates types and ranges. `eligible()` excludes recipes with selected allergen labels, recipes incompatible with a plant-based preference and unavailable recipes. Scoring never relaxes these conditions. Actual ingredients, prepared seasonings and cross-contact require separate verification beyond the existing labels.

## Nine selection groups

Each of three meals has one staple, one protein dish and one fruit/vegetable dish. Each group selects exactly one eligible recipe. Binary choice variables satisfy one choice per group and a total daily cost no greater than the budget. The objective maximizes the sum of demonstration preference scores. Missing candidate groups or an unaffordable minimum cost produce an explicit error.

## Daily dynamic programming

`solve_day()` stores the best score and chosen IDs for each reachable exact cost after processing a group. It starts at cost zero, tries every candidate in the next group, discards over-budget states and retains the highest score at each cost. The final solution maximizes score; equal scores prefer lower cost, with stable ID ordering as a further tie breaker.

Costs use integer hundredths of CNY to avoid floating-point budget errors. Merging by cost is valid because future daily scores depend only on the group, recipe and frozen history from preceding days. A future rule prohibiting all same-day repeats would require additional state or a different solver.

## Scores and multiple days

```text
100 + favorite bonus (30 or 0) + reproducible tie variation (0 through 9)
    - appearances on previous days * 20
```

This is a demonstration preference, not a nutrition or eye-health score. SHA-256 and the seed determine the stable variation; this is not machine learning. History is frozen while solving each day, then updated for the next day.

Each day's solution is exact for that day's fixed scores. The multi-day sequence is a heuristic, not a globally optimal weekly solution. Repetition is penalized but is not forbidden. Manual replacement still enforces budget and exclusions but does not preserve an optimality claim.

For nine groups K, budget B measured in hundredths of CNY and at most R candidates per group, the daily upper time bound is O(K * B * R). The implementation stores only reachable cost states.

## Validation and future work

Tests cover constraint combinations and compare a small independent brute-force optimum with the dynamic program. After obtaining reviewed portions, prices and nutrient data, future work could add evidence-based nutrient bounds and integer programming. The current implementation does not implement or validate those nutrition outcomes.
