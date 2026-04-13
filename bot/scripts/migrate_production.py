"""
生产数据库迁移脚本：从旧版数据库迁移到三端共通身份系统

将 scripts/chuchu.sqlite（生产环境旧版）迁移到当前数据库结构

主要变更：
1. 新增 UnifiedUser 表（统一用户表，含 sessionToken 等新字段）
2. 新增 GroupMapping 表（群组映射表）
3. 所有业务表使用 userId (INTEGER) 外键关联到 UnifiedUser
4. user 表重命名为 kusabase，移除冗余字段 isSuperAdmin/isRobot/relatedQQ
5. 修正字段类型：traderecord.userId, drawitemlist.authorId, workorder.authorId, flag.ownerId 均为 INTEGER
6. KusaField 新增 msgId/msgCreateTime/groupOpenid 字段

使用方法：
python scripts/migrate_production.py [源数据库路径] [目标数据库路径]

示例：
python scripts/migrate_production.py scripts/chuchu.sqlite database/chuchu_migrated.sqlite
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


def migrate_database(source_db_path, target_db_path):
    if not os.path.exists(source_db_path):
        print(f"❌ 源数据库不存在: {source_db_path}")
        return False

    shutil.copy(source_db_path, target_db_path)
    print(f"✅ 已复制源数据库到: {target_db_path}")

    conn = sqlite3.connect(target_db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("开始数据库迁移...")
    print("=" * 60)

    # ============================================================
    # 步骤1: 创建 UnifiedUser 表
    # ============================================================
    print("\n【步骤1: 创建 UnifiedUser 表】")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unifieduser (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            realQQ VARCHAR(12) UNIQUE,
            qqbotOpenid VARCHAR(128) UNIQUE,
            webToken VARCHAR(64) UNIQUE,
            webTokenCreatedAt TIMESTAMP,
            sessionToken VARCHAR(64) UNIQUE,
            sessionTokenExpiresAt TIMESTAMP,
            isSuperAdmin INTEGER DEFAULT 0,
            isRobot INTEGER DEFAULT 0,
            relatedUserId INTEGER DEFAULT NULL,
            createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ 创建 unifieduser 表成功")

    # ============================================================
    # 步骤2: 创建 GroupMapping 表 - 已禁用
    # ============================================================
    # print("\n【步骤2: 创建 GroupMapping 表】")
    # cursor.execute("""
    #     CREATE TABLE IF NOT EXISTS groupmapping (
    #         id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         onebotGroupId VARCHAR(12) UNIQUE,
    #         qqbotGroupOpenid VARCHAR(128) UNIQUE,
    #         groupName VARCHAR(64),
    #         allowAutoBind INTEGER DEFAULT 0,
    #         createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     )
    # """)
    # print("  ✅ 创建 groupmapping 表成功")

    # ============================================================
    # 步骤3: 从 user 表迁移数据到 UnifiedUser 和 KusaBase
    # ============================================================
    print("\n【步骤2: 迁移 user 表数据】")

    cursor.execute("SELECT qq, name, title, kusa, advKusa, vipLevel, isSuperAdmin, isRobot, relatedQQ, lastUseTime FROM user")
    users = cursor.fetchall()
    print(f"  找到 {len(users)} 条 user 记录")

    qq_to_userId = {}

    for user in users:
        qq, name, title, kusa, advKusa, vipLevel, isSuperAdmin, isRobot, relatedQQ, lastUseTime = user

        cursor.execute("""
            INSERT INTO unifieduser (realQQ, isSuperAdmin, isRobot, relatedUserId)
            VALUES (?, ?, ?, ?)
        """, (qq, isSuperAdmin if isSuperAdmin else 0, isRobot if isRobot else 0, None))

        userId = cursor.lastrowid
        qq_to_userId[qq] = userId

    print(f"  ✅ 已创建 {len(qq_to_userId)} 条 UnifiedUser 记录")

    # 更新 relatedUserId
    cursor.execute("SELECT id, realQQ FROM unifieduser WHERE realQQ IS NOT NULL")
    all_users = cursor.fetchall()
    qq_to_new_id = {row[1]: row[0] for row in all_users}

    updated_related = 0
    for user in users:
        qq = user[0]
        relatedQQ = user[8]
        if relatedQQ and str(relatedQQ) in qq_to_new_id:
            userId = qq_to_userId[qq]
            relatedUserId = qq_to_new_id[str(relatedQQ)]
            cursor.execute("UPDATE unifieduser SET relatedUserId = ? WHERE id = ?", (relatedUserId, userId))
            updated_related += 1

    print(f"  ✅ 已更新 {updated_related} 条 relatedUserId")

    # 创建新的 kusabase 表（不含 isSuperAdmin/isRobot/relatedQQ，符合 ORM 模型）
    cursor.execute("""
        CREATE TABLE kusabase_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            name TEXT,
            title TEXT,
            kusa INTEGER DEFAULT 0,
            advKusa INTEGER DEFAULT 0,
            vipLevel INTEGER DEFAULT 0,
            lastUseTime TIMESTAMP,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
        )
    """)

    for user in users:
        qq, name, title, kusa, advKusa, vipLevel, isSuperAdmin, isRobot, relatedQQ, lastUseTime = user
        userId = qq_to_userId.get(qq)
        if userId:
            cursor.execute("""
                INSERT INTO kusabase_new (userId, name, title, kusa, advKusa, vipLevel, lastUseTime)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (userId, name, title, kusa if kusa else 0, advKusa if advKusa else 0,
                  vipLevel if vipLevel else 0, lastUseTime))

    cursor.execute("DROP TABLE user")
    cursor.execute("ALTER TABLE kusabase_new RENAME TO kusabase")
    print(f"  ✅ 已迁移 {len(users)} 条记录到 kusabase 表")

    # ============================================================
    # 步骤3: 迁移 kusafield 表
    # ============================================================
    print("\n【步骤3: 迁移 kusafield 表】")

    cursor.execute("PRAGMA table_info(kusafield)")
    kusafield_cols = cursor.fetchall()
    kusafield_col_names = [col[1] for col in kusafield_cols]
    print(f"  kusafield 表列: {kusafield_col_names}")

    cursor.execute("SELECT * FROM kusafield")
    kusafields = cursor.fetchall()
    print(f"  找到 {len(kusafields)} 条 kusafield 记录")

    cursor.execute("""
        CREATE TABLE kusafield_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            kusaFinishTs INTEGER,
            isUsingKela INTEGER DEFAULT 0,
            isPrescient INTEGER DEFAULT 0,
            isMirroring INTEGER DEFAULT 0,
            overloadOnHarvest INTEGER DEFAULT 0,
            biogasEffect REAL DEFAULT 1,
            soilCapacity INTEGER DEFAULT 25,
            weedCosting INTEGER DEFAULT 0,
            kusaResult INTEGER DEFAULT 0,
            advKusaResult INTEGER DEFAULT 0,
            kusaType TEXT,
            defaultKusaType TEXT DEFAULT '草',
            lastUseTime TIMESTAMP,
            msgId TEXT,
            msgCreateTime TEXT,
            groupOpenid TEXT,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
        )
    """)

    qq_idx = kusafield_col_names.index('qq')
    kusaFinishTs_idx = kusafield_col_names.index('kusaFinishTs')
    defaultKusaType_idx = kusafield_col_names.index('defaultKusaType')
    isUsingKela_idx = kusafield_col_names.index('isUsingKela')
    isPrescient_idx = kusafield_col_names.index('isPrescient')
    isMirroring_idx = kusafield_col_names.index('isMirroring')
    overloadOnHarvest_idx = kusafield_col_names.index('overloadOnHarvest')
    biogasEffect_idx = kusafield_col_names.index('biogasEffect')
    soilCapacity_idx = kusafield_col_names.index('soilCapacity')
    weedCosting_idx = kusafield_col_names.index('weedCosting')
    kusaResult_idx = kusafield_col_names.index('kusaResult')
    advKusaResult_idx = kusafield_col_names.index('advKusaResult')
    lastUseTime_idx = kusafield_col_names.index('lastUseTime')
    kusaType_idx = kusafield_col_names.index('kusaType') if 'kusaType' in kusafield_col_names else -1

    migrated_count = 0
    for kf in kusafields:
        qq = kf[qq_idx]
        userId = qq_to_userId.get(qq)
        if userId:
            kusaType = kf[kusaType_idx] if kusaType_idx >= 0 else None
            cursor.execute("""
                INSERT INTO kusafield_new (userId, kusaFinishTs, isUsingKela, isPrescient, isMirroring,
                    overloadOnHarvest, biogasEffect, soilCapacity, weedCosting, kusaResult, advKusaResult,
                    kusaType, defaultKusaType, lastUseTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (userId, kf[kusaFinishTs_idx], kf[isUsingKela_idx], kf[isPrescient_idx], kf[isMirroring_idx],
                  kf[overloadOnHarvest_idx], kf[biogasEffect_idx], kf[soilCapacity_idx], kf[weedCosting_idx],
                  kf[kusaResult_idx], kf[advKusaResult_idx], kusaType, kf[defaultKusaType_idx], kf[lastUseTime_idx]))
            migrated_count += 1

    cursor.execute("DROP TABLE kusafield")
    cursor.execute("ALTER TABLE kusafield_new RENAME TO kusafield")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 kusafield 表")

    # ============================================================
    # 步骤4: 迁移 kusahistory 表
    # ============================================================
    print("\n【步骤4: 迁移 kusahistory 表】")

    cursor.execute("SELECT id, qq, kusaType, kusaResult, advKusaResult, createTimeTs FROM kusahistory")
    kusahistories = cursor.fetchall()
    print(f"  找到 {len(kusahistories)} 条 kusahistory 记录")

    cursor.execute("""
        CREATE TABLE kusahistory_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            kusaType TEXT DEFAULT '',
            kusaResult INTEGER DEFAULT 0,
            advKusaResult INTEGER DEFAULT 0,
            createTimeTs INTEGER NOT NULL,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
        )
    """)

    migrated_count = 0
    for kh in kusahistories:
        qq = kh[1]
        userId = qq_to_userId.get(qq)
        if userId:
            cursor.execute("""
                INSERT INTO kusahistory_new (userId, kusaType, kusaResult, advKusaResult, createTimeTs)
                VALUES (?, ?, ?, ?, ?)
            """, (userId, kh[2], kh[3], kh[4], kh[5]))
            migrated_count += 1

    cursor.execute("DROP TABLE kusahistory")
    cursor.execute("ALTER TABLE kusahistory_new RENAME TO kusahistory")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 kusahistory 表")

    # ============================================================
    # 步骤5: 迁移 drawitemstorage 表
    # ============================================================
    print("\n【步骤5: 迁移 drawitemstorage 表】")

    cursor.execute("SELECT id, qq, amount, item_id FROM drawitemstorage")
    drawitemstorages = cursor.fetchall()
    print(f"  找到 {len(drawitemstorages)} 条 drawitemstorage 记录")

    cursor.execute("""
        CREATE TABLE drawitemstorage_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            item_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES drawitemlist(id) ON DELETE CASCADE
        )
    """)

    migrated_count = 0
    for dis in drawitemstorages:
        qq = dis[1]
        userId = qq_to_userId.get(qq)
        if userId:
            cursor.execute("""
                INSERT INTO drawitemstorage_new (userId, item_id, amount)
                VALUES (?, ?, ?)
            """, (userId, dis[3], dis[2]))
            migrated_count += 1

    cursor.execute("DROP TABLE drawitemstorage")
    cursor.execute("ALTER TABLE drawitemstorage_new RENAME TO drawitemstorage")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 drawitemstorage 表")

    # ============================================================
    # 步骤6: 迁移 kusaitemstorage 表
    # ============================================================
    print("\n【步骤6: 迁移 kusaitemstorage 表】")

    cursor.execute("SELECT id, qq, amount, allowUse, item_id, timeLimitTs FROM kusaitemstorage")
    kusaitemstorages = cursor.fetchall()
    print(f"  找到 {len(kusaitemstorages)} 条 kusaitemstorage 记录")

    cursor.execute("""
        CREATE TABLE kusaitemstorage_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            item_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            allowUse INTEGER DEFAULT 1,
            timeLimitTs INTEGER,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES kusaitemlist(name) ON DELETE CASCADE
        )
    """)

    migrated_count = 0
    for kis in kusaitemstorages:
        qq = kis[1]
        userId = qq_to_userId.get(qq)
        if userId:
            cursor.execute("""
                INSERT INTO kusaitemstorage_new (userId, item_id, amount, allowUse, timeLimitTs)
                VALUES (?, ?, ?, ?, ?)
            """, (userId, kis[4], kis[2], kis[3], kis[5]))
            migrated_count += 1

    cursor.execute("DROP TABLE kusaitemstorage")
    cursor.execute("ALTER TABLE kusaitemstorage_new RENAME TO kusaitemstorage")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 kusaitemstorage 表")

    # ============================================================
    # 步骤7: 迁移 chatuser 表
    # ============================================================
    print("\n【步骤7: 迁移 chatuser 表】")

    cursor.execute("SELECT qq, allowPrivate, allowRole, allowAdvancedModel, dailyTokenLimit, chosenModel, tokenUse, todayTokenUse, chosenRoleId, createTime FROM chatuser")
    chatusers = cursor.fetchall()
    print(f"  找到 {len(chatusers)} 条 chatuser 记录")

    cursor.execute("""
        CREATE TABLE chatuser_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            allowPrivate INTEGER DEFAULT 0,
            allowRole INTEGER DEFAULT 0,
            allowAdvancedModel INTEGER DEFAULT 0,
            chosenModel TEXT DEFAULT 'deepseek-chat',
            tokenUse INTEGER DEFAULT 0,
            todayTokenUse INTEGER DEFAULT 0,
            dailyTokenLimit INTEGER DEFAULT 10000,
            chosenRoleId INTEGER DEFAULT 1,
            createTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
        )
    """)

    migrated_count = 0
    for cu in chatusers:
        qq = cu[0]
        userId = qq_to_userId.get(qq)
        if userId:
            cursor.execute("""
                INSERT INTO chatuser_new (userId, allowPrivate, allowRole, allowAdvancedModel, chosenModel, tokenUse, todayTokenUse, dailyTokenLimit, chosenRoleId, createTime)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (userId, cu[1], cu[2], cu[3], cu[5], cu[6], cu[7], int(cu[4]) if cu[4] else 10000, cu[8] if cu[8] else 1, cu[9]))
            migrated_count += 1

    cursor.execute("DROP TABLE chatuser")
    cursor.execute("ALTER TABLE chatuser_new RENAME TO chatuser")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 chatuser 表")

    # ============================================================
    # 步骤8: 迁移 chatrole 表
    # ============================================================
    print("\n【步骤8: 迁移 chatrole 表】")

    cursor.execute("SELECT id, name, detail, isPublic, creator, createTime FROM chatrole")
    chatroles = cursor.fetchall()
    print(f"  找到 {len(chatroles)} 条 chatrole 记录")

    cursor.execute("""
        CREATE TABLE chatrole_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            detail TEXT,
            isPublic INTEGER DEFAULT 0,
            userId INTEGER,
            createTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
        )
    """)

    migrated_count = 0
    for cr in chatroles:
        creator_qq = cr[4]
        userId = qq_to_userId.get(creator_qq)
        cursor.execute("""
            INSERT INTO chatrole_new (id, name, detail, isPublic, userId, createTime)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cr[0], cr[1], cr[2], cr[3], userId, cr[5]))
        migrated_count += 1

    cursor.execute("DROP TABLE chatrole")
    cursor.execute("ALTER TABLE chatrole_new RENAME TO chatrole")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 chatrole 表")

    # ============================================================
    # 步骤9: 迁移 donaterecord 表
    # ============================================================
    print("\n【步骤9: 迁移 donaterecord 表】")

    cursor.execute("SELECT id, qq, amount, donateDate, source, remark FROM donaterecord")
    donaterecords = cursor.fetchall()
    print(f"  找到 {len(donaterecords)} 条 donaterecord 记录")

    cursor.execute("""
        CREATE TABLE donaterecord_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER,
            amount REAL NOT NULL,
            donateDate TEXT NOT NULL,
            source TEXT NOT NULL,
            remark TEXT,
            FOREIGN KEY (userId) REFERENCES unifieduser(id) ON DELETE CASCADE
        )
    """)

    migrated_count = 0
    for dr in donaterecords:
        qq = dr[1]
        userId = qq_to_userId.get(qq)
        if userId:
            cursor.execute("""
                INSERT INTO donaterecord_new (id, userId, amount, donateDate, source, remark)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dr[0], userId, dr[2], dr[3], dr[4], dr[5]))
            migrated_count += 1

    cursor.execute("DROP TABLE donaterecord")
    cursor.execute("ALTER TABLE donaterecord_new RENAME TO donaterecord")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 donaterecord 表")

    # ============================================================
    # 步骤10: 迁移 traderecord 表
    # ============================================================
    print("\n【步骤10: 迁移 traderecord 表】")

    cursor.execute("SELECT operator, tradeType, gainItemAmount, gainItemName, costItemAmount, costItemName, detail, timestamp FROM traderecord")
    traderecords = cursor.fetchall()
    print(f"  找到 {len(traderecords)} 条 traderecord 记录")

    cursor.execute("""
        CREATE TABLE traderecord_new (
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
        )
    """)

    migrated_count = 0
    for tr in traderecords:
        operator_qq = tr[0]
        userId = qq_to_userId.get(operator_qq)
        if userId:
            cursor.execute("""
                INSERT INTO traderecord_new (userId, tradeType, gainItemAmount, gainItemName, costItemAmount, costItemName, detail, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (userId, tr[1], tr[2], tr[3], tr[4], tr[5], tr[6], tr[7]))
            migrated_count += 1

    cursor.execute("DROP TABLE traderecord")
    cursor.execute("ALTER TABLE traderecord_new RENAME TO traderecord")
    print(f"  ✅ 已迁移 {migrated_count} 条记录到 traderecord 表")

    # ============================================================
    # 步骤11: 迁移 drawitemlist 表
    # ============================================================
    print("\n【步骤11: 迁移 drawitemlist 表】")

    cursor.execute("SELECT id, name, pool, rareRank, detail, author FROM drawitemlist")
    drawitemlists = cursor.fetchall()
    print(f"  找到 {len(drawitemlists)} 条 drawitemlist 记录")

    cursor.execute("""
        CREATE TABLE drawitemlist_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(64),
            pool TEXT DEFAULT '默认',
            rareRank INTEGER,
            detail VARCHAR(1024),
            authorId INTEGER
        )
    """)

    for dil in drawitemlists:
        author_qq = dil[5]
        authorId = qq_to_userId.get(author_qq) if author_qq else None
        cursor.execute("""
            INSERT INTO drawitemlist_new (id, name, pool, rareRank, detail, authorId)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (dil[0], dil[1], dil[2], dil[3], dil[4], authorId))

    cursor.execute("DROP TABLE drawitemlist")
    cursor.execute("ALTER TABLE drawitemlist_new RENAME TO drawitemlist")
    print(f"  ✅ 已迁移 {len(drawitemlists)} 条记录到 drawitemlist 表")

    # ============================================================
    # 步骤12: 迁移 workorder 表
    # ============================================================
    print("\n【步骤12: 迁移 workorder 表】")

    cursor.execute("SELECT id, title, author, detail, reply FROM workorder")
    workorders = cursor.fetchall()
    print(f"  找到 {len(workorders)} 条 workorder 记录")

    cursor.execute("""
        CREATE TABLE workorder_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(128) NOT NULL,
            authorId INTEGER,
            detail VARCHAR(1024),
            reply VARCHAR(512)
        )
    """)

    for wo in workorders:
        author_qq = wo[2]
        authorId = qq_to_userId.get(author_qq) if author_qq else None
        cursor.execute("""
            INSERT INTO workorder_new (id, title, authorId, detail, reply)
            VALUES (?, ?, ?, ?, ?)
        """, (wo[0], wo[1], authorId, wo[3], wo[4]))

    cursor.execute("DROP TABLE workorder")
    cursor.execute("ALTER TABLE workorder_new RENAME TO workorder")
    print(f"  ✅ 已迁移 {len(workorders)} 条记录到 workorder 表")

    # ============================================================
    # 步骤13: 迁移 flag 表
    # ============================================================
    print("\n【步骤13: 迁移 flag 表】")

    cursor.execute("SELECT id, name, value, forAll, ownerId FROM flag")
    flags = cursor.fetchall()
    print(f"  找到 {len(flags)} 条 flag 记录")

    cursor.execute("""
        CREATE TABLE flag_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            value INTEGER DEFAULT 0,
            forAll INTEGER DEFAULT 1,
            ownerId INTEGER
        )
    """)

    for f in flags:
        owner_qq = f[4]
        ownerId = qq_to_userId.get(owner_qq) if owner_qq else None
        cursor.execute("""
            INSERT INTO flag_new (id, name, value, forAll, ownerId)
            VALUES (?, ?, ?, ?, ?)
        """, (f[0], f[1], f[2], f[3], ownerId))

    cursor.execute("DROP TABLE flag")
    cursor.execute("ALTER TABLE flag_new RENAME TO flag")
    print(f"  ✅ 已迁移 {len(flags)} 条记录到 flag 表")

    # ============================================================
    # 步骤14: 迁移 gvalue 表（原样复制）
    # ============================================================
    print("\n【步骤14: 迁移 gvalue 表】")

    cursor.execute("SELECT COUNT(*) FROM gvalue")
    gvalue_count = cursor.fetchone()[0]
    print(f"  gvalue 表有 {gvalue_count} 条记录，结构无变化，保持原样")
    print(f"  ✅ gvalue 表无需迁移")

    # ============================================================
    # 步骤15: 迁移 kusaitemlist 表（原样复制）
    # ============================================================
    print("\n【步骤15: 迁移 kusaitemlist 表】")

    cursor.execute("SELECT COUNT(*) FROM kusaitemlist")
    kusaitem_count = cursor.fetchone()[0]
    print(f"  kusaitemlist 表有 {kusaitem_count} 条记录，结构无变化，保持原样")
    print(f"  ✅ kusaitemlist 表无需迁移")

    # ============================================================
    # 步骤16: 更新 sqlite_sequence
    # ============================================================
    print("\n【步骤16: 更新 sqlite_sequence】")

    cursor.execute("DELETE FROM sqlite_sequence")

    tables_to_update = ['unifieduser', 'kusabase', 'kusafield', 'kusahistory', 'drawitemstorage',
                        'kusaitemstorage', 'chatuser', 'chatrole', 'donaterecord', 'traderecord',
                        'drawitemlist', 'workorder', 'flag', 'gvalue']

    for table in tables_to_update:
        try:
            cursor.execute(f"SELECT MAX(id) FROM {table}")
            max_id = cursor.fetchone()[0]
            if max_id:
                cursor.execute("INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)", (table, max_id))
        except Exception:
            pass

    print("  ✅ 已更新 sqlite_sequence")

    # ============================================================
    # 提交更改
    # ============================================================
    conn.commit()

    # ============================================================
    # 验证迁移结果
    # ============================================================
    print("\n" + "=" * 60)
    print("验证迁移结果...")
    print("=" * 60)

    verification_tables = [
        ('unifieduser', 'id, realQQ, isSuperAdmin, isRobot'),
        ('kusabase', 'id, userId, name, kusa'),
        ('kusafield', 'id, userId, kusaType'),
        ('kusahistory', 'id, userId, kusaType'),
        ('drawitemstorage', 'id, userId, item_id'),
        ('kusaitemstorage', 'id, userId, item_id'),
        ('chatuser', 'id, userId, chosenModel'),
        ('chatrole', 'id, name, userId'),
        ('donaterecord', 'id, userId, amount'),
        ('traderecord', 'id, userId, tradeType'),
        ('drawitemlist', 'id, name, authorId'),
        ('workorder', 'id, title, authorId'),
        ('flag', 'id, name, ownerId'),
        ('gvalue', 'id, cycle, turn'),
        ('kusaitemlist', 'name, type, detail'),
    ]

    for table, cols in verification_tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            cursor.execute(f"SELECT {cols} FROM {table} LIMIT 3")
            samples = cursor.fetchall()
            print(f"\n  {table}: {count} 条记录")
            for sample in samples:
                print(f"    {sample}")
        except Exception as e:
            print(f"\n  {table}: ❌ 查询失败 - {e}")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ 数据库迁移完成！")
    print(f"目标数据库: {target_db_path}")
    print("=" * 60)

    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python migrate_production.py <源数据库路径> <目标数据库路径>")
        print("示例: python migrate_production.py scripts/chuchu.sqlite database/chuchu_migrated.sqlite")
        sys.exit(1)

    source_db = sys.argv[1]
    target_db = sys.argv[2]

    migrate_database(source_db, target_db)
