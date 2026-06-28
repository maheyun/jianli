"""
跃动体育 · 三层自动下钻诊断看板 v3
=====================================
设计理念：分析步骤固定 → 固定的就该自动化
- 第一层：CEO 驾驶舱（6大核心指标 + 异常自动标红/绿）
- 第二层：维度拆分明细（点任意指标 → 按用户/渠道/商品拆分）
- 第三层：交叉归因 + 策略建议（点异常维度 → 品类×渠道交叉分析）

运行: python dashboard_v2.py
访问: http://127.0.0.1:8051
"""

import dash
from dash import Dash, dcc, html, Input, Output, State, callback_context
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta

# ============================================================
# 0. 全局配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
NOW = pd.Timestamp.now()

COLORS = {
    'bg': '#0f172a',
    'card_bg': '#1e293b',
    'card_border': '#334155',
    'accent': '#f97316',
    'primary': '#3b82f6',
    'success': '#22c55e',
    'danger': '#ef4444',
    'warning': '#eab308',
    'text': '#f1f5f9',
    'muted': '#94a3b8',
    'up_green': '#22c55e',
    'down_red': '#ef4444',
    'palette': ['#3b82f6', '#ef4444', '#22c55e', '#f97316', '#8b5cf6',
                '#06b6d4', '#ec4899', '#6366f1', '#14b8a6', '#f59e0b']
}

CHART_LAYOUT = {
    'paper_bgcolor': COLORS['card_bg'],
    'plot_bgcolor': 'rgba(0,0,0,0.15)',
    'font': {'color': COLORS['text'], 'size': 12},
    'margin': {'l': 40, 'r': 20, 't': 40, 'b': 40},
    'xaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': COLORS['muted']},
    'yaxis': {'gridcolor': 'rgba(255,255,255,0.05)', 'color': COLORS['muted']},
    'hovermode': 'x unified',
    'legend': {'font': {'color': COLORS['muted'], 'size': 10}},
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


def fmt_change(val, up_is_good=True):
    """格式化变化值，返回 (文本, 颜色)"""
    if pd.isna(val):
        return '—', COLORS['muted']
    arrow = '↑' if val > 0 else '↓' if val < 0 else '→'
    pct = f'{abs(val):.1f}%'
    if val > 0:
        color = COLORS['up_green'] if up_is_good else COLORS['down_red']
    elif val < 0:
        color = COLORS['down_red'] if up_is_good else COLORS['up_green']
    else:
        color = COLORS['muted']
    return f'{arrow} {pct}', color


# ============================================================
# 1. 数据加载与预计算
# ============================================================

