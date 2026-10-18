"""BrightBite: meal planning with budget, category and dietary constraints.

The daily solver is a multiple-choice knapsack dynamic program. Scores are
transparent demonstration preferences, NOT nutrient or medical-effect scores.
Across days we discourage reuse with a sequential heuristic, not a globally
optimal weekly model. See docs/ALGORITHM.md for the derivation.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable, Sequence

from .health import ingredient_health

ALLERGENS = ("花生", "坚果", "蛋", "奶", "鱼", "大豆", "麸质")
CATEGORIES = ("主食", "蛋白", "果蔬")
MEALS = ("早", "午", "晚")


from .errors import ValidationError
from .locale import label


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    category: str
    cost_cents: int
    ingredients: tuple[str, ...]
    allergens: tuple[str, ...]
    vegetarian: bool
    meal_slots: tuple[str, ...]
    steps: str

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "category": self.category,
            "cost_cents": self.cost_cents, "ingredients": list(self.ingredients),
            "allergens": list(self.allergens), "vegetarian": self.vegetarian,
            "meal_slots": list(self.meal_slots), "steps": self.steps,
            "health_support": ingredient_health(self.ingredients),
        }


def load_recipes(path: Path) -> tuple[Recipe, ...]:
    """Reject malformed data rather than silently inventing missing values."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValidationError("Recipe schema_version must be 1.")
    recipes, seen = [], set()
    for item in payload.get("recipes", []):
        for key in ("id", "name", "category", "steps"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValidationError(f"Recipe field {key} is missing or invalid.")
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", item["id"]):
            raise ValidationError("Recipe IDs must start with a lowercase letter and contain only lowercase letters, numbers, underscores or hyphens.")
        if item["id"] in seen:
            raise ValidationError(f"Duplicate recipe ID: {item['id']}")
        seen.add(item["id"])
        if type(item.get("cost_cents")) is not int or item["cost_cents"] <= 0:
            raise ValidationError("cost_cents must be a positive integer in hundredths of CNY.")
        if type(item.get("vegetarian")) is not bool:
            raise ValidationError("vegetarian must be true or false.")
        for key in ("ingredients", "allergens", "meal_slots"):
            if not isinstance(item.get(key), list) or not all(
                isinstance(value, str) and value for value in item[key]
            ):
                raise ValidationError(f"{key} must be a list of strings.")
        if not item["ingredients"] or not item["meal_slots"]:
            raise ValidationError("Ingredients and meal slots must not be empty.")
        if item["category"] not in CATEGORIES:
            raise ValidationError("Unknown food category.")
        if set(item["allergens"]) - set(ALLERGENS):
            raise ValidationError("Unknown allergen tag.")
        if set(item["meal_slots"]) - set(MEALS):
            raise ValidationError("Unknown meal slot.")
        recipes.append(Recipe(
            id=item["id"], name=item["name"], category=item["category"],
            cost_cents=item["cost_cents"], ingredients=tuple(item["ingredients"]),
            allergens=tuple(item["allergens"]), vegetarian=item["vegetarian"],
            meal_slots=tuple(item["meal_slots"]), steps=item["steps"],
        ))
    if not recipes:
        raise ValidationError("No recipes are available.")
    return tuple(recipes)


def parse_budget(value: object) -> int:
    """Use integer cents so that floating-point errors cannot exceed a budget."""
    if isinstance(value, bool):
        raise ValidationError("Budget must be a monetary amount.")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValidationError("Budget must be a valid monetary amount.") from error
    if not amount.is_finite() or not Decimal("1") <= amount <= Decimal("200"):
        raise ValidationError("Demo budgets range from CNY 1 to 200 per person per day.")
    cents = amount * 100
    if cents != cents.to_integral_value():
        raise ValidationError("Budget can have at most two decimal places.")
    return int(cents)


def normalize_options(payload: dict, recipes: Sequence[Recipe]) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Planning options must be a JSON object.")
    days = payload.get("days", 1)
    if type(days) is not int or days not in (1, 3, 7):
        raise ValidationError("Days must be the integer 1, 3 or 7.")
    allergies = payload.get("allergies", [])
    if not isinstance(allergies, list) or not all(isinstance(x, str) for x in allergies):
        raise ValidationError("Dietary exclusions must be a list of tags.")
    if set(allergies) - set(ALLERGENS):
        raise ValidationError("An allergen is not supported by the current data labels.")
    vegetarian = payload.get("vegetarian", False)
    if type(vegetarian) is not bool:
        raise ValidationError("The plant-based preference must be true or false.")
    seed = payload.get("seed", 1)
    if type(seed) is not int or not 0 <= seed <= 100000:
        raise ValidationError("seed must be an integer from 0 to 100000.")
    ids = {r.id for r in recipes}
    result = {
        "budget_cents": parse_budget(payload.get("budget", 30)), "days": days,
        "allergies": sorted(set(allergies)), "vegetarian": vegetarian, "seed": seed,
    }
    for key in ("available_ids", "preferred_ids"):
        values = payload.get(key, None if key == "available_ids" else [])
        if key == "available_ids" and values is None:
            result[key] = None
            continue
        if not isinstance(values, list) or not all(isinstance(x, str) for x in values):
            raise ValidationError(f"{key} must be a list of recipe IDs.")
        if set(values) - ids:
            raise ValidationError("The options contain an unknown recipe ID.")
        result[key] = sorted(set(values))
    return result


def eligible(recipe: Recipe, options: dict) -> bool:
    """Hard constraints are applied BEFORE preference scoring."""
    available = options["available_ids"]
    return (
        not set(recipe.allergens).intersection(options["allergies"])
        and (not options["vegetarian"] or recipe.vegetarian)
        and (available is None or recipe.id in available)
    )


def solve_day(
    groups: Sequence[Sequence[Recipe]],
    budget_cents: int,
    score: Callable[[Recipe, int], int],
) -> tuple[int, int, tuple[str, ...]]:
    """Exact optimum for additive scores with one choice from each group.

    dp[cost] = (best score, selected recipe IDs) after the processed groups.
    Keeping one state per exact cost is valid because future scores depend
    only on the group and recipe, not on the day's previous selections.
    """
    if any(not group for group in groups):
        raise ValidationError("A required meal category has no available recipes under these conditions.")
    minimum = sum(min(r.cost_cents for r in group) for group in groups)
    if minimum > budget_cents:
        raise ValidationError(
            f"The minimum demo cost for three meals under these conditions is CNY {minimum / 100:.2f} which exceeds the budget. "
            "Increase the budget or add suitable recipes. Allergen exclusions remain in place."
        )
    states: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, ())}
    for index, group in enumerate(groups):
        next_states: dict[int, tuple[int, tuple[str, ...]]] = {}
        for previous_cost, (previous_score, chosen) in states.items():
            for recipe in group:
                cost = previous_cost + recipe.cost_cents
                if cost > budget_cents:
                    continue
                candidate = (previous_score + score(recipe, index), chosen + (recipe.id,))
                current = next_states.get(cost)
                if current is None or candidate[0] > current[0] or (
                    candidate[0] == current[0] and candidate[1] < current[1]
                ):
                    next_states[cost] = candidate
        states = next_states
    best_cost, (best_score, selected) = min(
        states.items(), key=lambda item: (-item[1][0], item[0], item[1][1])
    )
    return best_cost, best_score, selected


