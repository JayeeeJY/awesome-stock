import {fileURLToPath} from 'node:url';import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const root=path.dirname(fileURLToPath(import.meta.url)),dist=path.join(root,'dist');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
function walk(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>{const p=path.join(dir,e.name);if(e.isSymbolicLink())throw Error('Symlink build input');return e.isDirectory()?walk(p):e.isFile()?[p]:[]}).sort()}
const assets=walk(dist).filter(p=>path.basename(p)!=='UI_BUILD_MANIFEST.json').map(p=>({path:path.relative(dist,p).split(path.sep).join('/'),sha256:hash(p)}));
const sources=[...walk(path.join(root,'src')),...walk(path.join(root,'public')),...['package.json','package-lock.json','vite.config.ts','tsconfig.json','index.html','write-build-manifest.mjs'].map(p=>path.join(root,p))].sort().map(p=>({path:path.relative(root,p).split(path.sep).join('/'),sha256:hash(p)}));
fs.writeFileSync(path.join(dist,'UI_BUILD_MANIFEST.json'),JSON.stringify({format:'awesome-owner-ui-build-v1',assets,sources},null,2)+'\n');