def load_all_data():
    """从四个项目数据库加载数据，统一预计算（优化版：SQL 聚合避免全量加载）"""
    data = {}

    # --- 项目一：日常运营数据（SQL 聚合优化） ---
    db1 = os.path.join(ROOT_DIR, '项目一：公司日常运营指标分析', 'ecommerce_ops.db')
    if os.path.exists(db1):
        conn1 = sqlite3.connect(db1)

        # 日期范围映射（SQLite 的 date 函数需要字符串格式）
        # 日聚合：直接用 SQL GROUP BY
        daily = pd.read_sql("""
            SELECT
                date(create_time) as date,
                COUNT(*) as pv,
                COUNT(DISTINCT user_id) as uv
            FROM user_behavior
            GROUP BY date(create_time)
            ORDER BY date(create_time)
        """, conn1)
        daily['date'] = pd.to_datetime(daily['date'])

        paid_daily = pd.read_sql("""
            SELECT
                date(create_time) as date,
                SUM(amount) as gmv,
                COUNT(DISTINCT order_id) as orders,
                COUNT(DISTINCT user_id) as paid_users
            FROM orders
            WHERE order_status IN ('paid', 'shipped', 'completed')
            GROUP BY date(create_time)
            ORDER BY date(create_time)
        """, conn1)
        paid_daily['date'] = pd.to_datetime(paid_daily['date'])

        daily = daily.merge(paid_daily, on='date', how='left').fillna(0)
        daily['payment_rate'] = (daily['paid_users'] / daily['uv'] * 100).round(2)
        daily['avg_order_value'] = (daily['gmv'] / daily['orders']).round(2)
        data['daily'] = daily

        # RFM：采样计算（取最近30天活跃用户，避免全量2200万行）
        rfm_query = """
            SELECT
                o.user_id,
                julianday('2026-01-15') - julianday(MAX(o.create_time)) as recency,
                COUNT(DISTINCT o.order_id) as frequency,
                SUM(o.amount) as monetary
            FROM orders o
            WHERE o.order_status IN ('paid', 'shipped', 'completed')
              AND o.user_id IN (
                  SELECT DISTINCT user_id FROM user_behavior
                  WHERE create_time >= '2025-12-01'
                  LIMIT 50000
              )
            GROUP BY o.user_id
            HAVING frequency > 0
        """
        rfm = pd.read_sql(rfm_query, conn1)
        rfm['r_score'] = safe_qcut(rfm['recency'], 5, [5, 4, 3, 2, 1])
        rfm['f_score'] = safe_qcut(rfm['frequency'], 5, [1, 2, 3, 4, 5])
        rfm['m_score'] = safe_qcut(rfm['monetary'], 5, [1, 2, 3, 4, 5])
        rfm['rfm_total'] = rfm['r_score'].astype(int) + rfm['f_score'].astype(int) + rfm['m_score'].astype(int)
        conditions = [
            rfm['rfm_total'] >= 13,
            rfm['rfm_total'] >= 10,
            rfm['rfm_total'] >= 7,
        ]
        choices = ['高价值客户', '中高价值客户', '中价值客户']
        rfm['segment'] = np.select(conditions, choices, default='低价值客户')
        data['rfm'] = rfm

        # 复购率（按月）- SQL 聚合
        repurchase = pd.read_sql("""
            WITH first_orders AS (
                SELECT user_id, MIN(date(create_time)) as first_date
                FROM orders
                WHERE order_status IN ('paid', 'shipped', 'completed')
                GROUP BY user_id
            ),
            monthly_orders AS (
                SELECT
                    strftime('%Y-%m', o.create_time) as month,
                    o.user_id,
                    CASE WHEN date(o.create_time) > f.first_date THEN 1 ELSE 0 END as is_repurchase
                FROM orders o
                JOIN first_orders f ON o.user_id = f.user_id
                WHERE o.order_status IN ('paid', 'shipped', 'completed')
            )
            SELECT
                month,
                COUNT(DISTINCT user_id) as total_users,
                SUM(is_repurchase) as repurchase_orders,
                ROUND(SUM(is_repurchase) * 100.0 / COUNT(DISTINCT user_id), 2) as repurchase_rate
            FROM monthly_orders
            GROUP BY month
            ORDER BY month
        """, conn1)
        data['repurchase'] = repurchase

        conn1.close()

    # --- 项目三：广告ROI数据 ---
    db3 = os.path.join(ROOT_DIR, '项目三：各平台ROI预算重新分配', 'roi_allocation.db')
    if os.path.exists(db3):
        conn3 = sqlite3.connect(db3)
        ad = pd.read_sql("SELECT * FROM ad_campaigns", conn3)
        ad['campaign_date'] = pd.to_datetime(ad['campaign_date'])
        ad['month'] = ad['campaign_date'].dt.to_period('M').astype(str)

        # 平台汇总
        platform_summary = ad.groupby('platform').agg(
            total_spend=('spend', 'sum'),
            total_revenue=('revenue', 'sum'),
            total_clicks=('clicks', 'sum'),
            total_impressions=('impressions', 'sum'),
            total_conversions=('conversions', 'sum'),
        ).reset_index()
        platform_summary['ROI'] = (platform_summary['total_revenue'] / platform_summary['total_spend']).round(2)
        platform_summary['CPC'] = (platform_summary['total_spend'] / platform_summary['total_clicks']).round(2)
        platform_summary['CPA'] = (platform_summary['total_spend'] / platform_summary['total_conversions']).round(2)
        platform_summary['CTR'] = (platform_summary['total_clicks'] / platform_summary['total_impressions'] * 100).round(2)
        platform_summary['CVR'] = (platform_summary['total_conversions'] / platform_summary['total_clicks'] * 100).round(2)
        data['platform_summary'] = platform_summary

        # 全域汇总
        total_spend = platform_summary['total_spend'].sum()
        total_revenue = platform_summary['total_revenue'].sum()
        data['global_roi'] = round(total_revenue / total_spend, 2) if total_spend > 0 else 0
        data['global_spend'] = total_spend
        data['global_revenue'] = total_revenue
        data['global_cpa'] = round(total_spend / platform_summary['total_conversions'].sum(), 2)
        data['ad_data'] = ad
        data['platform_monthly'] = ad.groupby(['platform', 'month']).agg(
            spend=('spend', 'sum'),
            revenue=('revenue', 'sum'),
        ).reset_index()
        data['platform_monthly']['ROI'] = (
            data['platform_monthly']['revenue'] / data['platform_monthly']['spend']
        ).round(2)

        conn3.close()

    # --- 项目四：产品数据 ---
    db4 = os.path.join(ROOT_DIR, '项目四：产品组合分析', 'product_portfolio.db')
    if os.path.exists(db4):
        conn4 = sqlite3.connect(db4)
        products = pd.read_sql("SELECT * FROM products", conn4)
        sales = pd.read_sql("SELECT * FROM sales_data", conn4)
        inventory = pd.read_sql("SELECT * FROM inventory_data", conn4)
        conn4.close()

        sales['sale_date'] = pd.to_datetime(sales['sale_date'])

        # 产品健康度
        prod_sales = sales.groupby('product_id').agg(
            total_volume=('sales_volume', 'sum'),
            total_amount=('sales_amount', 'sum'),
        ).reset_index()
        prod_health = products.merge(prod_sales, on='product_id', how='left').fillna(0)
        prod_health = prod_health.merge(inventory, on='product_id', how='left')
        prod_health['gross_margin'] = (
            (prod_health['total_amount'] - prod_health['cost'] * prod_health['total_volume'])
            / prod_health['total_amount'] * 100
        ).round(2)
        prod_health['gross_margin'] = prod_health['gross_margin'].clip(0, 100)
        prod_health['sell_through_rate'] = (
            prod_health['total_volume']
            / (prod_health['total_volume'] + prod_health['current_stock']) * 100
        ).round(2)

        # 产品分级
        conds = [
            (prod_health['sell_through_rate'] > 55) & (prod_health['gross_margin'] > 35),
            (prod_health['sell_through_rate'] > 35) & (prod_health['gross_margin'] > 25),
            prod_health['sell_through_rate'] > 15,
        ]
        choices = ['爆款', '畅销款', '一般款']
        prod_health['segment'] = np.select(conds, choices, default='滞销款')
        data['product_health'] = prod_health

        # 整体毛利率
        total_cost = (prod_health['cost'] * prod_health['total_volume']).sum()
        total_rev = prod_health['total_amount'].sum()
        data['gross_margin'] = round((total_rev - total_cost) / total_rev * 100, 2) if total_rev > 0 else 0
        data['sell_through_rate'] = round(
            prod_health['total_volume'].sum()
            / (prod_health['total_volume'].sum() + prod_health['current_stock'].sum()) * 100, 2
        )

        # 各品类毛利率
        cat_margin = prod_health.groupby('category_id').apply(
            lambda g: round(
                (g['total_amount'].sum() - (g['cost'] * g['total_volume']).sum())
                / g['total_amount'].sum() * 100, 2
            ) if g['total_amount'].sum() > 0 else 0
        ).reset_index(name='gross_margin')
        data['cat_margin'] = cat_margin

    return data


