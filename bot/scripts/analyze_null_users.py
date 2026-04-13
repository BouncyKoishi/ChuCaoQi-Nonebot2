import sqlite3

conn = sqlite3.connect('database/chuchu.sqlite')
cursor = conn.cursor()

# 1. 统计 NULL userId 记录数量
cursor.execute('SELECT COUNT(*) FROM kusabase WHERE userId IS NULL')
null_count = cursor.fetchone()[0]
print(f"NULL userId 记录数: {null_count}")

# 2. 查看 NULL userId 记录的特征
cursor.execute('''
    SELECT id, name, title, kusa, advKusa, vipLevel, lastUseTime 
    FROM kusabase 
    WHERE userId IS NULL 
    ORDER BY id
    LIMIT 20
''')
rows = cursor.fetchall()
print("\n前 20 条 NULL userId 记录:")
for row in rows:
    print(f"  id={row[0]}, name={row[1]}, title={row[2]}, kusa={row[3]}, advKusa={row[4]}, vipLevel={row[5]}")

# 3. 检查这些记录是否有对应的 kusafield
cursor.execute('''
    SELECT COUNT(*) 
    FROM kusabase kb 
    LEFT JOIN kusafield kf ON kb.id = kf.userId 
    WHERE kb.userId IS NULL AND kf.id IS NOT NULL
''')
has_kusafield = cursor.fetchone()[0]
print(f"\n有对应 kusafield 记录的: {has_kusafield}")

# 4. 检查这些记录是否有对应的 kusahistory
cursor.execute('''
    SELECT COUNT(*) 
    FROM kusabase kb 
    LEFT JOIN kusahistory kh ON kb.id = kh.userId 
    WHERE kb.userId IS NULL AND kh.id IS NOT NULL
''')
has_kusahistory = cursor.fetchone()[0]
print(f"有对应 kusahistory 记录的: {has_kusahistory}")

# 5. 检查有效记录的特征
cursor.execute('''
    SELECT COUNT(*), SUM(CASE WHEN name IS NULL THEN 1 ELSE 0 END) 
    FROM kusabase 
    WHERE userId IS NOT NULL
''')
valid_total, valid_null_name = cursor.fetchone()
print(f"\n有效 userId 记录总数: {valid_total}")
print(f"其中 name 为 NULL 的: {valid_null_name}")

# 6. 检查 unifieduser 和 kusabase 的数量关系
cursor.execute('SELECT COUNT(*) FROM unifieduser')
unified_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM kusabase WHERE userId IS NOT NULL')
kusabase_valid = cursor.fetchone()[0]
print(f"\nunifieduser 总数: {unified_count}")
print(f"kusabase 有效记录数: {kusabase_valid}")

conn.close()
