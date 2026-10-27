const assert=require('node:assert/strict');const {randomUUID:uuid}=require('node:crypto');
const {projectRequest,editableProject,sameEditableContent}=require(process.argv[2]+'/projectsApi.js');
const base={id:'p',title:'Tên',updated_at:'now',revision:2,response_language:'vi',idea:'Ý tưởng',constraints:[],answers:[],analysis:null,draft:null,feedback:null,feedback_is_current:false,versions:[],clarification_history:[]};
const scene={id:uuid(),title:'Cảnh',action:'Nguồn',location:'',time:'',characters:'',goal:'',purpose:'',viewer_intent:'',keep_or_avoid:'',staging_choices:{}};
const outline={id:uuid(),version:1,scenes:[scene],source:{id:uuid(),project_revision:1,version_id:'current',draft:{title:'Nguồn',logline:'',sections:[]},context:{idea:'Giữ khoảng lặng',constraints:[],clarifications:[],pending_questions:[]},response_language:'vi'}};
const block={id:uuid(),kind:'dialogue',speaker:'Con gái',text:'  Không sao đâu cha ạ…\n\n  '};
const script={id:uuid(),version:1,source_revision:1,source_outline:outline,scenes:[{id:uuid(),source_scene_id:scene.id,heading:'NỘI. NHÀ — CHIỀU',blocks:[block]}]};
(async()=>{
 const decode=async p=>{global.fetch=async()=>new Response(JSON.stringify(p));return projectRequest('/p')};
 assert.deepEqual(await decode(base),base);
 const p={...base,screenplay:script,screenplay_versions:[],screenplay_source_is_current:true};
 assert.deepEqual(await decode(p),p);
 const unicode=structuredClone(p);unicode.screenplay.scenes[0].blocks[0].text="🙂".repeat(10000);assert.deepEqual(await decode(unicode),unicode);
 assert.deepEqual(Object.keys(editableProject(p).screenplay).sort(),['id','scenes','version']);
 assert.equal(editableProject(p).screenplay.scenes[0].blocks[0].text,block.text);
 assert.equal('screenplay_versions' in editableProject(p),false);
 assert.equal('screenplay' in editableProject(base),false);
 assert.equal(sameEditableContent(p,{...p,revision:7,screenplay_source_is_current:false}),true);
 const other=structuredClone(p);other.screenplay.scenes[0].blocks[0].text='Cửa sổ khác sửa';assert.equal(sameEditableContent(p,other),false);
 for(const mutate of [
  p=>p.screenplay.scenes[0].source_scene_id=uuid(),
  p=>p.screenplay.scenes[0].blocks.push({...block}),
  p=>p.screenplay.scenes[0].blocks[0].kind='html',
  p=>p.screenplay.scenes[0].blocks[0].text='x'.repeat(10001),
  p=>p.screenplay.source_outline.source.context={},
  p=>p.screenplay_versions=[{id:uuid(),created_at:'now',screenplay:{}}],
 ]){const bad=structuredClone(p);mutate(bad);await assert.rejects(()=>decode(bad),/không hợp lệ/);}
 console.log('PASS M3 contract: legacy, editable whitelist, Vietnamese whitespace, source/ID/kind/size/history validation, concurrent edits');
})().catch(e=>{console.error(e);process.exit(1)});