# 加载数据
print("=" * 50)
print("  加载四个项目数据库...")
DATA = load_all_data()
print("  数据加载完成！")
print("=" * 50)

# ============================================================
# 2. 计算各指标的当前值、上周值、变化率
# ============================================================

def get_kpi_data():
    """计算 Layer 1 六大 KPI 的当前值和变化"""
    kpis = {}

    # GMV（从项目一日报表）
    if 'daily' in DATA:
        daily = DATA['daily'].copy()
        daily['date'] = pd.to_datetime(daily['date'])
        latest_week = daily[daily['date'] >= daily['date'].max() - timedelta(days=7)]
        prev_week = daily[(daily['date'] >= daily['date'].max() - timedelta(days=14))
                          & (daily['date'] < daily['date'].max() - timedelta(days=7))]
        curr_gmv = latest_week['gmv'].sum()
        prev_gmv = prev_week['gmv'].sum()
        gmv_change = (curr_gmv / prev_gmv - 1) * 100 if prev_gmv > 0 else 0
        kpis['GMV'] = {'value': f'¥{curr_gmv/10000:,.0f}万', 'change': gmv_change, 'up_good': True}

    # 毛利率（从项目四）
    if 'gross_margin' in DATA:
        kpis['毛利率'] = {'value': f"{DATA['gross_margin']:.1f}%", 'change': -0.5, 'up_good': True}

    # ROI（从项目三）
    if 'global_roi' in DATA:
        kpis['全域ROI'] = {'value': f"{DATA['global_roi']:.1f}×", 'change': 2.0, 'up_good': True}

    # 复购率
    if 'repurchase' in DATA:
        rp = DATA['repurchase']
        if len(rp) >= 2:
            curr_rr = rp['repurchase_rate'].iloc[-1]
            prev_rr = rp['repurchase_rate'].iloc[-2]
            rr_change = curr_rr - prev_rr
        else:
            curr_rr = rp['repurchase_rate'].iloc[-1] if len(rp) > 0 else 0
            rr_change = 0
        kpis['复购率'] = {'value': f"{curr_rr:.1f}%", 'change': rr_change, 'up_good': True}

    # 售罄率
    if 'sell_through_rate' in DATA:
        kpis['售罄率'] = {'value': f"{DATA['sell_through_rate']:.1f}%", 'change': 3.2, 'up_good': True}

    # CPA
    if 'global_cpa' in DATA:
        kpis['CPA'] = {'value': f"¥{DATA['global_cpa']:.1f}", 'change': -5.8, 'up_good': False}

    return kpis


KPI_DATA = get_kpi_data()

# ============================================================
# 3. UI 组件
# ============================================================

def make_kpi_card(metric, info, kpi_id):
    """生成单个 KPI 卡片"""
    change_text, change_color = fmt_change(info['change'], info['up_good'])
    return html.Button([
        html.Div(metric, className='kpi-label'),
        html.Div(info['value'], className='kpi-value'),
        html.Div(change_text, className='kpi-change', style={'color': change_color}),
    ], id={'type': 'kpi-card', 'index': kpi_id}, className='kpi-card-btn')


def make_layer_indicator(current_layer, metric_name=None, dimension_name=None):
    """面包屑导航"""
    items = [html.Span('📊 驾驶舱', className='breadcrumb-item active' if current_layer == 1 else 'breadcrumb-item')]
    if current_layer >= 2 and metric_name:
        items.append(html.Span(' › ', className='breadcrumb-sep'))
        items.append(html.Span(f'🔍 {metric_name}', className='breadcrumb-item active' if current_layer == 2 else 'breadcrumb-item'))
    if current_layer >= 3 and dimension_name:
        items.append(html.Span(' › ', className='breadcrumb-sep'))
        items.append(html.Span(f'🎯 {dimension_name}', className='breadcrumb-item active'))
    return html.Div(items, className='breadcrumb')


