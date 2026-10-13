const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
const p=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
await p.goto('http://127.0.0.1:8765');await p.waitForFunction(()=>document.querySelector('#connection').textContent.includes('已连接'));
const remote=await p.evaluate(()=>fetch('/api/state').then(r=>r.json()));
assert.deepEqual(await p.evaluate(()=>{const previous=remote;remote={sources:{a:{id:'a',kind:'feed',items:[{id:'a1',dedupKey:'same',feedId:'a',source:'A',nodes:['gold']}]},b:{id:'b',kind:'feed',items:[{id:'b1',dedupKey:'same',feedId:'b',source:'B',nodes:['silver']}]}}};const result=allNews();remote=previous;return {count:result.length,feeds:result[0].feedIds.sort()};}),{count:1,feeds:['a','b']});
for(const id of ['cn_pmi','cn_cpi','cn_m2','sge_gold','sge_silver','news_cls','news_sina','news_em','news_gold_company','news_silver_company']){assert.equal(remote.sources[id].status,'ok',id);assert((remote.sources[id].points||remote.sources[id].items).length>0);}
await p.locator('[data-route="macro"]').first().click();await p.locator('[data-node="growth"]').first().click();await p.locator('[data-tab="data"]').click();assert.match(await p.locator('#page').innerText(),/中国制造业 PMI/);assert.match(await p.locator('#page').innerText(),/观察月份/);
await p.locator('[data-route="metals"]').first().click();await p.locator('[data-node="silver"]').first().click();await p.locator('[data-tab="data"]').click();assert.match(await p.locator('#page').innerText(),/元\/千克/);assert.match(await p.locator('#page').innerText(),/延期交收/);
await p.screenshot({path:path.join(__dirname,'../prototype/silver-data-preview.png'),fullPage:true});
await p.locator('[data-tab="news"]').click();assert((await p.locator('#page .feed').count())>0);await p.screenshot({path:path.join(__dirname,'../prototype/news-preview.png'),fullPage:true});
await p.locator('#news-scope').selectOption('all');await p.locator('#news-source').selectOption('news_em');await p.locator('[data-action="filter-news"]').click();assert((await p.locator('#page .feed').count())>0);
await p.locator('#news-query').fill('不可能匹配的测试字符串123XYZ');await p.locator('[data-action="filter-news"]').click();assert.equal(await p.locator('#page .feed').count(),0);
await p.locator('[data-route="narrative"]').first().click();assert.equal(await p.locator('.template-card').count(),4);assert.equal(await p.evaluate(()=>state.watches.length),0);
await p.screenshot({path:path.join(__dirname,'../prototype/narrative-preview.png'),fullPage:true});
await p.locator('[data-action="template-detail"][data-template="silver-tech"]').click();assert.equal(await p.locator('.branch-grid section').count(),3);assert.match(await p.locator('#dialog').innerText(),/非原书原话/);await p.locator('#dialog [data-action="use-template"]').click();
assert.equal(await p.evaluate(()=>state.watches.length),0,'Template preview must not auto subscribe');
await p.locator('#watch-baseline').fill('测试：尚未取得可靠机构预测，只建立核查计划。');await p.locator('#save-watch').click();assert.equal(await p.evaluate(()=>state.watches.length),1);assert.equal(await p.locator('.milestone-list button').count(),3);
await p.locator('[data-action="milestone"]').first().click();await p.locator('#m-status').selectOption('出现反证');await p.locator('#m-save').click();assert.match(await p.locator('#m-error').innerText(),/依据/);
await p.locator('#m-evidence').fill('自动测试说明，不是真实证据：检查记录历史的行为。');await p.locator('#m-save').click();assert.equal(await p.evaluate(()=>state.watches[0].milestones[0].history.length),1);
await p.reload();await p.locator('[data-action="narrative-tab"][data-value="watches"]').click();assert.match(await p.locator('.milestone-list').innerText(),/出现反证/);
await p.setViewportSize({width:390,height:844});await p.locator('[data-action="narrative-tab"][data-value="library"]').click();assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.screenshot({path:path.join(__dirname,'../prototype/narrative-mobile-preview.png'),fullPage:true});
const offline=await browser.newPage();offline.on('pageerror',e=>errors.push(e.message));await offline.goto('file://'+path.resolve(__dirname,'../prototype/观澜-可交互原型.html'));
assert.match(await offline.locator('.snapshot-note').innerText(),/离线数据预览/);await offline.locator('[data-route="metals"]').first().click();await offline.locator('[data-tab="data"]').click();assert((await offline.locator('.metric').count())>0);await offline.locator('[data-tab="news"]').click();assert((await offline.locator('#page .feed').count())>0);
await offline.locator('[data-route="narrative"]').first().click();assert.equal(await offline.locator('.template-card').count(),4);
assert.deepEqual(errors,[]);await browser.close();console.log('PASS v0.3: 10 real AKShare sources, monthly period/contract units, classified news and filters, 4 templates, explicit adoption, milestone evidence/history/persistence, mobile, dated offline data/news; no JS errors.');
})().catch(e=>{console.error(e);process.exit(1)});
