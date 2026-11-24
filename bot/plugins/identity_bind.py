"""
身份绑定插件

- !绑定 <QQ号>：官方 Bot 端在群聊发起身份绑定，生成绑定信息由超管确认
- !openid：查询当前官方身份（群聊脱敏、私聊完整）
- !我的身份 / token / 群映射：保留原有能力
"""

import re
from datetime import datetime
from typing import Optional

from nonebot import logger, on_message, on_notice
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.rule import Rule

from reloader import db_command as on_command
from platform_context import (
    Ctx,
    get_context,
    get_platform_type,
    get_platform_user_id,
)
from multi_platform import send_finish
from kusa_base import is_super_admin, plugin_config
from core.db.user import getIdentityBindRequest, updateIdentityBindRequest
from core.services.identity_service import (
    BIND_TYPE_LABELS,
    approve_bind_request,
    bind_group_mapping,
    generate_web_token,
    get_group_mapping_by_onebot_id,
    get_group_mapping_by_openid,
    get_unified_user_by_id,
    get_unified_user_by_platform,
    get_unified_user_by_real_qq,
    prepare_bind_request,
)


def _mask_openid(openid: str) -> str:
    if len(openid) <= 8:
        return openid[:2] + '****' + openid[-2:]
    return openid[:4] + '****' + openid[-4:]


async def _superadmin_openids():
    from core.db.models import UnifiedUser
    admins = await UnifiedUser.filter(isSuperAdmin=True).all()
    return [admin.qqbotOpenid for admin in admins if admin.qqbotOpenid]


def _bind_keyboard(request_id: int, admin_openids) -> dict:
    """绑定卡的 inline keyboard：确认/取消，仅指定超管可点击"""
    permission = {'type': 0, 'specify_user_ids': list(admin_openids)}

    def button(btn_id: str, label: str, visited: str, style: int, action: str) -> dict:
        return {
            'id': btn_id,
            'render_data': {'label': label, 'visited_label': visited, 'style': style},
            'action': {
                'type': 1,
                'permission': permission,
                'data': f'bind:{action}:{request_id}',
                'unsupport_tips': '请升级 QQ 客户端后重试',
            },
        }

    return {
        'content': {
            'rows': [
                {'buttons': [
                    button('approve', '确认绑定', '已确认', 1, 'approve'),
                    button('reject', '取消绑定', '已取消', 0, 'reject'),
                ]},
            ]
        }
    }


async def _reject_unsent_request(request, note: str):
    """卡片没发出去时把绑定信息置为 rejected，避免 pending 永久占位"""
    try:
        await updateIdentityBindRequest(request, 'rejected', note=note)
    except Exception as exc:
        logger.warning(f'绑定信息标记失败 #{request.id}：{exc}')


async def _notify_card_failed(ctx: Ctx, event):
    try:
        await ctx.bot.send(event, '绑定信息卡发送失败，请稍后重试')
    except Exception as send_exc:
        logger.warning(f'绑定卡失败提示发送失败：{send_exc}')


async def _finish_bind_card(markdown: str, ctx: Ctx, request, admin_openids):
    """发送绑定信息卡（Markdown + 按钮，不做纯文本兜底），并记录消息ID"""
    from nonebot.adapters.qq import MessageSegment as QQMessageSegment
    from nonebot.adapters.qq.models import MessageKeyboard

    event = ctx.event
    markdown_seg = QQMessageSegment.markdown(markdown).data['markdown']

    keyboard = MessageKeyboard(
        content=_bind_keyboard(request.id, admin_openids)['content']
    )

    # 不传 content（适配器会把整条消息序列化成 content，官机客户端会再渲染一遍）
    # 也不传 message_reference（实测 markdown + 引用会让客户端重复渲染卡片），
    # 发起人改用卡片内的 @ 定位；msg_id/msg_seq 保留，确保是被动消息
    event._reply_seq = getattr(event, '_reply_seq', 0) + 1
    try:
        resp = await ctx.bot.call_api(
            'post_group_messages',
            group_openid=event.group_openid,
            msg_type=2,
            markdown=markdown_seg,
            msg_id=event.id,
            msg_seq=event._reply_seq,
            keyboard=keyboard,
        )
    except Exception as exc:
        logger.warning(f'Markdown 绑定卡发送失败：{exc}')
        await _reject_unsent_request(request, f'绑定卡发送失败：{exc}')
        await _notify_card_failed(ctx, event)
        return

    # 群聊面包按钮的交互事件不带 message_id，只能发卡时自己存
    if isinstance(resp, dict):
        message_id = resp.get('id')
    else:
        message_id = getattr(resp, 'id', None)
    if not message_id:
        # 发送接口未抛异常但没有返回消息ID，卡片实际未落地
        logger.warning(f'绑定卡发送未返回消息ID：{resp!r}')
        await _reject_unsent_request(request, '绑定卡发送后未返回消息ID')
        await _notify_card_failed(ctx, event)
        return

    request.cardMessageId = str(message_id)
    try:
        await request.save(update_fields=['cardMessageId'])
    except Exception as exc:
        # 卡片已发出，只是 ID 没落库：审批仍可进行，但之后无法删除原卡
        logger.warning(f'绑定卡消息ID保存失败 #{request.id}：{exc}')