def generate_plan(recipes: Sequence[Recipe], payload: dict) -> dict:
    options = normalize_options(payload, recipes)
    candidates = [r for r in recipes if eligible(r, options)]
    groups = []
    for meal in MEALS:
        for category in CATEGORIES:
            group = [r for r in candidates if meal in r.meal_slots and r.category == category]
            if not group:
                raise ValidationError(
                    f"After filtering, no recipe is available for {label(meal)} / {label(category)}; add suitable recipes. "
                    "Allergen and dietary exclusions remain in place."
                )
            groups.append(group)
    by_id = {r.id: r for r in recipes}
    seen: Counter[str] = Counter()
    days = []
    for day_index in range(options["days"]):
        # History is frozen for a whole day: this keeps the daily DP exact.
        def score(recipe: Recipe, slot: int) -> int:
            key = f"{options['seed']}:{day_index}:{slot}:{recipe.id}".encode("utf-8")
            tie_breaker = int(hashlib.sha256(key).hexdigest()[:4], 16) % 10
            favorite_bonus = 30 if recipe.id in options["preferred_ids"] else 0
            return 100 + favorite_bonus + tie_breaker - 20 * seen[recipe.id]

        cost, points, selected = solve_day(groups, options["budget_cents"], score)
        meals = []
        for index, slot in enumerate(MEALS):
            ids = selected[index * 3:index * 3 + 3]
            meals.append({
                "slot": slot, "ids": list(ids),
                "cost_cents": sum(by_id[item].cost_cents for item in ids),
            })
        days.append({"cost_cents": cost, "preference_score": points, "meals": meals})
        seen.update(selected)
    return {
        "options": options, "days": days,
        "dataset": "synthetic_demo", "manually_modified": False,
        "algorithm": "daily_multiple_choice_knapsack_with_sequential_repeat_penalty",
    }


def replacement_candidates(recipes: Sequence[Recipe], plan: dict, day: int, meal: int, position: int) -> list[Recipe]:
    for value in (day, meal, position):
        if type(value) is not int or value < 0:
            raise ValidationError("Meal-plan positions must be non-negative integers.")
    try:
        selected_meal = plan["days"][day]["meals"][meal]
        old_id = selected_meal["ids"][position]
    except (IndexError, KeyError, TypeError) as error:
        raise ValidationError("Meal-plan position not found.") from error
    by_id = {r.id: r for r in recipes}
    old = by_id[old_id]
    return [r for r in recipes if (
        r.id != old.id and r.category == old.category
        and selected_meal["slot"] in r.meal_slots and eligible(r, plan["options"])
        and plan["days"][day]["cost_cents"] - old.cost_cents + r.cost_cents
        <= plan["options"]["budget_cents"]
    )]


def replace_recipe(recipes: Sequence[Recipe], plan: dict, day: int, meal: int, position: int, new_id: str) -> None:
    if not isinstance(new_id, str):
        raise ValidationError("The replacement recipe ID must be text.")
    candidates = replacement_candidates(recipes, plan, day, meal, position)
    if new_id not in {r.id for r in candidates}:
        raise ValidationError("This replacement does not satisfy the meal, category, dietary or budget constraints.")
    by_id = {r.id: r for r in recipes}
    target = plan["days"][day]["meals"][meal]
    difference = by_id[new_id].cost_cents - by_id[target["ids"][position]].cost_cents
    target["ids"][position] = new_id
    target["cost_cents"] += difference
    plan["days"][day]["cost_cents"] += difference
    # Manual replacement stays feasible, but is not claimed to remain optimal.
    plan["days"][day]["preference_score"] = None
    plan["manually_modified"] = True
