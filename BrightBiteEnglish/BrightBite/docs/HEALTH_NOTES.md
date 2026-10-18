# BrightBite - Body functions and health context

Every selected dish can display body-function tags. **View nutrition notes** explains the matched ingredients, nutrients, general physiological role and related health concerns. The daily summary, saved-plan reload, replacements and text export are recomputed from actual recipe IDs. Source recipes and demonstration recipes use the same rules. Traditional efficacy paragraphs are not treated as verified conclusions.

## Six supported areas

| Body area | Example ingredients | Nutrition role | Health context |
| --- | --- | --- | --- |
| Eyes | Carrot, sweet potato, spinach | Vitamin A precursors and normal vision | Visual nutrition in people with myopia; no reduction in prescription |
| Bones and teeth | Milk, yogurt, cheese | Calcium and structural maintenance | Bone health and osteoporosis |
| Digestive system | Whole grains, vegetables, whole fruit | Fiber, digestion and regularity | Constipation and dietary choices |
| Muscles and body tissues | Eggs, meat, soy foods | Protein, growth and repair | Growth and everyday recovery |
| Blood | Beef, liver, lentils | Iron, hemoglobin and oxygen transport | Iron-deficiency anemia |
| Metabolic function | Oats, whole wheat, brown rice, lentils | Fiber and blood-sugar management | Diabetes diets still need portion and carbohydrate assessment |

These qualitative notes do not establish that a serving meets nutrient requirements or that a plan is appropriate for a disease. Liver appears only where present in the source material; these notes do not add it to automatic planning or increase its score.

Unknown ingredients receive no invented tags. Soy milk is not automatically treated as a calcium-rich dairy food. An uncertain alternative such as “milk or soy milk” does not confirm a calcium source. The rules accept English ingredient names and legacy Chinese inputs, while displaying English explanations.

## Myopia

Vitamin A contributes to normal vision. Myopia is a refractive problem. A food's nutritional role does not establish that it can lower a prescription. The app links to eye-care information without presenting recipes as treatment.

## Evidence

The following sources were checked in development on 2026-10-18. Individual cards in the app link to their relevant sources.

- [MedlinePlus - Vitamin A](https://medlineplus.gov/ency/article/002400.htm): visual function and food sources.
- [NEI - Nearsightedness](https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases/nearsightedness-myopia): causes and management of myopia.
- [NIH ODS - Calcium](https://ods.od.nih.gov/factsheets/Calcium-Consumer/): calcium, food sources and bone health.
- [MedlinePlus - Dietary Fiber](https://medlineplus.gov/dietaryfiber.html): fiber, digestion and regularity.
- [MedlinePlus - Protein in diet](https://medlineplus.gov/ency/article/002467.htm): growth, repair and food sources.
- [NIH ODS - Iron](https://ods.od.nih.gov/factsheets/Iron-Consumer/): iron, hemoglobin and deficiency.
- [CDC - Fiber and diabetes](https://www.cdc.gov/diabetes/healthy-eating/fiber-helps-diabetes.html): fiber and blood-sugar management.

## Implementation

`community/health.py` contains ingredient rules and references. Explanations are generated from selected recipes rather than permanently stored inside old plans. This avoids stale notes after a swap. Rules do not create disease-treatment scores, change budget constraints or calculate personal nutrient targets, serving sizes or clinical suitability.
