"""
开发环境数据库修复脚本

修复 database/chuchu.sqlite 中与 ORM 模型不一致的结构问题：
1. traderecord.userId: TEXT → INTEGER
2. drawitemlist.authorId: VARCHAR(12) → INTEGER
3. workorder.authorId: VARCHAR(12) → INTEGER
4. flag.ownerId: TEXT → INTEGER
5. kusabase: 删除冗余字段 isSuperAdmin/isRobot/relatedQQ
6. 删除残留临时表 _unifieduser_old_20260407

使用方法：
python scripts/fix_dev_db.py [数据库路径]

默认路径: database/chuchu.sqlite
"""

import sqlite3
import os
import sys
import shutil
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def check_column_type(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    for col in cursor.fetchall():
        if col[1] == column:
            return col[2].upper()
    return None


def has_columns(cursor, table, columns):
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {col[1] for col in cursor.fetchall()}
    return all(col in existing for col in columns)


def fix_table(cursor, table, new_schema, select_sql, insert_sql, transform_row=None):
    cursor.execute(f"DROP TABLE IF EXISTS {table}_new")
    cursor.execute(new_schema)

    cursor.execute(select_sql)
    rows = cursor.fetchall()

    migrated = 0
    for row in rows:
        if transform_row:
            row = transform_row(row)
        cursor.execute(insert_sql, row)
        migrated += 1

    cursor.execute(f"DROP TABLE {table}")
    cursor.execute(f"ALTER TABLE {table}_new RENAME TO {table}")
    return migrated


def fix_database(db_path):
    if not os.path.exists(db_path):
        print(f"[ERROR] database not found: {db_path}")
        return False

    backup_path = db_path.replace('.sqlite', f'_backup_before_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sqlite')
    shutil.copy(db_path, backup_path)
    print(f"[OK] backed up to: {backup_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("fixing dev database structure...")
    print("=" * 60)

    # ============================================================
    # fix1: traderecord.userId TEXT -> INTEGER
    # ============================================================
    print("\n[fix1: traderecord.userId type]")

    current_type = check_column_type(cursor, "traderecord", "userId")
    if current_type == "INTEGER":
        print("  [SKIP] already INTEGER")
    else:
        print(f"  current type: {current_type}")
        cursor.execute("SELECT COUNT(*) FROM traderecord")
        count = cursor.fetchone()[0]

        def transform_traderecord(row):
            try:
                user_id = int(row[1]) if row[1] is not None else None
            except (ValueError, TypeError):
                user_id = None
            return (row[0], user_id, row[2], row[3], row[4], row[5], row[6], row[7], row[8])

        migrated = fix_table(
            cursor, "traderecord",
            """CREATE TABLE traderecord_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER,
                tradeType TEXT NOT NULL,
                gainItemAmount INTEGER,
                gainItemName TEXT,
                costItemAmount INTEGER,
                costItemName TEXT,
                detail TEXT,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
            )""",
            "SELECT id, userId, tradeType, gainItemAmount, gainItemName, costItemAmount, costItemName, detail, timestamp FROM traderecord",
            "INSERT INTO traderecord_new (id, userId, tradeType, gainItemAmount, gainItemName, costItemAmount, costItemName, detail, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            transform_traderecord
        )
        print(f"  [OK] fixed {migrated}/{count} rows")

    # ============================================================
    # fix2: drawitemlist.authorId VARCHAR(12) -> INTEGER
    # ============================================================
    print("\n[fix2: drawitemlist.authorId type]")

    current_type = check_column_type(cursor, "drawitemlist", "authorId")
    if current_type == "INTEGER":
        print("  [SKIP] already INTEGER")
    else:
        print(f"  current type: {current_type}")
        cursor.execute("SELECT COUNT(*) FROM drawitemlist")
        count = cursor.fetchone()[0]

        def transform_drawitemlist(row):
            try:
                author_id = int(row[5]) if row[5] is not None else None
            except (ValueError, TypeError):
                author_id = None
            return (row[0], row[1], row[2], row[3], row[4], author_id)

        migrated = fix_table(
            cursor, "drawitemlist",
            """CREATE TABLE drawitemlist_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(64),
                pool TEXT DEFAULT '默认',
                rareRank INTEGER,
                detail VARCHAR(1024),
                authorId INTEGER
            )""",
            "SELECT id, name, pool, rareRank, detail, authorId FROM drawitemlist",
            "INSERT INTO drawitemlist_new (id, name, pool, rareRank, detail, authorId) VALUES (?, ?, ?, ?, ?, ?)",
            transform_drawitemlist
        )
        print(f"  [OK] fixed {migrated}/{count} rows")

    # ============================================================
    # fix3: workorder.authorId VARCHAR(12) -> INTEGER
    # ============================================================
    print("\n[fix3: workorder.authorId type]")

    current_type = check_column_type(cursor, "workorder", "authorId")
    if current_type == "INTEGER":
        print("  [SKIP] already INTEGER")
    else:
        print(f"  current type: {current_type}")
        cursor.execute("SELECT COUNT(*) FROM workorder")
        count = cursor.fetchone()[0]

        def transform_workorder(row):
            try:
                author_id = int(row[2]) if row[2] is not None else None
            except (ValueError, TypeError):
                author_id = None
            return (row[0], row[1], author_id, row[3], row[4])

        migrated = fix_table(
            cursor, "workorder",
            """CREATE TABLE workorder_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(128) NOT NULL,
                authorId INTEGER,
                detail VARCHAR(1024),
                reply VARCHAR(512)
            )""",
            "SELECT id, title, authorId, detail, reply FROM workorder",
            "INSERT INTO workorder_new (id, title, authorId, detail, reply) VALUES (?, ?, ?, ?, ?)",
            transform_workorder
        )
        print(f"  [OK] fixed {migrated}/{count} rows")

    # ============================================================
    # fix4: flag.ownerId TEXT -> INTEGER
    # ============================================================
    print("\n[fix4: flag.ownerId type]")

    current_type = check_column_type(cursor, "flag", "ownerId")
    if current_type == "INTEGER":
        print("  [SKIP] already INTEGER")
    else:
        print(f"  current type: {current_type}")
        cursor.execute("SELECT COUNT(*) FROM flag")
        count = cursor.fetchone()[0]

        def transform_flag(row):
            try:
                owner_id = int(row[4]) if row[4] is not None else None
            except (ValueError, TypeError):
                owner_id = None
            return (row[0], row[1], row[2], row[3], owner_id)

        migrated = fix_table(
            cursor, "flag",
            """CREATE TABLE flag_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                value INTEGER DEFAULT 0,
                forAll INTEGER DEFAULT 1,
                ownerId INTEGER
            )""",
            "SELECT id, name, value, forAll, ownerId FROM flag",
            "INSERT INTO flag_new (id, name, value, forAll, ownerId) VALUES (?, ?, ?, ?, ?)",
            transform_flag
        )
        print(f"  [OK] fixed {migrated}/{count} rows")

    # ============================================================
    # fix5: kusabase remove redundant fields
    # ============================================================
    print("\n[fix5: kusabase remove redundant fields]")

    if has_columns(cursor, "kusabase", ["isSuperAdmin", "isRobot", "relatedQQ"]):
        cursor.execute("SELECT COUNT(*) FROM kusabase")
        count = cursor.fetchone()[0]

        migrated = fix_table(
            cursor, "kusabase",
            """CREATE TABLE kusabase_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER,
                name TEXT,
                title TEXT,
                kusa INTEGER DEFAULT 0,
                advKusa INTEGER DEFAULT 0,
                vipLevel INTEGER DEFAULT 0,
                lastUseTime TIMESTAMP,
                FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
            )""",
            "SELECT id, userId, name, title, kusa, advKusa, vipLevel, lastUseTime FROM kusabase",
            "INSERT INTO kusabase_new (id, userId, name, title, kusa, advKusa, vipLevel, lastUseTime) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        print(f"  [OK] fixed {migrated}/{count} rows")
    else:
        print("  [SKIP] no redundant fields")

    # ============================================================
    # fix6: drop residual temp tables
    # ============================================================
    print("\n[fix6: drop residual temp tables]")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '\\_%' ESCAPE '\\' AND name NOT LIKE 'sqlite_%'")
    temp_tables = cursor.fetchall()
    for tt in temp_tables:
        table_name = tt[0]
        cursor.execute(f"DROP TABLE IF EXISTS [{table_name}]")
        print(f"  [OK] dropped: {table_name}")

    if not temp_tables:
        print("  [SKIP] no temp tables")

    # ============================================================
    # update sqlite_sequence
    # ============================================================
    print("\n[update sqlite_sequence]")

    cursor.execute("DELETE FROM sqlite_sequence")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '\\_%' ESCAPE '\\'")
    all_tables = cursor.fetchall()
    for (table_name,) in all_tables:
        try:
            cursor.execute(f"SELECT MAX(id) FROM [{table_name}]")
            max_id = cursor.fetchone()[0]
            if max_id:
                cursor.execute("INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table_name, max_id))
        except Exception:
            pass

    print("  [OK] updated sqlite_sequence")

    # ============================================================
    # commit
    # ============================================================
    conn.commit()

    # ============================================================
    # verify
    # ============================================================
    print("\n" + "=" * 60)
    print("verifying fixes...")
    print("=" * 60)

    checks = [
        ("traderecord", "userId", "INTEGER"),
        ("drawitemlist", "authorId", "INTEGER"),
        ("workorder", "authorId", "INTEGER"),
        ("flag", "ownerId", "INTEGER"),
    ]

    all_ok = True
    for table, col, expected_type in checks:
        actual_type = check_column_type(cursor, table, col)
        status = "[OK]" if actual_type == expected_type else "[FAIL]"
        if actual_type != expected_type:
            all_ok = False
        print(f"  {status} {table}.{col}: {actual_type} (expected: {expected_type})")

    if has_columns(cursor, "kusabase", ["isSuperAdmin", "isRobot", "relatedQQ"]):
        print("  [FAIL] kusabase still has redundant fields")
        all_ok = False
    else:
        print("  [OK] kusabase has no redundant fields")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '\\_%' ESCAPE '\\' AND name NOT LIKE 'sqlite_%'")
    temp_tables = cursor.fetchall()
    if temp_tables:
        print(f"  [FAIL] residual temp tables: {[t[0] for t in temp_tables]}")
        all_ok = False
    else:
        print("  [OK] no residual temp tables")

    conn.close()

    print("\n" + "=" * 60)
    if all_ok:
        print("[OK] database fix completed! all checks passed")
    else:
        print("[WARN] database fix completed, but some checks failed")
    print(f"database: {db_path}")
    print(f"backup: {backup_path}")
    print("=" * 60)

    return all_ok


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "database/chuchu.sqlite"
    fix_database(db_path)
