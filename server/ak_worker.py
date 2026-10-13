"""Isolated, bounded AKShare execution. No user accounts or browser cookies read."""
import sys,json,math,re,hashlib,html,contextlib
from datetime import datetime,date
from zoneinfo import ZoneInfo
from providers import AK_SOURCES,KEYWORDS

# Strip built-in tracking cookies from library requests. Preserve certificate verification.
import requests
original_request=requests.Session.request
def request(self,method,url,**kwargs):
    kwargs['timeout']=kwargs.get('timeout') or 12
    kwargs['headers']={k:v for k,v in (kwargs.get('headers') or {}).items() if k.lower()!='cookie'}
    kwargs.pop('cookies',None);self.cookies.clear()
    return original_request(self,method,url,**kwargs)
requests.Session.request=request

def clean(x):return html.unescape(re.sub(r'<[^>]*>','',str(x))).strip()
def published(value):
    try:
        dt=datetime.fromisoformat(str(value))
        return (dt.replace(tzinfo=ZoneInfo('Asia/Shanghai')) if dt.tzinfo is None else dt).isoformat()
    except ValueError:return None

def classify(title,body,defaults):
    text=(title+' '+body).lower(); hits={n:[k for k in keys if k.lower() in text] for n,keys in KEYWORDS.items()}
    hits={n:ks for n,ks in hits.items() if ks}
    nodes=list(dict.fromkeys([*defaults,*hits]))
    reasons=[f'{n}: '+','.join(ks[:3]) for n,ks in hits.items()]
    return nodes,('关键词匹配：'+'；'.join(reasons)) if reasons else ('预置公司检索主题' if defaults else '未匹配研究节点')

def news_item(source,title,body,pub,url=None,publisher=None):
    title,body=clean(title),clean(body)
    excerpt=False
    if not title:
        found=re.match(r'【([^】]+)】',body)
        title=found.group(1) if found else re.split(r'[。！？\n]',body)[0][:90]
        excerpt=True
    if not title:return None
    nodes,reason=classify(title,body,source['nodes'])
    normalized=re.sub(r'[\W_]+','',title).lower()
    timestamp=published(pub)
    identity=hashlib.sha256((source['id']+'|'+str(pub)+'|'+title).encode()).hexdigest()[:20]
    key=hashlib.sha256(((timestamp or '')[:10]+'|'+normalized).encode()).hexdigest()[:20] if len(normalized)>12 else identity
    # Store headline and provenance, not a full mirrored article.
    return {'id':identity,'dedupKey':key,'title':title,'url':url or source['url'],'linkKind':'article' if url else 'collection','titleKind':'内容短句' if excerpt else '来源标题','publishedAt':timestamp,'source':source['name'],'publisher':clean(publisher or source['name']),'nodes':nodes,'classification':reason,'feedId':source['id']}

def series_points(df,datecol,valuecol,monthly=False):
    points=[]
    for row in df.to_dict('records'):
        try:
            value=float(row[valuecol])
            if not math.isfinite(value):continue
            raw=str(row[datecol])
            if monthly:
                m=re.search(r'^(\d{4})(\d{2})$',raw) or re.search(r'(\d{4})\D+(\d{1,2})',raw)
                if not m or not 1<=int(m[2])<=12:continue
                observed=f'{int(m[1]):04d}-{int(m[2]):02d}'
                if observed>date.today().isoformat()[:7]:continue
            else:
                observed=date.fromisoformat(raw[:10]).isoformat()
                if observed>date.today().isoformat():continue
            points.append({'date':observed,'value':value})
        except (KeyError,ValueError,TypeError):continue
    points=list({p['date']:p for p in points}.values())
    if not points:raise ValueError('接口返回了数据，但没有符合口径的有效观察值')
    return {'points':sorted(points,key=lambda p:p['date'])[-100:],'publishedAt':None}

