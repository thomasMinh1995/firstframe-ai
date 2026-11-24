const assert=require('node:assert/strict'),{randomUUID:uuid}=require('node:crypto'),fs=require('node:fs');
const {projectRequest,editableProject,sameEditableContent}=require(process.argv[2]+'/projectsApi.js');
const {unfinishedScriptScenes}=require(process.argv[2]+'/screenplayTypes.js');
const {ScreenplayReading}=require(process.argv[2]+'/ScreenplayReading.js');
const {renderToStaticMarkup}=require('react-dom/server'),React=require('react');
const base=JSON.parse(fs.readFileSync('../docs/evaluations/m3-scene-review-qwen7b-2026-10-27/inputs.json','utf8'))[0].project;
const selection={id:uuid(),created_at:'now',source_revision:base.revision,source_version_id:'current',screenplay:structuredClone(base.screenplay)};
const selected={...base,screenplay_selections:[selection],screenplay_handoff:selection};
(async()=>{
 const decode=async p=>{global.fetch=async()=>new Response(JSON.stringify(p));return projectRequest('/p')};
 assert.deepEqual(await decode(base),base);assert.deepEqual(await decode(selected),selected);
 assert.equal('screenplay_selections' in editableProject(selected),false);assert.equal('screenplay_handoff' in editableProject(selected),false);
 assert.equal(sameEditableContent(base,selected),false,'new author source choice cannot be silently rebased');
 assert.equal(unfinishedScriptScenes(selection.screenplay).length,0);
 for(const mutate of [
  p=>p.screenplay_selections[0].id='forged',p=>p.screenplay_selections[0].source_version_id='proposal',
  p=>p.screenplay_selections[0].screenplay.scenes[0].heading=' ',
  p=>p.screenplay_selections[0].screenplay.scenes[0].blocks=[],
  p=>p.screenplay_selections[0].screenplay.scenes[1].blocks[1].speaker=' ',
  p=>p.screenplay_selections[0].screenplay.scenes[0].source_scene_id=uuid(),
  p=>p.screenplay_selections.push(structuredClone(p.screenplay_selections[0])),
  p=>p.screenplay_handoff={...p.screenplay_handoff,id:uuid()},p=>p.screenplay_handoff=null,
 ]){const p=structuredClone(selected);mutate(p);await assert.rejects(()=>decode(p),/không hợp lệ/);}
 const props={saved:selected,dirty:true,onSelect:async()=>{},onInspect:async()=>true,onEdit:()=>{}};
 const html=renderToStaticMarkup(React.createElement(ScreenplayReading,props));
 assert.match(html,/Có sửa chưa lưu/);assert.match(html,/Chưa xuất bản|chưa xuất bản/);assert.match(html,/Kịch bản đã chọn để xuất/);
 assert.equal((html.match(/data-reading-scene=/g)||[]).length,selection.screenplay.scenes.length*2);
 assert.ok(!html.includes('<textarea'),'reader must never edit a source');
 const draft=structuredClone(base);draft.screenplay.scenes[0].blocks=[];draft.screenplay.scenes[1].blocks[0].text='<script>alert(1)</script>';
 const preview=renderToStaticMarkup(React.createElement(ScreenplayReading,{...props,saved:draft}));
 assert.match(preview,/Cảnh chưa viết/);assert.match(preview,/Quay lại sửa cảnh 1/);assert.ok(!preview.includes('<script>'));assert.match(preview,/&lt;script&gt;/);
 console.log('PASS M3 selection: legacy, immutable payload, explicit author choice, source completeness/IDs/latest pointer, saved reader, missing scenes and escaped text');
})().catch(e=>{console.error(e);process.exit(1)});
