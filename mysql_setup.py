"""
MySQL 数据库一键搭建脚本
========================
将四个项目的数据全部导入 MySQL，供 Navicat 查询学习使用。

运行方式：python mysql_setup.py
连接信息：host=localhost, user=root, password=123456
数据库名：ecommerce_analysis

生成后可立即用 Navicat Premium 16 连接查询。
"""

import pymysql
import random
import datetime
import numpy as np

random.seed(42)
np.random.seed(42)

# ── MySQL 连接配置 ──────────────────────────────────────
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "charset": "utf8mb4",
}
DB_NAME = "ecommerce_analysis"
NOW = datetime.datetime(2026, 1, 15)
N_PRODUCTS = 200
PLATFORMS = ["天猫", "京东", "得物", "抖音"]


def get_conn(with_db=True):
    """获取数据库连接"""
    cfg = MYSQL_CONFIG.copy()
    if with_db:
        cfg["database"] = DB_NAME
    return pymysql.connect(**cfg)


def create_database():
    """创建数据库（如果不存在）"""
    conn = get_conn(with_db=False)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4")
    conn.commit()
    conn.close()
    print(f"[OK] 数据库 {DB_NAME} 已就绪")


# ====================================================================
# 项目一：公司日常运营指标分析
# ====================================================================
def create_project1_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_behavior (
            id INT PRIMARY KEY               COMMENT '行为ID_主键',
            user_id INT NOT NULL             COMMENT '用户ID',
            action VARCHAR(20) NOT NULL      COMMENT '行为类型: view浏览_add_to_cart加购_place_order下单_pay支付',
            product_id INT NOT NULL          COMMENT '商品ID',
            create_time DATETIME NOT NULL    COMMENT '行为发生时间',
            INDEX idx_ub_time (create_time),
            INDEX idx_ub_user (user_id),
            INDEX idx_ub_action (action)
        ) ENGINE=InnoDB COMMENT='用户行为记录表_项目一'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INT PRIMARY KEY          COMMENT '订单ID_主键',
            user_id INT NOT NULL              COMMENT '用户ID',
            amount DECIMAL(10,2) NOT NULL     COMMENT '订单金额_元',
            order_status VARCHAR(20) NOT NULL COMMENT '订单状态: unpaid待付款_paid已付款_shipped已发货_completed已完成_cancelled已取消',
            create_time DATETIME NOT NULL     COMMENT '订单创建时间',
            INDEX idx_o_time (create_time),
            INDEX idx_o_user (user_id)
        ) ENGINE=InnoDB COMMENT='订单记录表_项目一'
    """)


def generate_project1_data(cur):
    """生成项目一数据：用户行为 + 订单"""
    print("  [项目一] 生成用户行为 + 订单数据...")
    N_USERS = 1000
    START_DATE = datetime.date(2025, 1, 1)
    TOTAL_DAYS = 30

    # 用户行为
    behavior_rows = []
    bid = 1
    for day_offset in range(TOTAL_DAYS):
        current_date = START_DATE + datetime.timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5
        daily_active = int(np.random.normal(600 if is_weekend else 750, 50))
        daily_active = max(300, min(daily_active, N_USERS))
        active_users = random.sample(range(1, N_USERS + 1), daily_active)

        for user_id in active_users:
            n_views = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            viewed = random.sample(range(1, N_PRODUCTS + 1), min(n_views, N_PRODUCTS))
            for product_id in viewed:
                if random.random() >= 0.60:
                    continue
                behavior_rows.append((bid, user_id, 'view', product_id, current_date.isoformat()))
                bid += 1
                if random.random() >= 0.30:
                    continue
                behavior_rows.append((bid, user_id, 'add_to_cart', product_id, current_date.isoformat()))
                bid += 1
                if random.random() >= 0.33:
                    continue
                behavior_rows.append((bid, user_id, 'place_order', product_id, current_date.isoformat()))
                bid += 1
                if random.random() >= 0.70:
                    continue
                behavior_rows.append((bid, user_id, 'pay', product_id, current_date.isoformat()))
                bid += 1

        if len(behavior_rows) >= 5000:
            cur.executemany(
                "INSERT INTO user_behavior(id, user_id, action, product_id, create_time) "
                "VALUES (%s, %s, %s, %s, %s)", behavior_rows
            )
            behavior_rows = []

    if behavior_rows:
        cur.executemany(
            "INSERT INTO user_behavior(id, user_id, action, product_id, create_time) "
            "VALUES (%s, %s, %s, %s, %s)", behavior_rows
        )

    # 重新查询 place_order 用户
    cur.execute(
        "SELECT DISTINCT user_id, create_time FROM user_behavior WHERE action='place_order'"
    )
    place_orders = cur.fetchall()

    pay_set = set()
    cur.execute("SELECT user_id, create_time FROM user_behavior WHERE action='pay'")
    for row in cur.fetchall():
        pay_set.add((row[0], str(row[1])))

    order_rows = []
    for idx, (user_id, create_time) in enumerate(place_orders, start=1):
        amount = round(np.random.lognormal(np.log(120), 0.8), 2)
        amount = max(9.9, min(amount, 2000))
        ct_str = str(create_time)
        if (user_id, ct_str) in pay_set:
            status = random.choices(['paid', 'shipped', 'completed'], weights=[0.2, 0.3, 0.5])[0]
        else:
            status = random.choices(['unpaid', 'cancelled'], weights=[0.7, 0.3])[0]
        order_rows.append((idx, user_id, amount, status, ct_str))

    cur.executemany(
        "INSERT INTO orders(order_id, user_id, amount, order_status, create_time) "
        "VALUES (%s, %s, %s, %s, %s)", order_rows
    )
    print(f"    用户行为: {bid-1:,} 条  订单: {len(order_rows):,} 条")


# ====================================================================
# 项目二：老用户激活与价值提升
# ====================================================================
def create_project2_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users_p2 (
            user_id INT PRIMARY KEY             COMMENT '用户ID_主键',
            registration_date DATE NOT NULL     COMMENT '注册日期',
            gender VARCHAR(10)                  COMMENT '性别: 男_女_未知',
            age INT                             COMMENT '年龄',
            behavior_type VARCHAR(20)           COMMENT '用户行为画像: socks_only只买袜子_early_expander早期拓展者_late_expander后期拓展者'
        ) ENGINE=InnoDB COMMENT='老用户信息表_项目二'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders_p2 (
            order_id INT PRIMARY KEY            COMMENT '订单ID_主键',
            user_id INT NOT NULL                COMMENT '用户ID',
            amount DECIMAL(10,2) NOT NULL       COMMENT '订单金额_元',
            order_status VARCHAR(20) NOT NULL   COMMENT '订单状态: unpaid待付款_paid已付款_shipped已发货_completed已完成_cancelled已取消',
            create_time DATETIME NOT NULL       COMMENT '订单创建时间',
            INDEX idx_o2_user (user_id),
            INDEX idx_o2_time (create_time)
        ) ENGINE=InnoDB COMMENT='订单记录表_含品类信息_项目二'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items_p2 (
            order_item_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '订单明细ID_自增主键',
            order_id INT NOT NULL               COMMENT '所属订单ID',
            product_id INT NOT NULL             COMMENT '商品ID',
            quantity INT DEFAULT 1              COMMENT '购买数量',
            price DECIMAL(10,2)                 COMMENT '商品单价_元',
            INDEX idx_oi_order (order_id)
        ) ENGINE=InnoDB COMMENT='订单明细表_每行=一个订单中的一种商品_项目二'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products_p2 (
            product_id INT PRIMARY KEY          COMMENT '商品ID_主键',
            product_name VARCHAR(100)           COMMENT '商品名称',
            category_id INT                     COMMENT '品类ID: 1袜子_2服装',
            price DECIMAL(10,2)                 COMMENT '商品价格_元'
        ) ENGINE=InnoDB COMMENT='商品表_袜子与服装两品类_项目二'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_activities (
            id INT PRIMARY KEY AUTO_INCREMENT   COMMENT '记录ID_自增主键',
            user_id INT NOT NULL                COMMENT '用户ID',
            activity_id INT NOT NULL            COMMENT '活动ID_季度大促编号',
            activity_date DATE NOT NULL         COMMENT '活动日期',
            is_participated TINYINT DEFAULT 0   COMMENT '是否参与: 0未参与_1已参与',
            INDEX idx_ua_user (user_id)
        ) ENGINE=InnoDB COMMENT='用户活动参与记录表_项目二'
    """)


