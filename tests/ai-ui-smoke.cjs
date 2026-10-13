// Simulated model response only. No keys, network model calls, or real quality claim.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.route('**/api/state',r=>r.fulfill({json:{sources:{},catalog:[],ai:{configured:true,host:'example.test',model:'mock'}}}));
let release,started=false;
await page.route('**/api/analyze',async r=>{started=true;await new Promise(resolve=>{release=resolve});await r.fulfill({json:{suggestions:[{node:'policy',segment:1,quote:'政策尚未执行',claim:'材料指出政策尚未执行。',question:'是否有执行安排？',counter:'公开执行安排出现。',keywords:'policy'}]}});});
await page.goto('http://127.0.0.1:8765');await page.waitForFunction(()=>document.querySelector('#connection').textContent.includes('已连接'));
await page.locator('[data-route="reader"]').first().click();await page.locator('#source-title').fill('测试材料');await page.locator('#source-text').fill('政策尚未执行。');await page.locator('[data-action="reader-next"]').click();await page.locator('[data-action="ai"]').click();
await page.waitForFunction(()=>document.querySelector('[data-action="ai"]').disabled);
await page.locator('[data-action="reader-back"]').click();await page.locator('#source-text').fill('这已是一份不同的材料。');
release();await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('旧结果未应用'));
assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('guanlan-workbench-v2')).draft.claim),'');
await page.locator('#source-text').fill('政策尚未执行。');await page.locator('[data-action="reader-next"]').click();await page.locator('[data-action="ai"]').click();
// Wait until the second intercepted request provides its own release callback.
await page.waitForFunction(()=>document.querySelector('[data-action="ai"]').textContent.includes('分析中'));
await new Promise(r=>setTimeout(r,100));release();
await page.waitForFunction(()=>document.querySelector('#claim').value.includes('材料指出'));
assert.equal(await page.locator('#target-node').inputValue(),'policy');
assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('guanlan-workbench-v2')).entries.length),0);
await page.locator('[data-action="reader-check"]').click();await page.locator('[data-action="reader-save"]').click();
assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('guanlan-workbench-v2')).entries.length),1);
assert.deepEqual(errors,[]);await browser.close();console.log('PASS (mock model only): configured AI UI, delayed-result guard, suggestion editing, user confirmation before persistence.');
})().catch(e=>{console.error(e);process.exit(1)});
