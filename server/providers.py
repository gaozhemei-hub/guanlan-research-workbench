"""Public-source catalog. AKShare handles upstream parsing, this app owns semantics."""
AK_SOURCES = [
 dict(id='cn_m2',kind='series',driver='akshare',name='中国 M2 同比',unit='%',deltaUnit='个百分点',frequency='月度 · 货币和准货币同比',nodes=['financial'],url='https://data.eastmoney.com/cjsj/hbgyl.html',provider='人民银行数据 / 东方财富，经 AKShare',note='M2 是货币存量指标，不等同于新增社融或某个部门实际获得的融资。'),
 dict(id='cn_pmi',kind='series',driver='akshare',name='中国制造业 PMI',unit='指数',deltaUnit='点',frequency='月度 · 指数水平',nodes=['growth'],url='https://data.eastmoney.com/cjsj/pmi.html',provider='国家统计局数据 / 东方财富，经 AKShare',note='50 为扩张与收缩的参考分界，不是同比增速。'),
 dict(id='cn_cpi',kind='series',driver='akshare',name='中国 CPI 同比',unit='%',deltaUnit='个百分点',frequency='月度 · 全国居民消费价格同比',nodes=['inflation'],url='https://data.eastmoney.com/cjsj/cpi.html',provider='国家统计局数据 / 东方财富，经 AKShare',note='显示全国同比涨幅，未将指数水平、同比与环比混用。'),
 dict(id='sge_gold',kind='series',driver='akshare',name='上金所 Au99.99 收盘价',unit='元/克',deltaUnit='元/克',frequency='交易日 · 人民币实物合约',nodes=['gold'],url='https://www.sge.com.cn/sjzx/mrhq',provider='上海黄金交易所 / AKShare',note='Au99.99 是实物合约报价；不是国际美元金价，也不是矿企实现售价。'),
 dict(id='sge_silver',kind='series',driver='akshare',name='上金所 Ag(T+D) 收盘价',unit='元/千克',deltaUnit='元/千克',frequency='交易日 · 人民币延期交收合约',nodes=['silver'],url='https://www.sge.com.cn/sjzx/mrhq',provider='上海黄金交易所 / AKShare',note='Ag(T+D) 是延期交收合约；不能当作工业银现货成交均价。'),
 dict(id='news_cls',kind='feed',driver='akshare',name='财联社 · 电报',nodes=[],url='https://www.cls.cn/telegraph',provider='财联社 / AKShare',note='返回近期快讯；按标题与内容中的关键词分类，原接口未保留单篇链接。'),
 dict(id='news_sina',kind='feed',driver='akshare',name='新浪财经 · 7×24',nodes=[],url='https://finance.sina.com.cn/7x24',provider='新浪财经 / AKShare',note='返回近期快讯；没有独立标题时显示短句截取，链接指向来源列表。'),
 dict(id='news_em',kind='feed',driver='akshare',name='东方财富 · 财经快讯',nodes=[],url='https://kuaixun.eastmoney.com/7_24.html',provider='东方财富 / AKShare',note='宽源信息按研究节点过滤；转载不等于独立证据。'),
 dict(id='news_gold_company',kind='feed',driver='akshare',name='山东黄金 · 公司新闻样本',nodes=['gold','business'],url='https://so.eastmoney.com/news/s?keyword=600547',provider='东方财富个股检索 / AKShare',symbol='600547',note='预置公司新闻检索样本，不是推荐或个人自选。检索排序不保证覆盖所有最新公告。'),
 dict(id='news_silver_company',kind='feed',driver='akshare',name='盛达资源 · 公司新闻样本',nodes=['silver','business'],url='https://so.eastmoney.com/news/s?keyword=000603',provider='东方财富个股检索 / AKShare',symbol='000603',note='预置公司新闻检索样本，不是推荐或个人自选。检索排序不保证覆盖所有最新公告。'),
]
KEYWORDS = {
 'growth':['GDP','PMI','经济增长','消费','就业','出口','工业增加值','经济数据','制造业'],
 'inflation':['CPI','PPI','PCE','通胀','物价','油价','原油','inflation'],
 'policy':['政策','国务院','关税','财政','监管','美联储','央行','FOMC','DSA','提案'],
 'financial':['利率','美元','降息','加息','社融','贷款','货币','流动性','美联储','国债'],
 'gold':['黄金','金价','购金','金矿','gold','避险需求','山东黄金'],
 'silver':['白银','银价','银矿','光伏','耗银','盛达资源','silver'],
 'business':['公司','股份','公告','财报','产量','营收','利润','回购','资本开支'],
 'valuation':['估值','市盈率','市净率','盈利预测','业绩预告'],
 'technical':['股价','涨停','跌停','均线','成交量','换手率'],
 'narrative':['预期','技术路线','替代','突破','共识','量产','市场空间','银包铜','无银','低银'],
}