绑定_cmd = on_command('绑定', priority=5, block=True)


@绑定_cmd.handle()
async def handle_绑定(ctx: Ctx, args: Message = CommandArg()):
    if ctx.platform != 'qqbot':
        await send_finish(绑定_cmd, '当前为 NapCat 端，QQ 号即身份，无需绑定')
        return
    if not ctx.is_group:
        await send_finish(绑定_cmd, '请在群聊中发起绑定')
        return

    auth_groups = plugin_config.get('group', {}).get('adminAuthGroup', [])
    in_auth_group = False
    try:
        group_key = int(ctx.group_key)
        in_auth_group = group_key in [int(g) for g in auth_groups]
    except (TypeError, ValueError):
        in_auth_group = False
    if not in_auth_group:
        await send_finish(绑定_cmd, '本群无法认证，请在开发者所在的群聊发起绑定')
        return

    # 没有已录 openid 的超管时，卡片无人可点，直接纯文本提示（不能放开给所有人）
    admin_openids = await _superadmin_openids()
    if not admin_openids:
        await send_finish(绑定_cmd, '暂无已完成身份绑定的超级管理员，无法发起绑定，请联系开发者')
        return

    target_qq = args.extract_plain_text().strip()
    if not re.fullmatch(r'\d{5,12}', target_qq):
        await send_finish(绑定_cmd, '请输入正确的 QQ 号，格式：!绑定 123456789')
        return

    user_id = await ctx.get_user_id(auto_create=True)
    if not user_id:
        await send_finish(绑定_cmd, '获取用户信息失败，请稍后重试')
        return

    unified_user = await get_unified_user_by_id(user_id)
    if not unified_user:
        await send_finish(绑定_cmd, '获取用户信息失败，请稍后重试')
        return

    request, error = await prepare_bind_request(unified_user, target_qq)
    if error:
        await send_finish(绑定_cmd, error)
        return

    bind_type = BIND_TYPE_LABELS.get(request.bindType, request.bindType)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    masked_openid = _mask_openid(request.qqbotOpenid)

    md_card = (
        f'## 绑定信息 #{request.id}\n'
        f'**发起人**：<qqbot-at-user id="{request.qqbotOpenid}" />\n'
        f'**类型**：{bind_type}\n'
        f'**目标 QQ**：{request.targetQQ}\n'
        f'**OpenID**：{masked_openid}\n'
        f'**时间**：{now}\n\n'
        f'需要等待开发者确认\n\n'
        + ' '.join(f'<qqbot-at-user id="{oid}" />' for oid in admin_openids)
    )

    await _finish_bind_card(md_card, ctx, request, admin_openids)


def _bind_status_card(request, status_text: str) -> str:
    """审批后的状态卡（无按钮）：主体与原卡一致，末尾换成状态"""
    bind_type = BIND_TYPE_LABELS.get(request.bindType, request.bindType)
    created = request.createdAt.astimezone().strftime('%Y-%m-%d %H:%M')
    return (
        f'## 绑定信息 #{request.id}\n'
        f'**发起人**：<qqbot-at-user id="{request.qqbotOpenid}" />\n'
        f'**类型**：{bind_type}\n'
        f'**目标 QQ**：{request.targetQQ}\n'
        f'**OpenID**：{_mask_openid(request.qqbotOpenid)}\n'
        f'**时间**：{created}\n\n'
        f'**状态**：{status_text}'
    )


def _is_bind_button(bot, event) -> bool:
    from nonebot.adapters.qq import InteractionCreateEvent
    if not isinstance(event, InteractionCreateEvent):
        return False
    data = event.data.resolved.button_data or ''
    return data.startswith('bind:')


button_matcher = on_notice(rule=Rule(_is_bind_button), priority=1, block=True)


