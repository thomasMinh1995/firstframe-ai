"use client";
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {isComposingKey} from './inputEvents';
export function ReviewPanel({open,onClose,label,children,disabled=false}:{disabled?:boolean;open:boolean;onClose:()=>void;label:string;children:ReactNode}){
 const latest=useRef({open,onClose});latest.current={open,onClose};
 const marker=useRef<HTMLSpanElement>(null);const [stageVisible,setStageVisible]=useState(false);
 const [mobile,setMobile]=useState(false);const mode=useRef(mobile);mode.current=mobile;
 const dialog=useRef<HTMLDialogElement>(null);const composing=useRef(false);
 const resizeFocus=useRef<HTMLElement|null>(null);
 useEffect(()=>{const stage=marker.current?.closest<HTMLElement>('[data-workspace-stage]');const workspace=marker.current?.closest('[data-desktop-stage]');
  const update=()=>{const tourOpen=!!document.querySelector('.tour-layer[open]');if(tourOpen&&latest.current.open)latest.current.onClose();setStageVisible(!tourOpen&&(!stage||getComputedStyle(stage).display!=='none'))};update();
  const observer=new MutationObserver(update);if(workspace)observer.observe(workspace,{attributes:true,attributeFilter:['data-desktop-stage']});const dialogs=new MutationObserver(update);dialogs.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['open']});return()=>{observer.disconnect();dialogs.disconnect()};},[]);
 useEffect(()=>{const media=matchMedia('(max-width:1000px)');const update=()=>setMobile(media.matches);update();media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
 useEffect(()=>{
  const node=dialog.current;if(!node||!open||!stageVisible)return;
  const opener=document.activeElement;
  if(mobile)node.showModal();else node.open=true; // Non-modal desktop panel must not steal editor focus.
  if(resizeFocus.current?.isConnected&&resizeFocus.current.getClientRects().length)resizeFocus.current.focus({preventScroll:true});
  resizeFocus.current=null;
  return()=>{
   const switching=mode.current!==mobile;
   if(switching&&latest.current.open&&node.contains(document.activeElement))resizeFocus.current=document.activeElement as HTMLElement;
   node.close();
   if(mobile&&!switching&&opener instanceof HTMLElement&&opener.isConnected&&opener.getClientRects().length)opener.focus({preventScroll:true});
  };
 },[mobile,open,stageVisible]);
 // Keep one host across breakpoints: reparenting a portal remounts uncontrolled draft state.
 return <><span hidden ref={marker}/><dialog ref={dialog} className={mobile?'review-sheet':'review-side-panel'} aria-label={label}
  onCompositionStartCapture={()=>{composing.current=true}} onCompositionEndCapture={()=>{composing.current=false}}
  onKeyDownCapture={event=>{if(event.key==='Escape'&&(composing.current||isComposingKey(event))){event.preventDefault();event.stopPropagation()}}}
  onKeyDown={event=>{if(event.key==='Escape'&&!mobile&&!event.defaultPrevented){event.preventDefault();event.stopPropagation();onClose()}}}
  onCancel={event=>{event.preventDefault();if(!composing.current)onClose()}}>
  <button type="button" className="secondary review-panel-close" onClick={onClose}>Đóng panel góp ý</button>
  <div className="review-panel-body"><fieldset disabled={disabled} className="review-panel-fields">{children}</fieldset></div>
 </dialog></>;
}
