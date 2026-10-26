const assert=require('node:assert/strict');
const {projectRequest,editableProject}=require(process.argv[2]+'/projectsApi.js');
const {randomUUID}=require('node:crypto');
const base={id:'p',title:'Tên',updated_at:'now',revision:2,response_language:'vi',idea:'Ý tưởng',constraints:[],answers:[],analysis:null,draft:null,feedback:null,feedback_is_current:false,versions:[],clarification_history:[]};
const draft={title:'Nguồn',logline:'Kết mở.',sections:[]},context={idea:'Ý tưởng',constraints:[],clarifications:[],pending_questions:[]};
const s={id:randomUUID(),title:'Cảnh',action:'  Giữ khoảng trắng.  ',location:'',time:'',characters:'',goal:'',purpose:'',viewer_intent:'',keep_or_avoid:'',staging_choices:{blocking:'Chừa lối ra.'}};
const outline={id:randomUUID(),version:1,scenes:[s],source:{id:randomUUID(),project_revision:1,version_id:'current',draft,context,response_language:'vi'}};
(async()=>{
 const project={...base,scene_outline:outline,scene_versions:[],scene_handoff:null};
 const edit=editableProject(project);assert.deepEqual(Object.keys(edit.scene_outline).sort(),['id','scenes','version']);assert.equal('source' in edit.scene_outline,false);assert.equal('scene_versions' in edit,false);assert.equal(edit.scene_outline.scenes[0].action,s.action);
 const decode=async value=>{global.fetch=async()=>new Response(JSON.stringify(value));return projectRequest('/p')};
 assert.deepEqual(await decode(base),base);assert.deepEqual(await decode(project),project);
 await assert.rejects(()=>decode({...project,scene_outline:{...outline,scenes:[s,s]}}),/không hợp lệ/);
 await assert.rejects(()=>decode({...project,scene_outline:{...outline,source:{...outline.source,context:{}}}}),/không hợp lệ/);
 await assert.rejects(()=>decode({...project,scene_outline:{...outline,scenes:[{...s,staging_choices:{toString:'invalid'}}]}}),/không hợp lệ/);
 assert.equal('scene_outline' in editableProject({...base,scene_outline:null}),false);
 const proposal={id:randomUUID(),created_at:'now',source_revision:1,source_content:'frozen',source_outline:outline,
   mode:'list',target_scene_id:null,instructions:'Keep open',status:'ready',scenes:[s],transitions:{[s.id]:'Cut.'},
   provider:'fake',model:'fake',parameters:{},prompt_version:'scene-suggestions-v1',error:null,applied_revision:null};
 const withProposal={...project,scene_proposals:[proposal],applicable_scene_proposal_ids:[proposal.id]};
 assert.deepEqual(await decode(withProposal),withProposal);
 const adopting=editableProject({...withProposal,pending_scene_proposal_id:proposal.id});
 assert.equal(adopting.scene_proposal_id,proposal.id);
 assert.deepEqual(editableProject({...withProposal,pending_scene_previews:{[proposal.id]:[s]}}).scene_proposal_previews,{[proposal.id]:[s]});
 assert.equal('scene_proposals' in adopting,false);assert.equal('applicable_scene_proposal_ids' in adopting,false);
 await assert.rejects(()=>decode({...project,scene_proposals:[{...proposal,status:'invented'}]}),/không hợp lệ/);
 await assert.rejects(()=>decode({...project,scene_proposals:[{...proposal,source_outline:{}}]}),/không hợp lệ/);
 const {sameEditableContent}=require(process.argv[2]+'/projectsApi.js');
 assert.equal(sameEditableContent(project,{...withProposal,revision:project.revision+2}),true);
 assert.equal(sameEditableContent(project,{...withProposal,title:'Other window edit'}),false);
 assert.equal(sameEditableContent(project,{...withProposal,scene_outline:{...outline,version:2}}),false);
 const savedPreview={...withProposal,scene_proposals:[{...proposal,preview_scenes:[s]}]};
 const otherWindowPreview={...savedPreview,revision:3,scene_proposals:[{...proposal,preview_scenes:[{...s,action:'Other author edit'}]}]};
 assert.equal(sameEditableContent(savedPreview,otherWindowPreview),false,'do not advance revision over another window preview edit');
 assert.equal(sameEditableContent(savedPreview,{...savedPreview,revision:3,scene_proposals:[{...savedPreview.scene_proposals[0],status:'discarded'}]}),true,'status changes alone preserve content');

 const input={request_id:randomUUID(),mode:'append',target_scene_id:s.id,instructions:'Keep open'};
 const {streamProjectOperation}=require(process.argv[2]+'/projectsApi.js');
 let calls=0;
 global.fetch=async(url,options)=>{calls++;assert.match(url,/scene-suggestions\/stream$/);
   assert.deepEqual(JSON.parse(options.body),{revision:project.revision,...input});
   return new Response(JSON.stringify({type:'result',project:withProposal})+'\n');};
 assert.deepEqual(await streamProjectOperation(project,'scene-suggestions',()=>{},'vi',input),withProposal);
 assert.equal(calls,1);

 console.log('PASS M2 transport: legacy compatibility, read-only source/history excluded, text preserved, invalid sources/IDs/fields rejected');
})().catch(e=>{console.error(e);process.exit(1)});