FIN_FIELDS = {'revenue':'TOTALOPERATEREVE','profit':'PARENTNETPROFIT','coreProfit':'KCFJCXSYJLR','grossMargin':'XSMLL','roe':'ROEJQ','debtRatio':'ZCFZL','cashPerShare':'MGJYXJJE'}
def financial_reports(df,symbol):
    reports=[]
    for row in df.to_dict('records'):
        if row.get('SECUCODE')!=symbol:continue
        try:
            period=date.fromisoformat(str(row['REPORT_DATE'])[:10]).isoformat()
            notice=date.fromisoformat(str(row['NOTICE_DATE'])[:10]).isoformat()
            if period>date.today().isoformat() or notice>date.today().isoformat():continue
        except (ValueError,KeyError):continue
        values={}
        for key,field in FIN_FIELDS.items():
            try:v=float(row.get(field));values[key]=v if math.isfinite(v) else None
            except (TypeError,ValueError):values[key]=None
        if not any(v is not None for v in values.values()):continue
        reports.append({'period':period,'publishedAt':notice,'label':clean(row.get('REPORT_DATE_NAME',period)),'currency':clean(row.get('CURRENCY','未提供')),'values':values})
    if not reports:raise ValueError('没有已披露且证券代码一致的有效财务报告')
    return {'reports':sorted(reports,key=lambda x:x['period'],reverse=True)[:16],'fields':FIN_FIELDS}

def fetch(sid):
    import akshare as ak
    source=next(s for s in AK_SOURCES if s['id']==sid)
    if source['kind']=='financial':return financial_reports(ak.stock_financial_analysis_indicator_em(symbol=source['symbol'],indicator='按报告期'),source['symbol'])
    if sid in ('etf_gold','etf_silver'):return series_points(ak.macro_cons_gold() if sid=='etf_gold' else ak.macro_cons_silver(),'日期','总库存')
    if sid=='cn_ppi':return series_points(ak.macro_china_ppi(),'月份','当月同比增长',True)
    if sid=='cn_credit':return series_points(ak.macro_china_shrzgm(),'月份','社会融资规模增量',True)
    if sid=='cn_lpr':return series_points(ak.macro_china_lpr(),'TRADE_DATE','LPR1Y')
    if sid=='cn_m2':return series_points(ak.macro_china_money_supply(),'月份','货币和准货币(M2)-同比增长',True)
    if sid=='cn_pmi':return series_points(ak.macro_china_pmi(),'月份','制造业-指数',True)
    if sid=='cn_cpi':return series_points(ak.macro_china_cpi(),'月份','全国-同比增长',True)
    if sid in ('sge_gold','sge_silver'):
        return series_points(ak.spot_hist_sge(symbol='Au99.99' if sid=='sge_gold' else 'Ag(T+D)'),'date','close')
    items=[]
    if sid=='news_cls':
        rows=ak.stock_info_global_cls(symbol='全部').to_dict('records')
        for r in rows:items.append(news_item(source,r['标题'],r['内容'],str(r['发布日期'])+'T'+str(r['发布时间'])))
    elif sid=='news_sina':
        for r in ak.stock_info_global_sina().to_dict('records'):items.append(news_item(source,'',r['内容'],r['时间']))
    elif sid=='news_em':
        for r in ak.stock_info_global_em().to_dict('records'):items.append(news_item(source,r['标题'],r['摘要'],r['发布时间'],r['链接']))
    else:
        for r in ak.stock_news_em(symbol=source['symbol']).to_dict('records'):items.append(news_item(source,r['新闻标题'],r['新闻内容'],r['发布时间'],r['新闻链接'],r['文章来源']))
    items=[i for i in items if i]
    if not items:raise ValueError('未返回有效快讯')
    return {'items':items}

if __name__=='__main__':
    try:
        with contextlib.redirect_stdout(sys.stderr):result=fetch(sys.argv[1])
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
    except Exception as e:
        print(json.dumps({'error':f'{type(e).__name__}: {str(e)[:220]}'},ensure_ascii=False));sys.exit(1)
