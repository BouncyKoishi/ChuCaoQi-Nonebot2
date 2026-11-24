"""
身份服务模块
提供统一用户管理功能
"""

from typing import Optional
from tortoise.transactions import in_transaction
from tortoise.expressions import Q
from core.db.models import UnifiedUser, KusaBase, KusaField, IdentityBindRequest
from core.db import user as user_db
import hashlib
import secrets
import string
import datetime


def get_now():
    return datetime.datetime.now().astimezone()


def generate_friend_code(real_qq: str) -> str:
    """生成好友码（跨进程确定性，使用 md5 替代内置 hash 避免随机化）

    种子包含当前日期，使好友码每日更新，防止一次拿到就永久跨帐号使用。
    bot 端验证和 web 端展示用相同的日期种子，确保同一天内一致。
    """
    today = datetime.datetime.now().strftime('%Y%m%d')
    hashing_str = real_qq + 'confounding' + today
    hash_val = int(hashlib.md5(hashing_str.encode()).hexdigest(), 16)
    return f'{hash_val % 100000000:0>8}'


async def get_unified_user_by_platform(platform: str, platform_id: str) -> Optional[UnifiedUser]:
    return await user_db.getUnifiedUserByPlatform(platform, platform_id)


async def get_unified_user_by_real_qq(realQQ: str) -> Optional[UnifiedUser]:
    return await user_db.getUnifiedUserByRealQQ(realQQ)


async def get_unified_user_by_id(userId: int) -> Optional[UnifiedUser]:
    return await user_db.getUnifiedUser(userId)


async def create_unified_user_for_onebot(realQQ: str) -> UnifiedUser:
    unified_user, created = await UnifiedUser.get_or_create(realQQ=realQQ)
    
    existing_kusa_base = await KusaBase.filter(user_id=unified_user.id).first()
    if not existing_kusa_base:
        await KusaBase.create(user=unified_user, kusa=10000, lastUseTime=get_now())
        await KusaField.create(user=unified_user)
        from core.db.kusa_item import changeItemAmount
        await changeItemAmount(unified_user.id, "草地", 1)
    
    return unified_user


async def create_unified_user_for_qqbot(openid: str) -> UnifiedUser:
    """创建官机临时账号

    未完成身份绑定前不发放任何资源：禁止清单中的插件已被插件级门禁拦截，
    绑定成功后再按绑定类型发放（新建绑定 10000 草 + 1 草地）。
    """
    unified_user, created = await UnifiedUser.get_or_create(qqbotOpenid=openid)
    return unified_user


async def get_or_create_unified_user(platform: str, platform_id: str) -> UnifiedUser:
    unified_user = await get_unified_user_by_platform(platform, platform_id)
    if not unified_user:
        if platform == "onebot":
            unified_user = await create_unified_user_for_onebot(platform_id)
        elif platform == "qqbot":
            unified_user = await create_unified_user_for_qqbot(platform_id)
    return unified_user


async def get_real_qq(unified_user: UnifiedUser) -> Optional[str]:
    return unified_user.realQQ


async def get_user_id_by_event(event) -> Optional[int]:
    return None


async def bind_platform_identity(
    unified_user: UnifiedUser,
    platform: str,
    platform_id: str
) -> bool:
    return await user_db.bindPlatformIdentity(unified_user, platform, platform_id)


async def generate_web_token(unified_user: UnifiedUser) -> str:
    alphabet = string.ascii_letters + string.digits
    token = 'kusa_' + ''.join(secrets.choice(alphabet) for _ in range(32))
    
    await user_db.updateUnifiedUserWebToken(unified_user, token)
    
    return token


async def verify_web_token(token: str) -> Optional[UnifiedUser]:
    if not token:
        return None
    
    unified_user = await user_db.getUnifiedUserByWebToken(token)
    if not unified_user or not unified_user.webToken:
        return None
    
    return unified_user


async def reset_web_token(unified_user: UnifiedUser) -> str:
    await user_db.updateUnifiedUserWebToken(unified_user, None)
    
    return await generate_web_token(unified_user)


