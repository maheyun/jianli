"""
跃动体育 · 四项目交互式数据看板 v2
====================================
优化版：启动时预加载全部数据 + CSS Grid 响应式布局

运行: python dashboard.py
访问: http://127.0.0.1:8050
"""

import dash
from dash import Dash, dcc, html, dash_table, Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime

# ============================================================
# 0. 全局配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOW = pd.Timestamp.now()

COLORS = {
    'bg': '#1a1a2e',
    'card_bg': '#16213e',
    'card_border': '#0f3460',
    'accent': '#e94560',
    'primary': '#3498db',
    'success': '#2ecc71',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'text': '#ecf0f1',
    'muted': '#95a5a6',
    'palette': ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6',
                '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60']
}

CHART_LAYOUT_BASE = {
    'paper_bgcolor': COLORS['card_bg'],
    'plot_bgcolor': 'rgba(0,0,0,0.1)',
    'font': {'color': COLORS['text']},
    'margin': {'l': 40, 'r': 20, 't': 40, 'b': 40},
    'legend': {'font': {'color': COLORS['muted']}},
    'xaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': COLORS['muted']},
    'yaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': COLORS['muted']},
}

# ---- 工具函数 ----
def safe_qcut(s, q, labels):
    aq = min(q, len(s.unique()))
    if aq < 2:
        return pd.Series([labels[-1]] * len(s), index=s.index)
    try:
        return pd.qcut(s, aq, labels=labels[-aq:], duplicates='drop')
    except ValueError:
        return pd.cut(s, bins=aq, labels=labels[-aq:])


# ============================================================
# 1. 启动时预加载 & 预计算全部四项目数据
# ============================================================

print("=" * 60)
print("  跃动体育 · 数据看板 v2 — 预加载数据中...")
print("=" * 60)

# ---------- 项目一 ----------
print("  [1/4] 加载项目一：日常运营...", end=" ", flush=True)
_conn = sqlite3.connect(os.path.join(BASE_DIR, '项目一：公司日常运营指标分析', 'ecommerce_ops.db'))
_ub = pd.read_sql("SELECT * FROM user_behavior", _conn)
_orders1 = pd.read_sql("SELECT * FROM orders", _conn)
_conn.close()
_ub['create_time'] = pd.to_datetime(_ub['create_time'])
_orders1['create_time'] = pd.to_datetime(_orders1['create_time'])

# 付费订单
_paid1 = _orders1[_orders1['order_status'].isin(['paid', 'shipped', 'completed'])]

# KPI
P1 = {
    'pv': len(_ub),
    'uv': _ub['user_id'].nunique(),
    'paid_users': _paid1['user_id'].nunique(),
    'gmv': _paid1['amount'].sum(),
}
P1['payment_rate'] = P1['paid_users'] / P1['uv'] if P1['uv'] > 0 else 0
P1['avg_order_value'] = P1['gmv'] / len(_paid1) if len(_paid1) > 0 else 0

# 日报表
_daily = _ub.groupby(_ub['create_time'].dt.date).agg(pv=('id','count'), uv=('user_id','nunique')).reset_index()
_daily.columns = ['date', 'pv', 'uv']
_daily['date'] = pd.to_datetime(_daily['date'])
_dp = _paid1.groupby(_paid1['create_time'].dt.date).agg(
    paid_users=('user_id','nunique'), gmv=('amount','sum'), orders=('order_id','count')).reset_index()
_dp.columns = ['date', 'paid_users', 'gmv', 'orders']
_dp['date'] = pd.to_datetime(_dp['date'])
_daily = _daily.merge(_dp, on='date', how='left').fillna(0)
_daily['payment_rate'] = _daily['paid_users'] / _daily['uv']
_daily['avg_order_value'] = _daily['gmv'] / _daily['orders'].replace(0, np.nan)

# 近30天趋势
_recent30 = _daily.nlargest(30, 'date').sort_values('date')
P1['fig_trend'] = make_subplots(specs=[[{"secondary_y": True}]])
P1['fig_trend'].add_trace(go.Scatter(x=_recent30['date'], y=_recent30['pv'],
    name='PV', mode='lines+markers', line=dict(color=COLORS['primary'], width=2)), secondary_y=False)
P1['fig_trend'].add_trace(go.Scatter(x=_recent30['date'], y=_recent30['uv'],
    name='UV', mode='lines+markers', line=dict(color=COLORS['success'], width=2)), secondary_y=False)
P1['fig_trend'].add_trace(go.Scatter(x=_recent30['date'], y=_recent30['gmv'],
    name='GMV (元)', mode='lines+markers', line=dict(color=COLORS['accent'], width=2)), secondary_y=True)
P1['fig_trend'].update_yaxes(title_text="用户数", secondary_y=False)
P1['fig_trend'].update_yaxes(title_text="GMV (元)", secondary_y=True)
P1['fig_trend'].update_layout(**CHART_LAYOUT_BASE)
P1['fig_trend'].update_layout(title=dict(text="近 30 天 PV / UV / GMV 趋势", font=dict(color=COLORS['text'], size=14)))

