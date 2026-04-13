import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'scripts/chuchu.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print(f'=== 数据库表列表 ({db_path}) ===')
for t in tables:
    print(t[0])
print()
for t in tables:
    cursor.execute(f'PRAGMA table_info({t[0]})')
    cols = cursor.fetchall()
    cursor.execute(f'SELECT COUNT(*) FROM {t[0]}')
    count = cursor.fetchone()[0]
    print(f'--- {t[0]} ({count} rows) ---')
    for c in cols:
        print(f'  {c[1]} {c[2]} null={c[3]} default={c[4]}')
    print()
conn.close()
