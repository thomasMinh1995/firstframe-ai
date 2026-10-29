const assert=require('node:assert/strict'),{randomUUID:uuid}=require('node:crypto');
const {projectRequest,editableProject,sameEditableContent}=require(process.argv[2]+'/projectsApi.js');
const {reviewNoteSupported,reviewSourceMatches,sameReviewScript}=require(process.argv[2]+'/screenplayReviewTypes.js');
const base={id:'p',title:'Tên',updated_at:'now',revision:2,response_language:'vi',idea:'Ý tưởng',constraints:[],answers:[],analysis:null,draft:null,feedback:null,feedback_is_current:false,versions:[],clarification_history:[]};
const scene={id:uuid(),title:'Cảnh',action:'Con gái tự quyết định.',location:'',time:'',characters:'',goal:'',purpose:'',viewer_intent:'',keep_or_avoid:'',staging_choices:{blocking:'Giữ lối đi trống.'}};
const context={idea:'Một lựa chọn còn mở.',constraints:['Không nói đã tha thứ.'],clarifications:[{question:'Điều gì quan trọng?',answer:'Con gái tự quyết định.',input_index:0}],pending_questions:[]};
const outline={id:uuid(),version:1,scenes:[scene],source:{id:uuid(),project_revision:1,version_id:'current',draft:{title:'Nguồn',logline:'Kết mở.',sections:[]},context,response_language:'vi'}};
const b={id:uuid(),kind:'dialogue',speaker:'Con gái',text:'Con tha thứ cho cha.'},s={id:uuid(),source_scene_id:scene.id,heading:'NỘI. NHÀ',blocks:[b]};
const script={id:uuid(),version:1,source_revision:1,source_outline:outline,scenes:[s]};
const anchor={id:`block:${b.id}:text`,label:'Khối 1',text:b.text,category:'screenplay',scene_id:s.id,block_id:b.id,field:'text'};
const choice={id:'intent:constraint:0',label:'Giới hạn 1',text:context.constraints[0],category:'author_choice',scene_id:null,block_id:null,field:'choice'};
const note={id:uuid(),kind:'intent_mismatch',observation:'Câu nói chốt tha thứ.',impact:'Có thể đóng điều tác giả muốn để mở.',suggestion:'Cân nhắc một cử chỉ hoặc câu nói chưa kết luận.',evidence:[{source_id:anchor.id,quote:b.text},{source_id:choice.id,quote:choice.text}],assessment:null};
const review={id:uuid(),created_at:'now',source_revision:1,source_content:'snapshot',source_screenplay:script,source_outline:outline,target_scene_id:s.id,instructions:'',status:'ready',sources:[anchor,choice],notes:[note],question:'',provider:'fake',model:'reviewer',parameters:{},prompt_version:'v1',error:null};
(async()=>{
 const decode=async p=>{global.fetch=async()=>new Response(JSON.stringify(p));return projectRequest('/p')};
 const p={...base,screenplay:script,screenplay_reviews:[review],current_screenplay_review_ids:[review.id]};
 assert.deepEqual(await decode(p),p);assert.deepEqual(await decode(base),base);
 assert.equal('screenplay_reviews' in editableProject(p),false);assert.equal('current_screenplay_review_ids' in editableProject(p),false);
 assert.equal(reviewSourceMatches(script,anchor),true);assert.equal(reviewNoteSupported(review,note),true);
 const old=structuredClone(review);old.sources[1]={id:`m2:${scene.id}:action`,label:'Diễn tiến cũ',text:scene.action,category:'author_choice',scene_id:null,block_id:null,field:'choice'};
 old.notes[0].evidence[1]={source_id:old.sources[1].id,quote:scene.action};
 assert.deepEqual(await decode({...p,screenplay_reviews:[old]}),{...p,screenplay_reviews:[old]},'legacy source roles remain readable');
 assert.equal(reviewNoteSupported(old,old.notes[0]),false,'unknown legacy origin does not become a confirmed author choice');
 const ai=structuredClone(old),sourceId=ai.sources[1].id;
 const aiOrigin={origin:'ai_proposal',author_confirmed:false};
 ai.source_screenplay.source_outline.provenance={[sourceId]:aiOrigin};
 ai.sources[1].category='context';ai.sources[1].provenance={...aiOrigin};ai.notes[0].kind='craft';
 assert.deepEqual(await decode({...p,screenplay_reviews:[ai]}),{...p,screenplay_reviews:[ai]});
 const forgedLabel=structuredClone(ai);forgedLabel.sources[1].provenance.origin='author_input';
 await assert.rejects(()=>decode({...p,screenplay_reviews:[forgedLabel]}),/không hợp lệ/,'displayed origin must match the immutable source');
 const forgedFlag=structuredClone(ai);forgedFlag.source_screenplay.source_outline.provenance[sourceId].author_confirmed='false';
 forgedFlag.sources[1].category='author_choice';forgedFlag.notes[0].kind='intent_mismatch';
 await assert.rejects(()=>decode({...p,screenplay_reviews:[forgedFlag]}),/không hợp lệ/,'confirmation is a boolean, not a truthy string');
 const forgedOrigin=structuredClone(ai);forgedOrigin.source_screenplay.source_outline.provenance[sourceId].origin=['ai_proposal'];
 await assert.rejects(()=>decode({...p,screenplay_reviews:[forgedOrigin]}),/không hợp lệ/,'origin must be an enum string');
 assert.equal(sameReviewScript(script,{...script,version:7,source_revision:99}),true);
 const attributed={...script,provenance:{[anchor.id]:{origin:'author_input',author_confirmed:false},[`script:${s.id}:heading`]:{origin:'ai_proposal',author_confirmed:false}}};
 const reordered={...attributed,provenance:Object.fromEntries(Object.entries(attributed.provenance).reverse())};
 assert.equal(sameReviewScript(attributed,reordered),true,'restoring a snapshot may reorder provenance keys without changing evidence');
 const changed=structuredClone(script);changed.scenes[0].blocks[0].text='Nội dung mới';assert.equal(sameReviewScript(script,changed),false);
 for(const mutate of [r=>r.notes[0].evidence[0].quote='Quote bịa',r=>r.notes[0].evidence[0].source_id='unknown',r=>r.sources[0].text='Quote bịa',
   r=>{r.sources[0].text='Quote bịa';r.notes[0].evidence[0].quote='Quote bịa'},r=>r.sources[0].scene_id=uuid(),
   r=>r.notes[0].evidence=[r.notes[0].evidence[0]],r=>r.notes[0].evidence=[r.notes[0].evidence[1]],r=>r.notes[0].assessment='auto-rewrite']){
   const bad=structuredClone(review);mutate(bad);await assert.rejects(()=>decode({...p,screenplay_reviews:[bad]}),/không hợp lệ/);
 }
 assert.deepEqual(await decode({...p,screenplay_reviews:[{...review,notes:[],question:'Chưa đủ thông tin?'}]}),{...p,screenplay_reviews:[{...review,notes:[],question:'Chưa đủ thông tin?'}]});
 assert.equal(sameEditableContent({...p,screenplay_reviews:[]},p),true,'new AI feedback is metadata');
 assert.equal(sameEditableContent(p,{...p,screenplay_reviews:[{...review,notes:[{...note,assessment:'misleading'}]}]}),false,'author assessment must not be silently rebased');
 assert.equal(sameEditableContent(p,{...p,screenplay_reviews:[{...review,status:'discarded'}]}),false);
 console.log('PASS M3 review contract: legacy, read-only source, exact snapshot/quote/role checks, stale content/version metadata, empty notes and author decisions');
})().catch(e=>{console.error(e);process.exit(1)});