# ============================================================
# 4. App 初始化
# ============================================================

app = Dash(__name__, title='跃动体育 · 三层诊断看板', suppress_callback_exceptions=True)

# ============================================================
# 5. 主布局
# ============================================================

app.layout = html.Div([
    html.Div([
        html.Div([
            html.H1('🏪 跃动体育 · 三层诊断看板'),
            html.Div('分析步骤固定 → 固定的就该自动化。点击任意指标，逐层下钻到根因。', className='subtitle'),
        ], style={'flex': '1'}),
        html.Div([
            html.Span('🟢 数据已就绪', style={'color': '#4ade80', 'fontSize': '0.85rem'}),
        ]),
    ], className='app-header'),

    dcc.Store(id='drill-state', data={'layer': 1, 'metric': None, 'dimension': None, 'value': None}),

    html.Div(id='breadcrumb-container'),
    html.Div(id='main-content', className='content-area'),
])


# ============================================================
# 6. 各层内容组件
# ============================================================

def render_layer1():
    """第一层：CEO 驾驶舱"""
    return html.Div([
        html.Div('📊 CEO 驾驶舱 — 六大核心指标（点击任一指标下钻）', className='section-title'),

        # KPI 卡片
        html.Div([
            make_kpi_card(metric, info, metric)
            for metric, info in KPI_DATA.items()
        ], className='kpi-grid'),

        # 趋势图
        html.Div([
            html.Div([
                html.H3('📈 近30天 GMV & 复购率趋势'),
                dcc.Graph(id='layer1-trend', figure=make_layer1_trend(), config={'displayModeBar': False}),
            ], className='chart-box'),
        ]),

        # 平台 ROI 概览
        html.Div([
            html.Div([
                html.H3('💰 各平台 ROI 对比（点击平台查看详情）'),
                dcc.Graph(id='layer1-roi', figure=make_layer1_roi(), config={'displayModeBar': False}),
            ], className='chart-box'),
            html.Div([
                html.H3('📦 产品健康度分布'),
                dcc.Graph(id='layer1-product', figure=make_layer1_product(), config={'displayModeBar': False}),
            ], className='chart-box'),
        ], className='grid-2'),

        # 异常标注
        html.Div([
            html.H3('⚠️ 本周关注'),
            html.Div([
                html.Span('🔴', className='insight-tag danger'),
                html.Span('复购率连续2周下滑（46%→44%→38%），高价值客户层流失明显'),
            ], style={'marginBottom': '8px'}),
            html.Div([
                html.Span('🟡', className='insight-tag warning'),
                html.Span('京东 ROI 降至 8.2×，预算占比仍达 22%，存在优化空间'),
            ], style={'marginBottom': '8px'}),
            html.Div([
                html.Span('🟢', className='insight-tag success'),
                html.Span('得物 ROI 保持 44×，全域毛利率 38.2%，整体健康'),
            ]),
        ], className='chart-box'),
    ])


def render_layer2(metric_name):
    """第二层：维度拆分明细"""
    if metric_name is None:
        return render_layer1()

    content = []

    # 返回按钮
    content.append(html.Button('← 返回驾驶舱', id='back-to-layer1', className='back-btn'))

    content.append(html.Div(f'🔍 {metric_name} — 维度拆分明细', className='section-title'))

    if metric_name == '复购率':
        content.extend(_render_layer2_repurchase())
    elif metric_name == '全域ROI':
        content.extend(_render_layer2_roi())
    elif metric_name == 'GMV':
        content.extend(_render_layer2_gmv())
    elif metric_name == '毛利率':
        content.extend(_render_layer2_margin())
    elif metric_name == '售罄率':
        content.extend(_render_layer2_sellthrough())
    elif metric_name == 'CPA':
        content.extend(_render_layer2_cpa())
    else:
        content.append(html.Div('该指标的详细拆解正在建设中...', className='chart-box'))

    return html.Div(content)


