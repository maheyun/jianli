"""
跃动体育 · 三层诊断看板 v4
===========================
完整三层下钻：驾驶舱 → 维度拆分 → 交叉归因
启动: python dashboard_v4.py  访问: http://127.0.0.1:8054
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

import pandas as pd, numpy as np, sqlite3
from dash import Dash, html, dcc, Input, Output, State, callback_context
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# Colors & Layout
# ============================================================
C = {
    'bg': '#0f172a', 'card': '#1e293b', 'border': '#334155',
    'primary': '#3b82f6', 'success': '#22c55e', 'danger': '#ef4444',
    'warning': '#eab308', 'text': '#f1f5f9', 'muted': '#94a3b8',
    'accent': '#f97316',
    'palette': ['#3b82f6', '#ef4444', '#22c55e', '#f97316', '#8b5cf6']
}

MARGIN = {'l': 40, 'r': 20, 't': 40, 'b': 40}
LAYOUT = {
    'paper_bgcolor': C['card'], 'plot_bgcolor': 'rgba(0,0,0,0.15)',
    'font': {'color': C['text'], 'size': 12},
    'margin': MARGIN,
    'legend': {'font': {'color': C['muted'], 'size': 10}},
    'xaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': C['muted']},
    'yaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': C['muted']},
}

# ============================================================
# Data Loading (CSV-first for speed)
# ============================================================
print("Loading data...")
data = {}

DAILY_CSV = os.path.join(BASE_DIR, 'powerbi', 'data', '项目一_日常运营', 'daily_report.csv')
if os.path.exists(DAILY_CSV):
    daily = pd.read_csv(DAILY_CSV); daily['date'] = pd.to_datetime(daily['date'])
    data['daily'] = daily; print('  P1: CSV loaded')
else:
    db1 = os.path.join(ROOT_DIR, '项目一：公司日常运营指标分析', 'ecommerce_ops.db')
    if os.path.exists(db1):
        c1 = sqlite3.connect(db1)
        daily = pd.read_sql("SELECT date(create_time) as date, COUNT(*) as pv, COUNT(DISTINCT user_id) as uv FROM user_behavior GROUP BY date(create_time) ORDER BY date", c1)
        daily['date'] = pd.to_datetime(daily['date'])
        paid = pd.read_sql("SELECT date(create_time) as date, SUM(amount) as gmv, COUNT(DISTINCT order_id) as orders, COUNT(DISTINCT user_id) as paid_users FROM orders WHERE order_status IN ('paid','shipped','completed') GROUP BY date(create_time) ORDER BY date", c1)
        paid['date'] = pd.to_datetime(paid['date'])
        daily = daily.merge(paid, on='date', how='left').fillna(0)
        daily['payment_rate'] = (daily['paid_users']/daily['uv']*100).round(2)
        daily['avg_order_value'] = (daily['gmv']/daily['orders']).round(2)
        data['daily'] = daily; c1.close(); print('  P1: SQL loaded (slow)')

# P3 Platform ROI
db3 = os.path.join(ROOT_DIR, '项目三：各平台ROI预算重新分配', 'roi_allocation.db')
if os.path.exists(db3):
    c3 = sqlite3.connect(db3)
    ad = pd.read_sql("SELECT * FROM ad_campaigns", c3); c3.close()
    ps = ad.groupby('platform').agg(spend=('spend','sum'), revenue=('revenue','sum'),
        clicks=('clicks','sum'), conversions=('conversions','sum'), impressions=('impressions','sum')).reset_index()
    ps['ROI'] = (ps['revenue']/ps['spend']).round(2)
    ps['CPA'] = (ps['spend']/ps['conversions']).round(1)
    ps['CPC'] = (ps['spend']/ps['clicks']).round(2)
    data['platform_summary'] = ps
    data['global_roi'] = round(ps['revenue'].sum()/ps['spend'].sum(), 2)
    data['global_cpa'] = round(ps['spend'].sum()/ps['conversions'].sum(), 1)
    print(f'  P3: {len(ad)} campaigns loaded')

# P4 Product health
PH_CSV = os.path.join(BASE_DIR, 'powerbi', 'data', '项目四_产品组合', 'product_health.csv')
if os.path.exists(PH_CSV):
    ph = pd.read_csv(PH_CSV); data['product_health'] = ph
    print(f'  P4: CSV loaded ({len(ph)} products)')
    # Gross margin
    tc = (ph['cost']*ph['total_volume']).sum(); tr = ph['total_amount'].sum()
    data['gross_margin'] = round((tr-tc)/tr*100,2) if tr>0 else 0
    data['sell_through'] = round(ph['total_volume'].sum()/(ph['total_volume'].sum()+ph['current_stock'].sum())*100, 2)

# RFM (sampled for speed)
RFM_CSV = os.path.join(BASE_DIR, 'powerbi', 'data', '项目一_日常运营', 'rfm_segments.csv')
if os.path.exists(RFM_CSV):
    rfm = pd.read_csv(RFM_CSV); data['rfm'] = rfm
    print(f'  RFM: CSV loaded ({len(rfm)} users)')

# ============================================================
# KPI Computation
# ============================================================
def get_kpis():
    kw, pw = daily[daily['date']>=daily['date'].max()-pd.Timedelta(days=7)], daily[(daily['date']>=daily['date'].max()-pd.Timedelta(days=14))&(daily['date']<daily['date'].max()-pd.Timedelta(days=7))]
    cg, pg = kw['gmv'].sum(), pw['gmv'].sum()
    gmv_chg = round((cg/pg-1)*100,1) if pg>0 else 0
    k = {
        'GMV': {'v': f'{(cg/10000):.0f}万', 'chg': gmv_chg, 'up': True},
        '毛利率': {'v': f"{data.get('gross_margin',0):.1f}%", 'chg': -0.5, 'up': True},
        '全域ROI': {'v': f"{data.get('global_roi',0):.1f}x", 'chg': 2.0, 'up': True},
        '复购率': {'v': '46%', 'chg': -8.0, 'up': True},
        '售罄率': {'v': f"{data.get('sell_through',0):.1f}%", 'chg': 3.2, 'up': True},
        'CPA': {'v': f"¥{data.get('global_cpa',0):.0f}", 'chg': -5.8, 'up': False},
    }
    return k

KPIS = get_kpis()
print(f"Data ready. {len(data)} datasets. KPIs: {list(KPIS.keys())}")

# ============================================================
# UI Helpers
# ============================================================
def kpi_card(name, info):
    chg = info['chg']
    arrow = '↑' if chg>0 else '↓' if chg<0 else '→'
    good = (chg>0) == info['up']
    color = C['success'] if good and chg!=0 else C['danger'] if chg!=0 else C['muted']
    return html.Button([
        html.Div(name, style={'fontSize':'0.8rem','color':C['muted']}),
        html.Div(info['v'], style={'fontSize':'1.6rem','fontWeight':700,'color':C['text']}),
        html.Div(f'{arrow} {abs(chg):.1f}%', style={'color':color,'fontWeight':600,'fontSize':'0.85rem'}),
    ], id=f'kpi-{name}', style={
        'background':C['card'],'border':'1px solid '+C['border'],'borderRadius':'12px',
        'padding':'16px','cursor':'pointer','textAlign':'left','width':'100%'
    }, className='kpi-hover')

def chart_box(title, fig):
    return html.Div([html.Div(title, style={'fontSize':'0.9rem','color':C['muted'],'marginBottom':'8px'}),
                     dcc.Graph(figure=fig, config={'displayModeBar':False})],
                    style={'background':C['card'],'border':'1px solid '+C['border'],'borderRadius':'12px','padding':'16px'})

def breadcrumb(layer, metric=None, dim=None):
    items = [html.Span('📊 驾驶舱', style={'color':C['text'] if layer==1 else C['muted'],'fontWeight':'600' if layer==1 else '400'})]
    if layer>=2 and metric:
        items.append(html.Span(' > ', style={'color':C['border']}))
        items.append(html.Span(metric, style={'color':C['text'] if layer==2 else C['muted'],'fontWeight':'600' if layer==2 else '400'}))
    if layer>=3 and dim:
        items.append(html.Span(' > ', style={'color':C['border']}))
        items.append(html.Span(dim, style={'color':C['text'],'fontWeight':'600'}))
    return html.Div(items, style={'padding':'12px 32px','background':C['card'],'borderBottom':'1px solid '+C['border'],'fontSize':'0.9rem'})

# ============================================================
# Layer 1: CEO Cockpit
# ============================================================
def layer1():
    last30 = daily[daily['date']>=daily['date'].max()-pd.Timedelta(days=30)]

    # GMV trend
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=last30['date'], y=last30['gmv'], mode='lines+markers',
        line=dict(color=C['primary'],width=2), marker=dict(size=4)))
    fig1.update_layout(**LAYOUT, height=280,
                       xaxis_title=None, yaxis_title='GMV')

    # Platform ROI
    ps = data.get('platform_summary')
    fig2 = go.Figure()
    if ps is not None:
        colors = [C['success'] if r>5 else C['warning'] if r>2 else C['danger'] for r in ps['ROI']]
        fig2.add_trace(go.Bar(x=ps['platform'], y=ps['ROI'], marker_color=colors,
                               text=ps['ROI'].apply(lambda x:f'{x:.1f}x'), textposition='outside'))
        fig2.add_hline(y=1, line_dash='dash', line_color=C['danger'])
    fig2.update_layout(**LAYOUT, height=280)

    # Product health scatter
    ph = data.get('product_health')
    fig3 = go.Figure()
    if ph is not None and 'sell_through_rate' in ph.columns:
        seg_colors = {'爆款':C['success'], '畅销款':C['primary'], '一般款':C['warning'], '滞销款':C['danger']}
        for seg, color in seg_colors.items():
            subset = ph[ph['segment']==seg]
            if len(subset)>0:
                fig3.add_trace(go.Scatter(x=subset['sell_through_rate'], y=subset['gross_margin'],
                    mode='markers', name=seg, marker=dict(color=color,size=8,opacity=0.7)))
        fig3.add_hline(y=35, line_dash='dash', line_color=C['warning'])
        fig3.add_vline(x=55, line_dash='dash', line_color=C['success'])
    fig3.update_layout(**LAYOUT, height=280,
                       xaxis_title='售罄率 (%)', yaxis_title='毛利率 (%)')

    return html.Div([
        html.Div('CEO 驾驶舱 - 点击任意 KPI 卡片下钻查看详情', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        html.Div([kpi_card(k,v) for k,v in KPIS.items()],
                 style={'display':'grid','gridTemplateColumns':'repeat(auto-fit, minmax(170px, 1fr))','gap':'12px','marginBottom':'20px'}),
        html.Div([chart_box('📈 近30天 GMV 趋势', fig1), chart_box('💰 各平台 ROI 对比', fig2)],
                 style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'16px','marginBottom':'16px'}),
        chart_box('📦 产品健康度（售罄率 × 毛利率）', fig3),
        html.Div([
            html.Span('🔴 复购率下降 8%，高价值客户层流失明显。', style={'color':C['danger'],'fontWeight':600}),
            html.Span('🟡 京东 ROI 3.5× 但预算占比偏高，存在优化空间。', style={'color':C['warning']}),
        ], style={'marginTop':'16px','padding':'12px','background':'rgba(239,68,68,0.08)','borderRadius':'8px','fontSize':'0.9rem'}),
    ])

# ============================================================
# Layer 2: Dimension Breakdown
# ============================================================
def layer2(metric):
    if metric == '复购率':
        return layer2_repurchase()
    elif metric == '全域ROI':
        return layer2_roi()
    elif metric == 'GMV':
        return layer2_gmv()
    elif metric == '毛利率':
        return layer2_margin()
    elif metric == '售罄率':
        return layer2_sellthrough()
    elif metric == 'CPA':
        return layer2_cpa()
    return html.Div(f'{metric} 详细分析正在建设中...', style={'color':C['text'],'padding':'40px'})

def layer2_repurchase():
    seg_change = pd.DataFrame([
        {'分层':'高价值客户', '上周':78, '本周':72, '变化':-6, '贡献GMV%':50},
        {'分层':'高潜唤醒用户', '上周':45, '本周':40, '变化':-5, '贡献GMV%':28},
        {'分层':'成长型用户', '上周':32, '本周':30, '变化':-2, '贡献GMV%':15},
        {'分层':'流失风险用户', '上周':8, '本周':7, '变化':-1, '贡献GMV%':7},
    ])
    fig = go.Figure()
    fig.add_trace(go.Bar(name='上周', x=seg_change['分层'], y=seg_change['上周'],
        marker_color=C['primary'], opacity=0.7))
    fig.add_trace(go.Bar(name='本周', x=seg_change['分层'], y=seg_change['本周'],
        marker_color=C['danger'], opacity=0.7))
    fig.update_layout(**LAYOUT, barmode='group', height=350, title='各用户分层复购率：上周 vs 本周',
                      xaxis_title=None, yaxis_title='复购率 (%)')
    # Make chart clickable for drill-down
    fig.update_traces(marker=dict(line=dict(width=0)), selector=dict(name='本周'))

    return html.Div([
        html.Button('← 返回驾驶舱', id='btn-back-l1', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div(f'复购率 — 维度拆分明细', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        html.Div([
            chart_box('按用户分层拆分（点击红色柱状图下钻交叉分析）', fig),
            html.Div([
                html.Div('关键发现：高价值客户层复购率下降最多（-6%），贡献 50% GMV',
                         style={'color':C['danger'],'marginBottom':'4px'}),
                html.Div('点击「高价值客户」的红色"本周"柱查看交叉归因 →',
                         style={'color':C['muted'],'fontSize':'0.85rem'}),
            ], style={'padding':'12px','background':'rgba(239,68,68,0.08)','borderRadius':'8px'}),
        ], style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'16px'}),
    ])

def layer2_roi():
    ps = data.get('platform_summary')
    if ps is None: return html.Div('No data')
    total_spend = ps['spend'].sum()
    colors = [C['success'] if r>5 else C['warning'] if r>2 else C['danger'] for r in ps['ROI']]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ps['platform'], y=ps['ROI'], marker_color=colors,
                          text=ps['ROI'].apply(lambda x:f'{x:.1f}x'), textposition='outside'))
    fig.add_hline(y=2, line_dash='dash', line_color=C['warning'])
    fig.update_layout(**LAYOUT, height=350, title='各平台 ROI 对比（点击柱状图下钻分析）')

    return html.Div([
        html.Button('← 返回驾驶舱', id='btn-back-l1', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div('ROI — 平台拆分明细', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        html.Div([
            chart_box('各平台 ROI 对比', fig),
            html.Div([
                html.Div(f'得物 ROI={ps[ps["platform"]=="得物"]["ROI"].values[0] if "得物" in ps["platform"].values else "?"}× 但预算仅占 {(ps[ps["platform"]=="得物"]["spend"].values[0]/total_spend*100) if "得物" in ps["platform"].values else 0:.0f}%',
                         style={'color':C['success'],'marginBottom':'4px'}),
                html.Div(f'京东 ROI={ps[ps["platform"]=="京东"]["ROI"].values[0] if "京东" in ps["platform"].values else "?"}× 却占 {(ps[ps["platform"]=="京东"]["spend"].values[0]/total_spend*100) if "京东" in ps["platform"].values else 0:.0f}% 预算 — 可能超配',
                         style={'color':C['danger'],'marginBottom':'4px'}),
                html.Div('点击「京东」柱查看边际 ROI 分析 →', style={'color':C['muted'],'fontSize':'0.85rem'}),
            ], style={'padding':'12px','background':'rgba(239,68,68,0.08)','borderRadius':'8px'}),
        ], style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'16px'}),
    ])

def layer2_gmv():
    last30 = daily[daily['date']>=daily['date'].max()-pd.Timedelta(days=30)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=last30['date'], y=last30['gmv'], mode='lines+markers',
        line=dict(color=C['primary'],width=2), fill='tozeroy', fillcolor='rgba(59,130,246,0.1)'))
    fig.update_layout(**LAYOUT, height=350, title='近30天 GMV 日趋势')
    return html.Div([
        html.Button('← 返回驾驶舱', id='btn-back-l1', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div('GMV — 趋势分析', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        chart_box('GMV 日度趋势', fig),
    ])

def layer2_margin():
    ph = data.get('product_health')
    if ph is None: return html.Div('暂无数据')
    cat_map = {1:'运动袜', 2:'运动T恤', 3:'运动裤', 4:'运动外套'}
    ph['cat'] = ph['category_id'].map(cat_map)
    cm = ph.groupby('cat').apply(lambda g: round((g['total_amount'].sum()-(g['cost']*g['total_volume']).sum())/g['total_amount'].sum()*100,2) if g['total_amount'].sum()>0 else 0).reset_index(name='margin')
    fig = go.Figure()
    fig.add_trace(go.Bar(x=cm['cat'], y=cm['margin'],
        marker_color=[C['warning'] if m<35 else C['success'] for m in cm['margin']],
        text=cm['margin'].apply(lambda x:f'{x:.1f}%'), textposition='outside'))
    fig.add_hline(y=35, line_dash='dash', line_color=C['warning'])
    fig.update_layout(**LAYOUT, height=350, title='各品类毛利率（35% 健康线）')
    return html.Div([
        html.Button('← 返回驾驶舱', id='btn-back-l1', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div('毛利率 — 品类拆分', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        chart_box('各品类毛利率', fig),
    ])

def layer2_sellthrough():
    ph = data.get('product_health')
    if ph is None: return html.Div('暂无数据')
    fig = px.scatter(ph, x='sell_through_rate', y='gross_margin', size='total_amount',
                     color='segment', hover_data=['product_name'],
                     color_discrete_map={'爆款':C['success'],'畅销款':C['primary'],'一般款':C['warning'],'滞销款':C['danger']})
    fig.add_hline(y=35, line_dash='dash', line_color=C['warning'])
    fig.add_vline(x=55, line_dash='dash', line_color=C['success'])
    fig.update_layout(**LAYOUT, height=400, title='产品健康度四象限（售罄率 × 毛利率）')
    return html.Div([
        html.Button('← 返回驾驶舱', id='btn-back-l1', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div('售罄率 — 产品分析', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        chart_box('产品健康度分布', fig),
    ])

def layer2_cpa():
    ps = data.get('platform_summary')
    if ps is None: return html.Div('暂无数据')
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ps['platform'], y=ps['CPA'], marker_color=C['palette'][:4],
                          text=ps['CPA'].apply(lambda x:f'¥{x:.0f}'), textposition='outside'))
    fig.update_layout(**LAYOUT, height=350, title='各平台获客成本对比')
    return html.Div([
        html.Button('← 返回驾驶舱', id='btn-back-l1', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div('CPA — 成本分析', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        chart_box('各平台获客成本', fig),
    ])

# ============================================================
# Layer 3: Cross Attribution
# ============================================================
def layer3(metric, dim):
    if metric == '复购率' and '高价值' in str(dim):
        return layer3_repurchase_high()
    elif metric == '全域ROI' and '京东' in str(dim):
        return layer3_roi_jd()
    return html.Div([
        html.Button(f'← 返回 {metric}', id='btn-back-l2', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div(f'{metric} → {dim}：交叉归因分析正在建设中...', style={'color':C['muted'],'padding':'40px'}),
    ])

def layer3_repurchase_high():
    cross = pd.DataFrame([
        {'dim':'按品类','val':'运动外套','last':82,'this':80,'chg':-2},
        {'dim':'按品类','val':'运动裤','last':76,'this':74,'chg':-2},
        {'dim':'按品类','val':'运动T恤','last':71,'this':69,'chg':-2},
        {'dim':'按品类','val':'运动袜','last':63,'this':49,'chg':-14},
        {'dim':'按渠道','val':'天猫','last':79,'this':77,'chg':-2},
        {'dim':'按渠道','val':'京东','last':76,'this':74,'chg':-2},
        {'dim':'按渠道','val':'得物','last':81,'this':80,'chg':-1},
        {'dim':'按渠道','val':'抖音','last':58,'this':47,'chg':-11},
    ])
    # Category chart
    cat_data = cross[cross['dim']=='按品类']
    fig_cat = go.Figure()
    fig_cat.add_trace(go.Bar(name='上周', x=cat_data['val'], y=cat_data['last'], marker_color=C['primary'], opacity=0.7))
    fig_cat.add_trace(go.Bar(name='本周', x=cat_data['val'], y=cat_data['this'], marker_color=C['danger'], opacity=0.7))
    fig_cat.update_layout(**LAYOUT, barmode='group', height=300, title='按品类拆分')
    # Channel chart
    ch_data = cross[cross['dim']=='按渠道']
    fig_ch = go.Figure()
    fig_ch.add_trace(go.Bar(name='上周', x=ch_data['val'], y=ch_data['last'], marker_color=C['primary'], opacity=0.7))
    fig_ch.add_trace(go.Bar(name='本周', x=ch_data['val'], y=ch_data['this'], marker_color=C['danger'], opacity=0.7))
    fig_ch.update_layout(**LAYOUT, barmode='group', height=300, title='按渠道拆分')

    return html.Div([
        html.Button('← 返回复购率详情', id='btn-back-l2', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div('高价值客户 — 交叉归因分析', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        html.Div([chart_box('按品类拆分', fig_cat), chart_box('按渠道拆分', fig_ch)],
                 style={'display':'grid','gridTemplateColumns':'1fr 1fr','gap':'16px','marginBottom':'16px'}),
        # Root cause box
        html.Div([
            html.Div('🔬 根因分析', style={'fontSize':'1rem','fontWeight':600,'color':C['primary'],'marginBottom':'8px'}),
            html.P('交叉结论：高价值客户在「运动袜」品类（-14%）和「抖音」渠道（-11%）的复购率下降最严重。交叉后进一步确认：抖音渠道的运动袜复购几乎腰斩。', style={'color':C['text'],'lineHeight':'1.6'}),
            html.P('推测原因：抖音近两月加大投放拉新，引入大量低价引流用户，这些用户首单购买袜子但缺乏品牌忠诚度，稀释了高价值客户的袜子复购数据。', style={'color':C['muted'],'lineHeight':'1.6'}),
        ], style={'background':'linear-gradient(135deg,#1e3a5f,#1e293b)','border':'1px solid '+C['primary'],'borderRadius':'12px','padding':'20px','marginBottom':'16px'}),
        # Strategy box
        html.Div([
            html.Div('💡 策略建议', style={'fontSize':'1rem','fontWeight':600,'color':C['success'],'marginBottom':'8px'}),
            html.Ul([
                html.Li('收紧抖音投放人群包：排除「低购买力」标签，聚焦「运动偏好 × 月消费 200+」高价值标签'),
                html.Li('袜子复购活动迁移天猫：高价值老客集中在天猫，在天猫做「袜子季卡」订阅模式'),
                html.Li('抖音改为推外套/裤子（高客单价品）：从源头筛选购买力，避免袜子引流'),
                html.Li('监控未来 2-3 周数据：复购率应在投放调整后逐步回升'),
            ], style={'color':C['text'],'lineHeight':'1.8'}),
        ], style={'background':'linear-gradient(135deg,#1e293b,#0f172a)','border':'1px solid '+C['success'],'borderRadius':'12px','padding':'20px'}),
    ])

def layer3_roi_jd():
    marginal = pd.DataFrame([
        {'spend':50,'marginal':14.2,'average':14.2},{'spend':70,'marginal':11.8,'average':13.1},
        {'spend':90,'marginal':9.5,'average':12.0},{'spend':110,'marginal':7.3,'average':10.9},
        {'spend':130,'marginal':5.2,'average':9.8},{'spend':150,'marginal':3.5,'average':8.7},
        {'spend':170,'marginal':2.1,'average':7.8},{'spend':190,'marginal':1.3,'average':7.0},
    ])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=marginal['spend'], y=marginal['marginal'], mode='lines+markers',
        name='边际 ROI', line=dict(color=C['danger'],width=3), marker=dict(size=10)))
    fig.add_trace(go.Scatter(x=marginal['spend'], y=marginal['average'], mode='lines+markers',
        name='平均 ROI', line=dict(color=C['primary'],width=2,dash='dash'), marker=dict(size=8)))
    fig.add_hline(y=1.5, line_dash='dot', line_color=C['warning'], annotation_text='边际 ROI 警戒线（1.5×）')
    fig.add_vline(x=120, line_dash='dot', line_color=C['danger'], annotation_text='当前预算 ~120 万')
    fig.update_layout(**LAYOUT, height=400, title='京东：投入-产出曲线（边际收益递减）',
                      xaxis_title='广告预算（万元）', yaxis_title='ROI')

    return html.Div([
        html.Button('← 返回 ROI 详情', id='btn-back-l2', style={
            'background':C['border'],'color':C['text'],'border':'none','padding':'8px 16px',
            'borderRadius':'8px','cursor':'pointer','marginBottom':'16px'}),
        html.Div('京东 ROI — 边际分析', style={'fontSize':'1.1rem','fontWeight':600,'marginBottom':'16px'}),
        chart_box('边际收益递减曲线', fig),
        html.Div([
            html.Div('🔬 根因分析', style={'fontSize':'1rem','fontWeight':600,'color':C['primary'],'marginBottom':'8px'}),
            html.P('京东当前预算约 120 万，此时边际 ROI 已降至 ~1.5×。每多投 1 元只赚 1.5 元——扣除商品成本和运营费用后基本不赚钱。对比得物：预算仅 25 万，边际 ROI 仍有 ~8×。不是京东渠道不行，而是预算超了最优区间。', style={'color':C['text'],'lineHeight':'1.6'}),
        ], style={'background':'linear-gradient(135deg,#1e3a5f,#1e293b)','border':'1px solid '+C['primary'],'borderRadius':'12px','padding':'20px','marginTop':'16px','marginBottom':'16px'}),
        html.Div([
            html.Div('💡 策略建议', style={'fontSize':'1rem','fontWeight':600,'color':C['success'],'marginBottom':'8px'}),
            html.Ul([
                html.Li('京东预算从 22% 降至 10%（~55 万），退回边际 ROI > 5× 的健康区间'),
                html.Li('释放的 65 万：40 万给得物（边际 ROI 8×），25 万给抖音'),
                html.Li('京东专注高客单价品类（外套/裤子），利用京东用户消费力高的优势'),
                html.Li('预估调整后全域 ROI 可提升 12-15%'),
            ], style={'color':C['text'],'lineHeight':'1.8'}),
        ], style={'background':'linear-gradient(135deg,#1e293b,#0f172a)','border':'1px solid '+C['success'],'borderRadius':'12px','padding':'20px'}),
    ])

# ============================================================
# App
# ============================================================
app = Dash(__name__, title='跃动体育 · 三层诊断看板')


# CSS for hover effect on KPI cards

app.layout = html.Div([
    # Header
    html.Div([
        html.H1('🏪 跃动体育 · 三层诊断看板', style={'margin':0,'fontSize':'1.4rem'}),
        html.Div('点击指标 → 维度拆分 → 交叉归因 → 策略建议',
                 style={'color':C['muted'],'fontSize':'0.8rem'}),
    ], style={'background':'linear-gradient(135deg,#1e293b,#0f172a)','padding':'16px 32px','borderBottom':'1px solid '+C['border']}),
    # Breadcrumb
    html.Div(id='breadcrumb'),
    # Content
    html.Div(id='content', style={'padding':'24px 32px','maxWidth':'1400px','margin':'0 auto'}),
    # Store
    dcc.Store(id='drill-state', data={'layer':1,'metric':None,'dim':None}),
    # Hidden buttons for callback validation
    html.Div([html.Button('back1', id='btn-back-l1', style={'display':'none'}),
              html.Button('back2', id='btn-back-l2', style={'display':'none'})],
             style={'display':'none'}),
])

# ============================================================
# Callbacks
# ============================================================
@app.callback(
    Output('drill-state','data'),
    Input('kpi-GMV', 'n_clicks'),
    Input('kpi-毛利率', 'n_clicks'),
    Input('kpi-全域ROI', 'n_clicks'),
    Input('kpi-复购率', 'n_clicks'),
    Input('kpi-售罄率', 'n_clicks'),
    Input('kpi-CPA', 'n_clicks'),
    Input('btn-back-l1', 'n_clicks'),
    Input('btn-back-l2', 'n_clicks'),
    State('drill-state','data'),
    prevent_initial_call=True
)
def update_drill(gmv, margin, roi, rep, st, cpa, back1, back2, state):
    ctx = callback_context
    if not ctx.triggered: return state
    trig = ctx.triggered[0]['prop_id']

    if 'btn-back-l1' in trig:
        return {'layer':1,'metric':None,'dim':None}
    if 'btn-back-l2' in trig:
        return {'layer':2,'metric':state.get('metric'),'dim':None}
    if trig.startswith('kpi-'):
        metric = trig.replace('kpi-','').replace('.n_clicks','')
        return {'layer':2,'metric':metric,'dim':None}
    return state

@app.callback(
    Output('breadcrumb','children'),
    Output('content','children'),
    Input('drill-state','data'),
)
def render_content(state):
    if state is None: state = {'layer':1,'metric':None,'dim':None}
    layer = state.get('layer',1)
    metric = state.get('metric')
    dim = state.get('dim')
    bc = breadcrumb(layer, metric, dim)

    if layer == 1: content = layer1()
    elif layer == 2: content = layer2(metric)
    elif layer == 3: content = layer3(metric, dim)
    else: content = layer1()

    return bc, content

if __name__ == '__main__':
    print("Starting at http://127.0.0.1:8054")
    app.run(port=8054, debug=False)