# 漏斗
_funnel_users = [_ub[_ub['action']==a]['user_id'].nunique() for a in ['view','add_to_cart','place_order','pay']]
P1['fig_funnel'] = go.Figure(go.Funnel(
    y=['浏览','加购','下单','支付'], x=_funnel_users,
    text=[f"{u:,}" for u in _funnel_users],
    textposition="inside", textinfo="text+percent initial",
    marker=dict(color=[COLORS['primary'], COLORS['warning'], COLORS['accent'], COLORS['success']])))
P1['fig_funnel'].update_layout(**CHART_LAYOUT_BASE)
P1['fig_funnel'].update_layout(title=dict(text="转化漏斗", font=dict(color=COLORS['text'], size=14)))

# 转化率
P1['rates'] = []
_cn = ['浏览','加购','下单','支付']
for i in range(3):
    r = _funnel_users[i+1]/_funnel_users[i]*100 if _funnel_users[i]>0 else 0
    P1['rates'].append(f"{_cn[i]}→{_cn[i+1]}: {r:.1f}%")

# RFM 分层
_rfm = _paid1.groupby('user_id').agg(last_purchase=('create_time','max'), frequency=('order_id','nunique'), monetary=('amount','sum')).reset_index()
_rfm['recency'] = (NOW - _rfm['last_purchase']).dt.days
_rfm['r_score'] = safe_qcut(_rfm['recency'], 5, [5,4,3,2,1])
_rfm['f_score'] = safe_qcut(_rfm['frequency'], 5, [1,2,3,4,5])
_rfm['m_score'] = safe_qcut(_rfm['monetary'], 5, [1,2,3,4,5])
_score = _rfm['r_score'].astype(int)+_rfm['f_score'].astype(int)+_rfm['m_score'].astype(int)
_rfm['segment'] = np.select([_score>=12, _score>=9, _score>=6], ['高价值客户','中高价值客户','中价值客户'], default='低价值客户')
_seg = _rfm['segment'].value_counts().reset_index()
_seg.columns = ['segment','count']
P1['fig_pie'] = px.pie(_seg, values='count', names='segment', hole=0.5, color_discrete_sequence=COLORS['palette'])
P1['fig_pie'].update_traces(textinfo='percent+label')
P1['fig_pie'].update_layout(**CHART_LAYOUT_BASE)
P1['fig_pie'].update_layout(title=dict(text="客户分层占比", font=dict(color=COLORS['text'], size=14)))

# 近7天日报表
_recent7 = _daily.nlargest(7, 'date').sort_values('date', ascending=False)
P1['daily_table'] = _recent7[['date','pv','uv','gmv','payment_rate','avg_order_value']].copy()
P1['daily_table']['date'] = P1['daily_table']['date'].dt.strftime('%Y-%m-%d')
P1['daily_table']['payment_rate'] = (P1['daily_table']['payment_rate']*100).round(1).astype(str)+'%'
P1['daily_table']['gmv'] = P1['daily_table']['gmv'].round(0).astype(int)
P1['daily_table']['avg_order_value'] = P1['daily_table']['avg_order_value'].round(1)
P1['daily_table'].columns = ['日期','PV','UV','GMV','付费率','客单价']
del _ub, _orders1, _paid1, _daily, _dp, _recent30, _rfm, _seg
print("✅ (253万行)")

# ---------- 项目二 ----------
print("  [2/4] 加载项目二：老用户健康...", end=" ", flush=True)
_conn = sqlite3.connect(os.path.join(BASE_DIR, '项目二：老用户激活与价值提升', 'user_activation.db'))
_users2 = pd.read_sql("SELECT * FROM users", _conn)
_orders2 = pd.read_sql("SELECT * FROM orders", _conn)
_items2 = pd.read_sql("SELECT * FROM order_items", _conn)
_prods2 = pd.read_sql("SELECT * FROM products", _conn)
_conn.close()
_orders2['create_time'] = pd.to_datetime(_orders2['create_time'])
_users2['registration_date'] = pd.to_datetime(_users2['registration_date'])

_valid2 = _orders2[_orders2['order_status'].isin(['paid','shipped','completed'])]
_df2 = _valid2.merge(_items2, on='order_id', how='left').merge(_prods2, on='product_id', how='left')
_rfm2 = _df2.dropna(subset=['order_id']).groupby('user_id').agg(
    last_purchase=('create_time','max'), frequency=('order_id','nunique'), monetary=('amount','sum'),
    category_diversity=('category_id','nunique'), category_2_orders=('category_id', lambda x: (x==2).sum())).reset_index()
_rfm2['recency'] = (NOW - _rfm2['last_purchase']).dt.days
_rfm2['growth'] = _rfm2['category_diversity'] * _rfm2['frequency']
_rfm2['r_score'] = safe_qcut(_rfm2['recency'], 5, [5,4,3,2,1])
_rfm2['f_score'] = safe_qcut(_rfm2['frequency'], 5, [1,2,3,4,5])
_rfm2['m_score'] = safe_qcut(_rfm2['monetary'], 5, [1,2,3,4,5])
_rfm2['g_score'] = safe_qcut(_rfm2['growth'], 5, [1,2,3,4,5])
_score2 = _rfm2['r_score'].astype(int)+_rfm2['f_score'].astype(int)+_rfm2['m_score'].astype(int)+_rfm2['g_score'].astype(int)
_rfm2['segment'] = np.select([_score2>=16, _score2>=12, _score2>=8], ['高价值深耕用户','高潜唤醒用户','成长型用户'], default='流失风险用户')

