"""English nutrition explanations with legacy Chinese ingredient compatibility.

No clinical scores, nutrient amounts or disease-meal suitability are inferred.
"""
from __future__ import annotations
from copy import deepcopy
import re
REVIEWED_ON = '2026-10-18'
NOTICE = 'These notes describe general nutrition roles of listed ingredients. Nutrient quantities and disease-specific suitability have not been assessed.'
SOURCES = {'vitamin_a': {'title': 'MedlinePlus · Vitamin A', 'url': 'https://medlineplus.gov/ency/article/002400.htm'}, 'myopia': {'title': 'NEI · Nearsightedness (Myopia)', 'url': 'https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases/nearsightedness-myopia'}, 'calcium': {'title': 'NIH ODS · Calcium', 'url': 'https://ods.od.nih.gov/factsheets/Calcium-Consumer/'}, 'fiber': {'title': 'MedlinePlus · Dietary Fiber', 'url': 'https://medlineplus.gov/dietaryfiber.html'}, 'protein': {'title': 'MedlinePlus · Protein in diet', 'url': 'https://medlineplus.gov/ency/article/002467.htm'}, 'iron': {'title': 'NIH ODS · Iron', 'url': 'https://ods.od.nih.gov/factsheets/Iron-Consumer/'}, 'diabetes': {'title': 'CDC · Fiber and diabetes', 'url': 'https://www.cdc.gov/diabetes/healthy-eating/fiber-helps-diabetes.html'}}
RULES = ({'id': 'vision', 'part': 'Eyes', 'function': 'Maintain normal visual function', 'nutrients': 'Provitamin A carotenoids', 'ingredients': ('胡萝卜', '红薯', '南瓜', '菠菜', '西兰花', '小白菜', '青菜'), 'explanation': 'Some carotenoids in these vegetables can be converted to vitamin A, supporting normal vision and eye tissues.', 'concern': 'Myopia and visual nutrition', 'condition_note': 'Nutrition support does not reduce a prescription or replace eye exams, optical correction or professional myopia care.', 'sources': ('vitamin_a', 'myopia')}, {'id': 'bones', 'part': 'Bones and teeth', 'function': 'Support bone and tooth structure', 'nutrients': 'Calcium', 'ingredients': ('牛奶', '酸奶', '奶酪'), 'explanation': 'Dairy foods can provide calcium, which supports bones, teeth and normal muscle and nerve function.', 'concern': 'Bone health and osteoporosis', 'condition_note': 'Dietary calcium is one part of bone health. This does not establish that the meal meets calcium needs or replaces osteoporosis treatment.', 'sources': ('calcium',)}, {'id': 'gut', 'part': 'Digestive system', 'function': 'Support digestion and regular bowel movements', 'nutrients': 'Dietary fiber', 'ingredients': ('燕麦', '全麦', '糙米', '扁豆', '红薯', '苹果', '橙', '香蕉', '菠菜', '西兰花', '小白菜', '胡萝卜', '南瓜', '木耳', '黄瓜'), 'explanation': 'Whole grains, legumes, vegetables and whole fruit provide fiber that supports digestion and regular bowel movements.', 'concern': 'Constipation and dietary choices', 'condition_note': 'Increase fiber gradually and drink appropriate fluids. A recipe cannot establish the cause or treatment of constipation. Follow clinical advice if you need a low-fiber diet.', 'sources': ('fiber',)}, {'id': 'muscles', 'part': 'Muscles and body tissues', 'function': 'Support growth and tissue repair', 'nutrients': 'Protein', 'ingredients': ('鸡蛋', '牛奶', '酸奶', '奶酪', '黄豆', '豆浆', '豆腐', '鸡肉', '猪肉', '牛肉', '鱼肉', '鱼片', '扁豆', '花生', '核桃', '猪肝', '羊肝', '鸡肝', '鸭肝'), 'explanation': 'These ingredients can provide protein, which the body uses to make and repair cells and support growth.', 'concern': 'Growth and everyday recovery', 'condition_note': 'Needs vary with age, activity and health. People who need protein restrictions should not increase intake based on this tag.', 'sources': ('protein',)}, {'id': 'blood', 'part': 'Blood', 'function': 'Support normal blood formation and oxygen transport', 'nutrients': 'Iron', 'ingredients': ('牛肉', '猪肝', '羊肝', '鸡肝', '鸭肝', '扁豆'), 'explanation': 'These ingredients can provide iron, which is used to form hemoglobin and help red blood cells carry oxygen.', 'concern': 'Iron-deficiency anemia', 'condition_note': 'Iron-containing foods can support an eating plan, but anemia needs assessment of its cause. A meal does not replace testing, prescribed iron or other treatment.', 'sources': ('iron',)}, {'id': 'metabolic', 'part': 'Metabolic function', 'function': 'Provide fiber relevant to blood-sugar management', 'nutrients': 'Fiber from whole grains and legumes', 'ingredients': ('燕麦', '全麦', '糙米', '扁豆'), 'explanation': 'Whole grains and legumes are ways to add fiber, one factor considered in diabetes nutrition management.', 'concern': 'Diabetes and blood-sugar management', 'condition_note': 'Portions, total carbohydrate and the overall eating plan still need assessment. This app does not perform those checks and does not label this meal as a diabetes-specific diet.', 'sources': ('diabetes',)})
ALIASES = {'胡萝卜': ('carrot', 'carrots'), '红薯': ('sweet potato', 'sweet potatoes'), '南瓜': ('pumpkin',), '菠菜': ('spinach',), '西兰花': ('broccoli',), '小白菜': ('bok choy',), '青菜': ('leafy greens', 'choy sum'), '牛奶': ('milk',), '酸奶': ('yogurt',), '奶酪': ('cheese',), '燕麦': ('oats', 'oat', 'oatmeal'), '全麦': ('whole-wheat', 'whole wheat'), '糙米': ('brown rice',), '扁豆': ('lentils', 'lentil', 'flat beans'), '苹果': ('apple', 'apples'), '橙': ('orange', 'oranges'), '香蕉': ('banana', 'bananas'), '木耳': ('wood ear',), '黄瓜': ('cucumber',), '鸡蛋': ('egg', 'eggs'), '黄豆': ('soybeans', 'soybean'), '豆浆': ('soy milk',), '豆腐': ('tofu',), '鸡肉': ('chicken',), '猪肉': ('pork',), '牛肉': ('beef',), '鱼肉': ('fish',), '鱼片': ('fish fillets', 'fish slices'), '花生': ('peanut', 'peanuts'), '核桃': ('walnut', 'walnuts'), '猪肝': ('pork liver',), '羊肝': ('lamb liver',), '鸡肝': ('chicken liver',), '鸭肝': ('duck liver',)}
INGREDIENT_LABELS = {'胡萝卜': 'carrot', '红薯': 'sweet potato', '南瓜': 'pumpkin', '菠菜': 'spinach', '西兰花': 'broccoli', '小白菜': 'bok choy', '青菜': 'leafy greens', '牛奶': 'milk', '酸奶': 'yogurt', '奶酪': 'cheese', '燕麦': 'oats', '全麦': 'whole wheat', '糙米': 'brown rice', '扁豆': 'lentils / flat beans', '苹果': 'apple', '橙': 'orange', '香蕉': 'banana', '木耳': 'wood ear mushrooms', '黄瓜': 'cucumber', '鸡蛋': 'egg', '黄豆': 'soybeans', '豆浆': 'soy milk', '豆腐': 'tofu', '鸡肉': 'chicken', '猪肉': 'pork', '牛肉': 'beef', '鱼肉': 'fish', '鱼片': 'fish slices', '花生': 'peanuts', '核桃': 'walnuts', '猪肝': 'pork liver', '羊肝': 'lamb liver', '鸡肝': 'chicken liver', '鸭肝': 'duck liver'}

