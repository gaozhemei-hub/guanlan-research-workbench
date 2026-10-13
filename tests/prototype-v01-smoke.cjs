// Run with NODE_PATH pointing to a runtime that provides playwright.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.PROTOTYPE_URL||'http://127.0.0.1:8765');
 const read=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('guanlan-prototype-v1')));
 assert.equal((await read()).records.length,2);
 await page.screenshot({path:path.join(__dirname,'../prototype/desktop-preview.png'),fullPage:true});
 await page.locator('[data-source="ai-s1"][data-segment="2"]').first().click();
 assert(await page.locator('#seg-2').evaluate(e=>e.classList.contains('selected')));
 await page.getByRole('button',{name:'关闭',exact:true}).click();
 const before=(await read()).records[0].claim;
 await page.locator('#update').click();await page.locator('#sample-update').click();await page.locator('#save-update').click();
 assert.equal((await read()).records[0].claim,before,'Pending update must not mutate live claim');
 await page.locator('#accept-update').click();
 assert.equal((await read()).records[0].version,2);
 assert.notEqual((await read()).records[0].claim,before);
 await page.reload();assert.equal((await read()).records[0].version,2);
 // Create a pending proposal, edit current claim, verify stale proposal cannot apply.
 await page.locator('#update').click();await page.locator('#update-claim').fill('测试：一个不同的待审判断');await page.locator('#update-reason').fill('验证版本冲突');await page.locator('#e-source').selectOption('ai-s1');await page.locator('#e-segment').fill('3');await page.locator('#save-update').click();await page.getByRole('button',{name:'关闭',exact:true}).click();
 await page.locator('#edit-claim').click();await page.locator('#claim').fill('测试：记录已经独立修改');await page.locator('#save-claim').click();await page.locator('#update').click();assert.equal(await page.locator('#accept-update').count(),0);await page.locator('#reject-update').click();
 await page.locator('[data-tab="evidence"]').click();await page.locator('[data-signal="0"]').click();await page.locator('#signal-state').selectOption('支持假设');await page.locator('#save-signal').click();assert.match(await page.locator('#signal-error').innerText(),/理由/);await page.getByRole('button',{name:'关闭',exact:true}).click();
 await page.locator('[data-tab="leads"]').click();assert.match(await page.locator('#panel').innerText(),/暂时没有公司/);
 // User source preserves literal text and never becomes executable markup.
 await page.locator('#import').click();await page.locator('#source-title').fill('测试来源');await page.locator('#source-text').fill('第一段。\n\n<img src=x onerror="window.injected=true">');await page.locator('#save-source').click();assert.equal((await read()).records.length,3);await page.locator('[data-source]').first().click();assert.match(await page.locator('#dialog').innerText(),/<img/);assert.equal(await page.evaluate(()=>window.injected),undefined);await page.getByRole('button',{name:'关闭',exact:true}).click();
 const dl=page.waitForEvent('download');await page.locator('#export').click();assert.match((await dl).suggestedFilename(),/\.json$/);
 // Imported UTF-8 file.
 await page.locator('#import').click();await page.locator('#source-file').setInputFiles({name:'文件测试.md',mimeType:'text/markdown',buffer:Buffer.from('第一段正文。\n\n第二段正文。')});await page.waitForFunction(()=>document.querySelector('#source-text').value.length>0);await page.locator('#save-source').click();assert.equal((await read()).records.length,4);
 await page.reload();assert.equal((await read()).records.length,4);
 await page.setViewportSize({width:390,height:844});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),'Mobile overflow');
 await page.screenshot({path:path.join(__dirname,'../prototype/mobile-preview.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 console.log('PASS: seeded cases, citation anchor, staged update, confirmation, persistence, stale-version block, evidence validation, empty candidates, escaped import, JSON export, UTF-8 file, mobile overflow; no browser JS errors.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
