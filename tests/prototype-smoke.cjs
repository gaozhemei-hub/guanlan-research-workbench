const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.PROTOTYPE_URL||'http://127.0.0.1:8765');
 await page.waitForFunction(()=>document.querySelector('#connection').textContent.includes('已连接'));
 const read=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('guanlan-workbench-v2')));
 assert.equal((await read()).entries.length,0);
 await page.screenshot({path:path.join(__dirname,'../prototype/desktop-preview.png'),fullPage:true});
 await page.locator('[data-action="demo"]').click();
 await page.locator('[data-action="reader-next"]').click();
 assert.equal(await page.locator('#target-node').inputValue(),'policy');
 assert(await page.locator('[data-action="ai"]').isDisabled());
 await page.locator('[data-action="reader-check"]').click();
 assert.equal((await read()).entries.length,0,'Nothing committed before confirmation');
 await page.locator('[data-action="reader-save"]').click();
 let state=await read();assert.equal(state.entries.length,1);assert.equal(state.watches.length,1);
 assert.equal(state.entries[0].node,'policy');assert.equal(state.entries[0].segment,2);
 await page.locator('#view-archived').click();
 assert.match(await page.locator('#page').innerText(),/我的证据/);
 await page.locator('[data-action="source"]').click();
 assert(await page.locator('#seg-2').evaluate(e=>e.classList.contains('selected')));
 await page.getByRole('button',{name:'关闭',exact:true}).click();
 await page.locator('[data-action="edit-entry"]').click();
 const original=(await read()).entries[0].claim;
 await page.locator('#edit-claim').fill('测试：先核对政策是否落地，不从话题热度推导结论。');
 await page.locator('#edit-reason').fill('补充对执行环节的核验条件。');
 await page.locator('#review-change').click();
 assert.equal((await read()).entries[0].claim,original);
 await page.locator('#accept-change').click();
 assert.equal((await read()).entries[0].version,2);
 await page.reload();assert.equal((await read()).entries[0].version,2);
 // Explicitly start a new draft. Previous archive and source remain intact.
 await page.locator('[data-route="reader"]').first().click();
 await page.locator('[data-action="new-source"]').click();
 if(await page.locator('#clear-draft').count())await page.locator('#clear-draft').click();
 await page.locator('#source-title').fill('不执行 HTML');
 await page.locator('#source-file').setInputFiles({name:'本地笔记.md',mimeType:'text/markdown',buffer:Buffer.from('黄金需求尚待验证。\n\n<img src=x onerror="window.injected=true">')});
 await page.waitForFunction(()=>document.querySelector('#source-text').value.includes('<img'));
 await page.locator('[data-action="reader-next"]').click();
 await page.locator('#source-segment').selectOption('2');
 assert.equal(await page.evaluate(()=>window.injected),undefined);
 await page.locator('[data-action="reader-check"]').click();
 assert.match(await page.locator('#reader-error').innerText(),/请填写/);
 await page.locator('#claim').fill('来源中的这段文本没有提供可验证的数字。');
 await page.locator('#question').fill('查找原始数据出处。');
 await page.locator('#counter').fill('有可靠来源给出可重复验证的数据。');
 await page.locator('#target-node').selectOption('gold');
 await page.locator('[data-action="reader-check"]').click();
 await page.locator('[data-action="reader-save"]').click();
 await page.locator('#view-archived').click();
 assert.equal((await read()).entries.length,2);
 assert.equal((await read()).entries[1].demo,false);
 // Create a company and calculate real indicators from an explicitly synthetic test CSV.
 await page.locator('[data-route="companies"]').first().click();
 await page.locator('[data-action="add-company"]').first().click();
 await page.locator('#company-name').fill('测试公司（仅测试）');
 await page.locator('#company-code').fill('000001');
 await page.locator('#company-role').fill('测试角色');
 await page.locator('#company-reason').fill('自动测试，不是真实证券资料。');
 await page.locator('#save-company').click();
 await page.locator('[data-action="company-prices"]').click();
 const csv='date,close\n'+Array.from({length:50},(_,i)=>`${new Date(Date.UTC(2026,0,1+i)).toISOString().slice(0,10)},${100+i}`).join('\n');
 await page.locator('#price-file').setInputFiles({name:'test.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
 await page.locator('#price-source').fill('自动测试合成序列');
 await page.locator('#calculate').click();
 await page.waitForFunction(()=>!document.querySelector('#dialog').open);
 state=await read();assert.equal(state.companies[0].technical.close,149);
 assert.equal(state.companies[0].technical.ma20,139.5);
 assert.equal(state.companies[0].technical.rsi14,100);
 assert.equal(state.companies[0].technical.rows,50);
 // Backups are downloadable. Source export preserves escaped, non-executable content.
 const dl=page.waitForEvent('download');await page.locator('#export').click();assert.match((await dl).suggestedFilename(),/\.json$/);
 // All routes render at desktop and mobile; no horizontal overflow.
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:width===390?844:1050});
  for(const area of ['home','macro','metals','companies','narrative','reader','settings']){
   await page.locator(`[data-route="${area}"]`).first().click();
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),`Overflow: ${area}/${width}`);
  }
 }
 await page.locator('[data-route="home"]').first().click();
 await page.screenshot({path:path.join(__dirname,'../prototype/mobile-preview.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 // Legacy v1 data stays untouched while exposed via the retained backup.
 const legacyPage=await browser.newPage();
 await legacyPage.addInitScript(()=>localStorage.setItem('guanlan-prototype-v1',JSON.stringify({schema:1,records:[{id:'old',title:'旧记录',claim:'原判断',sources:[{text:'原材料'}]}]})));
 await legacyPage.goto('http://127.0.0.1:8765');
 assert.equal(await legacyPage.evaluate(()=>JSON.parse(localStorage.getItem('guanlan-prototype-v1')).records[0].claim),'原判断');
 assert.equal(await legacyPage.evaluate(()=>JSON.parse(localStorage.getItem('guanlan-workbench-v2')).legacy.records[0].title),'旧记录');
 console.log('PASS: archive approval, source anchors, version confirmation/history, persistence, UTF-8 import, injection escaping, required fields, company CSV/TA-Lib, JSON export, 7 routes desktop/mobile, legacy preservation; no JS errors.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
