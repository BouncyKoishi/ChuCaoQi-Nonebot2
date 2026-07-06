from tortoise import Tortoise

# 全局数据库初始化标志
_db_initialized = False

async def init_db():
    """初始化数据库（幂等操作）"""
    global _db_initialized
    if _db_initialized:
        return

    from . import models
    await Tortoise.init(
        db_url="sqlite://database/chuchu.sqlite?journal_mode=WAL&timeout=10",
        modules={"models": ["core.db.models"]},
        use_tz=True,
        timezone="Asia/Shanghai"
    )
    await Tortoise.generate_schemas()
    _db_initialized = True
    print("--- DB Init ---")