P2 = {'total_users': len(_rfm2)}
for _segname in ['高价值深耕用户','高潜唤醒用户','成长型用户','流失风险用户']:
    P2[f'count_{_segname}'] = len(_rfm2[_rfm2['segment']==_segname])

_seg2 = _rfm2.groupby('segment').agg(count=('user_id','nunique'), avg_recency=('recency','mean'), avg_frequency=('frequency','mean'), avg_monetary=('monetary','mean')).reset_index()

P2['fig_donut'] = px.pie(_seg2, values='count', names='segment', hole=0.6, color_discrete_sequence=COLORS['palette'])
P2['fig_donut'].update_traces(textinfo='percent+label')
P2['fig_donut'].update_layout(**CHART_LAYOUT_BASE)
P2['fig_donut'].update_layout(title=dict(text="用户分层占比", font=dict(color=COLORS['text'], size=14)))

_sgmv = _rfm2.groupby('segment')['monetary'].sum().reset_index()
_sgmv.columns=['segment','gmv']
_sgmv['pct'] = (_sgmv['gmv']/_sgmv['gmv'].sum()*100).round(1)
P2['fig_bar'] = px.bar(_sgmv, x='segment', y='gmv', text='pct', color='segment', color_discrete_sequence=COLORS['palette'])
P2['fig_bar'].update_traces(texttemplate='%{text}%', textposition='outside')
P2['fig_bar'].update_layout(**CHART_LAYOUT_BASE)
P2['fig_bar'].update_layout(title=dict(text="各分层 GMV 贡献", font=dict(color=COLORS['text'], size=14)))

_user_seg = _rfm2[['user_id','segment']]
_oseg = _valid2.merge(_user_seg, on='user_id', how='inner')
_oseg['month'] = _oseg['create_time'].dt.strftime('%Y-%m')
_monthly_seg = _oseg.groupby(['month','segment'])['amount'].sum().reset_index()
_monthly_seg['month'] = pd.to_datetime(_monthly_seg['month']+'-01')
_mt = _monthly_seg.groupby('month')['amount'].sum().reset_index(name='total')
_monthly_seg = _monthly_seg.merge(_mt, on='month')
_monthly_seg['pct'] = _monthly_seg['amount']/_monthly_seg['total']*100
P2['fig_monthly'] = px.line(_monthly_seg.sort_values('month'), x='month', y='pct', color='segment',
    color_discrete_sequence=COLORS['palette'], labels={'pct':'GMV 占比 (%)','month':'月份','segment':'分层'})
P2['fig_monthly'].update_traces(mode='lines+markers')
P2['fig_monthly'].update_layout(**CHART_LAYOUT_BASE)
P2['fig_monthly'].update_layout(title=dict(text="各分层月度 GMV 占比趋势", font=dict(color=COLORS['text'], size=14)))

_ucats = _df2.dropna(subset=['order_id']).groupby('user_id').agg(
    cat_1_orders=('category_id',lambda x:(x==1).sum()), cat_2_orders=('category_id',lambda x:(x==2).sum()),
    total_orders=('order_id','nunique')).reset_index()
_ucats = _ucats.merge(_user_seg, on='user_id', how='left')
P2['fig_scatter'] = px.scatter(_ucats, x='cat_1_orders', y='cat_2_orders', color='segment', size='total_orders',
    color_discrete_sequence=COLORS['palette'], hover_data=['user_id'],
    labels={'cat_1_orders':'品类1订单数','cat_2_orders':'品类2订单数','segment':'分层'})
P2['fig_scatter'].update_layout(**CHART_LAYOUT_BASE)
P2['fig_scatter'].update_layout(title=dict(text="用户品类拓展分布", font=dict(color=COLORS['text'], size=14)))

_profile = _seg2.round(1)
_profile.columns = ['分层','人数','平均Recency(天)','平均购买频次','平均消费金额']
P2['profile_table'] = _profile
del _users2, _orders2, _items2, _prods2, _valid2, _df2, _rfm2, _oseg, _ucats
print("✅ (12,000用户)")

# ---------- 项目三 ----------
print("  [3/4] 加载项目三：投放 ROI...", end=" ", flush=True)
_conn = sqlite3.connect(os.path.join(BASE_DIR, '项目三：各平台ROI预算重新分配', 'roi_allocation.db'))
_camps = pd.read_sql("SELECT * FROM ad_campaigns", _conn)
_attr = pd.read_sql("SELECT * FROM attribution_data", _conn)
_conn.close()
_camps['campaign_date'] = pd.to_datetime(_camps['campaign_date'])