async def delete_user_data(userId: int):
    from core.db.models import (
        KusaBase, KusaField, KusaHistory, DrawItemStorage,
        KusaItemStorage, ChatUser, ChatRole, DonateRecord, TradeRecord,
        Flag, PageView
    )
    
    await KusaBase.filter(user_id=userId).delete()
    await KusaField.filter(user_id=userId).delete()
    await KusaHistory.filter(user_id=userId).delete()
    await DrawItemStorage.filter(user_id=userId).delete()
    await KusaItemStorage.filter(user_id=userId).delete()
    await ChatUser.filter(user_id=userId).delete()
    await ChatRole.filter(user_id=userId).delete()
    await DonateRecord.filter(user_id=userId).delete()
    await TradeRecord.filter(user_id=userId).delete()
    await Flag.filter(ownerId=userId).delete()
    await PageView.filter(userId=userId).delete()


async def _migrate_source_ownership(source_id: int, target_id: int):
    """合并前处理归属数据

    - 转让记录保留，双方显式置 NULL，避免 target 账实不符
    - 工单 / 自制物品的作者改挂 target
    - 个人配置与访问记录随临时账号删除
    """
    from core.db.models import TransferRecord, WorkOrder, DrawItemList, Flag, PageView

    await TransferRecord.filter(fromUser_id=source_id).update(fromUser_id=None)
    await TransferRecord.filter(toUser_id=source_id).update(toUser_id=None)
    await WorkOrder.filter(authorId=source_id).update(authorId=target_id)
    await DrawItemList.filter(authorId=source_id).update(authorId=target_id)
    await Flag.filter(ownerId=source_id).delete()
    await PageView.filter(userId=source_id).delete()


# ===== 群映射 =====

_group_openid_to_onebot: dict = {}
_group_onebot_to_openid: dict = {}
_group_mapping_loaded = False


async def load_group_mappings(force: bool = False):
    """加载群映射到进程内缓存（启动时调用；映射变更后 force=True 刷新）"""
    global _group_mapping_loaded
    if _group_mapping_loaded and not force:
        return
    mappings = await user_db.getAllGroupMappings()
    openid_to_onebot = {}
    onebot_to_openid = {}
    for mapping in mappings:
        if mapping.qqbotGroupOpenid and mapping.onebotGroupId:
            openid_to_onebot[mapping.qqbotGroupOpenid] = mapping.onebotGroupId
            onebot_to_openid[mapping.onebotGroupId] = mapping.qqbotGroupOpenid
    _group_openid_to_onebot.clear()
    _group_openid_to_onebot.update(openid_to_onebot)
    _group_onebot_to_openid.clear()
    _group_onebot_to_openid.update(onebot_to_openid)
    _group_mapping_loaded = True
    print(f'--- 群映射缓存加载：{len(openid_to_onebot)} 条 ---')


def resolve_group_key(platform: str, group_id) -> Optional[str]:
    """把平台群标识解析成统一群标识

    OneBot 的群标识本来就是 QQ 群号；官方 Bot 用映射表换成 QQ 群号，
    未建立映射时回退 group_openid。
    """
    if group_id is None:
        return None
    group_id = str(group_id)
    if platform == 'qqbot':
        return _group_openid_to_onebot.get(group_id, group_id)
    return group_id


def get_onebot_group_id_by_openid(openid: str) -> Optional[str]:
    return _group_openid_to_onebot.get(str(openid))


def get_openid_by_onebot_group_id(onebot_group_id: str) -> Optional[str]:
    return _group_onebot_to_openid.get(str(onebot_group_id))


async def get_group_mapping_by_openid(openid: str):
    return await user_db.getGroupMappingByQqbotGroupOpenid(openid)


async def get_group_mapping_by_onebot_id(onebot_group_id: str):
    return await user_db.getGroupMappingByOnebotGroupId(onebot_group_id)


async def bind_group_mapping(openid: str, onebot_group_id: str):
    """建立或覆盖官方群 openid 到 QQ 群号的映射，并刷新缓存"""
    mapping = await user_db.upsertGroupMapping(onebot_group_id, openid)
    await load_group_mappings(force=True)
    return mapping


