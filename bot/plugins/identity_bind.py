"""
身份绑定插件
提供三端身份绑定、token管理等功能
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from reloader import db_command as on_command
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg
from nonebot.adapters import Message

from multi_platform import (
    get_user_id,
    get_platform_type,
    is_group_message,
    send_finish,
)
from services.identity_service import (
    get_unified_user_by_id,
    get_unified_user_by_real_qq,
    generate_web_token,

)
from dbConnection.user import saveUnifiedUser
from kusa_base import is_super_admin

bind_codes: Dict[str, Dict] = {}


获取绑定码_cmd = on_command('获取绑定码', priority=5, block=True)

@获取绑定码_cmd.handle()
async def handle_获取绑定码(bot: Bot, event: Event):
    if is_group_message(event):
        await send_finish(获取绑定码_cmd, '该指令只能在私聊中使用^ ^')
        return
    
    user_id = await get_user_id(event, auto_create=True)
    if not user_id:
        await send_finish(获取绑定码_cmd, '获取用户信息失败，请稍后重试')
        return
    
    unified_user = await get_unified_user_by_id(user_id)
    if not unified_user:
        await send_finish(获取绑定码_cmd, '获取用户信息失败，请稍后重试')
        return
    
    if unified_user.realQQ and unified_user.qqbotOpenid:
        await send_finish(获取绑定码_cmd, '您的账号已经完成了双端绑定，无需再次绑定')
        return
    
    bind_code = ''.join(random.choices(string.digits, k=6))
    expire_time = datetime.now() + timedelta(minutes=5)
    
    bind_codes[bind_code] = {
        'user_id': user_id,
        'platform': get_platform_type(event),
        'platform_id': get_user_id(event),
        'expire_time': expire_time
    }
    
    platform_name = 'NapCat端' if get_platform_type(event) == 'onebot' else '官方Bot端'
    await send_finish(获取绑定码_cmd, 
        f'您的绑定码为：{bind_code}\n'
        f'有效期：5分钟\n\n'
        f'请在另一个平台（{"官方Bot端" if get_platform_type(event) == "onebot" else "NapCat端"}）'
        f'使用 `/绑定 {bind_code}` 来完成身份绑定'
    )


绑定_cmd = on_command('绑定', priority=5, block=True)

@绑定_cmd.handle()
async def handle_绑定(bot: Bot, event: Event, args: Message = CommandArg()):
    if is_group_message(event):
        await send_finish(绑定_cmd, '该指令只能在私聊中使用^ ^')
        return
    
    bind_code = args.extract_plain_text().strip()
    if not bind_code or not bind_code.isdigit() or len(bind_code) != 6:
        await send_finish(绑定_cmd, '请输入正确的6位数字绑定码，格式：/绑定 123456')
        return
    
    if bind_code not in bind_codes:
        await send_finish(绑定_cmd, '绑定码不存在或已过期，请重新获取')
        return
    
    bind_info = bind_codes[bind_code]
    if datetime.now() > bind_info['expire_time']:
        del bind_codes[bind_code]
        await send_finish(绑定_cmd, '绑定码已过期，请重新获取')
        return
    
    current_platform = get_platform_type(event)
    current_platform_id = get_user_id(event)
    
    if current_platform == bind_info['platform']:
        await send_finish(绑定_cmd, '不能在同一平台进行绑定操作')
        return
    
    source_user_id = bind_info['user_id']
    source_unified_user = await get_unified_user_by_id(source_user_id)
    if not source_unified_user:
        await send_finish(绑定_cmd, '获取绑定用户信息失败，请重新获取绑定码')
        return
    
    if source_unified_user.realQQ and source_unified_user.qqbotOpenid:
        await send_finish(绑定_cmd, '该账号已完成双端绑定，无需再次绑定')
        return
    
    if bind_info['platform'] == 'onebot':
        source_unified_user.qqbotOpenid = current_platform_id
    else:
        source_unified_user.realQQ = current_platform_id

    await saveUnifiedUser(source_unified_user)
    del bind_codes[bind_code]
    
    await send_finish(绑定_cmd, '✅ 身份绑定成功！您现在可以在两个平台使用同一账号了')


我的身份_cmd = on_command('我的身份', priority=5, block=True)

@我的身份_cmd.handle()
async def handle_我的身份(bot: Bot, event: Event):
    user_id = await get_user_id(event, auto_create=False)
    if not user_id:
        await send_finish(我的身份_cmd, '您还没有创建账号，请先使用其他功能创建账号')
        return
    
    unified_user = await get_unified_user_by_id(user_id)
    if not unified_user:
        await send_finish(我的身份_cmd, '获取用户信息失败，请稍后重试')
        return
    
    output = f'您的统一用户ID：{user_id}\n\n'
    
    if unified_user.realQQ:
        output += f'✓ NapCat端：已绑定 (QQ: {unified_user.realQQ})\n'
    else:
        output += f'✗ NapCat端：未绑定\n'
    
    if unified_user.qqbotOpenid:
        output += f'✓ 官方Bot端：已绑定\n'
    else:
        output += f'✗ 官方Bot端：未绑定\n'
    
    if unified_user.webToken:
        output += f'\n✓ Web端token：已设置\n'
        output += f'  创建时间：{unified_user.webTokenCreatedAt.strftime("%Y-%m-%d %H:%M:%S") if unified_user.webTokenCreatedAt else "未知"}\n'
    else:
        output += f'\n✗ Web端token：未设置\n'
    
    await send_finish(我的身份_cmd, output)


生成token_cmd = on_command('生成token', priority=5, block=True)

@生成token_cmd.handle()
async def handle_生成token(bot: Bot, event: Event, args: Message = CommandArg()):
    if is_group_message(event):
        await send_finish(生成token_cmd, '该指令只能在私聊中使用^ ^')
        return
    
    arg_text = args.extract_plain_text().strip()
    target_user_id = None
    target_qq = None
    
    if arg_text:
        if not await is_super_admin(await get_user_id(event)):
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
        target_user_id = await get_user_id(event, auto_create=True)
        if not target_user_id:
            await send_finish(生成token_cmd, '获取用户信息失败，请稍后重试')
            return
    
    unified_user = await get_unified_user_by_id(target_user_id)
    if not unified_user:
        await send_finish(生成token_cmd, '获取用户信息失败，请稍后重试')
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
    elif target_user_id != await get_user_id(event):
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


查看token_cmd = on_command('查看token', priority=5, block=True, aliases=['查询token'])

@查看token_cmd.handle()
async def handle_查看token(bot: Bot, event: Event):
    if is_group_message(event):
        await send_finish(查看token_cmd, '该指令只能在私聊中使用^ ^')
        return
    
    user_id = await get_user_id(event, auto_create=False)
    if not user_id:
        await send_finish(查看token_cmd, '您还没有创建账号')
        return
    
    unified_user = await get_unified_user_by_id(user_id)
    if not unified_user:
        await send_finish(查看token_cmd, '获取用户信息失败，请稍后重试')
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
