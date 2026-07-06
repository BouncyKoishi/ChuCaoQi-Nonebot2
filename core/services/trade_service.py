"""
交易服务模块
从 kusa_base.py 提取的纯业务逻辑（buying/selling/item_charging）
不依赖任何 bot 基础设施，仅依赖 core.db 和 core.config
"""

from core.config import plugin_config


async def buying(
    userId: int,
    item_name_buying: str,
    item_amount_buying: int,
    total_price: int,
    trade_type: str,
    is_using_adv_kusa: bool = False,
    detail: str = None,
) -> bool:
    import core.db.kusa_system as base_db
    import core.db.kusa_item as item_db

    user = await base_db.getKusaUser(userId)
    item = await item_db.getItem(item_name_buying)

    if item_amount_buying < 0:
        return False
    if user is None or item is None:
        return False

    if is_using_adv_kusa:
        if not await base_db.deductKusa(userId, total_price, type='advKusa'):
            return False
    else:
        if not await base_db.deductKusa(userId, total_price):
            return False

    await item_db.changeItemAmount(userId, item_name_buying, item_amount_buying)

    bot_qq = plugin_config.get('qq', {}).get('bot', 0)

    if is_using_adv_kusa:
        await base_db.changeAdvKusa(bot_qq, total_price)
    else:
        await base_db.changeKusa(bot_qq, total_price)

    cost_item_name = '草之精华' if is_using_adv_kusa else '草'
    await base_db.setTradeRecord(
        userId=userId,
        tradeType=trade_type,
        detail=detail,
        gainItemName=item_name_buying,
        gainItemAmount=item_amount_buying,
        costItemName=cost_item_name,
        costItemAmount=total_price
    )
    return True


async def selling(
    userId: int,
    item_name_selling: str,
    item_amount_selling: int,
    total_price: int,
    trade_type: str,
    is_using_adv_kusa: bool = False
) -> bool:
    import core.db.kusa_system as base_db
    import core.db.kusa_item as item_db

    user = await base_db.getKusaUser(userId)
    item = await item_db.getItem(item_name_selling)
    item_amount = await item_db.getItemAmount(userId, item_name_selling)

    if item_amount_selling < 0:
        return False
    if user is None or item is None:
        return False
    if item_amount < item_amount_selling:
        return False

    await item_db.changeItemAmount(userId, item_name_selling, -item_amount_selling)

    bot_qq = plugin_config.get('qq', {}).get('bot', 0)

    if is_using_adv_kusa:
        await base_db.changeAdvKusa(userId, total_price)
        await base_db.changeAdvKusa(bot_qq, -total_price)
    else:
        await base_db.changeKusa(userId, total_price)
        await base_db.changeKusa(bot_qq, -total_price)

    gain_item_name = '草之精华' if is_using_adv_kusa else '草'
    await base_db.setTradeRecord(
        userId=userId,
        tradeType=trade_type,
        gainItemName=gain_item_name,
        gainItemAmount=total_price,
        costItemName=item_name_selling,
        costItemAmount=item_amount_selling
    )
    return True


async def item_charging(
    userId: int,
    item_name_gain: str,
    item_amount_gain: int,
    item_name_cost: str,
    item_amount_cost: int,
    trade_type: str,
    detail: str = None
) -> bool:
    import core.db.kusa_system as base_db
    import core.db.kusa_item as item_db

    user = await base_db.getKusaUser(userId)
    item_gain = await item_db.getItem(item_name_gain)
    item_cost = await item_db.getItem(item_name_cost)

    if item_amount_gain < 0 or item_amount_cost < 0:
        return False
    if user is None or item_gain is None or item_cost is None:
        return False

    item_cost_now_amount = await item_db.getItemAmount(userId, item_name_cost)
    if item_cost_now_amount < item_amount_cost:
        return False

    await item_db.changeItemAmount(userId, item_name_gain, item_amount_gain)
    await item_db.changeItemAmount(userId, item_name_cost, -item_amount_cost)
    await base_db.setTradeRecord(
        userId=userId,
        tradeType=trade_type,
        detail=detail,
        gainItemName=item_name_gain,
        gainItemAmount=item_amount_gain,
        costItemName=item_name_cost,
        costItemAmount=item_amount_cost
    )
    return True