_ps = _camps.groupby('platform').agg(spend=('spend','sum'), revenue=('revenue','sum'),
    impressions=('impressions','sum'), clicks=('clicks','sum'), conversions=('conversions','sum')).reset_index()
_ps['ROI'] = _ps['revenue'] / _ps['spend']
_ps['CPC'] = _ps['spend'] / _ps['clicks']
_ps['CPA'] = _ps['spend'] / _ps['conversions']

P3 = {
    'total_spend': _ps['spend'].sum(),
    'total_revenue': _ps['revenue'].sum(),
}
P3['overall_roi'] = P3['total_revenue'] / P3['total_spend'] if P3['total_spend'] > 0 else 0
P3['avg_cpa'] = P3['total_spend'] / _ps['conversions'].sum() if _ps['conversions'].sum() > 0 else 0
P3['avg_cpc'] = P3['total_spend'] / _ps['clicks'].sum() if _ps['clicks'].sum() > 0 else 0

P3['fig_roi_bar'] = px.bar(_ps.sort_values('ROI', ascending=False), x='platform', y='ROI',
    color='platform', text=_ps['ROI'].round(2), color_discrete_sequence=COLORS['palette'])
P3['fig_roi_bar'].update_traces(texttemplate='%{text}', textposition='outside')
P3['fig_roi_bar'].add_hline(y=1, line_dash="dash", line_color=COLORS['danger'],
    annotation_text="盈亏线 ROI=1", annotation_position="right")
P3['fig_roi_bar'].update_layout(**CHART_LAYOUT_BASE)
P3['fig_roi_bar'].update_layout(title=dict(text="各平台 ROI 对比", font=dict(color=COLORS['text'], size=14)))

_avg_cpc = _ps['CPC'].mean()
_avg_roi = _ps['ROI'].mean()
P3['fig_quad'] = px.scatter(_ps, x='CPC', y='ROI', size='spend', color='platform', text='platform',
    size_max=55, color_discrete_sequence=COLORS['palette'],
    hover_data={'spend':':,.0f','revenue':':,.0f','conversions':True})
P3['fig_quad'].add_hline(y=_avg_roi, line_dash="dash", line_color=COLORS['warning'], annotation_text=f"平均 ROI={_avg_roi:.2f}")
P3['fig_quad'].add_vline(x=_avg_cpc, line_dash="dash", line_color=COLORS['warning'], annotation_text=f"平均 CPC=¥{_avg_cpc:.2f}")
P3['fig_quad'].update_traces(textposition='top center')
_xr = [_ps['CPC'].min()*0.9, _ps['CPC'].max()*1.1]
_yr = [_ps['ROI'].min()*0.9, _ps['ROI'].max()*1.1]
P3['fig_quad'].update_layout(annotations=[
    dict(x=_avg_cpc/2, y=_yr[1]*1.05, text="低成本引流", showarrow=False, font=dict(color=COLORS['muted'],size=11)),
    dict(x=(_avg_cpc+_xr[1])/2, y=_yr[1]*1.05, text="高效拉新场", showarrow=False, font=dict(color=COLORS['success'],size=11)),
    dict(x=_avg_cpc/2, y=_yr[0]*0.95, text="需优化", showarrow=False, font=dict(color=COLORS['danger'],size=11)),
    dict(x=(_avg_cpc+_xr[1])/2, y=_yr[0]*0.95, text="高价值种草地", showarrow=False, font=dict(color=COLORS['primary'],size=11)),
])
P3['fig_quad'].update_layout(**CHART_LAYOUT_BASE)
P3['fig_quad'].update_layout(title=dict(text="四象限分析：CPC × ROI", font=dict(color=COLORS['text'], size=14)))

_camps['month'] = _camps['campaign_date'].dt.strftime('%Y-%m')
_mspend = _camps.groupby(['month','platform'])['spend'].sum().reset_index()
_mspend['month'] = pd.to_datetime(_mspend['month']+'-01')
P3['fig_stacked'] = px.bar(_mspend.sort_values('month'), x='month', y='spend', color='platform',
    color_discrete_sequence=COLORS['palette'], labels={'spend':'花费 (元)','month':'月份'})
P3['fig_stacked'].update_layout(**CHART_LAYOUT_BASE)
P3['fig_stacked'].update_layout(title=dict(text="各平台月度花费趋势", font=dict(color=COLORS['text'], size=14)))

_ac = _attr.groupby('platform').agg(total_attributions=('user_id','nunique'), last_click=('days_to_conversion',lambda x:(x<=1).sum())).reset_index()
P3['fig_attr'] = go.Figure()
P3['fig_attr'].add_trace(go.Bar(x=_ac['platform'], y=_ac['total_attributions'], name='归因转化', marker_color=COLORS['primary']))
P3['fig_attr'].add_trace(go.Bar(x=_ac['platform'], y=_ac['last_click'], name='末次点击', marker_color=COLORS['accent']))
P3['fig_attr'].update_layout(**CHART_LAYOUT_BASE)
P3['fig_attr'].update_layout(title=dict(text="归因分析", font=dict(color=COLORS['text'], size=14)))