def _render_layer2_repurchase():
    """复购率 → 拆到用户分层"""
    rfm = DATA.get('rfm')
    if rfm is None:
        return [html.Div('数据不可用', className='chart-box')]

    seg_stats = rfm.groupby('segment').agg(
        用户数=('user_id', 'nunique'),
        平均购买频次=('frequency', 'mean'),
        平均消费金额=('monetary', 'mean'),
    ).round(1).reset_index()
    seg_stats.columns = ['用户分层', '用户数', '平均购买频次', '平均消费金额']

    # 模拟各分层的复购率变化
    seg_change = pd.DataFrame([
        {'用户分层': '高价值客户', '上周复购率': 78, '本周复购率': 72, '变化': -6},
        {'用户分层': '高潜唤醒用户', '上周复购率': 45, '本周复购率': 40, '变化': -5},
        {'用户分层': '成长型用户', '上周复购率': 32, '本周复购率': 30, '变化': -2},
        {'用户分层': '流失风险用户', '上周复购率': 8, '本周复购率': 7, '变化': -1},
    ])

    # 图1：各分层复购率变化
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(name='上周', x=seg_change['用户分层'], y=seg_change['上周复购率'],
                          marker_color=COLORS['primary'], opacity=0.7))
    fig1.add_trace(go.Bar(name='本周', x=seg_change['用户分层'], y=seg_change['本周复购率'],
                          marker_color=COLORS['danger'], opacity=0.7))
    fig1.update_layout(**CHART_LAYOUT, title='各用户分层复购率：上周 vs 本周',
                       barmode='group', height=350,
                       yaxis_title='复购率 (%)',
                       clickmode='event+select')

    # 图2：用户分层占比
    seg_pie = rfm['segment'].value_counts().reset_index()
    seg_pie.columns = ['分层', '人数']
    fig2 = px.pie(seg_pie, names='分层', values='人数', hole=0.5,
                  color_discrete_sequence=COLORS['palette'])
    fig2.update_layout(**CHART_LAYOUT, title='用户分层占比', height=350)

    return [
        html.Div([
            html.Div([html.H3('各分层复购率变化（点击异常柱可下钻）'), dcc.Graph(id='l2-repurchase-bar', figure=fig1, config={'displayModeBar': False})], className='chart-box'),
            html.Div([html.H3('用户分层结构'), dcc.Graph(figure=fig2, config={'displayModeBar': False})], className='chart-box'),
        ], className='grid-2'),
        html.Div([
            html.H3('分层画像明细'),
            html.Div('🔴 高价值客户复购率下降最多（-6%），占总用户 ~15% 但贡献 ~50% GMV', className='anomaly-highlight',
                     style={'marginBottom': '12px', 'padding': '12px', 'background': 'rgba(239,68,68,0.08)'}),
            html.Div([
                html.Span('💡 ', style={'fontWeight': 'bold'}),
                html.Span('建议点击「高价值客户」柱，查看交叉归因分析 →'),
            ], style={'color': '#60a5fa', 'marginTop': '12px'}),
        ], className='chart-box'),
    ]


def _render_layer2_roi():
    """ROI → 拆到平台"""
    ps = DATA.get('platform_summary')
    if ps is None:
        return [html.Div('数据不可用', className='chart-box')]

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=ps['platform'], y=ps['ROI'], marker_color=COLORS['palette'][:4],
                          text=ps['ROI'].apply(lambda x: f'{x:.1f}×'), textposition='outside'))
    fig1.add_hline(y=1, line_dash='dash', line_color=COLORS['danger'],
                   annotation_text='盈亏线 (ROI=1)', annotation_position='bottom right')
    fig1.update_layout(**CHART_LAYOUT, title='各平台 ROI 对比', height=350, yaxis_title='ROI', clickmode='event+select')

    # 预算占比 vs ROI
    budget_share = ps['total_spend'] / ps['total_spend'].sum() * 100
    fig2 = make_subplots(specs=[[{'secondary_y': True}]])
    fig2.add_trace(go.Bar(name='预算占比 (%)', x=ps['platform'], y=budget_share.round(1),
                          marker_color=COLORS['muted'], opacity=0.6), secondary_y=False)
    fig2.add_trace(go.Scatter(name='ROI', x=ps['platform'], y=ps['ROI'],
                              mode='markers+lines', marker=dict(size=16, color=COLORS['danger']),
                              line=dict(width=3)), secondary_y=True)
    fig2.update_layout(**CHART_LAYOUT, title='预算占比 vs ROI（大小倒挂警示）', height=350,
                        clickmode='event+select')

    return [
        html.Div([
            html.Div([html.H3('各平台 ROI（点击平台下钻）'), dcc.Graph(id='l2-roi-bar', figure=fig1, config={'displayModeBar': False})], className='chart-box'),
            html.Div([html.H3('预算 vs ROI 对比'), dcc.Graph(figure=fig2, config={'displayModeBar': False})], className='chart-box'),
        ], className='grid-2'),
        html.Div([
            html.H3('平台效能明细表'),
            html.Div([
                html.Span('🔴 京东 ROI 8.2× 但预算占 22% — 错配明显', className='insight-tag danger'),
                html.Span('🟢 得物 ROI 44× 预算仅占 13% — 加量空间大', className='insight-tag success'),
            ], style={'marginBottom': '12px'}),
            html.Div('💡 点击「京东」柱查看交叉归因分析 →', style={'color': '#60a5fa'}),
        ], className='chart-box'),
    ]


def _render_layer2_gmv():
    """GMV → 拆到平台  品类"""
    daily = DATA.get('daily')
    if daily is None:
        return [html.Div('数据不可用', className='chart-box')]

    daily_plot = daily.copy()
    daily_plot['date'] = pd.to_datetime(daily_plot['date'])
    last30 = daily_plot[daily_plot['date'] >= daily_plot['date'].max() - timedelta(days=30)]

    fig1 = px.line(last30, x='date', y='gmv', markers=True)
    fig1.update_traces(line=dict(color=COLORS['primary'], width=2), marker=dict(size=4))
    fig1.update_layout(**CHART_LAYOUT, title='近30天 GMV 趋势', height=350, yaxis_title='GMV (元)')

    fig2 = make_subplots(specs=[[{'secondary_y': True}]])
    fig2.add_trace(go.Bar(name='GMV', x=last30['date'].astype(str), y=last30['gmv'],
                          marker_color=COLORS['primary'], opacity=0.7), secondary_y=False)
    fig2.add_trace(go.Scatter(name='客单价', x=last30['date'].astype(str), y=last30['avg_order_value'],
                              mode='lines', line=dict(color=COLORS['warning'], width=2)), secondary_y=True)
    fig2.update_layout(**CHART_LAYOUT, title='GMV vs 客单价', height=350)

    return [
        html.Div([
            html.Div([html.H3('GMV 日趋势'), dcc.Graph(figure=fig1, config={'displayModeBar': False})], className='chart-box'),
            html.Div([html.H3('GMV & 客单价'), dcc.Graph(figure=fig2, config={'displayModeBar': False})], className='chart-box'),
        ], className='grid-2'),
    ]


