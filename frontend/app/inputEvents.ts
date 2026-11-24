// Safari may report isComposing=false on the key that commits an IME candidate.
export function isComposingKey(event:{isComposing?:boolean;keyCode?:number;nativeEvent?:{isComposing?:boolean;keyCode?:number}}):boolean {
 return !!(event.isComposing||event.keyCode===229||event.nativeEvent?.isComposing||event.nativeEvent?.keyCode===229);
}
