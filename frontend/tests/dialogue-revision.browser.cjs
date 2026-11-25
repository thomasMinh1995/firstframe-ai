const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {randomUUID:uuid}=require('node:crypto');

(async()=>{
  const browser=await chromium.launch({headless:true,channel:'chrome'});
  try {
    const page=await browser.newPage({viewport:{width:1280,height:940}});
    await page.addInitScript(()=>localStorage.setItem('firstframe:onboarding',JSON.stringify({version:1,status:'dismissed',stepId:'save',projectId:null})));
    const req=async(route,method='GET',data)=>{
      const response=await page.request.fetch('http://127.0.0.1:8034'+route,{method,data});
      assert.ok(response.ok(),await response.text());
      return response.json();
    };
    let project=await req('/api/projects','POST');
    const url='/api/projects/'+project.id;
    const body=()=>Object.fromEntries(['revision','title','idea','constraints','answers','draft','response_language'].map(key=>[key,project[key]]));
    project=await req(url,'PUT',{...body(),title:'Lượt thử hội thoại',idea:'Hai cha con ngồi cạnh bàn.',response_language:'vi',
      draft:{title:'Lượt thử hội thoại',logline:'Hai cha con ngồi cạnh bàn.',sections:[{title:'Bàn ăn',purpose:'',content:'Cha đặt thư lên bàn.'}]}});
    project=await req(url+'/scene-outline','POST',{revision:project.revision,source_version_id:'current'});
    project=await req(url,'PUT',{...body(),scene_outline:{id:project.scene_outline.id,version:project.scene_outline.version,
      scenes:[{id:uuid(),title:'Bàn ăn',action:'Cha đặt thư lên bàn.'}]}});
    project=await req(url+'/screenplay','POST',{revision:project.revision,request_id:uuid()});
    const script=project.screenplay;
    const scene={...script.scenes[0],blocks:[
      {id:uuid(),kind:'action',text:'Cha vẫn giữ thư.',speaker:''},
      {id:uuid(),kind:'dialogue',text:'Con ngồi đây với cha.',speaker:'Con gái'},
      {id:uuid(),kind:'dialogue',text:'Con cứ ngồi.',speaker:'Cha'},
    ]};
    project=await req(url,'PUT',{...body(),screenplay:{id:script.id,version:script.version,scenes:[scene]}});
    await page.goto('http://127.0.0.1:3034/?project='+project.id);
    await page.locator('.workspace-stage-nav button[aria-controls="workspace-script"]').click();
    await page.locator('.screenplay-scene-list').getByRole('button').first().click();
    await page.locator('.screenplay-writing-tools > summary').click();
    const panel=page.locator('.screenplay-proposals');
    await panel.getByLabel('Phạm vi sửa').selectOption('dialogue');
    const options=panel.getByRole('group',{name:'Chọn lời thoại cần sửa'});
    assert.equal(await options.getByRole('checkbox').count(),2);
    await options.getByRole('checkbox',{name:/Con gái · Con ngồi/}).check();
    await panel.getByRole('button',{name:'Xem phạm vi sửa'}).click();
    await panel.getByRole('button',{name:'Tạo phương án sửa trong phạm vi này'}).click();
    const proposal=panel.locator(':scope > .screenplay-proposal').first();
    await proposal.getByRole('button',{name:'Chỉnh phương án',exact:true}).click();
    const saved=await req(url);
    assert.deepEqual(saved.screenplay.scenes,[scene]);
    assert.equal(saved.screenplay_proposals.at(-1).dialogue_only,true);
    assert.deepEqual(saved.screenplay_proposals.at(-1).block_ids,[scene.blocks[1].id]);
    await proposal.getByRole('textbox').fill('Con ngồi thêm một lát.');
    await proposal.getByRole('button',{name:'Dùng phương án và lưu'}).click();
    await proposal.getByText(/đã dùng và lưu/).waitFor();
    const applied=(await req(url)).screenplay.scenes[0];
    assert.deepEqual(applied,{...scene,blocks:[scene.blocks[0],{...scene.blocks[1],text:'Con ngồi thêm một lát.'},scene.blocks[2]]});
    await proposal.locator(':scope > summary').click();
    await proposal.getByRole('button',{name:'Hoàn tác lần nhận này'}).click();
    await proposal.getByText('Đã hoàn tác và giữ lịch sử.').waitFor({state:'attached'});
    assert.deepEqual((await req(url)).screenplay.scenes,[scene]);
    console.log('PASS dialogue-only selection, editable preview, apply and undo');
  } finally {
    await browser.close();
  }
})().catch(error=>{console.error(error);process.exit(1)});