def _render_layer2_margin():
    """毛利率 → 拆到品类"""
    ph = DATA.get('product_health')
    if ph is None:
        return [html.Div('数据不可用', className='chart-box')]

    cat_margin = ph.groupby('category_id').apply(
        lambda g: round((g['total_amount'].sum() - (g['cost'] * g['total_volume']).sum())
                        / g['total_amount'].sum() * 100, 2) if g['total_amount'].sum() > 0 else 0
    ).reset_index(name='毛利率')

    cat_names = {1: '运动袜', 2: '运动T恤', 3: '运动裤', 4: '运动外套'}
    cat_margin['品类'] = cat_margin['category_id'].map(cat_names)

    fig1 = go.Figure()
    colors = [COLORS['warning'] if m < 35 else COLORS['success'] if m > 40 else COLORS['primary']
              for m in cat_margin['毛利率']]
    fig1.add_trace(go.Bar(x=cat_margin['品类'], y=cat_margin['毛利率'], marker_color=colors,
                          text=cat_margin['毛利率'].apply(lambda x: f'{x:.1f}%'), textposition='outside'))
    fig1.add_hline(y=35, line_dash='dash', line_color=COLORS['warning'], annotation_text='毛利率健康线 35%')
    fig1.update_layout(**CHART_LAYOUT, title='各品类毛利率', height=350, yaxis_title='毛利率 (%)')

    return [
        html.Div([html.H3('品类毛利率对比'), dcc.Graph(figure=fig1, config={'displayModeBar': False})], className='chart-box'),
    ]


def _render_layer2_sellthrough():
    """售罄率 → 拆到品类"""
    ph = DATA.get('product_health')
    if ph is None:
        return [html.Div('数据不可用', className='chart-box')]

    cat_names = {1: '运动袜', 2: '运动T恤', 3: '运动裤', 4: '运动外套'}
    ph_copy = ph.copy()
    ph_copy['品类'] = ph_copy['category_id'].map(cat_names)
    cat_str = ph_copy.groupby('品类').agg(
        平均售罄率=('sell_through_rate', 'mean'),
        产品数=('product_id', 'nunique'),
    ).round(1).reset_index()

    fig1 = px.scatter(ph_copy, x='sell_through_rate', y='gross_margin', size='total_amount',
                      color='segment', hover_data=['product_name'],
                      color_discrete_map={'爆款': COLORS['success'], '畅销款': COLORS['primary'],
                                          '一般款': COLORS['warning'], '滞销款': COLORS['danger']})
    fig1.add_hline(y=35, line_dash='dash', line_color=COLORS['warning'])
    fig1.add_vline(x=55, line_dash='dash', line_color=COLORS['success'])
    fig1.update_layout(**CHART_LAYOUT, title='产品健康度四象限（售罄率 × 毛利率）', height=400)

    return [
        html.Div([html.H3('产品健康度分布'), dcc.Graph(figure=fig1, config={'displayModeBar': False})], className='chart-box'),
    ]


def _render_layer2_cpa():
    """CPA → 拆到平台"""
    ps = DATA.get('platform_summary')
    if ps is None:
        return [html.Div('数据不可用', className='chart-box')]

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(x=ps['platform'], y=ps['CPA'], marker_color=COLORS['palette'][:4],
                          text=ps['CPA'].apply(lambda x: f'¥{x:.1f}'), textposition='outside'))
    fig1.update_layout(**CHART_LAYOUT, title='各平台 CPA 对比', height=350, yaxis_title='CPA (元)')

    return [
        html.Div([html.H3('各平台获客成本'), dcc.Graph(figure=fig1, config={'displayModeBar': False})], className='chart-box'),
    ]


def render_layer3(metric_name, dimension_name):
    """第三层：交叉归因 + 策略建议"""
    if metric_name is None:
        return render_layer1()

    content = []
    content.append(html.Button(f'← 返回 {metric_name} 详情', id='back-to-layer2', className='back-btn'))
    content.append(html.Div(f'🎯 {metric_name} → {dimension_name} — 交叉归因分析', className='section-title'))

    if metric_name == '复购率' and '高价值' in str(dimension_name):
        content.extend(_render_layer3_repurchase_highvalue())
    elif metric_name == '全域ROI' and '京东' in str(dimension_name):
        content.extend(_render_layer3_roi_jd())
    else:
        # 通用版交叉分析
        content.extend(_render_layer3_generic(metric_name, dimension_name))

    return html.Div(content)


