import copy
import unittest
from pathlib import Path

from community.health import ingredient_health, day_health, explain_plan
from community.planner import load_recipes

ROOT=Path(__file__).resolve().parents[1]

class HealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipes=load_recipes(ROOT/'data/recipes_demo.json')
        cls.by_id={r.id:r for r in cls.recipes}

    def test_ingredient_support_and_conservative_unknowns(self):
        profiles=ingredient_health(['胡萝卜','鸡肉'])
        self.assertTrue({'vision','muscles'}.issubset({p['id'] for p in profiles}))
        self.assertEqual(next(p for p in profiles if p['id']=='vision')['matched_ingredients'],['carrot'])
        self.assertEqual(ingredient_health(['何首乌','不明药材']),[])
        self.assertNotIn('bones',{p['id'] for p in ingredient_health(['黄豆','水'])})
        self.assertNotIn('bones',{p['id'] for p in ingredient_health(['牛奶或豆浆'])})
        self.assertIn('bones',{p['id'] for p in ingredient_health(['牛奶'])})

    def test_english_ingredients_match_without_assuming_fortification(self):
        profiles=ingredient_health(['Carrot','Chicken','Cow milk'])
        self.assertTrue({'vision','muscles','bones'}.issubset({p['id'] for p in profiles}))
        for ingredient in ['soy milk','almond milk','coconut milk','milk or soy milk']:
            self.assertNotIn('bones',{p['id'] for p in ingredient_health([ingredient])})
        self.assertEqual(ingredient_health(['unidentified herb']),[])

    def test_daily_summary_is_from_actual_selection_and_deduplicated(self):
        day={'meals':[{'ids':['chicken','carrot','carrot','milk']}]}
        profiles=day_health(day,self.by_id)
        vision=next(p for p in profiles if p['id']=='vision')
        self.assertEqual(vision['matched_ingredients'],['carrot'])
        self.assertEqual(vision['recipe_names'],['Carrot and Chicken Stir-Fry','Carrot and Wood Ear Stir-Fry'])
        self.assertIn('bones',{p['id'] for p in profiles})
        self.assertNotIn('metabolic',{p['id'] for p in profiles})

    def test_old_plans_are_enriched_without_mutation_and_replacements_refresh(self):
        plan={'days':[{'meals':[{'ids':['milk','rice','carrot']}]}]}
        old=copy.deepcopy(plan)
        enriched=explain_plan(plan,self.by_id)
        self.assertEqual(plan,old)
        self.assertIn('bones',{p['id'] for p in enriched['days'][0]['health_support']})
        plan['days'][0]['meals'][0]['ids'][0]='soy'
        changed=explain_plan(plan,self.by_id)
        self.assertNotIn('bones',{p['id'] for p in changed['days'][0]['health_support']})
        self.assertIsNone(explain_plan(None,self.by_id))

    def test_condition_notes_have_evidence_without_disease_cure_claims(self):
        profiles=ingredient_health(['胡萝卜','牛奶','燕麦','牛肉'])
        self.assertEqual(len(profiles),6)
        for p in profiles:
            self.assertTrue(p['condition_note'])
            self.assertTrue(all(s['url'].startswith('https://') for s in p['sources']))
            self.assertNotIn('score',p)
            self.assertNotIn('nutrient_amount',p)
        eye=next(p for p in profiles if p['id']=='vision')
        self.assertIn('does not reduce a prescription',eye['condition_note'])
        metabolic=next(p for p in profiles if p['id']=='metabolic')
        self.assertIn('does not label this meal as a diabetes-specific diet',metabolic['condition_note'])

if __name__=='__main__':unittest.main()
