"""
跃动体育  项目管理中心
=======================
一站式管理脚本：数据生成、分析运行、看板启动、数据导出、清理重置

用法:
  python manage.py                  # 交互式菜单
  python manage.py setup            # 生成全部数据（100人规模）
  python manage.py setup --scale small   # 生成小规模数据（快速测试）
  python manage.py dashboard        # 启动 Dash Web 看板
  python manage.py powerbi          # 导出 Power BI 数据
  python manage.py analyze 1        # 运行项目一分析
  python manage.py analyze all      # 运行全部项目分析
  python manage.py clean            # 清理所有生成数据
  python manage.py info             # 查看项目信息
  python manage.py notebook         # 启动 Jupyter Notebook
"""

import argparse
import os
import sys
import subprocess
import time

# Windows 终端 UTF-8 编码支持
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================
# 0. 全局配置
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIRS = {
    "1": "项目一：公司日常运营指标分析",
    "2": "项目二：老用户激活与价值提升",
    "3": "项目三：各平台ROI预算重新分配",
    "4": "项目四：产品组合分析",
}

SCALE_CONFIGS = {
    "small": {"desc": "小规模（快速测试，~30秒）", "env": {"N_USERS": "5000", "DAU_WEEKDAY": "1200", "DAU_WEEKEND": "800", "DAYS": "90"}},
    "medium": {"desc": "中等规模（原版，~2分钟）", "env": {"N_USERS": "20000", "DAU_WEEKDAY": "5000", "DAU_WEEKEND": "3500", "DAYS": "365"}},
    "large": {"desc": "100人规模（正式版，~5分钟）", "env": {"N_USERS": "200000", "DAU_WEEKDAY": "45000", "DAU_WEEKEND": "30000", "DAYS": "365"}},
}

DB_FILES = [
    "项目一：公司日常运营指标分析/ecommerce_ops.db",
    "项目二：老用户激活与价值提升/user_activation.db",
    "项目三：各平台ROI预算重新分配/roi_allocation.db",
    "项目四：产品组合分析/product_portfolio.db",
]


# ============================================================
# 1. 核心功能
# ============================================================

def print_banner():
    """打印横幅"""
    print()
    print("=" * 50)
    print("    跃动体育  项目管理中心")
    print("    DTC 电商数据分析 Portfolio")
    print("=" * 50)
    print()


def print_info():
    """打印项目信息"""
    print_banner()
    print(" 项目概览：")
    print("  项目一：公司日常运营指标分析（流量转化RFM）")
    print("  项目二：老用户激活与价值提升（RFM-GAB测试）")
    print("  项目三：各平台ROI预算重新分配（边际ROI归因）")
    print("  项目四：产品组合分析（健康度预测补货）")
    print()
    print(" 数据状态：")
    for db_path in DB_FILES:
        full_path = os.path.join(BASE_DIR, db_path)
        if os.path.exists(full_path):
            size_mb = os.path.getsize(full_path) / (1024 * 1024)
            if size_mb > 1024:
                size_str = f"{size_mb/1024:.1f} GB"
            else:
                size_str = f"{size_mb:.1f} MB"
            print(f"  [OK] {db_path}  ({size_str})")
        else:
            print(f"  [--] {db_path}  (未生成)")
    print()
    print(" 常用命令：")
    print("  python manage.py setup           生成全部数据")
    print("  python manage.py dashboard       启动 Web 交互看板")
    print("  python manage.py powerbi         导出 Power BI 数据")
    print("  python manage.py analyze all     运行全部分析")
    print("  python manage.py clean           清理所有数据")
    print()


def run_cmd(cmd, cwd=None, desc=None):
    """运行命令并实时打印输出"""
    if desc:
        print(f"\n {desc}...")
        print(f"  $ {cmd}")
        print()

    cwd = cwd or BASE_DIR

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            text=True,
        )
        if result.returncode != 0:
            print(f"   命令退出码: {result.returncode}")
        else:
            print(f"   完成")
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\n   已中断")
        return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


# ---------- 数据生成 ----------

