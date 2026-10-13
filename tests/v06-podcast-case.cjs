const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),material=process.env.PODCAST_CASE_PATH;
if(!material)throw Error('Set PODCAST_CASE_PATH to the private Markdown notes. The full notes are not distributed with this project.');
const artifacts=process.env.TEST_ARTIFACT_DIR||path.join(root,'data/test-artifacts/v06-'+Date.now());fs.mkdirSync(artifacts,{recursive:true});
const text=fs.readFileSync(material,'utf8'),parts=text.split(/\n\s*\n/).map(x=>x.trim()).filter(Boolean);
const cases=[
 ['41:09–42:07','信用流向居民与地方政府，是检验价格拐点能否扩散的待验证条件。','financial','居民信用是否改善？先区分余额同比与新增贷款。','价格改善而居民信用持续偏弱，不能推出全面复苏。'],
 ['33:51–34:34','汽车产业的价值可能更多留在电池环节；需要公司层面的利润与回款验证。','business','汽车与电池企业的定价能力、分部利润和现金流是否支持该判断？','电芯降价、产能过剩或现金回款恶化都可能削弱判断。'],
 ['38:18–39:30','上游涨价向汽车与电池传导的程度，取决于议价能力、合同和库存周期。','business','传导指数的定义、样本和计算窗口是什么？','未提供公式，不能按小于1自动筛出行业名单。'],
 ['25:38–26:17','持续高油价可能推动2027年农产品价格，是需要追踪的预测。','inflation','应选择哪种油价基准，农业成本与供需是否支持传导？','能源回落或农产品供给增加，会削弱价格上涨预测。'],
 ['40:25–41:09','涨价品类扩散收窄，是对全面价格回升叙事的反向线索。','inflation','需要哪些分项价格序列、覆盖范围和窗口核实扩散？','没有分项数量与统一窗口，暂不能认定拐点已经逆转。'],
 ['08:44–09:32','材料报告8月PPI同比3.8%；数字需与同期间同口径原始发布核对。','inflation','是否为2026年8月全国工业生产者出厂价格同比？','不能把环比、购进价格或其他月份当成该值。']
];
(async()=>{fs.mkdirSync(path.join(root,'data/podcast-case'),{recursive:true});const b=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});try{
const context=await b.newContext({viewport:{width:1440,height:1050}}),p=await context.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));assert.equal((await p.goto('http://127.0.0.1:8765')).status(),200);await p.waitForFunction(()=>online);
const click=async(a)=>p.locator(`[data-action="${a}"]`).first().click(),close=async()=>p.getByRole('button',{name:'关闭',exact:true}).click(),shot=async(name)=>p.screenshot({path:path.join(artifacts,name+'.png'),fullPage:!(await p.locator('#dialog').evaluate(e=>e.open))});
await p.locator('[data-route="reader"]').first().click();await p.locator('#source-file').setInputFiles(material);await p.waitForFunction(n=>document.querySelector('#source-text').value.length===n,text.length);assert(text.length>20000);await p.locator('#source-title').fill('十分吸引 EP.02：中国走出通缩了吗（用户纪要，未核音频）');await shot('01-import');await click('reader-next');
for(let i=0;i<cases.length;i++){const [time,claim,node,q,counter]=cases[i];const ix=parts.findIndex(x=>x.startsWith('#')&&x.includes(time));assert(ix>=0);await p.locator('#source-segment').selectOption(String(ix+2));await p.locator('#claim').fill(claim);await p.locator('#target-node').selectOption(node);await p.locator('#question').fill(q);await p.locator('#counter').fill(counter);await click('reader-check');await p.locator('#track-topic').uncheck();await click('reader-save');if(i<cases.length-1)await p.locator('#another').click();else await close();}
let ids=await p.evaluate(()=>state.entries.map(e=>e.id));assert.equal(ids.length,6);assert.equal(await p.evaluate(id=>researchOf(state.entries.find(e=>e.id===id)).timestamp,ids[1]),cases[1][0]);
await p.locator('[data-route="inbox"]').first().click();await click('focus-edit');await p.locator('#focus-input').fill('信用,汽车,电池');await p.locator('#focus-save').click();assert.match(await p.locator('.research-entry').first().innerText(),/汽车|电池/);await shot('02-inbox');
const open=async id=>{await p.locator('[data-route="inbox"]').first().click();await p.locator(`[data-action="research-detail"][data-entry="${id}"]`).click();};
await open(ids[1]);await p.locator('#research-path').fill('原材料价格变化：先拆品种与期间\n采购成本：考虑合同及库存滞后\n中游议价能力：需核定价和竞争格局\n汽车与电池利润、回款：统一报告期\n候选公司比较：不把产业叙事当成盈利事实');await p.locator('#research-save').click();await close();
for(const c of [
 ['宁德时代','300750','动力与储能电池','材料点名；核查汽车电池盈利与回款，不把储能收入混为汽车。来源 https://www.catl.com/about/profile/'],
 ['比亚迪','002594','整车与电池一体化','材料点名；需要拆分整车、电池及内部配套口径。来源 https://www.bydglobal.com/cn/Investor/InvestorAnnals.html'],
 ['亿纬锂能','300014','电池业务比较样本','研究者补充，不是播客点名，也未认定为腰部或低开工率公司；核查业务结构及可比性。公司公开报告入口 https://www.evebattery.com/']
]){await open(ids[1]);await click('add-company');for(const [f,v]of [['name',c[0]],['code',c[1]],['role',c[2]],['reason',c[3]]])await p.locator('#company-'+f).fill(v);await p.locator('#save-company').click();}
await shot('03-companies');await open(ids[1]);await shot('04-chain');await close();
const checks=[
 [5,'PPI同比','3.8','%','2026-08','cn_ppi','待核实','先核对国家统计局2026-09-09发布；同比、环比不可混用。','https://www.stats.gov.cn/zwfwck/sjfb/202609/t20260909_1965262.html'],
 [1,'汽车产能利用率','70.8','%','2026-Q2','','原始发布抽样一致','核查原始发布的汽车制造业季度值；不能推出任一公司的利用率。','https://www.stats.gov.cn/sj/zxfbhjd/202607/t20260715_1964130.html'],
 [1,'汽车指数涨幅','30 / 20','%','近10个月 / 2026年1—8月','','口径不同 · 不可直接比较','两个时间窗口不同，指数名称仍待核；不直接标为矛盾。',''],
 [1,'韩国销量表述','3000 / 3002','辆','材料未明确同一期间','','可能取整 · 待核原始值','近似值与精确值可能共存，待核统计月份与来源。',''],
 [1,'库存天数','74','天','材料未明确','','待核实','需核厂家或经销商、样本、计算方法与日期。库存预警指数不能代替库存天数。','https://www.cada.cn/Data/list_85_1.html'],
 [0,'美国10年名义收益率','4.84','%','2026-09-09','dgs10','待核实','材料称昨夜盘中；日度收益率不能直接否定盘中报价，也不能用实际收益率替代。','https://fred.stlouisfed.org/series/DGS10'],
 [2,'PPI传导指数','<1','指数','定义与窗口待提供','','缺少定义或公式','没有可复现的公式、样本和数据源，因此不生成小于1行业清单。',''],
 [1,'份额与其余公司表述','64 / <30','%','样本与期间待核','','待核实','先核分母、是否全部企业以及数值是否取整；同口径下才可检查加总。','']
];
const catalog=await p.evaluate(()=>remote.catalog.map(s=>s.id));
for(const [idx,label,value,unit,period,series,status,reason,url]of checks){await open(ids[idx]);await p.locator('[data-action="entry-check"]:not([data-check])').click();for(const [k,v]of Object.entries({label,value,unit,period,reason,url}))await p.locator('#check-'+k).fill(v);await p.locator('#check-status').selectOption(status);if(series){let sid=series==='dgs10'?catalog.find(x=>x.toLowerCase().includes('dgs10')):series;assert(sid,'Missing nominal yield source');await p.locator('#check-series').selectOption(sid);}await p.locator('#check-save').click();if(series)await p.locator('[data-action="check-series"]').last().click();await close();}
await open(ids[1]);await p.getByRole('heading',{name:'3. 数据与口径核查'}).scrollIntoViewIfNeeded();await shot('05-checks');await close();
for(const [idx,title,rule,due]of [
 [0,'核对居民信用的统一口径','先记录人民银行居民贷款余额及可比基期；同比是否转正仅为研究者设定的观察条件，不等于复苏成立。来源不足时保持待核查。','2026-10-12'],
 [3,'固定油价基准与农业传导条件','先确认Brent或WTI、现货或期货，再观察成本、种植与供需；中高位阈值暂不设定，不任填X。2027涨价是预测。','2026-11-12'],
 [4,'核查涨价品类的扩散方向','收集同样本同窗口的分项价格；下降是对广泛复苏的反向线索，不能由总PPI代替扩散指标。','2026-10-12']
]){await open(ids[idx]);await click('entry-watch');await p.locator('#entry-watch-words').fill(idx===0?'居民,信贷':idx===3?'油价,原油,农产品':'PPI,价格');await p.locator('#entry-watch-save').click();await p.locator('[data-action="new-milestone"]').last().click();await p.locator('#milestone-title').fill(title);await p.locator('#milestone-rule').fill(rule);await p.locator('#milestone-due').fill(due);await p.locator('#milestone-add').click();}
await shot('06-watches');await p.locator('[data-action="milestone"]').last().click();await p.locator('#m-status').selectOption('出现反证');await p.locator('#m-evidence').fill('用户纪要40:25–41:09提到涨价品类减少，记录为对全面回升的反向线索；尚无分项数据验证，不足以判定整体假设失效。');await p.locator('#m-save').click();
await open(ids[1]);await click('edit-entry');await p.locator('#edit-claim').fill('电池可能比整车有更强的价值获取能力，但纪要34:34–35:19同时提示电芯降价与产能过剩；必须分公司核实，不能泛化为电池企业普遍受益。');await p.locator('#edit-reason').fill('同篇纪要34:34–35:19构成反向线索；保留原判断及来源，并收紧适用边界。');await p.locator('#review-change').click();await shot('07-revision');await p.locator('#accept-change').click();
await p.locator('[data-route="inbox"]').first().click();await p.setViewportSize({width:390,height:844});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.locator('#toast').waitFor({state:'hidden'}).catch(()=>{});await shot('08-mobile');await p.setViewportSize({width:1440,height:1050});
const downloadEvent=p.waitForEvent('download');await p.locator('#export').click();const download=await downloadEvent,backup=path.join(root,'data/podcast-case/ep02-private-backup.json');await download.saveAs(backup);
await p.reload();assert.equal(await p.evaluate(()=>state.entries.length),6);assert.equal(await p.evaluate(()=>state.entries[1].version),2);
const q=await (await b.newContext()).newPage();await q.goto('http://127.0.0.1:8765');await q.locator('[data-route="settings"]').first().click();await q.locator('[data-action="restore"]').click();await q.locator('#backup-file').setInputFiles(backup);await q.locator('#restore-confirm').click();await q.waitForFunction(()=>!document.querySelector('#dialog').open);assert.equal(await q.evaluate(()=>state.entries.length),6);assert.equal(await q.evaluate(()=>state.companies.filter(c=>c.originEntryIds?.length).length),3);assert.equal(await q.evaluate(()=>state.watches.length),3);assert.equal(await q.evaluate(()=>state.entries.reduce((n,e)=>n+e.research.checks.length,0)),8);assert.equal(await q.evaluate(()=>state.focusKeywords),'信用,汽车,电池');assert.deepEqual(errors,[]);
const result=await p.evaluate(()=>({entries:state.entries.length,companies:state.companies.length,watches:state.watches.length,checks:state.entries.flatMap(e=>e.research.checks).map(c=>({label:c.label,status:c.status,reason:c.reason})),timestamps:state.entries.map(e=>e.research.timestamp),versions:state.entries.map(e=>e.version)}));fs.writeFileSync(path.join(root,'data/podcast-case/verification.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));console.log('PASS: full private material import, six archives, priority ordering, three linked companies, eight checks, three milestones, revision, export/restore, reload and mobile.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1)});