async def _merge_users_core(
    source_id: int,
    target_id: int,
    keep_source_data: bool = False
) -> bool:
    """合并的数据库部分（不含事务与图库重命名）

    目标账号保留，源账号的身份字段与归属数据迁移后删除。
    """
    source_user = await get_unified_user_by_id(source_id)
    target_user = await get_unified_user_by_id(target_id)

    if not source_user or not target_user or source_user.id == target_user.id:
        return False

    source_openid = source_user.qqbotOpenid
    source_qq = source_user.realQQ

    # 先释放源账号的唯一身份值，避免与目标账号写入时唯一约束冲突
    source_user.realQQ = None
    source_user.qqbotOpenid = None
    await user_db.saveUnifiedUser(source_user)

    if source_qq and not target_user.realQQ:
        target_user.realQQ = source_qq
    if source_openid and not target_user.qqbotOpenid:
        target_user.qqbotOpenid = source_openid
    await user_db.saveUnifiedUser(target_user)

    await _migrate_source_ownership(source_id, target_id)

    # 清掉源账号遗留的待处理绑定信息，避免合并后 pending 挡住目标账号的新绑定
    stale_requests = await IdentityBindRequest.filter(
        Q(status='pending') & (
            Q(sourceUserId=source_id) | Q(qqbotOpenid=source_openid or '')
        )
    ).all()
    for request in stale_requests:
        await user_db.updateIdentityBindRequest(request, 'rejected', note='发起账号已合并')

    if not keep_source_data:
        await delete_user_data(source_id)
    await user_db.deleteUnifiedUser(source_user)
    return True


async def merge_users(
    source_id: int,
    target_id: int,
    keep_source_data: bool = False
) -> bool:
    """把临时官机账号合并进目标老账号

    数据库变更在单个事务内完成。未绑定官机账号不允许上传图库，
    合并时不涉及图库文件迁移。
    """
    async with in_transaction():
        return await _merge_users_core(source_id, target_id, keep_source_data)


# ===== 身份绑定 =====

BIND_TYPE_LABELS = {
    'new': '新建',
    'merge': '合并',
    'rebind': '换绑',
}


async def determine_bind_type(unified_user: UnifiedUser, target_qq: str):
    """判定绑定类型

    Returns:
        (bind_type, target_user, error)
    """
    target_qq = str(target_qq).strip()
    if unified_user.realQQ:
        if str(unified_user.realQQ) == target_qq:
            return None, None, '当前账号已绑定该 QQ'
        target_user = await get_unified_user_by_real_qq(target_qq)
        if target_user and target_user.id != unified_user.id:
            return None, target_user, '该 QQ 已被其他账号使用，请联系管理员处理'
        return 'rebind', None, None

    target_user = await get_unified_user_by_real_qq(target_qq)
    if target_user and target_user.id != unified_user.id:
        # 目标账号已有其它官方身份时无法合并，提前拒绝，避免发出注定被驳回的卡片
        if target_user.qqbotOpenid and target_user.qqbotOpenid != unified_user.qqbotOpenid:
            return None, target_user, '该 QQ 已绑定其他官方身份，请联系管理员处理'
        return 'merge', target_user, None
    return 'new', None, None


async def has_pending_bind_request(openid: Optional[str]) -> bool:
    """该 openid 是否已有待审批的绑定申请

    门禁提示据此静默：申请提交后用户再次触发受限指令时不再反复提示。
    """
    if not openid:
        return False
    return await user_db.getPendingBindRequestByOpenid(str(openid)) is not None