def generate_project2_data(cur):
    """生成项目二数据：老用户、品类订单、活动参与"""
    print("  [项目二] 生成老用户 + 品类订单 + 活动数据...")
    N_USERS = 500

    # 商品
    products_p2 = []
    for i in range(1, 21):
        products_p2.append((i, f"运动袜-{chr(64+i)}款", 1, round(random.uniform(19.9, 49.9), 1)))
    for i in range(21, 51):
        products_p2.append((i, f"运动T恤-{chr(64+i-20)}款", 2, round(random.uniform(89, 299), 1)))
    cur.executemany(
        "INSERT INTO products_p2(product_id, product_name, category_id, price) VALUES (%s,%s,%s,%s)",
        products_p2,
    )

    # 用户
    user_rows = []
    behavior_map = {}
    for uid in range(1, N_USERS + 1):
        days_ago = random.randint(180, 730)
        reg_date = (NOW - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")
        gender = random.choices(["男", "女", "未知"], weights=[0.55, 0.40, 0.05])[0]
        age = max(16, int(np.random.normal(28, 8)))
        behavior = random.choices(
            ["socks_only", "early_expander", "late_expander"],
            weights=[0.50, 0.30, 0.20],
        )[0]
        user_rows.append((uid, reg_date, gender, age, behavior))
        behavior_map[uid] = behavior
    cur.executemany(
        "INSERT INTO users_p2(user_id, registration_date, gender, age, behavior_type) "
        "VALUES (%s,%s,%s,%s,%s)", user_rows
    )

    # 订单和订单明细
    order_rows_p2 = []
    item_rows_p2 = []
    order_id = 1
    item_id = 1
    for uid in range(1, N_USERS + 1):
        behavior = behavior_map[uid]
        reg_date = next(r[1] for r in user_rows if r[0] == uid)
        if isinstance(reg_date, str):
            reg_date = datetime.datetime.strptime(reg_date, "%Y-%m-%d")
        n_orders = max(1, min(np.random.poisson(8), 30))
        for i in range(n_orders):
            days_since_reg = (NOW - reg_date).days
            order_offset = int(np.random.beta(1.5, 1.5) * days_since_reg)
            order_time = reg_date + datetime.timedelta(days=order_offset)
            order_pos = i / max(n_orders - 1, 1)

            if behavior == "socks_only":
                cat_prob_socks = 1.0
            elif behavior == "early_expander":
                cat_prob_socks = 0.9 if order_pos < 0.6 else 0.15
            else:
                cat_prob_socks = 0.9 if order_pos < 0.85 else 0.20

            target_cat = 1 if random.random() < cat_prob_socks else 2
            cat_prods = [p for p in products_p2 if p[2] == target_cat]
            if not cat_prods:
                continue

            n_items = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
            order_amount = 0
            for _ in range(n_items):
                prod = random.choice(cat_prods)
                qty = random.choices([1, 2], weights=[0.85, 0.15])[0]
                order_amount += prod[3] * qty
                item_rows_p2.append((item_id, order_id, prod[0], qty, prod[3]))
                item_id += 1

            time_factor = order_offset / max(days_since_reg, 1)
            if time_factor > 0.9:
                status = random.choices(
                    ["unpaid", "paid", "shipped", "completed", "cancelled"],
                    weights=[0.15, 0.25, 0.35, 0.20, 0.05],
                )[0]
            else:
                status = random.choices(
                    ["unpaid", "paid", "shipped", "completed", "cancelled"],
                    weights=[0.02, 0.03, 0.10, 0.80, 0.05],
                )[0]

            order_rows_p2.append((
                order_id, uid, round(order_amount, 2), status,
                order_time.strftime("%Y-%m-%d %H:%M:%S"),
            ))
            order_id += 1

    cur.executemany(
        "INSERT INTO orders_p2(order_id, user_id, amount, order_status, create_time) "
        "VALUES (%s,%s,%s,%s,%s)", order_rows_p2
    )
    cur.executemany(
        "INSERT INTO order_items_p2(order_item_id, order_id, product_id, quantity, price) "
        "VALUES (%s,%s,%s,%s,%s)", item_rows_p2
    )

    # 活动数据
    activity_rows = []
    for quarter in range(8):
        act_date = (NOW - datetime.timedelta(days=90 * (8 - quarter))).strftime("%Y-%m-%d")
        for uid in range(1, N_USERS + 1):
            order_cnt = sum(1 for o in order_rows_p2 if o[1] == uid and o[3] in ('paid','shipped','completed'))
            if order_cnt >= 5:
                p_participate = 0.7
            elif order_cnt >= 3:
                p_participate = 0.45
            elif order_cnt >= 1:
                p_participate = 0.25
            else:
                p_participate = 0.05
            activity_rows.append((uid, quarter + 1, act_date, 1 if random.random() < p_participate else 0))

    cur.executemany(
        "INSERT INTO user_activities(user_id, activity_id, activity_date, is_participated) "
        "VALUES (%s,%s,%s,%s)", activity_rows
    )
    print(f"    用户: {N_USERS}  订单: {len(order_rows_p2):,}  活动: {len(activity_rows):,}")


# ====================================================================
# 项目三：各平台ROI预算重新分配
# ====================================================================
def create_project3_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ad_campaigns (
            campaign_id INT PRIMARY KEY          COMMENT '广告活动ID_主键',
            platform VARCHAR(20) NOT NULL        COMMENT '投放平台: 天猫_京东_得物_抖音',
            campaign_type VARCHAR(30)            COMMENT '投放类型: 搜索广告_信息流_达人带货_品牌专区',
            campaign_date DATE NOT NULL          COMMENT '投放日期',
            spend DECIMAL(12,2) NOT NULL         COMMENT '投放花费_元',
            impressions INT                      COMMENT '曝光量_次',
            clicks INT                           COMMENT '点击量_次',
            conversions INT                      COMMENT '转化量_下单或成交',
            revenue DECIMAL(12,2)                COMMENT '广告带来的收入_元',
            INDEX idx_ac_plat (platform),
            INDEX idx_ac_date (campaign_date)
        ) ENGINE=InnoDB COMMENT='广告投放数据表_多平台ROI分析_项目三'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attribution_data (
            id INT PRIMARY KEY AUTO_INCREMENT    COMMENT '归因记录ID_自增主键',
            user_id INT NOT NULL                 COMMENT '用户ID',
            touchpoint VARCHAR(20)               COMMENT '触点平台_用户首次接触内容的平台',
            platform VARCHAR(20)                 COMMENT '转化平台_用户最终下单的平台',
            event_time DATE                      COMMENT '触点时间_用户首次接触广告的时间',
            conversion_time DATE                 COMMENT '转化时间_用户下单时间_NULL表示未转化',
            days_to_conversion INT               COMMENT '转化天数_从触点到转化的天数',
            INDEX idx_att_plat (platform)
        ) ENGINE=InnoDB COMMENT='跨平台归因数据表_项目三'
    """)


def generate_project3_data(cur):
    """生成项目三数据：广告投放 + 归因"""
    print("  [项目三] 生成广告投放 + 归因数据...")

    PLATFORM_PARAMS = {
        "天猫": {"base_spend": 50000, "base_cpc": 2.5, "base_cvr": 0.04},
        "京东": {"base_spend": 35000, "base_cpc": 3.0, "base_cvr": 0.03},
        "得物": {"base_spend": 20000, "base_cpc": 1.5, "base_cvr": 0.05},
        "抖音": {"base_spend": 45000, "base_cpc": 1.2, "base_cvr": 0.02},
    }
    CAMPAIGN_TYPES = ["搜索广告", "信息流", "达人带货", "品牌专区"]
    A_VALUES = {"天猫": 25000, "京东": 18000, "得物": 30000, "抖音": 22000}

    campaign_rows = []
    cid = 1
    for month_offset in range(6):
        month_start = NOW - datetime.timedelta(days=30 * (6 - month_offset))
        for platform in PLATFORMS:
            params = PLATFORM_PARAMS[platform]
            for ctype in CAMPAIGN_TYPES:
                n = random.choices([1, 2], weights=[0.6, 0.4])[0]
                for _ in range(n):
                    day = random.randint(1, 28)
                    c_date = month_start.replace(day=day).strftime("%Y-%m-%d")
                    spend = params["base_spend"] * random.uniform(0.7, 1.5) / 4
                    base_rev = A_VALUES[platform] * np.log(spend + 1)
                    noise = np.random.normal(0, base_rev * 0.2)
                    revenue = max(spend * 0.5, base_rev + noise)
                    cpc = params["base_cpc"] * random.uniform(0.8, 1.3)
                    ctr = random.uniform(0.015, 0.06)
                    impressions_ = int(spend / cpc / ctr)
                    clicks_ = int(impressions_ * ctr)
                    cvr = params["base_cvr"] * random.uniform(0.7, 1.5)
                    conversions_ = max(1, int(clicks_ * cvr))
                    campaign_rows.append((
                        cid, platform, ctype, c_date, round(spend, 2),
                        impressions_, clicks_, conversions_, round(revenue, 2),
                    ))
                    cid += 1

    cur.executemany(
        "INSERT INTO ad_campaigns VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)", campaign_rows
    )

    # 归因数据
    cross_platform = [
        ("抖音", "天猫", 0.30, 3), ("抖音", "京东", 0.20, 4),
        ("得物", "天猫", 0.25, 5), ("得物", "京东", 0.10, 6),
        ("抖音", "抖音", 0.15, 1), ("天猫", "天猫", 0.08, 2),
        ("京东", "京东", 0.02, 1),
    ]
    attr_rows = []
    for user_id in range(1, 801):
        n_tp = random.choices([1, 2, 3, 4, 5], weights=[0.3, 0.3, 0.2, 0.15, 0.05])[0]
        for _ in range(n_tp):
            choice = random.choices(cross_platform, weights=[c[2] for c in cross_platform])[0]
            disc_plat, conv_plat, prob, avg_days = choice
            days_ago = random.randint(1, 180)
            event_time = NOW - datetime.timedelta(days=days_ago)
            if random.random() < prob:
                conv_days = max(0, int(np.random.normal(avg_days, 2)))
                conv_time = event_time + datetime.timedelta(days=conv_days)
                if conv_time < NOW:
                    attr_rows.append((user_id, disc_plat, conv_plat, event_time.strftime("%Y-%m-%d"),
                                     conv_time.strftime("%Y-%m-%d"), conv_days))
                else:
                    attr_rows.append((user_id, disc_plat, conv_plat, event_time.strftime("%Y-%m-%d"), None, None))
            else:
                attr_rows.append((user_id, disc_plat, conv_plat, event_time.strftime("%Y-%m-%d"), None, None))

    cur.executemany(
        "INSERT INTO attribution_data(user_id, touchpoint, platform, event_time, conversion_time, days_to_conversion) "
        "VALUES (%s,%s,%s,%s,%s,%s)", attr_rows
    )
    print(f"    Campaigns: {len(campaign_rows)}  归因: {len(attr_rows):,}")


# ====================================================================
# 项目四：产品组合分析
# ====================================================================
def create_project4_tables(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products_p4 (
            product_id INT PRIMARY KEY          COMMENT '商品ID_主键',
            product_name VARCHAR(100)           COMMENT '商品名称',
            category_id INT                     COMMENT '品类ID: 1运动袜_2运动T恤_3运动裤_4运动外套',
            price DECIMAL(10,2)                 COMMENT '售价_元',
            cost DECIMAL(10,2)                  COMMENT '成本_元',
            launch_date DATE                    COMMENT '上市日期_新品定义为30天内',
            curve_type VARCHAR(20)              COMMENT '销售曲线类型: hot爆款_steady稳定款_slow一般款_dying滞销款'
        ) ENGINE=InnoDB COMMENT='新品信息表_项目四'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales_data (
            id INT PRIMARY KEY AUTO_INCREMENT   COMMENT '销售记录ID_自增主键',
            product_id INT NOT NULL             COMMENT '商品ID',
            platform VARCHAR(20)                COMMENT '销售平台: 天猫_京东_得物_抖音',
            sale_date DATE NOT NULL             COMMENT '销售日期',
            sales_volume INT                    COMMENT '销量_件',
            sales_amount DECIMAL(12,2)          COMMENT '销售额_元',
            INDEX idx_s_pid (product_id),
            INDEX idx_s_date (sale_date),
            INDEX idx_s_plat (platform)
        ) ENGINE=InnoDB COMMENT='每日销售记录表_按平台拆分_项目四'
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory_data (
            product_id INT PRIMARY KEY          COMMENT '商品ID_主键',
            initial_stock INT                   COMMENT '初始库存_件',
            current_stock INT                   COMMENT '当前库存_件',
            safety_stock INT                    COMMENT '安全库存_件_应对需求波动的缓冲量',
            lead_time_days INT                  COMMENT '补货提前期_天_从下单到入库的天数'
        ) ENGINE=InnoDB COMMENT='库存数据表_含补货参数_项目四'
    """)


