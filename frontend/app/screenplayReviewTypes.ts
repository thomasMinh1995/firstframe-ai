import type {StagingKey} from './sceneTypes';
import type {Screenplay} from './screenplayTypes';
import {isTextProvenance, unknownProvenance, type TextProvenance} from './provenance';
export type ReviewSource={id:string;label:string;text:string;category:'screenplay'|'author_choice'|'context';scene_id:string|null;block_id:string|null;field:'text'|'speaker'|'heading'|'choice'|'context';provenance?:TextProvenance|null};
export type ReviewAssessment='helpful'|'misleading'|'uncertain'|'dismissed';
export type ReviewNote={id:string;kind:'intent_mismatch'|'craft'|'uncertain';observation:string;impact:string;suggestion:string;evidence:{source_id:string;quote:string}[];assessment:ReviewAssessment|null};
export type ScreenplayReview={id:string;created_at:string;source_revision:number;source_content:string;source_screenplay:Screenplay;source_outline:Screenplay['source_outline']|null;target_scene_id:string;instructions:string;status:'pending'|'ready'|'failed'|'discarded';sources:ReviewSource[];notes:ReviewNote[];question:string;provider:string|null;model:string|null;parameters:Record<string,unknown>;prompt_version:string;error:string|null};

export function reviewSourceMatches(script:Screenplay,s:ReviewSource,allowLegacy=false):boolean {
  let expected:string|undefined;let category:ReviewSource['category']='context';let field:ReviewSource['field']='context';let sceneId:string|null=null,blockId:string|null=null;
  let provenance = unknownProvenance;
  const block=/^block:([0-9a-f-]+):(text|speaker)$/.exec(s.id),heading=/^script:([0-9a-f-]+):heading$/.exec(s.id);
  const choice=/^m2:([0-9a-f-]+):(action|keep_or_avoid|viewer_intent|location|time|characters|goal|purpose|staging:[a-z]+)$/.exec(s.id);
  const intent=/^intent:(constraint|answer):(0|[1-9][0-9]*)$/.exec(s.id),section=/^plan:section:(0|[1-9][0-9]*)$/.exec(s.id);
  const context=script.source_outline.source.context,draft=script.source_outline.source.draft;
  if(block){const owner=script.scenes.find(x=>x.blocks.some(b=>b.id===block[1]));const b=owner?.blocks.find(b=>b.id===block[1]);field=block[2] as 'text'|'speaker';expected=b?.[field];category='screenplay';sceneId=owner?.id??null;blockId=b?.id??null;provenance=script.provenance?.[s.id]??unknownProvenance;}
  else if(heading){const owner=script.scenes.find(x=>x.id===heading[1]);expected=owner?.heading;category='screenplay';field='heading';sceneId=owner?.id??null;provenance=script.provenance?.[s.id]??unknownProvenance;}
  else if(choice){const source=script.source_outline.scenes.find(x=>x.id===choice[1]);const key=choice[2];expected=key.startsWith('staging:')?source?.staging_choices[key.slice(8) as StagingKey]:source?.[key as 'action'|'keep_or_avoid'|'viewer_intent'|'location'|'time'|'characters'|'goal'|'purpose'];const origin=script.source_outline.provenance?.[s.id];provenance=origin??unknownProvenance;category=origin?.origin==='author_input'||origin?.author_confirmed===true||(allowLegacy&&!origin&&!s.provenance)?'author_choice':'context';field='choice';}
  else if(s.id==='intent:idea'){expected=context.idea;category='author_choice';field='choice';provenance={origin:'author_input',author_confirmed:false};}
  else if(intent){expected=intent[1]==='constraint'?context.constraints[Number(intent[2])]:context.clarifications[Number(intent[2])]?.answer;category='author_choice';field='choice';provenance={origin:'author_input',author_confirmed:false};}
  else if(s.id==='plan:logline'){expected=draft.logline;provenance=script.source_outline.source.draft_provenance?.logline??unknownProvenance;}
  else if(section){expected=draft.sections[Number(section[1])]?.content;provenance=script.source_outline.source.draft_provenance?.[`section:${Number(section[1])}:content`]??unknownProvenance;}
  const originMatches=isTextProvenance(provenance)&&(s.provenance==null||(isTextProvenance(s.provenance)
    &&s.provenance.origin===provenance.origin&&s.provenance.author_confirmed===provenance.author_confirmed));
  return originMatches&&typeof expected==='string'&&!!expected.trim()&&expected===s.text&&s.category===category&&s.field===field&&s.scene_id===sceneId&&s.block_id===blockId;
}

export function reviewNoteSupported(review:ScreenplayReview,note:ReviewNote,allowLegacy=false):boolean {
  const refs=note.evidence.map(e=>review.sources.find(s=>s.id===e.source_id));
  return refs.every((s,i)=>!!s&&reviewSourceMatches(review.source_screenplay,s,allowLegacy)&&!!note.evidence[i].quote.trim()&&s.text.includes(note.evidence[i].quote))
    &&refs.some(s=>s?.category==='screenplay'&&s.scene_id===review.target_scene_id&&s.field==='text')
    &&(note.kind!=='intent_mismatch'||refs.some(s=>s?.category==='author_choice'));
}

export function sameReviewScript(a:Screenplay,b:Screenplay):boolean {
  const content=(s:Screenplay)=>({id:s.id,scenes:s.scenes,provenance:s.provenance??{},source:{id:s.source_outline.id,scenes:s.source_outline.scenes,provenance:s.source_outline.provenance??{},source:s.source_outline.source}});
  const stable=(value:unknown):unknown=>Array.isArray(value)?value.map(stable)
    :value!==null&&typeof value==='object'?Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,stable(v)])):value;
  return JSON.stringify(stable(content(a)))===JSON.stringify(stable(content(b)));
}