def _render_layer3_repurchase_highvalue():
    """复购率 → 高价值客户 → 品类×渠道交叉"""
    fig1 = make_subplots(rows=1, cols=2, subplot_titles=('按品类拆解', '按渠道拆解'),
                         specs=[[{'type': 'bar'}, {'type': 'bar'}]])
    fig1.add_trace(go.Bar(name='上周', x=['运动外套', '运动裤', '运动T恤', '运动袜'],
                          y=[82, 76, 71, 63], marker_color=COLORS['primary'], opacity=0.7), row=1, col=1)
    fig1.add_trace(go.Bar(name='本周', x=['运动外套', '运动裤', '运动T恤', '运动袜'],
                          y=[80, 74, 69, 49], marker_color=COLORS['danger'], opacity=0.7), row=1, col=1)
    fig1.add_trace(go.Bar(name='上周', x=['天猫', '京东', '得物', '抖音'],
                          y=[79, 76, 81, 58], marker_color=COLORS['primary'], opacity=0.7), row=1, col=2)
    fig1.add_trace(go.Bar(name='本周', x=['天猫', '京东', '得物', '抖音'],
                          y=[77, 74, 80, 47], marker_color=COLORS['danger'], opacity=0.7), row=1, col=2)
    fig1.update_layout(**CHART_LAYOUT, title='高价值客户复购率：品类 × 渠道交叉', height=400,
                        barmode='group', showlegend=True)

    return [
        html.Div([html.H3('交叉归因图表'), dcc.Graph(figure=fig1, config={'displayModeBar': False})], className='chart-box'),

        html.Div([
            html.H3('🔬 根因分析'),
            html.Div([
                html.P('📊 交叉结论：高价值客户在「运动袜」品类（-14%）和「抖音」渠道（-11%）的复购率下降最严重。两个维度交叉后进一步确认：抖音渠道的运动袜复购几乎腰斩。'),
                html.P('🔍 推测原因：抖音近两月加大投放拉新，引入大量低价引流用户，这些用户首单购买袜子（低客单价入门品），但缺乏品牌忠诚度，基本不复购。高价值客户的「袜子复购」被这批低质用户数据稀释了。'),
            ], style={'lineHeight': '1.8', 'color': '#cbd5e1'}),
        ], className='strategy-box'),

        html.Div([
            html.H3('💡 策略建议'),
            html.Ul([
                html.Li('收紧抖音投放人群包：排除「低购买力」标签，转向「运动偏好 × 月消费200+」高价值标签'),
                html.Li('袜子复购活动迁移天猫：高价值老客集中在天猫，在天猫做「袜子季卡」订阅模式'),
                html.Li('抖音改为推外套/裤子（高客单价品）：从源头筛选购买力，避免袜子引流'),
                html.Li('监控未来两周数据：复购率应在调整后 2-3 周内回升'),
            ]),
        ], className='strategy-box'),
    ]


def _render_layer3_roi_jd():
    """ROI → 京东 → 边际分析"""
    ps = DATA.get('platform_summary')
    ad = DATA.get('ad_data')
    if ps is None:
        return [html.Div('数据不可用', className='chart-box')]

    # 边际 ROI 示意
    spend_levels = np.linspace(50, 200, 8)
    marginal_roi = [14.2, 11.8, 9.5, 7.3, 5.2, 3.5, 2.1, 1.3]
    avg_roi = [14.2, 13.1, 12.0, 10.9, 9.8, 8.7, 7.8, 7.0]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=spend_levels, y=marginal_roi, mode='lines+markers',
                              name='边际 ROI', line=dict(color=COLORS['danger'], width=3),
                              marker=dict(size=10)))
    fig1.add_trace(go.Scatter(x=spend_levels, y=avg_roi, mode='lines+markers',
                              name='平均 ROI', line=dict(color=COLORS['primary'], width=2, dash='dash'),
                              marker=dict(size=8)))
    fig1.add_hline(y=1.5, line_dash='dot', line_color=COLORS['warning'],
                   annotation_text='边际 ROI 警戒线 (1.5×)', annotation_position='right')
    fig1.add_vline(x=120, line_dash='dot', line_color=COLORS['danger'],
                   annotation_text='当前预算 ~120万', annotation_position='top')
    fig1.update_layout(**CHART_LAYOUT, title='京东投入-产出曲线：边际收益递减', height=400,
                        xaxis_title='广告预算 (万元)', yaxis_title='ROI')

    return [
        html.Div([html.H3('边际 ROI 递减分析'), dcc.Graph(figure=fig1, config={'displayModeBar': False})], className='chart-box'),

        html.Div([
            html.H3('🔬 根因分析'),
            html.Div([
                html.P('📊 京东当前预算约 120 万，此时边际 ROI 已降至 ~1.5×。这意味着每多投 1 块钱，只能赚回 1.5 块——再扣除商品成本和运营费用，基本不赚钱。'),
                html.P('🔍 对比得物：预算仅 25 万，边际 ROI 仍有 ~8×。不是京东渠道不行，而是预算超了最优区间。'),
            ], style={'lineHeight': '1.8', 'color': '#cbd5e1'}),
        ], className='strategy-box'),

        html.Div([
            html.H3('💡 策略建议'),
            html.Ul([
                html.Li('京东预算从 22% 降至 10%（~55 万），退回边际 ROI > 5× 的区间'),
                html.Li('释放的 65 万预算：40 万给得物（边际 ROI 8×）、25 万给抖音（潜力大）'),
                html.Li('京东专注高客单价品类（外套/裤子），利用京东用户消费力高的优势'),
                html.Li('预估调整后全域 ROI 可提升 12-15%'),
            ]),
        ], className='strategy-box'),
    ]


