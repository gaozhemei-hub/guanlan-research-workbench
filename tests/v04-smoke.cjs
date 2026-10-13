const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
 const b=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const p=await b.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 const response=await p.goto('http://127.0.0.1:8765');assert.equal(response.status(),200);await p.waitForFunction(()=>online);
 await p.locator('[data-route="macro"]').first().click();await p.locator('[data-node="inflation"]').click();await p.locator('[data-tab="data"]').click();assert.match(await p.locator('#page').innerText(),/中国 PPI 同比/);
 await p.locator('[data-node="financial"]').click();assert.match(await p.locator('#page').innerText(),/社会融资规模增量/);assert.match(await p.locator('#page').innerText(),/覆盖较旧/);await p.screenshot({path:path.join(__dirname,'../prototype/v04-macro.png'),fullPage:true});
 await p.locator('[data-route="companies"]').first().click();await p.locator('[data-tab="financials"]').click();await p.locator('#financial-period').selectOption('2025-06-30');assert.match(await p.locator('table').innerText(),/567.66/);assert.match(await p.locator('table').innerText(),/9.06/);assert.match(await p.locator('#page').innerText(),/每股经营现金流不能替代/);await p.screenshot({path:path.join(__dirname,'../prototype/v04-financials.png'),fullPage:true});
 await p.evaluate(()=>{remote.sources.finance_600547.status='stale';render()});assert.match(await p.locator('#page').innerText(),/旧缓存/);assert.match(await p.locator('table').innerText(),/567.66/);
 await p.evaluate(()=>{remote.sources.finance_000603.reports=remote.sources.finance_000603.reports.filter(r=>r.period!=='2025-06-30');render()});assert.match(await p.locator('table').innerText(),/本期缺失/);
 await p.setViewportSize({width:390,height:844});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 const f=await b.newPage();await f.goto('file://'+path.resolve(__dirname,'../prototype/观澜-可交互原型.html'));await f.locator('[data-route="companies"]').first().click();await f.locator('[data-tab="financials"]').click();assert.equal(await f.locator('tbody tr').count(),7);assert.match(await f.locator('.snapshot-note').innerText(),/离线/);
 assert.deepEqual(errors,[]);await b.close();console.log('PASS v0.4: real macro/financial data, same-period units, stale cache, missing report, mobile and offline snapshot.');
})().catch(e=>{console.error(e);process.exit(1)});
