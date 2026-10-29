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
 const proposal={id:uuid(),created_at:'now',source_revision:p.revision,source_content:'snapshot',source_screenplay:script,source_outline:outline,target_scene_id:script.scenes[0].id,instructions:'Giữ kết mở',status:'ready',scene:script.scenes[0],preview_scene:null,provider:'fake',model:'writer',parameters:{},prompt_version:'v1',error:null,applied_revision:null};
 const withProposal={...p,screenplay_proposals:[proposal],applicable_screenplay_proposal_ids:[proposal.id]};
 assert.deepEqual(await decode(withProposal),withProposal);assert.equal(sameEditableContent(p,withProposal),true);
 assert.equal('screenplay_proposals' in editableProject(withProposal),false);
 const scoped={...proposal,scope:'blocks',block_ids:[block.id]};
 assert.deepEqual(await decode({...withProposal,screenplay_proposals:[scoped]}),{...withProposal,screenplay_proposals:[scoped]});
 for(const mutate of [r=>r.block_ids=[uuid()],r=>r.scope='all',r=>r.scene={...r.scene,heading:'Outside scope'},r=>r.scene={...r.scene,blocks:[...r.scene.blocks,{...block,id:uuid()}]}]){
  const bad=structuredClone(scoped);mutate(bad);await assert.rejects(()=>decode({...withProposal,screenplay_proposals:[bad]}),/không hợp lệ/);
 }
 const preview={...withProposal,pending_screenplay_proposal_id:proposal.id,pending_screenplay_previews:{[proposal.id]:proposal.scene}};
 assert.equal(editableProject(preview).screenplay_proposal_id,proposal.id);
 assert.deepEqual(editableProject(preview).screenplay_proposal_previews,{[proposal.id]:proposal.scene});
 await assert.rejects(()=>decode({...withProposal,screenplay_proposals:[{...proposal,scene:{...proposal.scene,id:uuid()}}]}),/không hợp lệ/);
 assert.equal(sameEditableContent(withProposal,{...withProposal,screenplay_proposals:[{...proposal,preview_scene:{...proposal.scene,heading:'Other window preview'}}]}),false);
 assert.equal(sameEditableContent(withProposal,{...withProposal,screenplay_proposals:[{...proposal,status:'discarded'}]}),false);
 const oversized={...proposal.scene,blocks:Array.from({length:21},()=>({...block,id:uuid(),text:'x'.repeat(10000)}))};await assert.rejects(()=>decode({...withProposal,screenplay_proposals:[{...proposal,preview_scene:oversized}]}),/không hợp lệ/);
 console.log('PASS M3 contract: legacy, editable whitelist, Vietnamese whitespace, source/ID/kind/size/history validation, concurrent edits');
})().catch(e=>{console.error(e);process.exit(1)});
