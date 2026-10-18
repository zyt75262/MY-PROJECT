/* UI only. All meal planning, validation and persistence run in Python.
 * This file never asks an AI model to generate a meal or a medical claim.
 */
(() => {
  'use strict';
  const labels = {"手机操作": "Phone help", "视频通话": "Video calls", "办事步骤": "Everyday tasks", "其他问题": "Other questions", "花生": "Peanut", "坚果": "Tree nuts", "蛋": "Egg", "奶": "Milk", "鱼": "Fish", "大豆": "Soy", "麸质": "Gluten", "主食": "Staple", "蛋白": "Protein", "果蔬": "Fruit & vegetables", "早": "Breakfast", "午": "Lunch", "晚": "Dinner", "全部": "All", "菜品": "Dishes", "粥": "Porridges", "汤": "Soups", "饮品": "Drinks", "羹": "Thick soups & puddings", "干果": "Nuts", "糕点": "Cakes", "其它": "Other", "想尝试": "Would try", "已经做过": "Made it", "不合口味": "Not for me"};
  const label = value => labels[value] || value;
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const money = cents => (cents / 100).toFixed(cents % 100 ? 2 : 0);
  const time = value => new Date(value).toLocaleString('en-US', {month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
  const state = {view:'plan',day:0,query:'',category:'全部',catalog:'source',error:'',form:{budget:30,days:1,allergies:[],vegetarian:false,seed:1,available_ids:null}};
  let writes=0, polling=false;
  let data = {source_recipes:[],recipes:[],allergens:[],plan:null,favorites:[]};
  const paths = {
    leaf:'M18 3C7 2 2 6 4 13c2 7 12 7 14-10Z M4 20 15 8',
    grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    book:'M4 4h6c2 0 2 2 2 2s0-2 2-2h6v15h-6c-2 0-2 2-2 2s0-2-2-2H4z M12 6v15',
    heart:'M20.5 4.7a5 5 0 0 0-7 0L12 6.2l-1.5-1.5a5 5 0 0 0-7 7L12 20l8.5-8.3a5 5 0 0 0 0-7Z',
    help:'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M9.5 9a2.5 2.5 0 0 1 5 0c0 2-2.5 2-2.5 4 M12 16v.1',
    message:'M21 11a8 8 0 0 1-8 8H8l-5 3v-9a8 8 0 0 1 8-10h2a8 8 0 0 1 8 8Z M7 9h10 M7 13h7',
    home:'m3 10 9-7 9 7 M5 9v12h5v-7h4v7h5V9',
    check:'m5 12 4 4L19 6', arrow:'M4 12h15 m-5-5 5 5-5 5',
    swap:'M4 7h15m-4-4 4 4-4 4 M20 17H5m4-4-4 4 4 4',
    users:'M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z M2 21v-2a7 7 0 0 1 14 0v2 M17 4a4 4 0 0 1 0 7 M20 21v-2a7 7 0 0 0-3-6',
    mic:'M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0Z M5 10v2a7 7 0 0 0 14 0v-2 M12 19v3 M8 22h8',
    image:'M3 3h18v18H3z m0 13 5-5 4 4 3-3 6 6 M15 7h.1',
    bowl:'M3 11h18c0 6-4 9-9 9s-9-3-9-9Z M7 3v4 M12 2v5 M17 3v4',
    sun:'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Z M12 1v3 M12 20v3 M1 12h3 M20 12h3',
    download:'M12 3v12m-5-5 5 5 5-5 M4 16v5h16v-5', plus:'M12 4v16 M4 12h16'
  };
  const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.leaf}"/></svg>`;
  const foodNav = [['plan','grid','Meal planner'],['library','book','Recipe library'],['favorites','heart','Favorites']];
  const recipe = id => [...data.recipes,...data.source_recipes].find(item => item.id === id);
  const libraryItems = () => state.catalog==='source' ? data.source_recipes.filter(item=>item.edible) : data.recipes;

  async function api(path, payload) {
    const options = payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-Local-Request':'1'},body:JSON.stringify(payload)};
    let response;
    const controller = new AbortController(), timeout = setTimeout(()=>controller.abort(),12000);
    options.signal=controller.signal;
    try { response = await fetch(path, options); }
    catch (_) { throw new Error('Cannot connect to the Python server. Keep app.py running, then refresh this page.'); }
    finally { clearTimeout(timeout); }
    const result = await response.json();
    if (!response.ok) { const error=new Error(result.error || 'The action failed. Please try again.');error.status=response.status;throw error; }
    return result;
  }
  async function refresh() { data = await api('/api/state'); }
  function toast(message) { $('#toast').textContent = message; $('#toast').classList.add('show'); clearTimeout(toast.timer); toast.timer = setTimeout(() => $('#toast').classList.remove('show'), 4000); }
  function empty(title, text) { return `<div class="empty">${icon('leaf')}<h3>${title}</h3><p>${text}</p></div>`; }
  function dishArt(item) { return `<div class="dishart ${item.category === '蛋白' ? 'protein' : item.category === '果蔬' ? 'veg' : ''}">${icon(item.category === '主食' ? 'bowl' : item.category === '果蔬' ? 'leaf' : 'sun')}</div>`; }
  function navigate(view) { state.view=view;state.error='';render();window.scrollTo({top:0,behavior:'smooth'}); }
  function modal(title, html) { $('#modal').innerHTML = `<div class="modal-top"><h2>${esc(title)}</h2><button class="close" data-action="close" aria-label="Close">×</button></div><div class="modal-content">${html}</div>`; $('#modal').showModal(); }
  function closeModal() { $('#modal').close(); }

  function render() {
    document.body.className = '';
    $('#app').innerHTML = `<header class="topbar"><div class="brand"><div class="brandmark">${icon('leaf')}</div><span>BrightBite</span></div><span class="statuspill">Standalone app · Python</span></header><div class="shell"><aside class="sidebar"><div class="appbrand"><strong>BrightBite</strong><span>Thoughtful meals</span></div><nav class="nav" aria-label="Application navigation">${foodNav.map(([view,name,label])=>`<button data-action="nav" data-view="${view}" title="${label}" class="${state.view===view?'active':''}" ${state.view===view?'aria-current="page"':''}>${icon(name)}<span>${label}</span></button>`).join('')}</nav><div class="side-note">${data.source_recipes.filter(item=>item.edible).length} source recipes to browse and search.<p class="space">Records are stored in this application\'s own database.</p></div></aside><main class="main"><div class="breadcrumb"><span>BrightBite</span><span >Meal planning and nutrition support</span></div>${foodContent()}<p class="bottom-note">Meal planning uses demonstration recipes. Body-function notes are general nutrition information, not disease-specific meal plans.</p></main></div>`;
  }

  function foodContent() { return state.view === 'plan' ? planView() : libraryView(); }
  function planView() {
    const form = state.form;
    return `<section class="hero"><div><div class="eyebrow">A LITTLE CARE, EVERY MEAL</div><h1>Make balanced meals<br>part of every day.</h1><p>Set your dietary needs, preferences and budget.<br>Understand the ingredients behind each meal.</p><div class="hero-pills"><span class="tag">${icon('check')}Budget limits</span><span class="tag">${icon('leaf')}Dietary filters</span><span class="tag">${icon('swap')}Swap with confidence</span></div></div><div class="hero-art" aria-hidden="true"><svg viewBox="0 0 250 190"><ellipse cx="125" cy="104" rx="87" ry="63" fill="#cfdcbd"/><ellipse cx="125" cy="90" rx="87" ry="63" fill="#fafcf4"/><ellipse cx="125" cy="90" rx="67" ry="46" fill="#eff0e2"/><g fill="#86a168"><circle cx="87" cy="71" r="18"/><circle cx="105" cy="65" r="18"/><circle cx="94" cy="91" r="20"/></g><ellipse cx="151" cy="80" rx="27" ry="29" fill="#e3b280"/><path d="m140 66 22 17m-25-7 23 17" stroke="#c38e58" stroke-width="3" stroke-linecap="round"/><ellipse cx="127" cy="119" rx="32" ry="16" fill="#fffef9"/><path d="m220 30-8 125m16-125-8 125" stroke="#9e9978" stroke-width="4" stroke-linecap="round"/></svg></div></section><div class="columns"><section class="panel formpanel"><div class="panel-head"><h2>Plan your meals</h2>${icon('bowl')}</div><form id="planform"><label class="label" for="days">Number of days</label><select id="days" name="days" class="control">${[1,3,7].map(value => `<option value="${value}" ${form.days===value?'selected':''}>${value} ${value===1?'day':'days'} · three meals a day</option>`).join('')}</select><label class="label" for="preference">Dietary preference</label><select id="preference" name="preference" class="control"><option value="all">Mixed diet</option><option value="veg" ${form.vegetarian?'selected':''}>Plant-based ingredients</option></select><label class="label" for="budget">Daily budget per person</label><div class="budget"><span class="small muted">Demonstration prices, CNY</span><b id="budgetvalue">¥${form.budget}</b></div><input id="budget" name="budget" type="range" min="15" max="60" step="1" value="${form.budget}"><fieldset><legend>Allergies / exclusions</legend><div class="choices">${data.allergens.map(value => `<label class="checkchip"><input type="checkbox" name="allergy" value="${value}" ${form.allergies.includes(value)?'checked':''}>${esc(label(value))}</label>`).join('')}</div></fieldset><details><summary>Set available recipes</summary><p class="help">Uncheck unavailable recipes. Leave all selected to allow every recipe.</p><div class="supply">${data.recipes.map(item => `<label><input type="checkbox" name="available" value="${item.id}" ${form.available_ids===null||form.available_ids.includes(item.id)?'checked':''}>${esc(item.name)}</label>`).join('')}</div></details><p class="help">Favorites receive a preference bonus. Check actual ingredients and allergen information separately.</p><button type="submit" class="btn full">${icon('plus')}Generate meal plan</button></form></section><section><div class="result-head"><div><h2>${state.error?'No plan fits these conditions':data.plan?'Your meal plan is ready':'Start with your first meal plan'}</h2><p>Python uses your filters and budget. Plans are saved on the server computer.</p></div>${data.plan&&!state.error?`<a class="textbtn" href="/api/plans/${data.plan.id}/export">${icon('download')}Export</a>`:''}</div>${state.error?`<div class="error" role="alert">${esc(state.error)}</div>`:data.plan?mealView():empty('Choose your preferences first','Set a budget and dietary exclusions, then generate a plan.')}<div class="notice">Meals combine a staple, a protein dish and fruit or vegetables. Individual nutrient targets are not calculated. Preference scores are not health or eye-care scores.</div></section></div>`;
  }
  function healthBadges(item) {
    const profiles=item.health_support||[];
    return profiles.length?`<div class="health-tags" aria-label="Body-function tags">${profiles.slice(0,3).map(profile=>`<span class="health-tag">${esc(profile.part)}</span>`).join('')}</div>`:'';
  }
  function healthCards(profiles, includeDishes=false) {
    if(!profiles?.length)return '<p class="help">No reliable body-function notes have been added for these ingredients yet.</p>';
    return `<div class="health-grid">${profiles.map(profile=>`<article class="health-card"><span class="health-part">${esc(profile.part)}</span><h3>${esc(profile.function)}</h3><p><strong>Nutrient: </strong>${esc(profile.nutrients)}</p><p><strong>Ingredients: </strong>${esc(profile.matched_ingredients.join(', '))}</p>${includeDishes?`<p class="health-dishes">Included in: ${esc(profile.recipe_names.join(', '))}</p>`:''}<p>${esc(profile.explanation)}</p><details><summary>Related health context: ${esc(profile.concern)}</summary><p>${esc(profile.condition_note)}</p><div class="health-sources">${profile.sources.map(source=>`<a href="${esc(source.url)}" target="_blank" rel="noopener noreferrer">${esc(source.title)}</a>`).join('')}</div></details></article>`).join('')}</div>`;
  }
  function dailyHealth(day) {
    return `<section class="health-panel" aria-label="Meal-plan nutrition support"><h2>Which body functions does this plan support?</h2><p class="help">${esc(data.plan.health_notice||data.health_notice||'These notes describe general nutrition support, not a therapeutic diet or a promise of treatment.')}</p>${healthCards(day.health_support,true)}</section>`;
  }
  function recipeHealth(item) {
    return `<section class="health-panel"><h3>Body functions and nutrition support</h3><p class="help">Based on the listed ingredients. Nutrient amounts and suitability for a medical condition have not been assessed.</p>${healthCards(item.health_support)}</section>`;
  }
  function healthModal(id) { const item=recipe(id);modal(item.name+' · Nutrition support',recipeHealth(item)); }
  function mealView() {
    const plan = data.plan, day = plan.days[state.day] || plan.days[0];
    return `<p class="small muted">Current plan: daily budget CNY ${money(plan.options.budget_cents)}; exclusions: ${esc(plan.options.allergies.map(label).join(', ')||'None')}.</p><div class="days space">${plan.days.map((_,index) => `<button data-action="day" data-day="${index}" class="${state.day===index?'active':''}">Day ${index+1}</button>`).join('')}</div>${day.meals.map((meal,mi) => `<article class="meal"><header class="meal-top"><strong>${label(meal.slot)}</strong><span>Demo estimate CNY ${money(meal.cost_cents)}</span></header>${meal.ids.map((id,position) => {const item=recipe(id);return `<div class="dishrow">${dishArt(item)}<div class="dish-info"><button data-action="recipe" data-id="${id}">${esc(item.name)}</button><p>${label(item.category)} · ${esc(item.ingredients.slice(0,2).join(' / '))}</p>${healthBadges(item)}<button class="textbtn health-more" data-action="health" data-id="${id}">View nutrition notes</button></div><span class="dish-price">¥${money(item.cost_cents)}</span><button class="swap" data-action="swap" data-index="${state.day},${mi},${position}" aria-label="Swap ${esc(item.name)}">${icon('swap')}</button></div>`;}).join('')}</article>`).join('')}<div class="summary"><span>${icon('check')}Meets selected budget and recipe-tag constraints</span><span>Total<b>¥${money(day.cost_cents)}</b></span></div>${dailyHealth(day)}<div class="feedback"><span class="muted">How was this plan?</span>${['想尝试','已经做过','不合口味'].map(value => `<button data-action="feedback" data-value="${value}" class="${plan.feedback===value?'selected':''}">${esc(label(value))}</button>`).join('')}</div>`;
  }
  function libraryView() { const favorites=state.view==='favorites';return `<div class="result-head"><div><div class="eyebrow muted">${favorites?'SAVED WITH CARE':'A SMALL RECIPE COLLECTION'}</div><h1 style="font-size:32px;margin-top:8px">${favorites?'Keep your favorites here.':'Recipe library'}</h1><p>${libraryItems().length} ${state.catalog==='source'?'source recipes':'demonstration recipes'} · Select one for ingredients and preparation</p></div></div><div class="row space"><button class="btn secondary" data-action="catalog" data-value="source">112 source recipes</button><button class="btn secondary" data-action="catalog" data-value="demo">Planning demo recipes</button></div><p class="help">The source contains 113 numbered entries. The non-food entry, No. 113, is excluded. Duplicate titles are retained. Source recipes are not used in automatic meal planning.</p><div class="filterbar"><input id="recipesearch" class="control" type="search" aria-label="Search recipes or ingredients" value="${esc(state.query)}" placeholder="Search a recipe or ingredient..."><select id="recipefilter" class="control" aria-label="Filter by category">${['全部',...new Set(libraryItems().map(item=>item.category))].map(value=>`<option value="${esc(value)}" ${state.category===value?'selected':''}>${esc(label(value))}</option>`).join('')}</select></div><div id="recipegrid">${recipeGrid()}</div>`; }
  function recipeGrid() { const selected=libraryItems().filter(item=>(state.view!=='favorites'||data.favorites.includes(item.id))&&(state.category==='全部'||state.category===item.category)&&(!state.query||[item.name,...item.ingredients].join(' ').toLowerCase().includes(state.query.toLowerCase())));return selected.length?`<div class="grid3">${selected.map(item=>`<article class="recipe-card">${dishArt(item)}<h3>${esc(item.name)}</h3><p>${esc(item.ingredients.slice(0,3).join(' · '))}</p>${healthBadges(item)}<div class="row"><span class="tag">${label(item.category)}</span>${item.allergens.length?`<span class="tag warm">Contains ${item.allergens.map(label).join(', ')}</span>`:''}</div><div class="foot"><button class="textbtn" data-action="recipe" data-id="${item.id}">View recipe ${icon('arrow')}</button><button class="heart ${data.favorites.includes(item.id)?'saved':''}" data-action="favorite" data-id="${item.id}" aria-label="Save or unsave ${esc(item.name)}" aria-pressed="${data.favorites.includes(item.id)}">${data.favorites.includes(item.id)?'♥':'♡'}</button></div></article>`).join('')}</div>`:empty('No matching recipes','Try another search or browse the library to save favorites.'); }
  function recipeModal(id) { const item=recipe(id);if(item.source){modal(item.name,`<p class="tag">Source entry ${item.number} · ${esc(label(item.category))}</p><p><strong>Ingredients - English translation</strong><br>${esc(item.ingredients.join(', '))}</p>${recipeHealth(item)}<p><strong>Preparation - English translation</strong><br>${esc(item.steps).replace(/\n/g,'<br>')}</p><div class="notice">This translated source collection has not been nutritionally or clinically reviewed. Herbal ingredients, quantities and suitability need professional review. It is not evidence of a treatment for myopia.</div><details class="space"><summary>Entry and translation notes</summary><p>${esc(item.original).replace(/\n/g,'<br>')}</p></details><p class="help">Source: ${esc(data.catalog_info.source_file)}, entry ${item.number}. No verified per-serving prices, yields or nutrient values are provided.</p>`);return;}modal(item.name,`${dishArt(item)}<p><span class="tag">${label(item.category)}</span> <span class="tag warm">Demonstration recipe</span></p><p><strong>Ingredients</strong><br>${esc(item.ingredients.join(', '))}</p><p><strong>Preparation</strong><br>${esc(item.steps)}</p>${recipeHealth(item)}<p><strong>Tagged allergens</strong><br>${esc(item.allergens.map(label).join(', ')||'None of the supported allergens are tagged. Still check the actual recipe and preparation environment.')}</p><div class="notice">Demo estimate CNY ${money(item.cost_cents)} per serving. Quantities, nutrient values and suitability have not been professionally reviewed.</div>`); }

  function readPlanForm() { const form=$('#planform');if(!form)return;const fields=new FormData(form);state.form={budget:Number(fields.get('budget')),days:Number(fields.get('days')),allergies:fields.getAll('allergy'),vegetarian:fields.get('preference')==='veg',available_ids:fields.getAll('available'),seed:state.form.seed}; }

  document.addEventListener('click',async event=>{
    const button=event.target.closest('[data-action]');if(!button||button.disabled)return;
    const action=button.dataset.action;button.disabled=true;writes++;
    try {
      if(action==='catalog'){state.catalog=button.dataset.value;state.category='全部';render();}
      else if(action==='nav'){await refresh();navigate(button.dataset.view);}
      else if(action==='refresh'){await refresh();render();toast('Records refreshed');}
      else if(action==='day'){state.day=Number(button.dataset.day);render();}
      else if(action==='close')closeModal();
      else if(action==='recipe')recipeModal(button.dataset.id);
      else if(action==='health')healthModal(button.dataset.id);
      else if(action==='favorite'){const result=await api('/api/favorites/'+button.dataset.id,{saved:!data.favorites.includes(button.dataset.id)});data.favorites=result.favorites;render();}
      else if(action==='feedback'){data.plan=await api(`/api/plans/${data.plan.id}/feedback`,{feedback:button.dataset.value});render();toast('Feedback saved');}
      else if(action==='swap'){const [day,meal,position]=button.dataset.index.split(',').map(Number);const result=await api(`/api/plans/${data.plan.id}/replacements?day=${day}&meal=${meal}&position=${position}`);modal('Choose a replacement',`<p>The current budget and dietary exclusions remain in place.</p>${result.recipes.length?result.recipes.map(item=>`<button class="replace-option" data-action="replace" data-index="${day},${meal},${position}" data-id="${item.id}"><span>${esc(item.name)}</span><span>¥${money(item.cost_cents)}</span></button>`).join(''):'<p>No replacement currently meets all the constraints.</p>'}`);}
      else if(action==='replace'){const [day,meal,position]=button.dataset.index.split(',').map(Number);data.plan=await api(`/api/plans/${data.plan.id}/replace`,{day,meal,position,recipe_id:button.dataset.id});closeModal();render();toast('Recipe replaced. Budget and exclusions are preserved.');}
    } catch(error){toast(error.message);}finally{button.disabled=false;writes--;}
  });
  document.addEventListener('input',event=>{if(event.target.id==='budget')$('#budgetvalue').textContent='¥'+event.target.value;if(event.target.closest('#planform'))readPlanForm();if(event.target.id==='recipesearch'){state.query=event.target.value;$('#recipegrid').innerHTML=recipeGrid();}});
  document.addEventListener('change',event=>{if(event.target.id==='recipefilter'){state.category=event.target.value;$('#recipegrid').innerHTML=recipeGrid();}if(event.target.closest('#planform'))readPlanForm();});
  document.addEventListener('submit',async event=>{
    event.preventDefault();const form=event.target,fields=new FormData(form),button=form.querySelector('button[type=submit]');
    if(button?.disabled)return;if(button)button.disabled=true;writes++;
    try {
      if(form.id==='planform'){readPlanForm();state.form.seed=(state.form.seed+1)%100001;data.plan=await api('/api/plans',{...state.form,preferred_ids:data.favorites.filter(id=>data.recipes.some(item=>item.id===id))});state.day=0;state.error='';render();toast('Python generated and saved your plan');}
    } catch(error){if(form.id==='planform'){state.error=error.message;render();}else toast(error.message);}finally{if(button)button.disabled=false;writes--;}
  });
  refresh().then(()=>{if(data.plan){const options=data.plan.options;state.form={...options,budget:options.budget_cents/100};}render();}).catch(error=>{$('#app').innerHTML=`<div class="loading"><h1>Local server not connected</h1><p>${esc(error.message)}</p><p>In the project folder, run <code>python app.py</code>，then open the address shown in the startup window.</p></div>`;});
})();
