const fs=require('fs'),vm=require('vm'),assert=require('assert');
const assertEnglish=html=>assert(!/[\u4e00-\u9fff]/.test(html.replace(/<[^>]*>/g,'')),'Untranslated visible interface text');
const project=require('path').resolve(__dirname,'..');
const source=JSON.parse(fs.readFileSync(project+'/data/recipes_source.json','utf8'));
const demo=JSON.parse(fs.readFileSync(project+'/data/recipes_demo.json','utf8'));
const {execFileSync}=require('child_process');
const python=process.env.PYTHON||(process.platform==='win32'?'python':'python3');
const fixture=JSON.parse(execFileSync(python,['-c',`
import json
from pathlib import Path
from community.planner import load_recipes, generate_plan
from community.health import ingredient_health, explain_plan, NOTICE
root=Path('.')
recipes=load_recipes(root/'data/recipes_demo.json')
source=json.loads((root/'data/recipes_source.json').read_text())
print(json.dumps({'recipes':[r.to_dict() for r in recipes],
 'source_recipes':[{**r,'health_support':ingredient_health(r['ingredients']) if r['edible'] else []} for r in source['recipes']],
 'catalog_info':source['info'],'plan':None,'favorites':[],'stories':[],'tickets':[],'allergens':['花生','蛋'],
 'health_notice':NOTICE,
 'test_plan':explain_plan({**generate_plan(recipes,{'budget':60,'preferred_ids':['milk','chicken']}),'id':'a'*32,'feedback':''},{r.id:r for r in recipes})},ensure_ascii=False))
`],{cwd:project,encoding:'utf8'}));
const elements=new Map();
const el=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',open:false,addEventListener(){},classList:{add(){},remove(){}},showModal(){this.open=true},close(){this.open=false}});return elements.get(id)};
let modalOpen=false, shared={tickets:[],stories:[]};
const document={hidden:false,activeElement:null,body:{},querySelector(s){if(s==='#loginform'||s==='#planform'||s==='#storyform')return null;return el(s)},querySelectorAll(){return []},addEventListener(){}};
const context={AbortController,console,document,location:{hash:''},window:{addEventListener(){},scrollTo(){}},navigator:{},setTimeout(){},clearTimeout(){},setInterval(){},fetch:async path=>({ok:true,json:async()=>path==='/api/shared'?shared:fixture}),FormData:class{},FileReader:class{},Blob:class{}};
context.globalThis=context;
vm.createContext(context);
let js=fs.readFileSync(project+'/web/app.js','utf8').replace(/\}\)\(\);\s*$/,'globalThis.testUI={state,getData:()=>data,setData:value=>{data=value},render,recipeModal};})();');
(async()=>{vm.runInContext(js,context);await new Promise(r=>setImmediate(r));const ui=context.testUI;
 for(const view of ['plan','library','favorites']){ui.state.view=view;ui.render();assert(el('#app').innerHTML.includes('BrightBite'));assert(!el('#app').innerHTML.includes('银龄桥'));assert(!el('#app').innerHTML.includes('data-action="app"'));assertEnglish(el('#app').innerHTML);assert(!el('#app').innerHTML.includes('undefined'));}
 ui.state.app='food';ui.state.view='library';ui.render();assert.equal((el('#app').innerHTML.match(/class="recipe-card"/g)||[]).length,112);assert(!el('#app').innerHTML.includes('菊花养眼法'));
 ui.recipeModal('source_001');assert(el('#modal').innerHTML.includes('Ingredients - English translation'));el('#modal').close();
 ui.setData({...fixture,plan:fixture.test_plan});ui.state.app='food';ui.state.view='plan';ui.render();
 assert(el('#app').innerHTML.includes('Which body functions does this plan support?'));
 assert(el('#app').innerHTML.includes('View nutrition notes'));
 assert(el('#app').innerHTML.includes('Myopia and visual nutrition'));
 assert(el('#app').innerHTML.includes('Bones and teeth'));
 assert(el('#app').innerHTML.includes('Related health context'));
 assert(!el('#app').innerHTML.includes('undefined'));
 for(const item of fixture.source_recipes.filter(r=>r.edible)){ui.recipeModal(item.id);assertEnglish(el('#modal').innerHTML);el('#modal').close();}
 ui.recipeModal('milk');assert(el('#modal').innerHTML.includes('NIH ODS'));
 assert(el('#modal').innerHTML.includes('Support bone and tooth structure'));el('#modal').close();
 console.log('PASS: page rendering, 112 source entries, selected-meal body labels, daily function summary, disease context, reference links, recipe modal, standalone navigation without a switcher. This is a stub-DOM test, not browser visual QA.');
})().catch(e=>{console.error(e);process.exit(1)});