@button_matcher.handle()
async def handle_bind_button(bot, event):
    """处理绑定卡按钮点击：仅超管可操作，回应交互后发送审批结果"""
    from nonebot.adapters.qq import InteractionCreateEvent
    if not isinstance(event, InteractionCreateEvent):
        return

    async def _respond(code: int):
        try:
            await bot.put_interaction(interaction_id=event.id, code=code)
        except Exception as exc:
            logger.warning(f'交互回应失败：{exc}')

    try:
        _, action, raw_id = (event.data.resolved.button_data or '').split(':', 2)
        request_id = int(raw_id)
    except (ValueError, AttributeError):
        # 无效按钮数据也要回应，否则客户端会一直转圈
        await _respond(3)
        return

    clicker = event.group_member_openid or event.user_openid or ''
    clicker_user = await get_unified_user_by_platform('qqbot', clicker) if clicker else None
    if not (clicker_user and clicker_user.isSuperAdmin):
        # 4 = 没有权限；客户端会给出无权限提示
        await _respond(4)
        return

    request = await getIdentityBindRequest(request_id)
    if not request or request.status != 'pending':
        await _respond(3)  # 3 = 重复操作
        return

    await _respond(0)
    approve = action == 'approve'
    result = await approve_bind_request(request_id, approve)
    if result.get('success'):
        status = '已确认' if approve else '已取消'
    else:
        status = f'处理失败（{result.get("error")}）'

    # 官机不支持编辑群消息：删除原卡片，重发无按钮的状态卡
    from nonebot.adapters.qq import MessageSegment as QQMessageSegment
    message_id = event.data.resolved.message_id or request.cardMessageId
    if message_id:
        try:
            await bot.delete_group_message(
                group_openid=event.group_openid, message_id=message_id
            )
        except Exception as exc:
            logger.warning(f'删除绑定卡失败：{exc}')
    try:
        await bot.send(event, QQMessageSegment.markdown(_bind_status_card(request, status)))
    except Exception as exc:
        logger.warning(f'发送绑定结果卡失败：{exc}')


openid_cmd = on_command('openid', priority=5, block=True)


@openid_cmd.handle()
async def handle_openid(ctx: Ctx):
    if ctx.platform == 'onebot':
        real_qq = await ctx.get_real_qq()
        await send_finish(openid_cmd, f'当前为 NapCat 端，您的 QQ 号：{real_qq or "未知"}')
        return

    openid = ctx.platform_user_id
    if not openid:
        await send_finish(openid_cmd, '获取官方身份失败，请稍后重试')
        return

    if ctx.is_group:
        await send_finish(
            openid_cmd,
            f'您的 OpenID：{_mask_openid(openid)}\n私聊发送 !openid 可获取完整值'
        )
    else:
        await send_finish(openid_cmd, f'您的 OpenID：{openid}')


我的身份_cmd = on_command('我的身份', priority=5, block=True)


@我的身份_cmd.handle()
async def handle_我的身份(ctx: Ctx):
    user_id = await ctx.get_user_id(auto_create=False)
    if not user_id:
        await send_finish(我的身份_cmd, '您还没有创建账号，请先使用其他功能创建账号')
        return

    unified_user = await get_unified_user_by_id(user_id)
    if not unified_user:
        await send_finish(我的身份_cmd, '获取用户信息失败，请稍后重试')
        return

    output = f'您的统一用户ID：{user_id}\n'

    if unified_user.realQQ:
        output += f'✓ QQ 身份：已绑定 (QQ: {unified_user.realQQ})\n'
    else:
        output += f'✗ QQ 身份：未绑定\n'

    if unified_user.qqbotOpenid:
        output += f'✓ 官方Bot身份：已绑定\n'
    else:
        output += f'✗ 官方Bot身份：未绑定\n'

    if unified_user.webToken:
        output += f'✓ Web端token：已设置\n'
        output += f'  创建时间：{unified_user.webTokenCreatedAt.strftime("%Y-%m-%d %H:%M:%S") if unified_user.webTokenCreatedAt else "未知"}\n'
    else:
        output += f'✗ Web端token：未设置\n'

    await send_finish(我的身份_cmd, output.rstrip('\n'))


生成token_cmd = on_command('生成token', priority=5, block=True)


