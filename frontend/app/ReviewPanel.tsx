"use client";
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
export function ReviewPanel({open,onClose,label,children,disabled=false}:{disabled?:boolean;open:boolean;onClose:()=>void;label:string;children:ReactNode}){
 const [mobile,setMobile]=useState(false);const dialog=useRef<HTMLDialogElement>(null);
 const opener=useRef<Element|null>(null);
 useEffect(()=>{const media=matchMedia('(max-width:1000px)');const update=()=>setMobile(media.matches);update();media.addEventListener('change',update);return()=>media.removeEventListener('change',update)},[]);
 useEffect(()=>{if(!mobile||!open||!dialog.current)return;opener.current=document.activeElement;dialog.current.showModal();return()=>{dialog.current?.close();if(opener.current instanceof HTMLElement&&opener.current.isConnected)opener.current.focus({preventScroll:true})}},[mobile,open]);
 const content=<><button type="button" className="secondary review-panel-close" onClick={onClose}>Đóng panel góp ý</button><fieldset disabled={disabled} className="review-panel-fields">{children}</fieldset></>;
 if(mobile)return open?createPortal(<dialog ref={dialog} className="review-sheet" aria-label={label} onCancel={e=>{e.preventDefault();onClose()}}>{content}</dialog>,document.body):null;
 return <aside className="review-side-panel" aria-label={label} hidden={!open}>{content}</aside>;
}
