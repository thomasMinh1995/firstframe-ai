const assert=require('node:assert/strict');
const {isComposingKey}=require(process.argv[2]+'/inputEvents.js');
for(const event of [
 {isComposing:true,keyCode:13},
 {isComposing:false,keyCode:229},
 {nativeEvent:{isComposing:true,keyCode:13}},
 {nativeEvent:{isComposing:false,keyCode:229}},
 {keyCode:229,nativeEvent:{isComposing:false}},
])assert.equal(isComposingKey(event),true,'IME keys must not trigger editor or Escape navigation');
for(const event of [{keyCode:13},{keyCode:27},{isComposing:false,nativeEvent:{isComposing:false,keyCode:13}},{}])assert.equal(isComposingKey(event),false,'normal Enter/Escape keep their existing behavior');
console.log('PASS IME key guard: native and React composition, Safari 229 fallback, normal Enter/Escape');
