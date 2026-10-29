"use client";
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
export function ReviewPanel({open,onClose,label,children,disabled=false}:{disabled?:boolean;open:boolean;onClose:()=>void;label:string;children:ReactNode}){
 const latest=useRef({open,onClose});latest.current={open,onClose};
 const marker=useRef<HTMLSpanElement>(null);const [stageVisible,setStageVisible]=useState(false);
 const [mobile,setMobile]=useState(false);const dialog=useRef<HTMLDialogElement>(null);
 const opener=useRef<Element|null>(null);
 useEffect(()=>{const stage=marker.current?.closest<HTMLElement>('[data-workspace-stage]');const workspace=marker.current?.closest('[data-desktop-stage]');
  const update=()=>{const tourOpen=!!document.querySelector('.tour-layer[open]');if(tourOpen&&latest.current.open)latest.current.onClose();setStageVisible(!tourOpen&&(!stage||getComputedStyle(stage).display!=='none'))};update();
  const observer=new MutationObserver(update);if(workspace)observer.observe(workspace,{attributes:true,attributeFilter:['data-desktop-stage']});const dialogs=new MutationObserver(update);dialogs.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['open']});return()=>{observer.disconnect();dialogs.disconnect()};},[]);
 useEffect(()=>{const media=matchMedia('(max-width:1000px)');const update=()=>setMobile(media.matches);update();media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
 useEffect(()=>{if(!mobile||!open||!stageVisible||!dialog.current)return;opener.current=document.activeElement;dialog.current.showModal();return()=>{dialog.current?.close();if(opener.current instanceof HTMLElement&&opener.current.isConnected&&opener.current.getClientRects().length)opener.current.focus({preventScroll:true})}},[mobile,open,stageVisible]);
 const content=<><button type="button" className="secondary review-panel-close" onClick={onClose}>Đóng panel góp ý</button><fieldset disabled={disabled} className="review-panel-fields">{children}</fieldset></>;
 if(mobile)return <><span hidden ref={marker}/>{createPortal(<dialog ref={dialog} className="review-sheet" aria-label={label} onCancel={e=>{e.preventDefault();onClose()}}>{content}</dialog>,document.body)}</>;
 return <><span hidden ref={marker}/><aside className="review-side-panel" aria-label={label} hidden={!open||!stageVisible}>{content}</aside></>;
}