@生成token_cmd.handle()
async def handle_生成token(ctx: Ctx, args: Message = CommandArg()):
    if ctx.is_group:
        await send_finish(生成token_cmd, '该指令只能在私聊中使用^ ^')
        return

    arg_text = args.extract_plain_text().strip()
    target_user_id = None
    target_qq = None

    if arg_text:
        if not await is_super_admin(await ctx.get_user_id()):
            await send_finish(生成token_cmd, '只有管理员才能代他人生成token')
            return

        try:
            num = int(arg_text)
            if num < 1000000:
                target_user = await get_unified_user_by_id(num)
                if target_user:
                    target_user_id = target_user.id
                else:
                    target_user = await get_unified_user_by_real_qq(str(num))
                    if target_user:
                        target_user_id = target_user.id
                        target_qq = target_user.realQQ
            else:
                target_user = await get_unified_user_by_real_qq(str(num))
                if target_user:
                    target_user_id = target_user.id
                    target_qq = target_user.realQQ
        except ValueError:
            pass

        if not target_user_id:
            await send_finish(生成token_cmd, f'未找到用户：{arg_text}')
            return

    if not target_user_id:
        target_user_id = await ctx.get_user_id(auto_create=True)
        if not target_user_id:
            await send_finish(生成token_cmd, '获取用户信息失败，请稍后重试')
            return

    unified_user = await get_unified_user_by_id(target_user_id)
    if not unified_user:
        await send_finish(生成token_cmd, '获取用户信息失败，请稍后重试')
        return

    if not unified_user.realQQ:
        await send_finish(生成token_cmd, '该账号尚未完成身份绑定，无法使用 Web 端。请先完成绑定')
        return

    old_token_exists = bool(unified_user.webToken)

    token = await generate_web_token(unified_user)

    if target_qq:
        await send_finish(生成token_cmd,
            f'✅ 已为用户 {target_qq} 生成Web端token！\n\n'
            f'Token：{token}\n\n'
            f'{"（已覆盖旧token）" if old_token_exists else ""}'
            f'请通知用户妥善保管此token，不要泄露给他人'
        )
    elif target_user_id != await ctx.get_user_id():
        await send_finish(生成token_cmd,
            f'✅ 已为用户ID {target_user_id} 生成Web端token！\n\n'
            f'Token：{token}\n\n'
            f'{"（已覆盖旧token）" if old_token_exists else ""}'
            f'请通知用户妥善保管此token，不要泄露给他人'
        )
    else:
        await send_finish(生成token_cmd,
            f'✅ Web端token生成成功！\n\n'
            f'您的token：{token}\n\n'
            f'{"（已覆盖旧token）" if old_token_exists else ""}'
            f'请妥善保管此token，不要泄露给他人\n'
            f'使用方法：在Web端登录页面输入此token'
        )


查看token_cmd = on_command('查看token', priority=5, block=True, aliases={'查询token'})


@查看token_cmd.handle()
async def handle_查看token(ctx: Ctx):
    if ctx.is_group:
        await send_finish(查看token_cmd, '该指令只能在私聊中使用^ ^')
        return

    user_id = await ctx.get_user_id(auto_create=False)
    if not user_id:
        await send_finish(查看token_cmd, '您还没有创建账号')
        return

    unified_user = await get_unified_user_by_id(user_id)
    if not unified_user:
        await send_finish(查看token_cmd, '获取用户信息失败，请稍后重试')
        return

    if not unified_user.realQQ:
        await send_finish(查看token_cmd, '该账号尚未完成身份绑定，无法使用 Web 端。请先完成绑定')
        return

    if not unified_user.webToken:
        await send_finish(查看token_cmd,
            '您还没有设置Web端token\n'
            '请使用 !生成token 指令生成token'
        )
        return

    await send_finish(查看token_cmd,
        f'您的Web端token：\n{unified_user.webToken}\n\n'
        f'创建时间：{unified_user.webTokenCreatedAt.strftime("%Y-%m-%d %H:%M:%S") if unified_user.webTokenCreatedAt else "未知"}'
    )


群映射_cmd = on_command('群映射', priority=5, block=True)


@群映射_cmd.handle()
async def handle_群映射(ctx: Ctx, args: Message = CommandArg()):
    """群映射：官方 Bot 端为唯一写入口，OneBot 端只读"""
    if not ctx.is_group:
        await send_finish(群映射_cmd, '该指令只能在群聊中使用^ ^')
        return

    user_id = await ctx.get_user_id(auto_create=False)
    if not user_id or not await is_super_admin(user_id):
        await send_finish(群映射_cmd, '只有管理员才能操作群映射')
        return

    if ctx.platform == 'onebot':
        mapping = await get_group_mapping_by_onebot_id(ctx.group_id)
        if mapping and mapping.qqbotGroupOpenid:
            await send_finish(群映射_cmd, '本群已绑定官方Bot群')
        else:
            await send_finish(群映射_cmd, '本群未绑定官方Bot群')
        return

    arg_text = args.extract_plain_text().strip()
    mapping = await get_group_mapping_by_openid(ctx.group_id)
    if not arg_text:
        if mapping and mapping.onebotGroupId:
            await send_finish(群映射_cmd, f'本群已绑定QQ群：{ctx.group_key}')
        else:
            await send_finish(群映射_cmd, '本群未绑定QQ群')
        return

    if not arg_text.isdigit():
        await send_finish(群映射_cmd, '请输入正确的QQ群号，格式：!群映射 123456789')
        return

    await bind_group_mapping(ctx.group_id, arg_text)
    await send_finish(群映射_cmd, f'✅ 群映射成功：本群 → QQ群 {arg_text}')