def cmd_setup(scale="large"):
    """生成模拟数据"""
    config = SCALE_CONFIGS.get(scale, SCALE_CONFIGS["large"])
    print_banner()
    print(f" 数据生成模式：{config['desc']}")
    print()

    # 检查是否已有数据
    existing = [db for db in DB_FILES if os.path.exists(os.path.join(BASE_DIR, db))]
    if existing:
        print(f" 已存在 {len(existing)} 个数据库文件，将被覆盖。")
        print("  如需保留，请先备份。")
        print()
        confirm = input("  确认生成？[Y/n] ").strip().lower()
        if confirm and confirm != 'y':
            print("  已取消。")
            return

    # 修改 company_scale_setup.py 中的参数（临时方案：通过环境变量）
    # 实际做法：直接运行脚本，脚本内已设为 large（100人规模）
    t0 = time.time()
    run_cmd("python company_scale_setup.py", desc="生成 SQLite 数据（四个项目）")
    elapsed = time.time() - t0
    print(f"\n 总耗时: {elapsed:.0f} 秒")
    print_info()


def cmd_clean():
    """清理所有生成的数据"""
    print_banner()
    print(" 清理生成数据...")
    print()

    removed = []
    skipped = []
    for db_path in DB_FILES:
        full_path = os.path.join(BASE_DIR, db_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            removed.append(db_path)
        else:
            skipped.append(db_path)

    for p in removed:
        print(f"   已删除: {p}")
    for p in skipped:
        print(f"   跳过（不存在）: {p}")

    # 清理 Power BI 导出数据
    pbi_data = os.path.join(BASE_DIR, "可视化", "powerbi", "data")
    if os.path.exists(pbi_data):
        import shutil
        for item in os.listdir(pbi_data):
            item_path = os.path.join(pbi_data, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
        print(f"   已清理 Power BI 导出数据")

    print(f"\n 清理完成。运行 'python manage.py setup' 可重新生成。")


# ---------- 分析运行 ----------

def cmd_analyze(project_id):
    """运行指定项目的分析脚本"""
    print_banner()

    if project_id == "all":
        for pid in ["1", "2", "3", "4"]:
            _run_one_analysis(pid)
    elif project_id in PROJECT_DIRS:
        _run_one_analysis(project_id)
    else:
        print(f" 无效项目编号: {project_id}")
        print("  可选: 1, 2, 3, 4, all")


def _run_one_analysis(pid):
    """运行单个项目分析"""
    proj_dir = PROJECT_DIRS[pid]
    proj_path = os.path.join(BASE_DIR, proj_dir)

    # 检查数据库
    db_files_in_dir = [f for f in os.listdir(proj_path) if f.endswith('.db')] if os.path.exists(proj_path) else []
    if not db_files_in_dir:
        print(f"   项目{pid}：数据库不存在，请先运行 'python manage.py setup'")
        return

    # 运行 analysis.py
    analysis_py = os.path.join(proj_path, "analysis.py")
    if os.path.exists(analysis_py):
        run_cmd(f"python analysis.py", cwd=proj_path, desc=f"项目{pid}：{proj_dir}")
    else:
        print(f"   项目{pid}：analysis.py 不存在")


# ---------- 看板 & 工具 ----------

def cmd_dashboard():
    """启动 Dash Web 看板"""
    print_banner()
    print(" 启动 Dash Web 交互看板...")
    print("  浏览器访问: http://127.0.0.1:8050")
    print("  按 Ctrl+C 停止")
    print()

    vis_dir = os.path.join(BASE_DIR, "可视化")
    run_cmd("python dashboard.py", cwd=vis_dir, desc="启动看板服务器")


def cmd_powerbi():
    """导出 Power BI 数据"""
    print_banner()
    print(" 导出 Power BI 数据...")
    vis_dir = os.path.join(BASE_DIR, "可视化")
    run_cmd("python export_for_powerbi.py", cwd=vis_dir, desc="导出 CSV 数据")
    print()
    print("  下一步：打开 Power BI Desktop  获取数据  CSV")
    print("  看板文件: 可视化/powerbi/项目可视化.pbix")


def cmd_notebook():
    """启动 Jupyter Notebook"""
    print_banner()
    print(" 启动 Jupyter Notebook...")
    print("  在浏览器中选择项目目录下的 .ipynb 文件即可开始分析")
    print()
    run_cmd("jupyter notebook", cwd=BASE_DIR, desc="启动 Jupyter")


# ============================================================
# 2. 交互式菜单
# ============================================================

def interactive_menu():
    """交互式命令行菜单"""
    while True:
        print_banner()
        print("请选择操作：")
        print()
        print("   数据管理")
        print("    [1]  生成全部数据（100人规模）")
        print("    [2]  生成小规模数据（快速测试）")
        print("    [3]  清理所有生成数据")
        print()
        print("   分析运行")
        print("    [4]  运行项目一分析")
        print("    [5]  运行项目二分析")
        print("    [6]  运行项目三分析")
        print("    [7]  运行项目四分析")
        print("    [8]  运行全部项目分析")
        print()
        print("   可视化")
        print("    [9]  启动 Dash Web 看板")
        print("    [10] 导出 Power BI 数据")
        print()
        print("   工具")
        print("    [11] 启动 Jupyter Notebook")
        print("    [12] 查看项目信息")
        print()
        print("  [q]  退出")
        print()

        choice = input("请输入选项: ").strip()

        if choice == 'q':
            print(" 再见！")
            break
        elif choice == '1':
            cmd_setup("large")
        elif choice == '2':
            cmd_setup("small")
        elif choice == '3':
            cmd_clean()
        elif choice == '4':
            cmd_analyze("1")
        elif choice == '5':
            cmd_analyze("2")
        elif choice == '6':
            cmd_analyze("3")
        elif choice == '7':
            cmd_analyze("4")
        elif choice == '8':
            cmd_analyze("all")
        elif choice == '9':
            cmd_dashboard()
        elif choice == '10':
            cmd_powerbi()
        elif choice == '11':
            cmd_notebook()
        elif choice == '12':
            print_info()
        else:
            print(f"\n 无效选项: {choice}")

        if choice.isdigit() and 1 <= int(choice) <= 12:
            input("\n按 Enter 返回菜单...")


# ============================================================
# 3. CLI 入口（argparse）
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="跃动体育  项目管理中心",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python manage.py                    交互式菜单
  python manage.py setup              生成全部数据
  python manage.py setup --scale small  生成小规模测试数据
  python manage.py dashboard          启动 Web 看板
  python manage.py analyze all        运行全部分析
  python manage.py clean              清理数据
        """,
    )

    sub = parser.add_subparsers(dest="command", help="可用命令")

    # setup
    p_setup = sub.add_parser("setup", help="生成模拟数据")
    p_setup.add_argument("--scale", choices=["small", "medium", "large"],
                         default="large", help="数据规模 (默认: large)")

    # clean
    sub.add_parser("clean", help="清理所有生成数据")

    # analyze
    p_analyze = sub.add_parser("analyze", help="运行分析脚本")
    p_analyze.add_argument("project", choices=["1", "2", "3", "4", "all"],
                           help="项目编号 (1/2/3/4/all)")

    # dashboard
    sub.add_parser("dashboard", help="启动 Dash Web 交互看板")

    # powerbi
    sub.add_parser("powerbi", help="导出 Power BI 数据")

    # notebook
    sub.add_parser("notebook", help="启动 Jupyter Notebook")

    # info
    sub.add_parser("info", help="查看项目信息")

    args = parser.parse_args()

    if not args.command:
        # 无参数  交互式菜单
        try:
            interactive_menu()
        except KeyboardInterrupt:
            print("\n 再见！")
    elif args.command == "setup":
        cmd_setup(args.scale)
    elif args.command == "clean":
        cmd_clean()
    elif args.command == "analyze":
        cmd_analyze(args.project)
    elif args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "powerbi":
        cmd_powerbi()
    elif args.command == "notebook":
        cmd_notebook()
    elif args.command == "info":
        print_info()


if __name__ == "__main__":
    main()