AK_SOURCES += [
 dict(id='cn_ppi',kind='series',driver='akshare',name='中国 PPI 同比',unit='%',deltaUnit='个百分点',frequency='月度 · 工业生产者出厂价格同比',nodes=['inflation'],url='https://data.eastmoney.com/cjsj/ppi.html',provider='国家统计局数据 / 东方财富，经 AKShare',note='总量同比，不代表贵金属或单个行业价格；不是指数水平。'),
 dict(id='cn_credit',kind='series',driver='akshare',name='中国社会融资规模增量',unit='亿元',deltaUnit='亿元',frequency='月度 · 当月增量',nodes=['financial'],url='https://data.mofcom.gov.cn/gnmy/shrzgm.shtml',provider='商务数据中心转录 / AKShare',note='当月流量，不是社融存量或同比增速；月间有季节性，需与上年同月比较。此接口分项不完整，不能加总成完整融资结构。'),
 dict(id='cn_lpr',kind='series',driver='akshare',name='中国 1 年期 LPR',unit='%',deltaUnit='个百分点',frequency='按报价发布日期',nodes=['policy','financial'],url='https://data.eastmoney.com/cjsj/globalRateLPR.html',provider='东方财富 / AKShare',note='贷款市场报价利率，不等同于央行政策利率或企业实际贷款利率。'),
]
for code,name,market in [('600547','山东黄金','SH'),('000603','盛达资源','SZ'),('300750','宁德时代','SZ'),('002594','比亚迪','SZ'),('300014','亿纬锂能','SZ')]:
 AK_SOURCES.append(dict(id='finance_'+code,kind='financial',driver='akshare',name=name+' · 财务指标',symbol=code+'.'+market,company=name,nodes=['business'],url='https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code='+market+code+'&color=b#/cwfx',provider='东方财富财务分析 / AKShare',note='公开财务研究样本；不是自选股或推荐。利润表指标按年初至报告期末累计，资产负债率为期末；缺失值留空，未年化。'))

AK_SOURCES += [
 dict(id='etf_gold',kind='series',driver='akshare',name='SPDR Gold Trust · 黄金持有量',unit='吨',deltaUnit='吨',frequency='日度 · 单只基金持有量',nodes=['gold'],url='https://datacenter.jin10.com/reportType/dc_etf_gold',provider='金十转录 / AKShare',note='仅 SPDR Gold Trust（GLD），不代表全球黄金 ETF。吨数变化不等于美元资金净流入；以观察日期判断覆盖范围。'),
 dict(id='etf_silver',kind='series',driver='akshare',name='iShares Silver Trust · 白银持有量',unit='吨',deltaUnit='吨',frequency='日度 · 单只基金持有量',nodes=['silver'],url='https://datacenter.jin10.com/reportType/dc_etf_sliver',provider='金十转录 / AKShare',note='仅 iShares Silver Trust（SLV），不代表全球白银库存或全部 ETF。不能与交易所库存直接相加，以免重叠。'),
]
