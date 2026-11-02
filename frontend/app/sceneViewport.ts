export function viewportScrollDelta(top:number,bottom:number,visibleTop:number,visibleBottom:number,align:'start'|'nearest'|'center'='nearest'){
 if(align==='start'||bottom-top>visibleBottom-visibleTop)return top-visibleTop;
 if(align==='center'){
  const delta=(top+bottom-visibleTop-visibleBottom)/2;
  return top>=visibleTop&&bottom<=visibleBottom&&Math.abs(delta)<=(visibleBottom-visibleTop)/4?0:delta;
 }
 if(top>=visibleTop&&bottom<=visibleBottom)return 0;
 if(top<visibleTop)return top-visibleTop;
 return bottom>visibleBottom?bottom-visibleBottom:0;
}

// Scroll inner scene lists first, then place the row below the actual sticky bars.
export function revealSceneInViewport(target:HTMLElement,align:'start'|'nearest'|'center'='nearest'){
 const margin=12;
 for(let parent=target.parentElement;parent&&parent!==document.scrollingElement;parent=parent.parentElement){
  if(!/(auto|scroll)/.test(getComputedStyle(parent).overflowY)||parent.scrollHeight<=parent.clientHeight)continue;
  const box=parent.getBoundingClientRect(),row=target.getBoundingClientRect();
  const top=box.top+parent.clientTop;
  const delta=viewportScrollDelta(row.top,row.bottom,top+margin,top+parent.clientHeight-margin,align==='center'?'center':'nearest');
  if(delta)parent.scrollBy({top:delta,behavior:'instant'});
 }
 let inset=margin;
 for(const bar of document.querySelectorAll<HTMLElement>('.save-toolbar,.draft-workflow-current.is-active')){
  const style=getComputedStyle(bar),box=bar.getBoundingClientRect();
  if(!box.height||!box.width||!['sticky','fixed'].includes(style.position))continue;
  if(style.position==='sticky'&&(!bar.parentElement?.contains(target)||!(bar.compareDocumentPosition(target)&Node.DOCUMENT_POSITION_FOLLOWING)))continue;
  const top=Number.parseFloat(style.top);
  if(Number.isFinite(top))inset=Math.max(inset,top+box.height+margin);
 }
 const row=target.getBoundingClientRect();
 const delta=viewportScrollDelta(row.top,row.bottom,inset,window.innerHeight-margin,align);
 if(delta)window.scrollBy({top:delta,behavior:'instant'});
}
