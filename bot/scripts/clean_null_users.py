"""
清理开发数据库中 userId 为 NULL 的无效记录

这些记录是早期开发遗留的测试/占位数据，没有有效的用户关联
"""

import sqlite3
import shutil
from datetime import datetime

db_path = 'database/chuchu.sqlite'

# 备份
backup_path = db_path.replace('.sqlite', f'_backup_before_clean_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sqlite')
shutil.copy(db_path, backup_path)
print(f"[OK] backed up to: {backup_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 统计并删除
tables_to_clean = [
    ('kusabase', 'userId'),
    ('kusafield', 'userId'),
    ('kusaitemstorage', 'userId'),
]

total_deleted = 0
for table, col in tables_to_clean:
    cursor.execute(f'SELECT COUNT(*) FROM {table} WHERE {col} IS NULL')
    count = cursor.fetchone()[0]
    if count > 0:
        cursor.execute(f'DELETE FROM {table} WHERE {col} IS NULL')
        print(f"[OK] deleted {count} records from {table}")
        total_deleted += count
    else:
        print(f"[SKIP] no NULL {col} in {table}")

# 更新 sqlite_sequence
cursor.execute("DELETE FROM sqlite_sequence")
for table, _ in tables_to_clean:
    try:
        cursor.execute(f"SELECT MAX(id) FROM {table}")
        max_id = cursor.fetchone()[0]
        if max_id:
            cursor.execute("INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, max_id))
    except:
        pass

conn.commit()
conn.close()

print(f"\n[OK] total deleted: {total_deleted} records")
