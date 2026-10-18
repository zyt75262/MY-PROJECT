import copy
import itertools
import json
import tempfile
import unittest
from pathlib import Path

from community.planner import (
    CATEGORIES, MEALS, Recipe, ValidationError, eligible, generate_plan,
    load_recipes, normalize_options, parse_budget, replace_recipe,
    replacement_candidates, solve_day,
)

ROOT = Path(__file__).resolve().parents[1]


class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipes = load_recipes(ROOT / "data" / "recipes_demo.json")
        cls.by_id = {recipe.id: recipe for recipe in cls.recipes}

    def test_demo_dataset_is_labeled(self):
        raw = json.loads((ROOT / "data" / "recipes_demo.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["dataset_type"], "synthetic_demo")
        self.assertEqual(len(self.recipes), 29)

    def test_constraints_across_scenarios(self):
        for budget, days, vegetarian, allergies in itertools.product(
            (22, 30, 60), (1, 3, 7), (False, True),
            ([], ["蛋", "奶"], ["花生", "鱼", "麸质"]),
        ):
            with self.subTest(budget=budget, days=days, vegetarian=vegetarian, allergies=allergies):
                plan = generate_plan(self.recipes, dict(budget=budget, days=days, vegetarian=vegetarian, allergies=allergies))
                self.assertEqual(len(plan["days"]), days)
                for day in plan["days"]:
                    self.assertLessEqual(day["cost_cents"], budget * 100)
                    self.assertEqual(day["cost_cents"], sum(meal["cost_cents"] for meal in day["meals"]))
                    for slot, meal in zip(MEALS, day["meals"]):
                        self.assertEqual(slot, meal["slot"])
                        self.assertEqual(len(meal["ids"]), 3)
                        for category, identifier in zip(CATEGORIES, meal["ids"]):
                            recipe = self.by_id[identifier]
                            self.assertEqual(category, recipe.category)
                            self.assertIn(slot, recipe.meal_slots)
                            self.assertTrue(eligible(recipe, plan["options"]))

    def test_impossible_budget_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "exceeds the budget"):
            generate_plan(self.recipes, {"budget": 1})

    def test_allergy_filter_is_never_relaxed(self):
        with self.assertRaisesRegex(ValidationError, "Breakfast"):
            generate_plan(self.recipes, {"budget": 200, "allergies": ["蛋", "奶", "大豆"]})

    def test_availability_is_a_hard_constraint(self):
        allowed = ["millet", "soy", "apple", "rice", "tofu", "cabbage"]
        plan = generate_plan(self.recipes, {"available_ids": allowed, "budget": 30})
        for day in plan["days"]:
            for meal in day["meals"]:
                self.assertTrue(set(meal["ids"]).issubset(allowed))
        with self.assertRaises(ValidationError):
            generate_plan(self.recipes, {"available_ids": []})

    def test_money_and_types_are_validated(self):
        self.assertEqual(parse_budget("30.25"), 3025)
        for invalid in (True, None, "NaN", "Infinity", -10, 300, "30.001", "bad"):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                parse_budget(invalid)
        for invalid in ({"days": True}, {"days": 2}, {"allergies": ["unknown"]}, {"vegetarian": "false"}, {"available_ids": ["missing"]}):
            with self.subTest(invalid=invalid), self.assertRaises(ValidationError):
                normalize_options(invalid, self.recipes)

    def test_reproducible_result(self):
        self.assertEqual(generate_plan(self.recipes, {"seed": 19, "days": 3}),
                         generate_plan(self.recipes, {"seed": 19, "days": 3}))

    def test_manual_replacement_stays_feasible(self):
        plan = generate_plan(self.recipes, {"allergies": ["蛋", "花生"], "budget": 30})
        candidates = replacement_candidates(self.recipes, plan, 0, 0, 0)
        self.assertTrue(candidates)
        replace_recipe(self.recipes, plan, 0, 0, 0, candidates[0].id)
        self.assertTrue(plan["manually_modified"])
        self.assertIsNone(plan["days"][0]["preference_score"])
        self.assertLessEqual(plan["days"][0]["cost_cents"], 3000)
        before = copy.deepcopy(plan)
        with self.assertRaises(ValidationError):
            replace_recipe(self.recipes, plan, 0, 0, 0, "peanutchicken")
        self.assertEqual(plan, before)
        with self.assertRaises(ValidationError):
            replacement_candidates(self.recipes, plan, -1, 0, 0)

    def test_dynamic_program_matches_brute_force_oracle(self):
        def item(identifier, cost):
            return Recipe(identifier, identifier, "主食", cost, ("test",), (), True, ("早",), "test")
        groups = [[item("a", 120), item("b", 200)], [item("c", 90), item("d", 180)], [item("e", 110), item("f", 220)]]
        points = {"a": 3, "b": 9, "c": 2, "d": 6, "e": 4, "f": 8}
        for budget in (320, 400, 500, 600):
            valid = [combination for combination in itertools.product(*groups) if sum(r.cost_cents for r in combination) <= budget]
            expected = min(valid, key=lambda combination: (-sum(points[r.id] for r in combination), sum(r.cost_cents for r in combination), tuple(r.id for r in combination)))
            cost, score, chosen = solve_day(groups, budget, lambda r, index: points[r.id])
            self.assertEqual(chosen, tuple(r.id for r in expected))
            self.assertEqual(cost, sum(r.cost_cents for r in expected))
            self.assertEqual(score, sum(points[r.id] for r in expected))

    def test_invalid_recipe_data_is_rejected(self):
        content = json.loads((ROOT / "data" / "recipes_demo.json").read_text(encoding="utf-8"))
        content["recipes"][0]["cost_cents"] = 1.5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(content), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_recipes(path)


if __name__ == "__main__":
    unittest.main()