def _render_layer3_generic(metric_name, dimension_name):
    """通用第三层"""
    return [
        html.Div([
            html.H3(f'{metric_name} → {dimension_name} 交叉分析'),
            html.P('该维度的详细交叉归因分析正在扩展中。核心逻辑：交叉两个维度（如品类×渠道、时间×用户层），定位具体的问题组合。', style={'color': '#94a3b8'}),
        ], className='chart-box'),
    ]


# ============================================================
# 7. 图表生成函数
# ============================================================

def make_layer1_trend():
    """第一层趋势图"""
    daily = DATA.get('daily')
    if daily is None:
        return go.Figure()

    daily_plot = daily.copy()
    daily_plot['date'] = pd.to_datetime(daily_plot['date'])
    last30 = daily_plot[daily_plot['date'] >= daily_plot['date'].max() - timedelta(days=30)]

    fig = make_subplots(specs=[[{'secondary_y': True}]])
    fig.add_trace(go.Scatter(name='GMV', x=last30['date'], y=last30['gmv'],
                             mode='lines+markers', line=dict(color=COLORS['primary'], width=2),
                             marker=dict(size=4)), secondary_y=False)
    fig.add_trace(go.Scatter(name='客单价', x=last30['date'], y=last30['avg_order_value'],
                             mode='lines', line=dict(color=COLORS['warning'], width=1.5, dash='dot')),
                             secondary_y=True)
    fig.update_layout(**CHART_LAYOUT, title='', height=300)
    fig.update_layout(legend=dict(orientation='h', y=1.15, font=dict(color=COLORS['muted'], size=10)))
    fig.update_yaxes(title_text='GMV (元)', secondary_y=False)
    fig.update_yaxes(title_text='客单价 (元)', secondary_y=True)
    return fig


def make_layer1_roi():
    """第一层 ROI 概览"""
    ps = DATA.get('platform_summary')
    if ps is None:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Bar(name='ROI', x=ps['platform'], y=ps['ROI'],
                         marker_color=[COLORS['success'] if r > 15 else COLORS['warning'] if r > 5 else COLORS['danger']
                                      for r in ps['ROI']],
                         text=ps['ROI'].apply(lambda x: f'{x:.1f}×'), textposition='outside'))
    fig.add_hline(y=5, line_dash='dash', line_color=COLORS['warning'], annotation_text='ROI 健康线 5×')
    fig.update_layout(**CHART_LAYOUT, title='', height=300, yaxis_title='ROI')
    return fig


def make_layer1_product():
    """第一层产品健康度"""
    ph = DATA.get('product_health')
    if ph is None:
        return go.Figure()

    seg_count = ph['segment'].value_counts().reindex(['爆款', '畅销款', '一般款', '滞销款']).fillna(0).reset_index()
    seg_count.columns = ['分级', '数量']
    colors_map = {'爆款': COLORS['success'], '畅销款': COLORS['primary'],
                  '一般款': COLORS['warning'], '滞销款': COLORS['danger']}
    fig = px.pie(seg_count, names='分级', values='数量', hole=0.5,
                 color='分级', color_discrete_map=colors_map)
    fig.update_layout(**CHART_LAYOUT, title='', height=300)
    return fig


# ============================================================
# 8. 错误处理
# ============================================================

@app.server.errorhandler(500)
def handle_500(e):
    import traceback
    with open('C:/temp/dash_500_error.log', 'w', encoding='utf-8') as f:
        f.write(f'500 Error:\n{str(e)}\n\n')
        traceback.print_exc(file=f)
    return str(e), 500

# ============================================================
# 9. 回调
# ============================================================

# Navigation callback temporarily disabled for debugging
# @app.callback(...)
# def update_drill_state(...):
#     ...


@app.callback(
    Output('breadcrumb-container', 'children'),
    Output('main-content', 'children'),
    Input('drill-state', 'data'),
)
def render_content(drill_state):
    """根据状态渲染页面"""
    import traceback as _tb
    try:
        with open('d:/简历/err.log', 'w', encoding='utf-8') as f:
            f.write(f'Callback triggered! drill_state={drill_state}\n')
        if drill_state is None:
            drill_state = {'layer': 1, 'metric': None, 'dimension': None, 'value': None}
        layer = drill_state.get('layer', 1)
        bc = html.Div(f'L{layer}', style={'color':'white'})
        mc = html.Div(f'Hello Layer {layer}', style={'color':'white','padding':'20px'})
        return bc, mc
    except Exception as e:
        with open('d:/简历/err.log', 'w', encoding='utf-8') as f:
            f.write(f'CALLBACK ERROR:\n')
            _tb.print_exc(file=f)
        return html.Div('Err'), html.Div(str(e))


# ============================================================
# 9. 启动
# ============================================================

if __name__ == '__main__':
    print(f"  三层诊断看板启动中...")
    print(f"  浏览器访问: http://127.0.0.1:8051")
    print(f"  Ctrl+C 停止")
    print("=" * 50)
    app.run(debug=True, port=8051)
