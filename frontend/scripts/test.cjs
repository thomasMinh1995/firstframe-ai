const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),output=fs.mkdtempSync(path.join(os.tmpdir(),'firstframe-tests-'));
function run(args){
 const result=spawnSync(process.execPath,args,{cwd:root,stdio:'inherit',env:{...process.env,NODE_PATH:path.join(root,'node_modules')}});
 if(result.error)throw result.error;
 if(result.status!==0)throw Error(`Check failed (${result.status}): ${args[0]}`);
}
try{
 run(['node_modules/typescript/lib/tsc.js','--outDir',output,'--noEmit','false','--module','commonjs','--moduleResolution','node','--target','es2020','--lib','esnext,dom,dom.iterable','--jsx','react-jsx','--esModuleInterop','--skipLibCheck','app/Workspace.tsx','app/draftWorkflowState.ts','app/OnboardingTour.tsx']);
 const suites=fs.readdirSync(path.join(root,'tests')).filter(file=>file.endsWith('.cjs')&&!file.endsWith('.browser.cjs')&&!file.endsWith('browser-helpers.cjs')).sort();
 for(const suite of suites)run([path.join('tests',suite),output]);
 console.log(`${suites.length} frontend suites passed`);
}catch(error){console.error(error.message);process.exitCode=1}finally{fs.rmSync(output,{recursive:true,force:true})}
