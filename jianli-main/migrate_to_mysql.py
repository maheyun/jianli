"""
SQLite → MySQL 数据迁移脚本
============================
将公司规模 SQLite 数据一键导入 MySQL，供 Navicat 连接查询。

前提: 已运行 company_scale_setup.py 生成 SQLite 数据
运行: python migrate_to_mysql.py
结果: MySQL 中创建 ecommerce_analysis 库，包含全部 13 张表
"""

import sqlite3
import pymysql
import os

# 所有 MySQL 表的手动建表语句（避免 SQLite DDL 转换的兼容性问题）
MYSQL_SCHEMAS = {
    "user_behavior": """CREATE TABLE user_behavior (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        action VARCHAR(20) NOT NULL,
        product_id INT NOT NULL,
        create_time VARCHAR(30) NOT NULL,
        INDEX idx_ub_time (create_time),
        INDEX idx_ub_user (user_id)
    ) ENGINE=InnoDB""",
    "orders": """CREATE TABLE orders (
        order_id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        amount DOUBLE NOT NULL,
        order_status VARCHAR(20) NOT NULL,
        create_time VARCHAR(30) NOT NULL,
        INDEX idx_o_user (user_id),
        INDEX idx_o_time (create_time)
    ) ENGINE=InnoDB""",
    "users_p2": """CREATE TABLE users_p2 (
        user_id INT PRIMARY KEY,
        registration_date VARCHAR(20) NOT NULL,
        gender VARCHAR(10),
        age INT,
        behavior_type VARCHAR(20),
        INDEX idx_u2_id (user_id)
    ) ENGINE=InnoDB""",
    "orders_p2": """CREATE TABLE orders_p2 (
        order_id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        amount DOUBLE NOT NULL,
        order_status VARCHAR(20) NOT NULL,
        create_time VARCHAR(30) NOT NULL,
        INDEX idx_o2_user (user_id),
        INDEX idx_o2_time (create_time)
    ) ENGINE=InnoDB""",
    "order_items_p2": """CREATE TABLE order_items_p2 (
        order_item_id INT PRIMARY KEY AUTO_INCREMENT,
        order_id INT NOT NULL,
        product_id INT NOT NULL,
        quantity INT DEFAULT 1,
        price DOUBLE,
        INDEX idx_oi_order (order_id)
    ) ENGINE=InnoDB""",
    "products_p2": """CREATE TABLE products_p2 (
        product_id INT PRIMARY KEY,
        product_name VARCHAR(100),
        category_id INT,
        price DOUBLE
    ) ENGINE=InnoDB""",
    "user_activities": """CREATE TABLE user_activities (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        activity_id INT,
        activity_date VARCHAR(20),
        is_participated TINYINT DEFAULT 0,
        INDEX idx_ua_user (user_id)
    ) ENGINE=InnoDB""",
    "ad_campaigns": """CREATE TABLE ad_campaigns (
        campaign_id INT PRIMARY KEY,
        platform VARCHAR(20) NOT NULL,
        campaign_type VARCHAR(30),
        campaign_date VARCHAR(20) NOT NULL,
        spend DOUBLE NOT NULL,
        impressions INT,
        clicks INT,
        conversions INT,
        revenue DOUBLE,
        INDEX idx_ac_plat (platform),
        INDEX idx_ac_date (campaign_date)
    ) ENGINE=InnoDB""",
    "attribution_data": """CREATE TABLE attribution_data (
        id INT PRIMARY KEY AUTO_INCREMENT,
        user_id INT NOT NULL,
        touchpoint VARCHAR(20),
        platform VARCHAR(20),
        event_time VARCHAR(20),
        conversion_time VARCHAR(20),
        days_to_conversion INT,
        INDEX idx_att_plat (platform)
    ) ENGINE=InnoDB""",
    "products_p4": """CREATE TABLE products_p4 (
        product_id INT PRIMARY KEY,
        product_name VARCHAR(100),
        category_id INT,
        price DOUBLE,
        cost DOUBLE,
        launch_date VARCHAR(20),
        curve_type VARCHAR(20)
    ) ENGINE=InnoDB""",
    "sales_data": """CREATE TABLE sales_data (
        id INT PRIMARY KEY AUTO_INCREMENT,
        product_id INT NOT NULL,
        platform VARCHAR(20),
        sale_date VARCHAR(20) NOT NULL,
        sales_volume INT,
        sales_amount DOUBLE,
        INDEX idx_s_pid (product_id),
        INDEX idx_s_date (sale_date)
    ) ENGINE=InnoDB""",
    "inventory_data": """CREATE TABLE inventory_data (
        product_id INT PRIMARY KEY,
        initial_stock INT,
        current_stock INT,
        safety_stock INT,
        lead_time_days INT
    ) ENGINE=InnoDB""",
}

MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "charset": "utf8mb4",
}
DB_NAME = "ecommerce_analysis"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据映射: (sqlite文件路径, {sqlite表名: mysql表名})
# MySQL 中所有表在同一库，需要区分项目来源
PROJECTS = [
    ("项目一：公司日常运营指标分析/ecommerce_ops.db", {
        "user_behavior": "user_behavior",      # 唯一，不加后缀
        "orders": "orders",                    # 唯一，不加后缀
    }),
    ("项目二：老用户激活与价值提升/user_activation.db", {
        "users": "users_p2",
        "orders": "orders_p2",
        "order_items": "order_items_p2",
        "products": "products_p2",
        "user_activities": "user_activities",
    }),
    ("项目三：各平台ROI预算重新分配/roi_allocation.db", {
        "ad_campaigns": "ad_campaigns",        # 唯一
        "attribution_data": "attribution_data", # 唯一
    }),
    ("项目四：产品组合分析/product_portfolio.db", {
        "products": "products_p4",
        "sales_data": "sales_data",
        "inventory_data": "inventory_data",
    }),
]


def get_mysql_conn(with_db=True):
    cfg = MYSQL_CONFIG.copy()
    if with_db:
        cfg["database"] = DB_NAME
    return pymysql.connect(**cfg)


def create_database():
    conn = get_mysql_conn(with_db=False)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4")
    conn.commit()
    conn.close()
    print(f"[OK] 数据库 {DB_NAME} 已就绪")


def get_sqlite_schema(sqlite_path, table_name):
    """从 SQLite 获取建表信息"""
    conn = sqlite3.connect(os.path.join(BASE_DIR, sqlite_path))
    cur = conn.cursor()
    cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    row = cur.fetchone()
    print(row)
    conn.close()
    if row:
        return row[0]
    return None


def migrate_table(mysql_cur, sqlite_path, sqlite_table, mysql_table):
    """将单张表从 SQLite 复制到 MySQL"""
    full_path = os.path.join(BASE_DIR, sqlite_path)
    sq_conn = sqlite3.connect(full_path)
    sq_cur = sq_conn.cursor()

    # 获取列名
    sq_cur.execute(f"PRAGMA table_info({sqlite_table})")
    columns = [row[1] for row in sq_cur.fetchall()]

    # 读取数据（分批处理，避免内存爆）
    sq_cur.execute(f"SELECT * FROM {sqlite_table}")

    batch_size = 5000
    total = 0
    placeholders = ", ".join(["%s"] * len(columns))
    cols_str = ", ".join([f"`{c}`" for c in columns])
    insert_sql = f"INSERT INTO `{mysql_table}` ({cols_str}) VALUES ({placeholders})"

    while True:
        rows = sq_cur.fetchmany(batch_size)
        if not rows:
            break
        mysql_cur.executemany(insert_sql, rows)
        total += len(rows)

    sq_conn.close()
    return total


def main():
    print("=" * 60)
    print("  SQLite → MySQL 数据迁移")
    print("=" * 60)

    # 1. 建库
    create_database()
    mysql_conn = get_mysql_conn(with_db=True)
    mysql_cur = mysql_conn.cursor()

    # 2. 处理每个项目
    for sqlite_path, table_map in PROJECTS:
        project_name = os.path.dirname(sqlite_path)
        print(f"\n[{project_name}]")

        for sqlite_table, mysql_table in table_map.items():
            mysql_cur.execute(f"DROP TABLE IF EXISTS `{mysql_table}`")

            # 使用硬编码的 MySQL 建表语句（比解析 SQLite DDL 更可靠）
            # 仅需 VARCHAR 替代 TEXT、DOUBLE 替代 REAL、AUTO_INCREMENT 替代 AUTOINCREMENT
            create_sql = MYSQL_SCHEMAS.get(mysql_table)
            if create_sql is None:
                print(f"  [WARN] 无 MySQL 建表语句: {mysql_table}，跳过")
                continue

            try:
                mysql_cur.execute(create_sql)
            except Exception as e:
                print(f"  [ERR] 建表失败 {mysql_table}: {e}")
                continue

            # 迁移数据
            try:
                n = migrate_table(mysql_cur, sqlite_path, sqlite_table, mysql_table)
                print(f"  {sqlite_table} -> {mysql_table}: {n:,} 行")
            except Exception as e:
                print(f"  [ERR] 数据迁移失败: {e}")
                import traceback; traceback.print_exc()
                continue

            mysql_conn.commit()

    # 3. 统计
    print(f"\n{'='*60}")
    print("  数据汇总:")
    print(f"{'='*60}")
    for sqlite_path, table_map in PROJECTS:
        for mysql_table in table_map.values():
            try:
                mysql_cur.execute(f"SELECT COUNT(*) FROM `{mysql_table}`")
                cnt = mysql_cur.fetchone()[0]
                print(f"  {table_name:>30s}: {cnt:>10,} 行")
            except:
                pass
    print("=" * 60)

    mysql_conn.close()
    print(f"""
  迁移完成！
  连接方式: localhost / root / 123456
  数据库:   {DB_NAME}
  表数量:   13 张

  现在可以用 Navicat 连接查询了.
""")


if __name__ == "__main__":
    main()
