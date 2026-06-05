"""
百人电商公司 — 全量模拟数据生成器
====================================
生成匹配 100 人规模 DTC 电商公司的完整数据集，覆盖四个分析项目的全部数据。

公司画像：
  品牌: 运动服饰 DTC 品牌（袜子 / T恤 / 裤装 / 外套）
  年营收: ~5000 万元
  团队: ~100 人（运营 30 + 市场 15 + 商品 10 + 客服 15 + 技术 10 + 其他 20）
  渠道: 天猫 / 京东 / 得物 / 抖音
  用户量: ~20,000 注册用户
  月订单: ~15,000-30,000 单
  月广告费: ~80-150 万元

运行方式: python company_scale_setup.py
生成文件: 每个项目目录下的 .db 文件将被更新为真实规模数据
"""

import sqlite3
import random
import datetime
import os
import numpy as np

random.seed(42)
np.random.seed(42)

# ============================================================
# 全局参数 — 百人电商公司量级
# ============================================================
N_USERS = 20_000          # 注册用户总数
N_PRODUCTS = 500           # 总 SKU 数
DAU_BASE_WEEKDAY = 5_000   # 工作日日均活跃
DAU_BASE_WEEKEND = 3_500   # 周末日均活跃
START_DATE = datetime.date(2025, 1, 1)
TOTAL_DAYS = 365           # 2025 全年数据
NOW = datetime.datetime(2026, 1, 15)
PLATFORMS = ["天猫", "京东", "得物", "抖音"]

# 漏斗概率（基于真实行业基准）
P_VIEW = 0.65              # 活跃用户中 65% 产生浏览
P_CART_GIVEN_VIEW = 0.25   # 浏览→加购 25%
P_ORDER_GIVEN_CART = 0.30  # 加购→下单 30%
P_PAY_GIVEN_ORDER = 0.72   # 下单→支付 72%

# 订单金额分布（对数正态, 元）
ORDER_AMOUNT_MEAN = np.log(135)
ORDER_AMOUNT_SIGMA = 0.9

# 产品分类
CATEGORIES = {
    1: ("运动袜",  19.9,  69.9,  0.42),
    2: ("运动T恤",  89,   249,   0.38),
    3: ("运动裤",  129,   349,   0.35),
    4: ("运动外套", 199,   599,   0.32),
}
PLATFORM_WEIGHTS = {"天猫": 0.38, "京东": 0.25, "得物": 0.15, "抖音": 0.22}

print("=" * 60)
print("  百人电商公司 — 全量模拟数据生成器")
print("=" * 60)
print(f"  用户: {N_USERS:,}  |  商品: {N_PRODUCTS}  |  数据跨度: {TOTAL_DAYS} 天")
print(f"  日均活跃: ~{DAU_BASE_WEEKDAY:,} (工作日) / ~{DAU_BASE_WEEKEND:,} (周末)")
print()