_ps['spend_pct'] = (_ps['spend']/P3['total_spend']*100).round(1)
_bgt = _ps[['platform','spend','revenue','ROI','CPC','CPA','spend_pct']].round(2)
_bgt.columns = ['平台','花费','收入','ROI','CPC','CPA','花费占比%']
P3['budget_table'] = _bgt
del _camps, _attr, _ps
print("✅ (1,284条投放)")

# ---------- 项目四 ----------
print("  [4/4] 加载项目四：产品健康度...", end=" ", flush=True)
_conn = sqlite3.connect(os.path.join(BASE_DIR, '项目四：产品组合分析', 'product_portfolio.db'))
_prods4 = pd.read_sql("SELECT * FROM products", _conn)
_sales4 = pd.read_sql("SELECT * FROM sales_data", _conn)
_inv4 = pd.read_sql("SELECT * FROM inventory_data", _conn)
_conn.close()
_sales4['sale_date'] = pd.to_datetime(_sales4['sale_date'])
_prods4['launch_date'] = pd.to_datetime(_prods4['launch_date'])

_ps4 = _sales4.groupby('product_id').agg(total_volume=('sales_volume','sum'), total_amount=('sales_amount','sum')).reset_index()
_pm = _prods4.merge(_ps4, on='product_id', how='left').fillna(0)
_pm = _pm.merge(_inv4, on='product_id', how='left')
_pm['gross_profit'] = _pm['total_amount'] - _pm['cost']*_pm['total_volume']
_pm['gross_margin'] = (_pm['gross_profit']/_pm['total_amount'].replace(0,np.nan)).fillna(0)
_pm['sell_through_rate'] = (_pm['total_volume']/(_pm['total_volume']+_pm['current_stock'])).clip(0,1)
_pm['segment'] = np.select(
    [(_pm['sell_through_rate']>0.55)&(_pm['gross_margin']>0.35),
     (_pm['sell_through_rate']>0.35)&(_pm['gross_margin']>0.25),
     _pm['sell_through_rate']>0.15],
    ['爆款','畅销款','一般款'], default='滞销款')
_pm['avg_daily'] = _pm['total_volume']/30
_pm['reorder_point'] = _pm['avg_daily']*_pm['lead_time_days']+_pm['safety_stock']
_pm['suggested_reorder'] = np.ceil(_pm['avg_daily']*(_pm['lead_time_days']+7)-_pm['current_stock']).clip(0)
_pm['needs_replenishment'] = _pm['current_stock'] < _pm['reorder_point']
_pm['inventory_value'] = _pm['cost']*_pm['current_stock']

P4 = {
    'total_products': len(_pm),
    'hit_products': len(_pm[_pm['segment']=='爆款']),
    'dead_products': len(_pm[_pm['segment']=='滞销款']),
    'total_inventory_value': _pm['inventory_value'].sum(),
    'needs_replen': _pm['needs_replenishment'].sum(),
}

P4['fig_bubble'] = px.scatter(_pm, x='sell_through_rate', y='gross_margin',
    size='total_amount', color='segment', text=_pm['product_name'].str[:6], size_max=45,
    color_discrete_map={'爆款':COLORS['success'],'畅销款':COLORS['primary'],'一般款':COLORS['warning'],'滞销款':COLORS['danger']},
    hover_data={'product_name':True,'total_volume':True,'total_amount':':,.0f','current_stock':True,'sell_through_rate':':.1%','gross_margin':':.1%'})
P4['fig_bubble'].add_hline(y=0.3, line_dash="dash", line_color=COLORS['muted'], annotation_text="毛利率=30%")
P4['fig_bubble'].add_vline(x=0.4, line_dash="dash", line_color=COLORS['muted'], annotation_text="售罄率=40%")
P4['fig_bubble'].update_traces(textposition='top center')
P4['fig_bubble'].update_layout(**CHART_LAYOUT_BASE)
P4['fig_bubble'].update_layout(title=dict(text="产品健康度：售罄率 × 毛利率", font=dict(color=COLORS['text'], size=14)))

_sc4 = _pm['segment'].value_counts().reset_index()
_sc4.columns=['segment','count']
P4['fig_donut'] = px.pie(_sc4, values='count', names='segment', hole=0.6,
    color='segment', color_discrete_map={'爆款':COLORS['success'],'畅销款':COLORS['primary'],'一般款':COLORS['warning'],'滞销款':COLORS['danger']})
P4['fig_donut'].update_traces(textinfo='percent+label')
P4['fig_donut'].update_layout(**CHART_LAYOUT_BASE)
P4['fig_donut'].update_layout(title=dict(text="产品分级占比", font=dict(color=COLORS['text'], size=14)))

_plat = _sales4.groupby('platform')['sales_amount'].sum().reset_index()
P4['fig_platform_bar'] = px.bar(_plat.sort_values('sales_amount', ascending=False),
    x='platform', y='sales_amount', color='platform', text=_plat['sales_amount'].round(0),
    color_discrete_sequence=COLORS['palette'])
P4['fig_platform_bar'].update_traces(texttemplate='¥%{text:,.0f}', textposition='outside')
P4['fig_platform_bar'].update_layout(**CHART_LAYOUT_BASE)
P4['fig_platform_bar'].update_layout(title=dict(text="各平台销售金额", font=dict(color=COLORS['text'], size=14)))

