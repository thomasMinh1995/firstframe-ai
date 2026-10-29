const assert=require('node:assert/strict'),fs=require('node:fs'),{randomUUID:uuid}=require('node:crypto');
const {selectReadScreenplay,downloadScreenplayPdf}=require(process.argv[2]+'/screenplayExport.js');
const base=JSON.parse(fs.readFileSync('../docs/evaluations/m3-scene-review-qwen7b-2026-10-27/inputs.json','utf8'))[0].project;
(async()=>{
 let calls=[];global.fetch=async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(base));};
 const read=structuredClone(base.screenplay),id=uuid();
 await selectReadScreenplay(base,{request_id:id,source_version_id:'current'},read);
 assert.equal(JSON.parse(calls[0].options.body).revision,base.revision);
 const changed=structuredClone(base);changed.screenplay.scenes[0].blocks[0].text='Chữ mới khi đang flush';
 await assert.rejects(()=>selectReadScreenplay(changed,{request_id:id,source_version_id:'current'},read),/đã đổi/);
 assert.equal(calls.length,1,'changed read source must never be selected silently');
 changed.screenplay_versions=[{id:'history',created_at:'now',screenplay:read}];
 await selectReadScreenplay(changed,{request_id:id,source_version_id:'history'},read);
 assert.equal(JSON.parse(calls[1].options.body).source_version_id,'history');
 const clicks=[];let revoked=false;const oldCreate=URL.createObjectURL,oldRevoke=URL.revokeObjectURL,oldTimeout=global.setTimeout;
 URL.createObjectURL=()=> 'blob:pdf';URL.revokeObjectURL=()=>{revoked=true};global.setTimeout=f=>{f();return 0};
 global.document={body:{appendChild(){}},createElement(){return {href:'',download:'',click(){clicks.push(this.download)},remove(){}}}};
 try{
  global.fetch=async(url,options)=>{calls.push({url,options});return new Response('%PDF-test',{headers:{'Content-Type':'application/pdf','Content-Disposition':'attachment; filename="La-thu.pdf"'}})};
  await downloadScreenplayPdf(base.id,id);assert.deepEqual(clicks,['La-thu.pdf']);assert.equal(revoked,true);
  assert.ok(calls.at(-1).url.endsWith(`/screenplay-selections/${id}/pdf`));assert.equal(calls.at(-1).options.cache,'no-store');
  global.fetch=async()=>new Response(JSON.stringify({detail:'Bản đã chọn vẫn giữ'}),{status:503});
  await assert.rejects(()=>downloadScreenplayPdf(base.id,id),/Bản đã chọn vẫn giữ/);
  global.fetch=async()=>new Response('not PDF',{headers:{'Content-Type':'application/pdf'}});
  await assert.rejects(()=>downloadScreenplayPdf(base.id,id),/PDF hợp lệ/);assert.equal(clicks.length,1);
 }finally{URL.createObjectURL=oldCreate;URL.revokeObjectURL=oldRevoke;global.setTimeout=oldTimeout;}
 console.log('PASS PDF export: exact read snapshot after flush, explicit history source, selection-ID download, errors and invalid payloads');
})().catch(error=>{console.error(error);process.exit(1)});