async def prepare_bind_request(unified_user: UnifiedUser, target_qq: str):
    """创建绑定信息（同一 openid 只保留一条 pending）

    Returns:
        (request, error)
    """
    if not unified_user.qqbotOpenid:
        return None, '当前账号缺少官方身份，无法发起绑定'

    existing = await user_db.getPendingBindRequestByOpenid(unified_user.qqbotOpenid)
    if existing:
        return None, f'你已有一条待确认的绑定信息（#{existing.id}），请等待处理'

    bind_type, _target_user, error = await determine_bind_type(unified_user, target_qq)
    if error:
        return None, error

    request = await user_db.createIdentityBindRequest(
        qqbotOpenid=unified_user.qqbotOpenid,
        sourceUserId=unified_user.id,
        targetQQ=str(target_qq),
        bindType=bind_type,
    )
    return request, None


async def _apply_bind_request(request) -> dict:
    """按审核信息执行绑定，执行前重新校验身份状态"""
    source = await user_db.getUnifiedUserByQQBotOpenid(request.qqbotOpenid)
    if not source:
        return {'success': False, 'error': '发起绑定的账号不存在'}
    if request.sourceUserId is not None and source.id != request.sourceUserId:
        return {'success': False, 'error': '发起绑定的账号已变更，请重新发起'}

    target_qq = str(request.targetQQ)
    target_user = await get_unified_user_by_real_qq(target_qq)
    bind_type = request.bindType

    if bind_type == 'new':
        if source.realQQ:
            return {'success': False, 'error': '当前账号已绑定 QQ，绑定信息已失效'}
        if target_user and target_user.id != source.id:
            return {'success': False, 'error': '目标 QQ 已被其他账号使用'}
        source.realQQ = target_qq
        await user_db.saveUnifiedUser(source)
        from core.db import kusa_system
        await kusa_system.createKusaUser(source.id)
        return {'success': True, 'userId': source.id, 'bindType': bind_type}

    if bind_type == 'merge':
        if source.realQQ:
            return {'success': False, 'error': '当前账号已绑定 QQ，绑定信息已失效'}
        if not target_user or target_user.id == source.id:
            return {'success': False, 'error': '目标 QQ 账号不存在'}
        if target_user.qqbotOpenid and target_user.qqbotOpenid != source.qqbotOpenid:
            return {'success': False, 'error': '目标账号已绑定其他官方身份，请联系管理员处理'}
        ok = await merge_users(source.id, target_user.id)
        if not ok:
            return {'success': False, 'error': '合并失败，请稍后重试'}
        return {
            'success': True,
            'userId': target_user.id,
            'bindType': bind_type,
        }

    if bind_type == 'rebind':
        if not source.realQQ:
            return {'success': False, 'error': '当前账号尚未绑定 QQ'}
        if str(source.realQQ) == target_qq:
            return {'success': True, 'userId': source.id, 'bindType': bind_type}
        if target_user and target_user.id != source.id:
            return {'success': False, 'error': '目标 QQ 已被其他账号使用'}
        source.realQQ = target_qq
        await user_db.saveUnifiedUser(source)
        return {'success': True, 'userId': source.id, 'bindType': bind_type}

    return {'success': False, 'error': '未知的绑定类型'}


async def approve_bind_request(request_id: int, approve: bool) -> dict:
    """确认 / 取消绑定信息

    确认时以当时数据重新校验；成功后驳回同一目标 QQ 的其它 pending。
    """
    request = await user_db.getIdentityBindRequest(request_id)
    if not request:
        return {'success': False, 'error': '绑定信息不存在'}
    if request.status != 'pending':
        return {'success': False, 'error': '该绑定信息已处理'}

    if not approve:
        await user_db.updateIdentityBindRequest(request, 'rejected')
        return {'success': True, 'status': 'rejected', 'requestId': request.id}

    async with in_transaction():
        result = await _apply_bind_request(request)
        if result.get('success'):
            await user_db.updateIdentityBindRequest(request, 'approved')
            others = await user_db.getPendingBindRequestsByTargetQQ(request.targetQQ)
            for other in others:
                if other.id != request.id:
                    await user_db.updateIdentityBindRequest(
                        other, 'rejected', note='目标 QQ 已被其他绑定信息使用'
                    )
        else:
            await user_db.updateIdentityBindRequest(
                request, 'rejected', note=result.get('error')
            )

    result['requestId'] = request.id
    return result