_top5 = _pm[_pm['segment']=='爆款'].nlargest(5, 'total_amount')['product_id']
_ts = _sales4[_sales4['product_id'].isin(_top5)].merge(_pm[['product_id','product_name']], on='product_id')
_tsd = _ts.groupby(['sale_date','product_name'])['sales_volume'].sum().reset_index()
_tsd['sale_date'] = pd.to_datetime(_tsd['sale_date'])
_tsd = _tsd.sort_values(['product_name','sale_date'])
_tsd['ma7'] = _tsd.groupby('product_name')['sales_volume'].transform(lambda x: x.rolling(7,min_periods=1).mean())
P4['fig_top5'] = px.line(_tsd, x='sale_date', y='ma7', color='product_name',
    color_discrete_sequence=COLORS['palette'], labels={'ma7':'7日移动平均销量','sale_date':'日期','product_name':'产品'})
P4['fig_top5'].update_layout(**CHART_LAYOUT_BASE)
P4['fig_top5'].update_layout(title=dict(text="Top 5 爆款 7日移动平均销量趋势", font=dict(color=COLORS['text'], size=14)))

_repl = _pm[_pm['needs_replenishment']][['product_name','current_stock','reorder_point','suggested_reorder','lead_time_days','sell_through_rate','segment']].copy()
_repl.columns = ['产品名','当前库存','补货点','建议补货量','提前期(天)','售罄率','分级']
_repl = _repl.sort_values('建议补货量', ascending=False)
P4['replen_table'] = _repl
del _prods4, _sales4, _inv4, _pm
print("✅ (150产品)")

print("=" * 60)
print("  ✅ 全部数据预加载完成！启动 Web 服务...")
print("=" * 60)


# ============================================================
# 2. UI 组件
# ============================================================

def kpi_card(title, value, prefix="", suffix="", color=COLORS['primary']):
    display = f"{prefix}{value:,.0f}{suffix}" if isinstance(value, (int, float)) else f"{prefix}{value}{suffix}"
    return html.Div([
        html.Div(title, style={'color': COLORS['muted'], 'fontSize': 'clamp(11px, 1.1vw, 13px)', 'marginBottom': '6px'}),
        html.Div(display, style={'color': color, 'fontSize': 'clamp(20px, 2.5vw, 28px)', 'fontWeight': 'bold'}),
    ], style={
        'background': COLORS['card_bg'], 'borderRadius': '8px', 'padding': 'clamp(8px, 1.2vw, 16px)',
        'border': f'1px solid {COLORS["card_border"]}', 'textAlign': 'center',
        'flex': '1 1 140px', 'minWidth': '120px',
    })


def chart_box(title, figure):
    """图表卡片 — 宽度由 CSS Grid 控制"""
    figure.update_layout(**CHART_LAYOUT_BASE)
    figure.update_layout(title=dict(text=title, font=dict(color=COLORS['text'], size=14)))
    return html.Div([
        dcc.Graph(
            figure=figure,
            config={'displayModeBar': True, 'displaylogo': False, 'responsive': True},
            style={'width': '100%', 'height': '100%'},
        )
    ], className='chart-card')


def table_box(title, dataframe, columns=None, page_size=10, conditional=None):
    """表格卡片"""
    if columns is None:
        columns = [{'name': c, 'id': c} for c in dataframe.columns]
    style_cond = conditional or []
    return html.Div([
        html.H4(title, style={'color': COLORS['text'], 'marginBottom': '8px', 'fontSize': 'clamp(12px, 1.2vw, 14px)'}),
        dash_table.DataTable(
            data=dataframe.to_dict('records'),
            columns=columns,
            page_size=page_size,
            style_header={'backgroundColor': COLORS['card_border'], 'color': COLORS['text'],
                          'fontWeight': 'bold', 'fontSize': '12px'},
            style_cell={'backgroundColor': COLORS['card_bg'], 'color': COLORS['text'],
                        'border': '1px solid rgba(255,255,255,0.05)', 'textAlign': 'center',
                        'fontSize': 'clamp(10px, 0.9vw, 12px)', 'padding': '6px'},
            style_data_conditional=style_cond,
        )
    ], className='chart-card')


# ============================================================
# 3. 四项目布局（纯组装，无数据计算）
# ============================================================

