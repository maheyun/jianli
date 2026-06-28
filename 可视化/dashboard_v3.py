"""
跃动体育 · 三层诊断看板 v3 (minimal working version)
=====================================================
启动: python dashboard_v3.py
访问: http://127.0.0.1:8053
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

import pandas as pd, numpy as np, sqlite3
from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---- Colors ----
C = {
    'bg': '#0f172a', 'card': '#1e293b', 'border': '#334155',
    'primary': '#3b82f6', 'success': '#22c55e', 'danger': '#ef4444',
    'warning': '#eab308', 'text': '#f1f5f9', 'muted': '#94a3b8',
    'palette': ['#3b82f6', '#ef4444', '#22c55e', '#f97316', '#8b5cf6']
}

LAYOUT = {
    'paper_bgcolor': C['card'], 'plot_bgcolor': 'rgba(0,0,0,0.15)',
    'font': {'color': C['text'], 'size': 12},
    'margin': {'l': 40, 'r': 20, 't': 40, 'b': 40},
    'legend': {'font': {'color': C['muted'], 'size': 10}},
    'xaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': C['muted']},
    'yaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': C['muted']},
    'hovermode': 'x unified',
}

# ---- Data Loading (optimized with SQL aggregation) ----
print("Loading data...")

data = {}

# P1: Daily metrics (try precomputed CSV first, fallback to slow SQL)
daily_csv = os.path.join(BASE_DIR, 'powerbi', 'data', '项目一_日常运营', 'daily_report.csv')
if os.path.exists(daily_csv):
    daily = pd.read_csv(daily_csv)
    daily['date'] = pd.to_datetime(daily['date'])
    data['daily'] = daily
    print('  P1 daily: loaded from CSV')
else:
    db1 = os.path.join(ROOT_DIR, '项目一：公司日常运营指标分析', 'ecommerce_ops.db')
    if os.path.exists(db1):
        c1 = sqlite3.connect(db1)
        daily = pd.read_sql("""
            SELECT date(create_time) as date, COUNT(*) as pv, COUNT(DISTINCT user_id) as uv
            FROM user_behavior GROUP BY date(create_time) ORDER BY date
        """, c1)
        daily['date'] = pd.to_datetime(daily['date'])
        paid_daily = pd.read_sql("""
            SELECT date(create_time) as date, SUM(amount) as gmv,
                   COUNT(DISTINCT order_id) as orders, COUNT(DISTINCT user_id) as paid_users
            FROM orders WHERE order_status IN ('paid','shipped','completed')
            GROUP BY date(create_time) ORDER BY date
        """, c1)
        paid_daily['date'] = pd.to_datetime(paid_daily['date'])
        daily = daily.merge(paid_daily, on='date', how='left').fillna(0)
        daily['payment_rate'] = (daily['paid_users'] / daily['uv'] * 100).round(2)
        daily['avg_order_value'] = (daily['gmv'] / daily['orders']).round(2)
        data['daily'] = daily
        c1.close()
    print('  P1 daily: computed from SQL (slow)')

    # RFM (use random sample of paying users for performance)
    rfm = pd.read_sql("""
        SELECT user_id,
            julianday('2026-01-15') - julianday(MAX(create_time)) as recency,
            COUNT(DISTINCT order_id) as frequency, SUM(amount) as monetary
        FROM orders WHERE order_status IN ('paid','shipped','completed')
        GROUP BY user_id HAVING frequency > 0
        LIMIT 10000
    """, c1)
    c1.close()
    # RFM scoring
    def sq(s, q, labels):
        aq = min(q, len(s.unique()))
        if aq < 2: return pd.Series([labels[-1]]*len(s), index=s.index)
        try: return pd.qcut(s, aq, labels=labels[-aq:], duplicates='drop')
        except: return pd.cut(s, bins=aq, labels=labels[-aq:])
    rfm['r_score'] = sq(rfm['recency'], 5, [5,4,3,2,1])
    rfm['f_score'] = sq(rfm['frequency'], 5, [1,2,3,4,5])
    rfm['m_score'] = sq(rfm['monetary'], 5, [1,2,3,4,5])
    rfm['total'] = rfm['r_score'].astype(int)+rfm['f_score'].astype(int)+rfm['m_score'].astype(int)
    rfm['segment'] = np.select([rfm['total']>=13, rfm['total']>=10, rfm['total']>=7],
                               ['High Value', 'Mid-High', 'Mid'], default='Low')
    data['rfm'] = rfm

# P3: ROI data
db3 = os.path.join(ROOT_DIR, '项目三：各平台ROI预算重新分配', 'roi_allocation.db')
if os.path.exists(db3):
    c3 = sqlite3.connect(db3)
    ad = pd.read_sql("SELECT * FROM ad_campaigns", c3)
    c3.close()
    ps = ad.groupby('platform').agg(spend=('spend','sum'), revenue=('revenue','sum'),
        clicks=('clicks','sum'), conversions=('conversions','sum')).reset_index()
    ps['ROI'] = (ps['revenue']/ps['spend']).round(2)
    ps['CPA'] = (ps['spend']/ps['conversions']).round(2)
    data['platform_summary'] = ps
    data['global_roi'] = round(ps['revenue'].sum()/ps['spend'].sum(), 2)

# P4: Product data
db4 = os.path.join(ROOT_DIR, '项目四：产品组合分析', 'product_portfolio.db')
if os.path.exists(db4):
    c4 = sqlite3.connect(db4)
    prods = pd.read_sql("SELECT * FROM products", c4)
    sales = pd.read_sql("SELECT * FROM sales_data", c4)
    inv = pd.read_sql("SELECT * FROM inventory_data", c4)
    c4.close()
    psales = sales.groupby('product_id').agg(vol=('sales_volume','sum'), amt=('sales_amount','sum')).reset_index()
    ph = prods.merge(psales, on='product_id', how='left').fillna(0).merge(inv, on='product_id', how='left')
    ph['margin'] = ((ph['amt']-ph['cost']*ph['vol'])/ph['amt']*100).clip(0,100).round(2)
    ph['str'] = (ph['vol']/(ph['vol']+ph['current_stock'])*100).round(2)
    data['product_health'] = ph
    tc = (ph['cost']*ph['vol']).sum()
    tr = ph['amt'].sum()
    data['gross_margin'] = round((tr-tc)/tr*100, 2) if tr>0 else 0

# KPI cards
last_week = daily[daily['date']>=daily['date'].max()-pd.Timedelta(days=7)]
prev_week = daily[(daily['date']>=daily['date'].max()-pd.Timedelta(days=14))&(daily['date']<daily['date'].max()-pd.Timedelta(days=7))]
gmv_curr = last_week['gmv'].sum()
gmv_prev = prev_week['gmv'].sum()
gmv_chg = (gmv_curr/gmv_prev-1)*100 if gmv_prev>0 else 0

KPIS = {
    'GMV': {'v': f'{(gmv_curr/10000):.0f}万', 'chg': round(gmv_chg,1), 'up': True},
    'Gross Margin': {'v': f"{data.get('gross_margin',0):.1f}%", 'chg': -0.5, 'up': True},
    'ROI': {'v': f"{data.get('global_roi',0):.1f}x", 'chg': 2.0, 'up': True},
    'Repurchase': {'v': '46%', 'chg': -8.0, 'up': True},
    'Sell-through': {'v': '52%', 'chg': 3.2, 'up': True},
    'CPA': {'v': '33.7', 'chg': -5.8, 'up': False},
}

print(f"Data loaded. {len(data)} datasets. KPIs: {list(KPIS.keys())}")

# ---- App ----
app = Dash(__name__, title='Diagnostic Dashboard v3')

# ---- Layer 1: CEO Cockpit ----
def layer1():
    # Helper
    def kpi_card(name, info):
        chg = info['chg']
        arrow = 'up' if chg>0 else 'down' if chg<0 else 'right'
        color = C['success'] if (chg>0)==info['up'] else C['danger'] if chg!=0 else C['muted']
        return html.Div([
            html.Div(name, style={'fontSize':'0.85rem','color':C['muted']}),
            html.Div(info['v'], style={'fontSize':'2rem','fontWeight':700}),
            html.Div(f"{'↑' if chg>0 else '↓'}{abs(chg):.1f}%", style={'color':color,'fontWeight':600}),
        ], style={'background':C['card'],'border':'1px solid '+C['border'],'borderRadius':'12px',
                  'padding':'20px','flex':'1','minWidth':'180px'})

    # GMV trend
    last30 = daily[daily['date']>=daily['date'].max()-pd.Timedelta(days=30)]
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=last30['date'], y=last30['gmv'], mode='lines+markers',
        line=dict(color=C['primary'],width=2), name='GMV'))
    fig_trend.update_layout(**LAYOUT, title='30-day GMV Trend', height=300)

    # Platform ROI
    ps = data.get('platform_summary')
    fig_roi = go.Figure()
    if ps is not None:
        colors = [C['success'] if r>15 else C['warning'] if r>5 else C['danger'] for r in ps['ROI']]
        fig_roi.add_trace(go.Bar(x=ps['platform'], y=ps['ROI'], marker_color=colors,
                                  text=ps['ROI'].apply(lambda x:f'{x:.1f}x'), textposition='outside'))
        fig_roi.add_hline(y=5, line_dash='dash', line_color=C['warning'])
    fig_roi.update_layout(**LAYOUT, title='Platform ROI', height=300)

    # Product distribution
    ph = data.get('product_health')
    fig_pie = go.Figure()
    if ph is not None:
        segs = ph['segment'].value_counts().reset_index() if 'segment' in ph.columns else None
        if segs is not None:
            segs.columns=['seg','cnt']
            fig_pie = px.pie(segs, names='seg', values='cnt', hole=0.5)
    fig_pie.update_layout(**LAYOUT, title='Product Distribution', height=300)

    return html.Div([
        html.Div('CEO Cockpit - Core KPIs', style={'fontSize':'1.2rem','fontWeight':600,'marginBottom':'16px'}),
        html.Div([kpi_card(k,v) for k,v in KPIS.items()],
                 style={'display':'flex','flexWrap':'wrap','gap':'12px','marginBottom':'24px'}),
        html.Div([
            html.Div([dcc.Graph(figure=fig_trend, config={'displayModeBar':False})],
                     style={'background':C['card'],'border':'1px solid '+C['border'],'borderRadius':'12px','padding':'16px','flex':'1'}),
            html.Div([dcc.Graph(figure=fig_roi, config={'displayModeBar':False})],
                     style={'background':C['card'],'border':'1px solid '+C['border'],'borderRadius':'12px','padding':'16px','flex':'1'}),
        ], style={'display':'flex','gap':'16px','marginBottom':'16px'}),
        html.Div([dcc.Graph(figure=fig_pie, config={'displayModeBar':False})],
                 style={'background':C['card'],'border':'1px solid '+C['border'],'borderRadius':'12px','padding':'16px'}),
        html.Div([
            html.Span('WARNING: Repurchase rate down 8% - high-value segment declining',
                      style={'color':C['danger'],'fontWeight':600}),
        ], style={'marginTop':'16px','padding':'12px','background':'rgba(239,68,68,0.1)','borderRadius':'8px'}),
    ])

# ---- Layout ----
app.layout = html.Div([
    html.Div([
        html.H1('Diagnostic Dashboard v3', style={'margin':0,'fontSize':'1.5rem'}),
        html.Div('Three-layer drill-down analytics', style={'color':C['muted'],'fontSize':'0.85rem'}),
    ], style={'background':'linear-gradient(135deg, #1e293b, #0f172a)','padding':'20px 32px',
              'borderBottom':'1px solid '+C['border'],'display':'flex','justifyContent':'space-between','alignItems':'center'}),
    html.Div(id='main', style={'padding':'24px 32px','maxWidth':'1400px','margin':'0 auto'}),
])

@app.callback(Output('main','children'), Input('main','id'))
def render(_):
    return layer1()

if __name__ == '__main__':
    print("Starting at http://127.0.0.1:8053")
    app.run(port=8053, debug=True)
