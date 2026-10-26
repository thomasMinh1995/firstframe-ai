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
 console.log('PASS M2 transport: legacy compatibility, read-only source/history excluded, text preserved, invalid sources/IDs/fields rejected');
})().catch(e=>{console.error(e);process.exit(1)});