def layout_project1():
    data = P1
    return html.Div([
        # KPI 行：flex wrap 响应式
        html.Div([
            kpi_card("📊 总 PV", data['pv'], color=COLORS['primary']),
            kpi_card("👤 总 UV", data['uv'], color=COLORS['success']),
            kpi_card("💳 付费用户", data['paid_users'], color=COLORS['warning']),
            kpi_card("💰 GMV", data['gmv'], prefix="¥", color=COLORS['accent']),
            kpi_card("📈 付费率", data['payment_rate']*100, suffix="%", color=COLORS['palette'][4]),
            kpi_card("🛒 客单价", data['avg_order_value'], prefix="¥", color=COLORS['palette'][5]),
        ], className='kpi-row'),

        # 趋势图（全宽）
        html.Div([chart_box("近 30 天 PV / UV / GMV 趋势", data['fig_trend'])], className='chart-full'),

        # 漏斗 + 饼图（响应式双列）
        html.Div([
            chart_box("转化漏斗", data['fig_funnel']),
            chart_box("客户分层占比", data['fig_pie']),
        ], className='chart-grid-2'),

        # 转化率
        html.Div([
            html.Strong("环节转化率："),
            html.Span(" | ".join(data['rates']), style={'color': COLORS['muted']})
        ], style={'background': COLORS['card_bg'], 'padding': '12px 16px', 'borderRadius': '8px',
                   'fontSize': 'clamp(12px, 1vw, 14px)'}),

        # 近 7 天日报
        table_box("近 7 天日报明细", data['daily_table'], columns=[
            {'name': c, 'id': c} for c in data['daily_table'].columns
        ], page_size=7, conditional=[
            {'if': {'column_id': 'GMV'}, 'color': COLORS['accent']},
            {'if': {'column_id': 'PV'}, 'color': COLORS['primary']},
        ]),
    ])


def layout_project2():
    data = P2
    return html.Div([
        html.Div([
            kpi_card("👥 老用户总数", data['total_users'], color=COLORS['primary']),
            kpi_card("⭐ 高价值深耕", data['count_高价值深耕用户'], color=COLORS['success']),
            kpi_card("📈 高潜唤醒", data['count_高潜唤醒用户'], color=COLORS['warning']),
            kpi_card("⚠️ 流失风险", data['count_流失风险用户'], color=COLORS['danger']),
        ], className='kpi-row'),

        html.Div([
            chart_box("用户分层占比", data['fig_donut']),
            chart_box("各分层 GMV 贡献", data['fig_bar']),
        ], className='chart-grid-2'),

        html.Div([chart_box("各分层月度 GMV 占比趋势", data['fig_monthly'])], className='chart-full'),

        html.Div([
            chart_box("用户品类拓展分布", data['fig_scatter']),
            table_box("分层画像", data['profile_table'], columns=[
                {'name': c, 'id': c} for c in data['profile_table'].columns
            ]),
        ], className='chart-grid-2'),
    ])


def layout_project3():
    data = P3
    return html.Div([
        html.Div([
            kpi_card("💸 总花费", data['total_spend'], prefix="¥", color=COLORS['accent']),
            kpi_card("💰 总收入", data['total_revenue'], prefix="¥", color=COLORS['success']),
            kpi_card("📊 全域 ROI", data['overall_roi'], color=COLORS['primary']),
            kpi_card("🎯 平均 CPA", data['avg_cpa'], prefix="¥", color=COLORS['warning']),
            kpi_card("🖱️ 平均 CPC", data['avg_cpc'], prefix="¥", color=COLORS['palette'][4]),
        ], className='kpi-row'),

        html.Div([
            chart_box("各平台 ROI 对比（红线 = 盈亏线）", data['fig_roi_bar']),
            chart_box("四象限分析：CPC × ROI", data['fig_quad']),
        ], className='chart-grid-2'),

        html.Div([chart_box("各平台月度花费趋势", data['fig_stacked'])], className='chart-full'),

        html.Div([
            chart_box("归因分析：末次点击 vs 全域归因", data['fig_attr']),
            table_box("预算分配明细", data['budget_table'], columns=[
                {'name': c, 'id': c} for c in data['budget_table'].columns
            ], conditional=[
                {'if': {'filter_query': '{ROI} < 1', 'column_id': 'ROI'}, 'color': COLORS['danger']},
                {'if': {'filter_query': '{ROI} >= 1', 'column_id': 'ROI'}, 'color': COLORS['success']},
            ]),
        ], className='chart-grid-2'),
    ])


def layout_project4():
    data = P4
    return html.Div([
        html.Div([
            kpi_card("📦 产品总数", data['total_products'], color=COLORS['primary']),
            kpi_card("🔥 爆款数", data['hit_products'], color=COLORS['success']),
            kpi_card("❄️ 滞销品数", data['dead_products'], color=COLORS['danger']),
            kpi_card("💎 库存总价值", data['total_inventory_value'], prefix="¥", color=COLORS['accent']),
            kpi_card("📋 需补货", data['needs_replen'], color=COLORS['warning']),
        ], className='kpi-row'),

        html.Div([chart_box("产品健康度气泡图（X=售罄率, Y=毛利率, 气泡=销售额）", data['fig_bubble'])], className='chart-full'),

        html.Div([
            chart_box("产品分级占比", data['fig_donut']),
            chart_box("各平台销售金额", data['fig_platform_bar']),
        ], className='chart-grid-2'),

        html.Div([chart_box("Top 5 爆款 7日移动平均销量趋势", data['fig_top5'])], className='chart-full'),

        table_box("需要补货的产品清单", data['replen_table'].head(20), columns=[
            {'name': c, 'id': c} for c in data['replen_table'].columns
        ], page_size=10, conditional=[
            {'if': {'filter_query': '{分级} = "爆款"', 'column_id': '分级'}, 'color': COLORS['success']},
            {'if': {'filter_query': '{分级} = "滞销款"', 'column_id': '分级'}, 'color': COLORS['danger']},
        ]),
    ])


