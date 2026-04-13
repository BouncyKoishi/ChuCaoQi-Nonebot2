"""
从生产数据库导出 initialize.sql

仅导出必备种子数据：
- kusaitemlist 全部数据
- flag 中 forAll=1 的全局配置

使用方法：
python scripts/export_initialize_sql.py [源数据库路径]
"""

import sqlite3
import sys
import os


def escape_sql_value(val):
    if val is None:
        return 'NULL'
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''").replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return f"'{s}'"


def export_initialize_sql(db_path):
    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    lines = []
    lines.append("-- ============================================================")
    lines.append("-- 除草器Bot 冷启动初始化数据")
    lines.append("-- 自动生成，请勿手动修改")
    lines.append("-- ============================================================")
    lines.append("")

    # kusaitemlist
    lines.append("-- ----------------------------")
    lines.append("-- Records of kusaitemlist")
    lines.append("-- ----------------------------")

    cursor.execute("SELECT name, detail, type, isControllable, isTransferable, shopPrice, sellingPrice, priceRate, priceType, amountLimit, shopPreItems FROM kusaitemlist ORDER BY name")
    rows = cursor.fetchall()
    for row in rows:
        values = ", ".join([escape_sql_value(v) for v in row])
        lines.append(f"INSERT INTO \"kusaitemlist\" VALUES ({values});")

    lines.append("")

    # flag (forAll=1)
    lines.append("-- ----------------------------")
    lines.append("-- Records of flag (global flags only)")
    lines.append("-- ----------------------------")

    cursor.execute("SELECT name, value, forAll FROM flag WHERE forAll = 1 ORDER BY id")
    rows = cursor.fetchall()
    for row in rows:
        name, value, forAll = row
        lines.append(f"INSERT INTO \"flag\" (\"name\", \"value\", \"forAll\") VALUES ({escape_sql_value(name)}, {escape_sql_value(value)}, {escape_sql_value(forAll)});")

    conn.close()

    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "initialize.sql")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")

    print(f"[OK] exported to: {output_path}")
    print(f"   kusaitemlist: {len(rows)} 条 flag 记录")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "scripts/chuchu.sqlite"
    export_initialize_sql(db_path)