def generate_project4_data(cur):
    """生成项目四数据：新品 + 销售 + 库存"""
    print("  [项目四] 生成产品 + 销售 + 库存数据...")
    N_P4 = 40
    CATS = {1: "运动袜", 2: "运动T恤", 3: "运动裤", 4: "运动外套"}
    BASE_PRICES = {1: (19.9, 49.9), 2: (89, 199), 3: (129, 299), 4: (199, 499)}
    COST_RATIOS = {1: 0.45, 2: 0.40, 3: 0.38, 4: 0.35}
    START_DATE = datetime.date(2025, 12, 16)

    product_curves = {}
    product_rows_p4 = []
    for pid in range(1, N_P4 + 1):
        cat_id = min((pid - 1) // 10 + 1, 4)
        price = round(random.uniform(*BASE_PRICES[cat_id]), 1)
        cost = round(price * COST_RATIOS[cat_id] * random.uniform(0.9, 1.1), 1)
        launch_offset = random.randint(0, 29)
        launch_date = (START_DATE + datetime.timedelta(days=launch_offset)).strftime("%Y-%m-%d")
        curve = random.choices(["hot", "steady", "slow", "dying"], weights=[0.25, 0.30, 0.25, 0.20])[0]
        name = f"{CATS[cat_id]}-{pid:02d}"
        product_rows_p4.append((pid, name, cat_id, price, cost, launch_date, curve))
        product_curves[pid] = (curve, launch_date)

    cur.executemany(
        "INSERT INTO products_p4 VALUES (%s,%s,%s,%s,%s,%s,%s)", product_rows_p4
    )

    # 销售数据
    sales_rows = []
    for pid in range(1, N_P4 + 1):
        curve, launch_str = product_curves[pid]
        launch_date = datetime.date.fromisoformat(launch_str)
        for day_offset in range(30):
            sale_date = START_DATE + datetime.timedelta(days=day_offset)
            if sale_date < launch_date:
                continue
            days_since = (sale_date - launch_date).days
            is_weekend = sale_date.weekday() >= 5

            if curve == "hot":
                base = 15 + days_since * 2
            elif curve == "steady":
                base = 10
            elif curve == "slow":
                base = 3
            else:
                base = max(1, 12 - days_since * 0.5)
            if is_weekend:
                base *= 1.3

            daily_vol = max(0, int(np.random.poisson(max(1, base))))
            if daily_vol == 0:
                continue

            price = next(p[3] for p in product_rows_p4 if p[0] == pid)
            plat_weights = {"天猫": 0.35, "京东": 0.25, "得物": 0.15, "抖音": 0.25}
            for plat, w in plat_weights.items():
                pv = int(np.random.binomial(daily_vol, w))
                if pv > 0:
                    actual_price = price * random.uniform(0.85, 0.98)
                    sales_rows.append((pid, plat, sale_date.strftime("%Y-%m-%d"), pv, round(pv * actual_price, 2)))

    cur.executemany(
        "INSERT INTO sales_data(product_id, platform, sale_date, sales_volume, sales_amount) "
        "VALUES (%s,%s,%s,%s,%s)", sales_rows
    )

    # 库存数据
    total_sales = {}
    for row in sales_rows:
        total_sales[row[0]] = total_sales.get(row[0], 0) + row[3]

    inv_rows = []
    for pid in range(1, N_P4 + 1):
        ts = total_sales.get(pid, 0)
        initial = random.randint(200, 800)
        current = max(0, initial - ts)
        avg_daily = ts / 30
        lead_time = random.randint(3, 14)
        safety = max(10, int(avg_daily * lead_time * 1.5))
        inv_rows.append((pid, initial, current, safety, lead_time))

    cur.executemany(
        "INSERT INTO inventory_data VALUES (%s,%s,%s,%s,%s)", inv_rows
    )
    print(f"    产品: {N_P4}  销售: {len(sales_rows):,}  库存: {len(inv_rows)}")


# ====================================================================
# 主流程
# ====================================================================
def main():
    print("=" * 60)
    print("  MySQL 数据分析学习库 — 一键搭建")
    print("=" * 60)

    # 1. 建库
    create_database()

    # 2. 连接数据库
    conn = get_conn(with_db=True)
    cur = conn.cursor()

    # 3. 清理旧表（如有）
    tables = [
        "user_behavior", "orders",
        "users_p2", "orders_p2", "order_items_p2", "products_p2", "user_activities",
        "ad_campaigns", "attribution_data",
        "products_p4", "sales_data", "inventory_data",
    ]
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t}")

    # 4. 创建所有表
    print("\n[1] 创建表结构...")
    create_project1_tables(cur)
    create_project2_tables(cur)
    create_project3_tables(cur)
    create_project4_tables(cur)
    conn.commit()
    print("  所有表创建完毕")

    # 5. 生成数据
    print("\n[2] 生成并插入数据...")
    generate_project1_data(cur)
    conn.commit()
    generate_project2_data(cur)
    conn.commit()
    generate_project3_data(cur)
    conn.commit()
    generate_project4_data(cur)
    conn.commit()

    # 6. 打印汇总
    print("\n[3] 数据汇总:")
    print("=" * 60)
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"  {t:>30s}: {cnt:>10,} 行")
    print("=" * 60)

    conn.close()

    print(f"""
┌─────────────────────────────────────────────────────┐
│  数据库搭建完成！                                     │
│                                                      │
│  数据库名: {DB_NAME}                      │
│  连接方式: localhost / root / 123456                 │
│  共 {len(tables)} 张表，涵盖四个项目的全部数据              │
│                                                      │
│  下一步: 用 Navicat Premium 16 连接查询               │
└─────────────────────────────────────────────────────┘
""")


if __name__ == "__main__":
    main()
