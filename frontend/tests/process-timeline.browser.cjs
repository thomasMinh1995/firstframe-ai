// Exercises the real progress component without AI calls or project writes.
// First compile OperationProgress.tsx to CommonJS and pass that directory as argv[2].
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const compiled = path.resolve(process.argv[2]);
const webpack = require(path.join(root,'node_modules/next/dist/compiled/webpack/webpack'));
webpack.init();
const stages = {
 analyze:['prepare','reasoning_context','reasoning','reasoning_validation','saving'],
 plan:['prepare','plan_choices','planning_context','planning','planning_structure','plan_checkpoint','evaluation','plan_save'],
 review:['prepare','fidelity','fidelity_audit','evaluation','saving'],
 'scene-suggestions':['prepare','scene_source','scene_checkpoint','staging_generation','staging_validation','scene_proposal_save'],
 'scene-sketches':['prepare','sketch_checkpoint','sketch_generation','sketch_validation','sketch_save'],
 'screenplay-proposals':['prepare','screenplay_source','screenplay_checkpoint','screenplay_generation','screenplay_validation','screenplay_proposal_save'],
 'screenplay-reviews':['prepare','screenplay_review_source','screenplay_review_checkpoint','screenplay_review','screenplay_review_validation','screenplay_review_save'],
};
(async()=>{
 const temporary = await fs.mkdtemp(path.join(os.tmpdir(),'ff-process-browser-'));
 const entry=path.join(temporary,'entry.cjs');
 await fs.writeFile(entry,`const React=require('react');const {createRoot}=require('react-dom/client');const {flushSync}=require('react-dom');const {OperationProgress}=require(${JSON.stringify(path.join(compiled,'OperationProgress.js'))});const root=createRoot(document.getElementById('root'));window.renderProgress=props=>{const stage=props.timing.kind==='analyze'?'choices':['plan','review'].includes(props.timing.kind)?'draft':props.timing.kind.startsWith('scene-')?'outline':'script';document.querySelector('main').dataset.desktopStage='workspace-'+stage;flushSync(()=>root.render(React.createElement('div',{className:'workspace-content'},React.createElement('div',{'data-progress-stage':'workspace-'+stage},React.createElement(OperationProgress,props)))));};`);
 const compiler=webpack.webpack({ mode:'development',devtool:false,entry,output:{path:temporary,filename:'bundle.js'},resolve:{modules:[path.join(root,'node_modules'),'node_modules']},infrastructureLogging:{level:'error'} });
 await new Promise((resolve,reject)=>compiler.run((error,stats)=>{compiler.close(()=>{});if(error||stats.hasErrors())reject(error||new Error(stats.toString({all:false,errors:true})));else resolve();}));
 const bundle=await fs.readFile(path.join(temporary,'bundle.js'),'utf8');
 const css=(await Promise.all(['globals.css','storyWorkspace.css'].map(file=>fs.readFile(path.join(root,'app',file),'utf8')))).join('\n');
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  for(const width of [1280,390]){
   const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('http://process.test/**',route=>route.fulfill({contentType:'text/html',body:`<html lang="vi"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style><body><main class="story-workspace" style="max-width:960px;margin:24px auto;padding:16px"><div id="root"></div></main></body></html>`}));
   await page.goto('http://process.test/');await page.addScriptTag({content:bundle});
   const render=props=>page.evaluate(props=>window.renderProgress(props),props);
   for(const language of ['vi','en'])for(const [kind,sequence] of Object.entries(stages)){
    const steps=sequence.map((stage,i)=>({stage,occurrence:1,status:i<2?'completed':i===2?'active':'pending'})).filter(s=>s.status!=='pending');
    const props={steps,language,failed:false,timing:{kind,startedAt:performance.now(),finishedAt:null}};
    await render(props);
    const active=page.locator('.process-group.is-active');
    assert.equal(await active.count(),1,kind);
    assert.equal(await active.locator('button').getAttribute('aria-expanded'),'true');
    assert.equal(await page.locator('[data-progress-status="active"]').isVisible(),true);
    const first=page.locator('.process-group').first();
    if(await first.getAttribute('class').then(c=>c.includes('is-completed'))){
     assert.equal(await first.locator('button').getAttribute('aria-expanded'),'false');
     await first.locator('button').click();assert.equal(await first.locator('.process-children').isVisible(),true);
     await first.locator('button').click();assert.equal(await first.locator('.process-children').isVisible(),false);
    }
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`${width}/${kind}: horizontal overflow`);
    if(language==='vi'&&kind==='plan')await page.screenshot({path:`/private/tmp/firstframe-process-${width}.png`,fullPage:true});
    // An interrupted stream stops all active indicators and preserves the step.
    await render({...props,failed:true,timing:{...props.timing,finishedAt:performance.now()}});
    assert.equal(await page.locator('.process-spinner').count(),0);
    assert.equal(await page.locator('[data-progress-status="interrupted"]').isVisible(),true);
    // Failure keeps its group open, future work remains unperformed.
    await render({...props,failed:true,steps:steps.map(s=>s.status==='active'?{...s,status:'failed'}:s),timing:{...props.timing,finishedAt:performance.now()}});
    assert.equal(await page.locator('.process-group.is-failed button').getAttribute('aria-expanded'),'true');
    // Full success collapses all groups; reopening shows the actual children.
    await render({...props,steps:sequence.map(stage=>({stage,occurrence:1,status:'completed'})),timing:{...props.timing,finishedAt:performance.now()}});
    assert.equal(await page.locator('.process-parent button[aria-expanded="true"]').count(),0);
    await page.locator('.process-parent button').first().focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('.process-children').first().isVisible(),true);
    assert.equal(await page.locator('[data-progress-status="pending"]').count(),0);
   }
   assert.deepEqual(errors,[]);await context.close();console.log(`PASS ${width}px: seven workflows, vi/en, auto-expansion, collapse, keyboard, failures, interruptions and no overflow`);
  }
 }finally{await browser.close();await fs.rm(temporary,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