def _matches(name, value):
    if name in value:
        return True
    value=value.lower()
    if name == '牛奶':
        value=re.sub(r'\b(?:soy|oat|almond|coconut|plant)[ -]milk\b','',value)
    return any(re.search(r'(?<![a-z])'+re.escape(alias)+r'(?![a-z])',value) for alias in ALIASES.get(name,()))

def ingredient_health(ingredients):
    if not isinstance(ingredients,(list,tuple)):return []
    values=[v for v in ingredients if isinstance(v,str)]
    result=[]
    for rule in RULES:
        matched=[name for name in rule['ingredients'] if any(_matches(name,value) for value in values)]
        if not matched:continue
        if rule['id']=='bones' and any(('或' in v or re.search(r'\bor\b',v.lower())) for v in values if any(_matches(name,v) for name in matched)):
            continue
        item={k:v for k,v in rule.items() if k not in ('ingredients','sources')}
        item['matched_ingredients']=[INGREDIENT_LABELS[name] for name in matched]
        item['sources']=[dict(SOURCES[key]) for key in rule['sources']]
        result.append(item)
    return result

def day_health(day: dict, by_id: dict) -> list[dict]:
    groups = {}
    for meal in day.get('meals', []):
        for identifier in meal.get('ids', []):
            recipe = by_id.get(identifier)
            if recipe is None:
                continue
            for profile in ingredient_health(recipe.ingredients):
                key = profile['id']
                if key not in groups:
                    groups[key] = {**profile, 'recipe_names': []}
                target = groups[key]
                if recipe.name not in target['recipe_names']:
                    target['recipe_names'].append(recipe.name)
                target['matched_ingredients'] = list(dict.fromkeys(target['matched_ingredients'] + profile['matched_ingredients']))
    return [groups[rule['id']] for rule in RULES if rule['id'] in groups]


def explain_plan(plan: dict | None, by_id: dict) -> dict | None:
    """Compute from current recipe IDs, including old saved plans and replacements."""
    if plan is None:
        return None
    result = deepcopy(plan)
    result['health_notice'] = NOTICE
    for day in result.get('days', []):
        day['health_support'] = day_health(day, by_id)
    return result