# ============================================================
# 4. Dash 应用 & CSS 注入
# ============================================================

app = Dash(__name__, title='跃动体育 · 数据看板', suppress_callback_exceptions=True)

# 响应式 CSS 样式
app.index_string = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>跃动体育 · 数据看板</title>
    <style>
        :root {
            --bg: #1a1a2e;
            --card: #16213e;
            --border: #0f3460;
            --text: #ecf0f1;
            --accent: #e94560;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
            color: var(--text);
        }

        /* ===== KPI 行：自动折行 ===== */
        .kpi-row {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 16px;
        }

        /* ===== 图表网格：响应式双列 ===== */
        .chart-grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(min(100%, 480px), 1fr));
            gap: 16px;
            margin-bottom: 16px;
        }

        /* ===== 全宽图表 ===== */
        .chart-full {
            margin-bottom: 16px;
        }

        /* ===== 图表卡片容器 ===== */
        .chart-card {
            background: var(--card);
            border-radius: 8px;
            border: 1px solid var(--border);
            padding: 12px;
            min-width: 0;
        }

        /* ===== Dash Graph 自适应 ===== */
        .chart-card .js-plotly-plot, .chart-card .plot-container {
            width: 100% !important;
        }

        /* ===== Dash Tab 样式 ===== */
        .dash-tabs {
            margin: 0 24px;
        }
        .dash-tab {
            background: var(--card) !important;
            color: #95a5a6 !important;
            border: none !important;
            padding: 12px 24px !important;
            font-weight: bold !important;
            font-size: clamp(12px, 1.1vw, 14px) !important;
        }
        .dash-tab--selected {
            background: var(--accent) !important;
            color: white !important;
        }

        /* ===== 表格自适应 ===== */
        .dash-spreadsheet .dash-cell {
            font-size: clamp(10px, 0.85vw, 12px) !important;
        }

        /* ===== 移动端适配 ===== */
        @media (max-width: 768px) {
            .chart-grid-2 {
                grid-template-columns: 1fr;
            }
            .kpi-row > div {
                flex: 1 1 45% !important;
            }
            .dash-tab {
                padding: 8px 12px !important;
                font-size: 11px !important;
            }
        }

        @media (max-width: 480px) {
            .kpi-row > div {
                flex: 1 1 100% !important;
            }
        }
    </style>
    {%metas%}
    {%css%}
</head>
<body>
    {%app_entry%}
    {%config%}
    {%scripts%}
    {%renderer%}
</body>
</html>'''

app.layout = html.Div([
    # 顶部标题栏
    html.Div([
        html.H1("🏀 跃动体育 · 数据看板", style={
            'margin': '0', 'fontSize': 'clamp(16px, 2vw, 24px)', 'flex': '1'}),
        html.Div([
            html.Span(f"最后刷新: {NOW.strftime('%Y-%m-%d %H:%M')}  "),
            html.Span("|", style={'margin': '0 8px'}),
            html.A("🔄 刷新数据", href="/", style={'color': COLORS['primary'], 'textDecoration': 'none'}),
        ], style={'color': COLORS['muted'], 'fontSize': 'clamp(11px, 0.9vw, 13px)', 'whiteSpace': 'nowrap'}),
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
              'padding': '12px 24px', 'background': COLORS['card_bg'],
              'borderBottom': f'2px solid {COLORS["accent"]}', 'flexWrap': 'wrap', 'gap': '8px'}),

    # 四标签页
    dcc.Tabs(id='main-tabs', value='tab1', children=[
        dcc.Tab(label='📊 项目一：日常运营', value='tab1'),
        dcc.Tab(label='👥 项目二：老用户健康', value='tab2'),
        dcc.Tab(label='💰 项目三：投放 ROI', value='tab3'),
        dcc.Tab(label='📦 项目四：产品健康度', value='tab4'),
    ]),

    # 加载指示器
    dcc.Loading(
        id="loading-spinner",
        type="cube",
        color=COLORS['accent'],
        children=html.Div(id='tab-content', style={'padding': 'clamp(8px, 1.5vw, 20px) 24px'}),
    ),
], style={'backgroundColor': COLORS['bg'], 'minHeight': '100vh'})


@app.callback(Output('tab-content', 'children'), Input('main-tabs', 'value'))
def render_tab(tab):
    """切换标签——数据已预加载，仅组装 HTML，毫秒级响应"""
    layouts = {
        'tab1': layout_project1,
        'tab2': layout_project2,
        'tab3': layout_project3,
        'tab4': layout_project4,
    }
    return layouts.get(tab, lambda: html.Div("加载中..."))()


# ============================================================
# 5. 启动
# ============================================================

if __name__ == '__main__':
    print()
    print("  启动地址: http://127.0.0.1:8050")
    print("  按 Ctrl+C 停止服务")
    print()
    app.run(debug=False, host='127.0.0.1', port=8050)
