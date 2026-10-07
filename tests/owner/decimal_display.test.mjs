import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(new URL('../../frontend/owner-ui/package.json',import.meta.url));
const ts=require('typescript');
const source=await readFile(new URL('../../frontend/owner-ui/src/utils/decimal.ts',import.meta.url),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const {sum,compare,divide,percent,money}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
test('cash totals retain cents beyond the safe floating-point integer range',()=>{
 assert.equal(sum(['999999999999.12345678','0.00000001','-999999999999.12345678']),'0.00000001');
 assert.equal(sum(['9007199254740992.01','0.01']),'9007199254740992.02');
 assert.equal(compare('9007199254740992.01','9007199254740992.02'),-1);
});
test('formatting rounds half away from zero without changing saved decimal values',()=>{
 assert.equal(money('123456789012345678.995'),'123,456,789,012,345,679.00');
 assert.equal(money('-0.005'),'-0.01');assert.equal(money('100.001',4),'100.0010');
 assert.equal(money(null),'—');assert.equal(money('0.00000001',8),'0.00000001');
});
test('ratios have explicit undefined denominator and do not manufacture a value',()=>{
 assert.equal(divide('21','2'),'10.5');assert.equal(divide('1','0'),null);
 assert.equal(percent('1','4'),'25.00%');assert.equal(percent('0','0'),'—');
 assert.equal(sum(['0E-8','1E-8']),'0.00000001');assert.equal(sum(['1e6','1']),'1000001');
 assert.throws(()=>sum(['Infinity','1']),/Invalid decimal/);assert.throws(()=>sum(['1e999']),/Invalid decimal/);
});