# ============================================================
# 项目一: 公司日常运营指标分析
# ============================================================
def build_project1():
    """生成 ecommerce_ops.db — 用户行为 + 订单"""
    print("[项目一] 日常运营指标分析数据...")
    db_path = os.path.join("项目一：公司日常运营指标分析", "ecommerce_ops.db")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass  # 文件被占用时跳过删除
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # 清空旧表
    cur.execute("DROP TABLE IF EXISTS user_behavior")
    cur.execute("DROP TABLE IF EXISTS orders")

    # 建表
    cur.execute("""
        CREATE TABLE user_behavior (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('view','add_to_cart','place_order','pay')),
            product_id INTEGER NOT NULL,
            create_time TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            order_status TEXT NOT NULL
                CHECK(order_status IN ('unpaid','paid','shipped','completed','cancelled')),
            create_time TEXT NOT NULL
        )
    """)
    for idx_col in ["user_id", "action", "create_time"]:
        cur.execute(f"CREATE INDEX idx_ub_{idx_col} ON user_behavior({idx_col})")
    for idx_col in ["user_id", "create_time", "order_status"]:
        cur.execute(f"CREATE INDEX idx_o_{idx_col} ON orders({idx_col})")

    # 生成数据 — 按天批量插入以获得更真实的时间序列
    behavior_rows = []
    order_rows = []
    bid = 1
    oid = 1

    # 每个用户的「活跃倾向」（部分用户天天活跃，部分偶尔活跃）
    user_activity_bias = np.random.beta(0.5, 2.0, N_USERS)

    # 真实时间分布: 电商活跃时段 10:00-23:00, 凌晨 2:00-6:00 最低
    # 权重按小时分配: 0点=1, 1点=1, 2-5点=0.5, 6-7点=2, 8-9点=5, 10-22点=10, 23点=5
    HOUR_WEIGHTS = [1, 1, 0.5, 0.5, 0.5, 0.5, 2, 2, 5, 5] + [10]*13 + [5]

    def random_timestamp(date_str):
        hour = random.choices(range(24), weights=HOUR_WEIGHTS, k=1)[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        return f"{date_str} {hour:02d}:{minute:02d}:{second:02d}"

    for day_off in range(TOTAL_DAYS):
        current = START_DATE + datetime.timedelta(days=day_off)
        is_weekend = current.weekday() >= 5
        daily_base = DAU_BASE_WEEKEND if is_weekend else DAU_BASE_WEEKDAY
        # 特殊日期的流量波动（双十一、双十二等）
        if current.month == 11 and current.day == 11:
            daily_base = int(daily_base * 2.5)  # 双十一
        elif current.month == 12 and current.day == 12:
            daily_base = int(daily_base * 1.8)  # 双十二
        elif current.day == 1:
            daily_base = int(daily_base * 1.15)  # 月初有促销

        daily_active = max(500, int(np.random.normal(daily_base, daily_base * 0.12)))

        # 按活跃倾向采样当天活跃用户
        active_pool = random.choices(
            range(1, N_USERS + 1),
            weights=list(user_activity_bias),
            k=min(daily_active * 3, N_USERS)
        )
        active_users = list(set(active_pool))[:daily_active]

        for uid in active_users:
            if random.random() > P_VIEW:
                continue
            # 用户浏览行为
            n_views = random.choices([1, 2, 3, 4], weights=[0.55, 0.28, 0.12, 0.05])[0]
            viewed = random.sample(range(1, N_PRODUCTS + 1), min(n_views, N_PRODUCTS))
            for pid in viewed:
                # 每个行为独立时间戳，模拟一天中不同时段的行为
                # 同一个转化链(view->cart->order->pay)时间递增
                base_ts = random_timestamp(current.isoformat())
                behavior_rows.append((uid, 'view', pid, base_ts))
                bid += 1
                if random.random() > P_CART_GIVEN_VIEW:
                    continue
                # 加购通常发生在浏览后几分钟到几小时内
                cart_ts = random_timestamp(current.isoformat())
                behavior_rows.append((uid, 'add_to_cart', pid, cart_ts))
                bid += 1
                if random.random() > P_ORDER_GIVEN_CART:
                    continue
                order_ts = random_timestamp(current.isoformat())
                behavior_rows.append((uid, 'place_order', pid, order_ts))
                bid += 1
                if random.random() > P_PAY_GIVEN_ORDER:
                    continue
                pay_ts = random_timestamp(current.isoformat())
                behavior_rows.append((uid, 'pay', pid, pay_ts))
                bid += 1

        # 每 10 天批处理一次，控制内存
        if day_off % 10 == 9 and behavior_rows:
            cur.executemany(
                "INSERT INTO user_behavior(user_id, action, product_id, create_time) VALUES (?,?,?,?)",
                behavior_rows,
            )
            behavior_rows = []

    if behavior_rows:
        cur.executemany(
            "INSERT INTO user_behavior(user_id, action, product_id, create_time) VALUES (?,?,?,?)",
            behavior_rows,
        )

    # 生成订单（基于 place_order 用户）
    cur.execute("SELECT DISTINCT user_id, create_time FROM user_behavior WHERE action='place_order'")
    place_orders = cur.fetchall()

    # 收集 pay 用户集合（按天匹配，因为每个行为的时间戳不同）
    cur.execute("SELECT DISTINCT user_id, date(create_time) FROM user_behavior WHERE action='pay'")
    pay_set = {(r[0], r[1]) for r in cur.fetchall()}

    for uid, ct in place_orders:
        amount = max(9.9, min(round(np.random.lognormal(ORDER_AMOUNT_MEAN, ORDER_AMOUNT_SIGMA), 2), 3000))
        # 按日期（不是精确时间戳）判断该用户当天是否有支付行为
        if (uid, ct[:10]) in pay_set:
            status = random.choices(['paid', 'shipped', 'completed'], weights=[0.2, 0.35, 0.45])[0]
        else:
            status = random.choices(['unpaid', 'cancelled'], weights=[0.65, 0.35])[0]
        order_rows.append((uid, amount, status, ct))
        oid += 1

        if len(order_rows) >= 5000:
            cur.executemany(
                "INSERT INTO orders(user_id, amount, order_status, create_time) VALUES (?,?,?,?)",
                order_rows,
            )
            order_rows = []

    if order_rows:
        cur.executemany(
            "INSERT INTO orders(user_id, amount, order_status, create_time) VALUES (?,?,?,?)",
            order_rows,
        )

    conn.commit()
    # 统计
    cur.execute("SELECT COUNT(*) FROM user_behavior")
    n_behavior = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders")
    n_orders = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM user_behavior")
    n_unique = cur.fetchone()[0]
    print(f"  用户行为: {n_behavior:,} 条  |  订单: {n_orders:,} 条  |  活跃用户: {n_unique:,}")
    conn.close()
    return n_behavior, n_orders


# ============================================================
# 项目二: 老用户激活与价值提升
# ============================================================
def build_project2():
    """生成 user_activation.db — 老用户 + 品类订单 + 活动"""
    print("\n[项目二] 老用户激活与价值提升数据...")
    db_path = os.path.join("项目二：老用户激活与价值提升", "user_activation.db")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass  # 文件被占用，连接后覆盖写入
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for t in ["users", "orders", "order_items", "products", "user_activities"]:
        cur.execute(f"DROP TABLE IF EXISTS {t}")

    N_OLD_USERS = 12_000  # 注册超 6 个月的老用户
    N_P2_PRODUCTS = 120    # 袜子 60 + 服装 60

    # 建表
    for ddl in [
        """CREATE TABLE users (
            user_id INTEGER PRIMARY KEY, registration_date TEXT NOT NULL,
            gender TEXT, age INTEGER, behavior_type TEXT
        )""",
        """CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount REAL NOT NULL, order_status TEXT NOT NULL
                CHECK(order_status IN ('unpaid','paid','shipped','completed','cancelled')),
            create_time TEXT NOT NULL
        )""",
        """CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1, price REAL
        )""",
        """CREATE TABLE products (
            product_id INTEGER PRIMARY KEY, product_name TEXT,
            category_id INTEGER, price REAL
        )""",
        """CREATE TABLE user_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            activity_id INTEGER, activity_date TEXT, is_participated INTEGER DEFAULT 0
        )""",
    ]:
        cur.execute(ddl)
    cur.execute("CREATE INDEX idx_o2_user ON orders(user_id)")
    cur.execute("CREATE INDEX idx_o2_time ON orders(create_time)")
    cur.execute("CREATE INDEX idx_oi_order ON order_items(order_id)")
    cur.execute("CREATE INDEX idx_ua_user ON user_activities(user_id)")

    # 产品
    products = []
    for i in range(1, 61):
        products.append((i, f"运动袜-{i:03d}", 1, round(random.uniform(19.9, 69.9), 1)))
    for i in range(61, N_P2_PRODUCTS + 1):
        products.append((i, f"运动服-{i-60:03d}", 2, round(random.uniform(89, 499), 1)))
    cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

    # 老用户
    users = []
    behavior_map = {}
    for uid in range(1, N_OLD_USERS + 1):
        days_ago = random.randint(185, 1000)
        reg_date = (NOW - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
        gender = random.choices(["男", "女", "未知"], weights=[0.52, 0.43, 0.05])[0]
        age = max(16, min(65, int(np.random.normal(28, 9))))
        behavior = random.choices(
            ["socks_only", "early_expander", "late_expander"],
            weights=[0.45, 0.32, 0.23],
        )[0]
        users.append((uid, reg_date, gender, age, behavior))
        behavior_map[uid] = behavior
    cur.executemany("INSERT INTO users VALUES (?,?,?,?,?)", users)

    # 预建字典: user_id → registration_date（O(1) 查找）
    user_reg_dict = {u[0]: u[1] for u in users}
    # 预分组产品: category_id → 产品列表（避免每笔订单遍历全部产品）
    products_by_cat = {1: [p for p in products if p[2] == 1],
                       2: [p for p in products if p[2] == 2]}

    # 订单 + 订单项
    order_rows_p2 = []
    item_rows_p2 = []
    oid = 1
    iid = 1
    for uid in range(1, N_OLD_USERS + 1):
        behavior = behavior_map[uid]
        reg_date = datetime.datetime.strptime(user_reg_dict[uid], "%Y-%m-%d")
        days_since_reg = max((NOW - reg_date).days, 1)
        n_orders = max(1, min(np.random.poisson(9), 35))

        for order_pos in range(n_orders):
            order_offset = int(np.random.beta(1.3, 1.3) * days_since_reg)
            order_time = reg_date + datetime.timedelta(days=min(order_offset, days_since_reg - 1))
            pos_ratio = order_pos / max(n_orders - 1, 1)

            # 品类倾向：随着时间推移，拓展用户从袜子→服装
            if behavior == "socks_only":
                cat_prob_socks = 0.95
            elif behavior == "early_expander":
                cat_prob_socks = 0.85 if pos_ratio < 0.55 else 0.12
            else:
                cat_prob_socks = 0.88 if pos_ratio < 0.80 else 0.18

            target_cat = 1 if random.random() < cat_prob_socks else 2
            cat_prods = products_by_cat[target_cat]
            if not cat_prods:
                continue

            n_items = random.choices([1, 2, 3, 4], weights=[0.48, 0.30, 0.15, 0.07])[0]
            order_amount = 0
            for _ in range(n_items):
                prod = random.choice(cat_prods)
                qty = random.choices([1, 2, 3], weights=[0.82, 0.14, 0.04])[0]
                order_amount += prod[3] * qty
                item_rows_p2.append((oid, prod[0], qty, prod[3]))
                iid += 1

            time_factor = order_offset / max(days_since_reg, 1)
            if time_factor > 0.88:
                weights = [0.12, 0.22, 0.36, 0.25, 0.05]
            else:
                weights = [0.02, 0.03, 0.10, 0.80, 0.05]
            status = random.choices(
                ["unpaid", "paid", "shipped", "completed", "cancelled"],
                weights=weights,
            )[0]
            order_rows_p2.append((uid, round(order_amount, 2), status,
                                  order_time.strftime("%Y-%m-%d %H:%M:%S")))
            oid += 1

    cur.executemany("INSERT INTO orders(user_id, amount, order_status, create_time) VALUES (?,?,?,?)",
                    order_rows_p2)
    cur.executemany("INSERT INTO order_items(order_id, product_id, quantity, price) VALUES (?,?,?,?)",
                    item_rows_p2)

    # 活动参与数据（8 个季度大促）
    activity_rows = []
    for quarter in range(8):
        act_date = (NOW - datetime.timedelta(days=90 * (8 - quarter))).strftime("%Y-%m-%d")
        for uid in range(1, N_OLD_USERS + 1):
            order_cnt = sum(1 for o in order_rows_p2 if o[0] == uid and o[2] in ('paid','shipped','completed'))
            if order_cnt >= 8:
                p = 0.75
            elif order_cnt >= 4:
                p = 0.50
            elif order_cnt >= 1:
                p = 0.25
            else:
                p = 0.04
            activity_rows.append((uid, quarter + 1, act_date, 1 if random.random() < p else 0))

    cur.executemany("INSERT INTO user_activities(user_id, activity_id, activity_date, is_participated) VALUES (?,?,?,?)",
                    activity_rows)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM orders")
    n_o = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM orders WHERE order_status IN ('paid','shipped','completed')")
    n_paid = cur.fetchone()[0]
    print(f"  老用户: {N_OLD_USERS:,}  |  订单: {n_o:,}  |  有购买用户: {n_paid:,}  |  活动: {len(activity_rows):,}")
    conn.close()


# ============================================================
# 项目三: 各平台 ROI 预算重新分配
# ============================================================
def build_project3():
    """生成 roi_allocation.db — 广告投放 + 归因"""
    print("\n[项目三] ROI 预算分配数据...")
    db_path = os.path.join("项目三：各平台ROI预算重新分配", "roi_allocation.db")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass  # 文件被占用时跳过删除
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for t in ["ad_campaigns", "user_behavior", "attribution_data"]:
        cur.execute(f"DROP TABLE IF EXISTS {t}")

    cur.execute("""
        CREATE TABLE ad_campaigns (
            campaign_id INTEGER PRIMARY KEY, platform TEXT NOT NULL,
            campaign_type TEXT, campaign_date TEXT NOT NULL,
            spend REAL NOT NULL, impressions INTEGER, clicks INTEGER,
            conversions INTEGER, revenue REAL
        )
    """)
    cur.execute("""
        CREATE TABLE user_behavior (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            platform TEXT, session_id TEXT, action TEXT, create_time TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE attribution_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            touchpoint TEXT, platform TEXT, event_time TEXT,
            conversion_time TEXT, days_to_conversion INTEGER
        )
    """)
    for idx in ["platform", "campaign_date"]:
        cur.execute(f"CREATE INDEX idx_ac_{idx} ON ad_campaigns({idx})")

    PLATFORM_PARAMS = {
        "天猫": {"monthly_spend": 180_000, "base_cpc": 2.8, "base_cvr": 0.035, "base_ctr": 0.035},
        "京东": {"monthly_spend": 120_000, "base_cpc": 3.2, "base_cvr": 0.028, "base_ctr": 0.028},
        "得物": {"monthly_spend": 80_000,  "base_cpc": 1.6, "base_cvr": 0.045, "base_ctr": 0.040},
        "抖音": {"monthly_spend": 150_000, "base_cpc": 1.3, "base_cvr": 0.018, "base_ctr": 0.025},
    }
    CAMPAIGN_TYPES = ["搜索广告", "信息流", "达人带货", "品牌专区", "直播推广"]
    # 产出函数：对数递减收益
    # 产出系数 — 校准到 ROI 约 1.5-3.5 (真实电商投放水平)
    # revenue = A * ln(spend + 1), 对于单次投放 spend ~8000,
    # ln(8000)≈9, A=2500 → revenue≈22500, ROI≈2.8
    A_VALUES = {"天猫": 3_200, "京东": 2_500, "得物": 3_600, "抖音": 2_200}

    campaign_rows = []
    cid = 1
    for month_off in range(12):
        month_start = NOW - datetime.timedelta(days=30 * (12 - month_off))
        for plat in PLATFORMS:
            params = PLATFORM_PARAMS[plat]
            # 大促月份预算翻倍
            is_promo = month_start.month in [6, 11]
            month_budget = params["monthly_spend"] * (2.0 if is_promo else 1.0) * random.uniform(0.85, 1.15)
            n_campaigns = random.randint(15, 30) * (2 if is_promo else 1)
            for _ in range(n_campaigns):
                ctype = random.choice(CAMPAIGN_TYPES)
                day = random.randint(1, 28)
                c_date = month_start.replace(day=min(day, 28)).strftime("%Y-%m-%d")
                spend = month_budget / n_campaigns * random.uniform(0.5, 2.0)
                base_rev = A_VALUES[plat] * np.log(spend + 1)
                noise = np.random.normal(0, base_rev * 0.25)
                revenue = max(spend * 0.4, base_rev + noise)
                ctr = params["base_ctr"] * random.uniform(0.6, 1.6)
                cpc = params["base_cpc"] * random.uniform(0.75, 1.4)
                if ctr > 0 and cpc > 0:
                    clicks_ = int(spend / cpc)
                    impressions_ = int(clicks_ / ctr)
                else:
                    clicks_ = 0; impressions_ = 0
                cvr = params["base_cvr"] * random.uniform(0.6, 1.5)
                conversions_ = max(1, int(clicks_ * cvr))
                campaign_rows.append((
                    cid, plat, ctype, c_date, round(spend, 2),
                    impressions_, clicks_, conversions_, round(revenue, 2),
                ))
                cid += 1

    cur.executemany(
        "INSERT INTO ad_campaigns VALUES (?,?,?,?,?,?,?,?,?)", campaign_rows
    )

    # 归因数据（跨平台触点）
    cross_platform = [
        ("抖音", "天猫", 0.28, 3), ("抖音", "京东", 0.18, 4),
        ("得物", "天猫", 0.22, 5), ("得物", "京东", 0.08, 6),
        ("抖音", "抖音", 0.14, 1), ("天猫", "天猫", 0.10, 2),
        ("京东", "京东", 0.03, 1), ("得物", "得物", 0.02, 1),
        ("天猫", "京东", 0.05, 3),
    ]
    attr_rows = []
    for uid in range(1, 3001):
        n_tp = random.choices([1, 2, 3, 4, 5], weights=[0.25, 0.30, 0.22, 0.15, 0.08])[0]
        for _ in range(n_tp):
            choice = random.choices(cross_platform, weights=[c[2] for c in cross_platform])[0]
            tp_plat, conv_plat, prob, avg_days = choice
            days_ago = random.randint(1, 365)
            et = NOW - datetime.timedelta(days=days_ago)
            if random.random() < prob:
                cd = max(0, int(np.random.normal(avg_days, 2.5)))
                cvt = et + datetime.timedelta(days=cd)
                if cvt < NOW:
                    attr_rows.append((uid, tp_plat, conv_plat, et.strftime("%Y-%m-%d"),
                                     cvt.strftime("%Y-%m-%d"), cd))
                else:
                    attr_rows.append((uid, tp_plat, conv_plat, et.strftime("%Y-%m-%d"), None, None))
            else:
                attr_rows.append((uid, tp_plat, conv_plat, et.strftime("%Y-%m-%d"), None, None))

    cur.executemany(
        "INSERT INTO attribution_data(user_id, touchpoint, platform, event_time, conversion_time, days_to_conversion) "
        "VALUES (?,?,?,?,?,?)", attr_rows
    )

    conn.commit()
    cur.execute("SELECT COUNT(*), SUM(spend), SUM(revenue) FROM ad_campaigns")
    n, total_spend, total_rev = cur.fetchone()
    print(f"  投放记录: {n:,}  |  总花费: {total_spend:,.0f} 元  |  总收入: {total_rev:,.0f} 元  |  全域ROI: {total_rev/total_spend:.2f}")
    conn.close()


# ============================================================
# 项目四: 产品组合分析
# ============================================================
def build_project4():
    """生成 product_portfolio.db — 产品 + 销售 + 库存"""
    print("\n[项目四] 产品组合分析数据...")
    db_path = os.path.join("项目四：产品组合分析", "product_portfolio.db")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass  # 文件被占用时跳过删除
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for t in ["products", "sales_data", "inventory_data"]:
        cur.execute(f"DROP TABLE IF EXISTS {t}")

    N_P4 = 150  # 新品数
    START_P4 = datetime.date(2025, 1, 15)   # 新品从1月中开始陆续上线
    TOTAL_SALES_DAYS = 350                   # 覆盖全年

    cur.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY, product_name TEXT,
            category_id INTEGER, price REAL, cost REAL,
            launch_date TEXT, curve_type TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE sales_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL,
            platform TEXT, sale_date TEXT NOT NULL,
            sales_volume INTEGER, sales_amount REAL
        )
    """)
    cur.execute("""
        CREATE TABLE inventory_data (
            product_id INTEGER PRIMARY KEY, initial_stock INTEGER,
            current_stock INTEGER, safety_stock INTEGER, lead_time_days INTEGER
        )
    """)
    for idx in ["product_id", "sale_date", "platform"]:
        cur.execute(f"CREATE INDEX idx_s_{idx} ON sales_data({idx})")

    # 产品
    product_rows = []
    product_curves = {}
    for pid in range(1, N_P4 + 1):
        cat = min((pid - 1) // 38 + 1, 4)
        cat_name, p_min, p_max, cost_ratio = CATEGORIES[cat]
        price = round(random.uniform(p_min, p_max), 1)
        cost = round(price * cost_ratio * random.uniform(0.88, 1.12), 1)
        launch_off = random.randint(0, 300)  # 产品在全年内陆续上线
        launch_date = (START_P4 + datetime.timedelta(days=launch_off)).strftime("%Y-%m-%d")
        curve = random.choices(["hot", "steady", "slow", "dying"], weights=[0.22, 0.33, 0.28, 0.17])[0]
        name = f"{cat_name}-{pid:03d}"
        product_rows.append((pid, name, cat, price, cost, launch_date, curve))
        product_curves[pid] = (curve, launch_date)
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?)", product_rows)

    # 销售数据
    sales_rows = []
    for pid in range(1, N_P4 + 1):
        curve, launch_str = product_curves[pid]
        launch_date = datetime.date.fromisoformat(launch_str)
        for day_off in range(TOTAL_SALES_DAYS):
            sale_date = START_P4 + datetime.timedelta(days=day_off)
            if sale_date < launch_date:
                continue
            days_since = (sale_date - launch_date).days
            is_weekend = sale_date.weekday() >= 5

            if curve == "hot":
                base = 18 + days_since * 2.5
            elif curve == "steady":
                base = 12 + np.sin(days_since / 7) * 3
            elif curve == "slow":
                base = 4
            else:
                base = max(0.5, 15 - days_since * 0.6 + np.sin(days_since / 5) * 2)

            if is_weekend: base *= 1.35
            # 大促日
            if sale_date.month == 11 and sale_date.day == 11:
                base *= 3.5
            elif sale_date.month == 12 and sale_date.day == 12:
                base *= 2.5

            daily_vol = max(0, int(np.random.poisson(max(1, base))))
            if daily_vol == 0:
                continue

            price = next(p[3] for p in product_rows if p[0] == pid)
            for plat, w in PLATFORM_WEIGHTS.items():
                pv = int(np.random.binomial(daily_vol, w))
                if pv > 0:
                    actual_price = price * random.uniform(0.82, 0.98)
                    sales_rows.append((pid, plat, sale_date.strftime("%Y-%m-%d"), pv,
                                       round(pv * actual_price, 2)))

    cur.executemany(
        "INSERT INTO sales_data(product_id, platform, sale_date, sales_volume, sales_amount) "
        "VALUES (?,?,?,?,?)", sales_rows
    )

    # 库存
    total_sales = {}
    for row in sales_rows:
        total_sales[row[0]] = total_sales.get(row[0], 0) + row[3]

    inv_rows = []
    for pid in range(1, N_P4 + 1):
        ts = total_sales.get(pid, 0)
        initial = random.randint(300, 2000)
        current = max(0, initial - ts)
        avg_daily = ts / max(TOTAL_SALES_DAYS, 1)
        lead_time = random.randint(3, 14)
        safety = max(15, int(avg_daily * lead_time * 1.5))
        inv_rows.append((pid, initial, current, safety, lead_time))

    cur.executemany("INSERT INTO inventory_data VALUES (?,?,?,?,?)", inv_rows)

    conn.commit()
    cur.execute("SELECT COUNT(*), SUM(sales_volume), SUM(sales_amount) FROM sales_data")
    n, total_vol, total_amt = cur.fetchone()
    cur.execute("SELECT SUM(current_stock * cost) FROM inventory_data i JOIN products p ON i.product_id = p.product_id")
    stock_value = cur.fetchone()[0]
    print(f"  产品: {N_P4}  |  销售记录: {n:,}  |  总销量: {total_vol:,} 件  |  总销售额: {total_amt:,.0f} 元  |  库存资金: {stock_value:,.0f} 元")
    conn.close()


# ============================================================
# 主流程
# ============================================================
def main():
    t_start = datetime.datetime.now()

    n_b1, n_o1 = build_project1()
    build_project2()
    build_project3()
    build_project4()

    elapsed = (datetime.datetime.now() - t_start).total_seconds()
    print("\n" + "=" * 60)
    print(f"  全部数据生成完毕！耗时 {elapsed:.1f} 秒")
    print(f"  公司规模: ~100 人  |  注册用户: ~{N_USERS:,}  |  SKU: {N_PRODUCTS}")
    print(f"  数据跨度: {TOTAL_DAYS} 天  |  行为记录: ~{n_b1:,} 条  |  订单: ~{n_o1:,} 条")
    print("=" * 60)
    print()
    print("  现在可以在各项目目录中运行 Jupyter Notebook 进行分析:")
    print("    cd 项目一：公司日常运营指标分析")
    print("    jupyter notebook analysis.ipynb")
    print()


if __name__ == "__main__":
    main()
