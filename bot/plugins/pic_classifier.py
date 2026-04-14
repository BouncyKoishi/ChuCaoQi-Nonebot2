import random
import httpx
import aiohttp
import time
from io import BytesIO
from PIL import Image
from typing import Optional
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent

from kusa_base import plugin_config
from utils import checkBanAvailable
from .reply_commands import reply_command, set_duel_confirmations

nailongModel = None
modelPath = './model_best.pth'
img_transform = None
device = None
RUN_NAILONG_MODEL_FLAG = (plugin_config.get('env', '') == 'prod')

if RUN_NAILONG_MODEL_FLAG:
    import torch
    from torch import nn
    from torchvision import transforms
    from torchvision import models

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    img_transform = transforms.Compose([
        transforms.Resize([224, 224]),
        transforms.ToTensor(),
    ])
    try:
        nailongModel = models.resnet50()
        nailongModel.fc = torch.nn.Linear(nailongModel.fc.in_features, 2)
        nailongModel.load_state_dict(torch.load(modelPath, map_location=device, weights_only=True)['model'])
        nailongModel = nailongModel.to(device)
        nailongModel.eval()
        print("奶龙检测模型加载成功")
    except Exception as e:
        print(f"奶龙检测模型加载失败: {e}")
else:
    print("当前环境不加载奶龙检测模型")

lastUsedTime = {}


def time_check(command: str, ctx: dict):
    if 'group_id' not in ctx or ctx['group_id'] != plugin_config.get('group', {}).get('sysu'):
        return True, None

    command = command.replace('#', '')
    key = f'{ctx["user_id"]}_{command}'
    if key in lastUsedTime:
        now_time = int(time.time())
        end_time = lastUsedTime[key] + 3 * 3600
        if now_time < end_time:
            time_strf = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
            sign = f'冷却时间还没结束，请在{time_strf}以后再来。'
            return False, sign
    return True, None


def time_updater(command: str, group_id: int, user_id: int):
    global lastUsedTime
    if group_id != plugin_config.get('group', {}).get('sysu'):
        return
    command = command.replace('#', '')
    key = f'{user_id}_{command}'
    lastUsedTime[key] = int(time.time())


async def nsfw_preprocessor(event: GroupMessageEvent, img_url: str):
    user_id = event.user_id
    reply_user_id = event.reply.sender.user_id if event.reply else user_id

    time_check_result, sign = time_check('#nsfw', event.dict())
    if not time_check_result:
        return False, sign

    if user_id != reply_user_id and random.random() < 1/8:
        duel_msg = f"你触发了黑暗决斗。\n如果这张图片是色图，发图的人将会被口球，否则你会被口球。口球的秒数等于adult/everyone的分值×10。\n输入y继续检测，输入其他表示取消。"
        set_duel_confirmations(user_id, {
            'sender': reply_user_id,
            'imgUrl': img_url,
            'imgMsgId': event.reply.message_id if event.reply else 0,
            'commandMsgId': event.message_id,
            'type': 'nsfw'
        })
        return False, duel_msg

    return True, None


async def nailong_preprocessor(event: GroupMessageEvent, img_url: str):
    user_id = event.user_id
    reply_user_id = event.reply.sender.user_id if event.reply else user_id

    time_check_result, sign = time_check('#nailong', event.dict())
    if not time_check_result:
        return False, sign

    if user_id != reply_user_id and random.random() < 1/8:
        duel_msg = "你触发了奶龙决斗。\n如果这张图片的奶龙指数大于50，发图的人将会被口球。否则你会被口球。口球的秒数等于abs(奶龙指数-50)×40。\n输入y继续检测，输入其他表示取消。"
        set_duel_confirmations(user_id, {
            'sender': reply_user_id,
            'imgUrl': img_url,
            'imgMsgId': event.reply.message_id if event.reply else 0,
            'commandMsgId': event.message_id,
            'type': 'nailong'
        })
        return False, duel_msg

    return True, None


async def check_nsfw(event: GroupMessageEvent, img_url: str, bot: Bot) -> str:
    await bot.send(event=event, message="正在检测……")

    moderate_content_api_key = plugin_config.get('web', {}).get('moderateContent', {}).get('key', '')
    if not moderate_content_api_key:
        return '未配置 NSFW 检测 API Key'
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(img_url)
            image = Image.open(BytesIO(response.content))
            image = image.resize((600, 600), Image.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format='WEBP', quality=80)
            buffer.seek(0)

            files = {'file': ('image.webp', buffer, 'image/webp')}
            data = {'key': moderate_content_api_key}
            r = await client.post('https://api.moderatecontent.com/moderate/', data=data, files=files)
            result = r.json()
            print(f'NSFW检测结果：{result}')

            if 'predictions' not in result:
                return f'API没有返回检测结果，请稍后再来…_φ(･ω･` )\n{result.get("error")}'
            else:
                time_updater('#nsfw', event.group_id if hasattr(event, 'group_id') else 0, event.user_id)
                return '检测结果：\n' + '\n'.join([f'{k} {v:.4f}' for k, v in result['predictions'].items()])
    except Exception as e:
        print(f"处理图片失败 {img_url}: {e}")
        return f'检测失败了…_φ(･ω･` )'


async def check_nailong(event: GroupMessageEvent, img_url: str, bot: Bot) -> str:
    await bot.send(event=event, message="正在检测……")

    if nailongModel is None:
        return '奶龙模型未加载，暂无法使用…_φ(･ω･` )'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(img_url, timeout=25) as response:
                if response.status == 200:
                    content = await response.read()
                    img = Image.open(BytesIO(content)).convert('RGB')
                    img_tensor = img_transform(img).unsqueeze(0)

                    with torch.no_grad():
                        img_tensor = img_tensor.to(device)
                        outputs = nailongModel(img_tensor)
                        prob = nn.Softmax(dim=1)(outputs)
                        result = float(prob[0, 1]) * 100

                    time_updater('#nailong', event.group_id if hasattr(event, 'group_id') else 0, event.user_id)
                    return f'奶龙指数：{result:.4f}'
    except Exception as e:
        print(f"处理图片失败 {img_url}: {e}")
        return f'检测失败了…_φ(･ω･` )'


@reply_command('nsfw', preprocessor=nsfw_preprocessor)
async def nsfw_cmd(event: GroupMessageEvent, img_url: str, bot: Bot) -> str:
    return await check_nsfw(event, img_url, bot)


@reply_command('nailong', preprocessor=nailong_preprocessor)
async def nailong_cmd(event: GroupMessageEvent, img_url: str, bot: Bot) -> str:
    return await check_nailong(event, img_url, bot)


confirm_duel = on_message(priority=10, block=False)


@confirm_duel.handle()
async def handle_confirm_duel(bot: Bot, event: GroupMessageEvent):
    from .reply_commands import get_duel_confirmations, del_duel_confirmations

    user_qq = event.user_id
    confirmations = get_duel_confirmations()
    if user_qq not in confirmations:
        return

    message_text = str(event.get_message()).strip().lower()
    if message_text.startswith('#'):
        return

    if message_text != 'y':
        del_duel_confirmations(user_qq)
        await bot.send(event=event, message="已取消决斗。")
        return

    info = confirmations[user_qq]
    command_type = info['type']

    await bot.send(event=event, message=f"正在启动{'黑暗' if command_type == 'nsfw' else '奶龙'}决斗……")

    if command_type == 'nsfw':
        result_str = await _do_nsfw_check(info['imgUrl'])
        result_dict = await _get_nsfw_result_dict(info['imgUrl'])
        if result_dict:
            adult_score = result_dict.get('adult', 0)
            everyone_score = result_dict.get('everyone', 0)
            is_adult = adult_score > everyone_score
            target_id = info['sender'] if is_adult else user_qq
            fight_result_str = (f'决斗成功！图片发送者' if is_adult else '决斗失败！检测者')

            if hasattr(event, 'group_id'):
                can_ban_target = await checkBanAvailable(target_id, event.group_id)
                if can_ban_target:
                    mute_duration = int(max(adult_score, everyone_score) * 10)
                    await bot.set_group_ban(group_id=event.group_id, user_id=target_id, duration=mute_duration)
                    fight_result_str += f'获得了{mute_duration}秒的口球！'
                else:
                    msg_id = info['imgMsgId'] if is_adult else info['commandMsgId']
                    await bot.set_msg_emoji_like(message_id=msg_id, emoji_id=128074)
                    fight_result_str += f'无法被口球，获得了除草器的一拳！'
            await bot.send(event=event, message=f'{result_str}\n{fight_result_str}')
        else:
            await bot.send(event=event, message=result_str)
        time_updater('nsfw', event.group_id if hasattr(event, 'group_id') else 0, user_qq)

    elif command_type == 'nailong':
        nailong_score = await _get_nailong_score(info['imgUrl'])
        result_str = await _do_nailong_check(info['imgUrl'])
        if nailong_score is not None:
            is_nailong = nailong_score > 50
            target_id = info['sender'] if is_nailong else user_qq
            fight_result_str = (f'决斗成功！图片发送者' if is_nailong else '决斗失败！检测者')

            if hasattr(event, 'group_id'):
                can_ban_target = await checkBanAvailable(target_id, event.group_id)
                if can_ban_target:
                    mute_duration = int(abs(nailong_score - 50) * 40)
                    await bot.set_group_ban(group_id=event.group_id, user_id=target_id, duration=mute_duration)
                    fight_result_str += f'获得了{mute_duration}秒的口球！'
                else:
                    msg_id = info['imgMsgId'] if is_nailong else info['commandMsgId']
                    await bot.set_msg_emoji_like(message_id=msg_id, emoji_id=128074)
                    fight_result_str += f'无法被口球，获得了除草器的一拳！'
            await bot.send(event=event, message=f'{result_str}\n{fight_result_str}')
        else:
            await bot.send(event=event, message=result_str)
        time_updater('nailong', event.group_id if hasattr(event, 'group_id') else 0, user_qq)

    del_duel_confirmations(user_qq)


async def _do_nsfw_check(img_url: str) -> str:
    moderate_content_api_key = plugin_config.get('web', {}).get('moderateContent', {}).get('key', '')
    if not moderate_content_api_key:
        return '未配置 NSFW 检测 API Key'
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(img_url)
            image = Image.open(BytesIO(response.content))
            image = image.resize((600, 600), Image.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format='WEBP', quality=80)
            buffer.seek(0)

            files = {'file': ('image.webp', buffer, 'image/webp')}
            data = {'key': moderate_content_api_key}
            r = await client.post('https://api.moderatecontent.com/moderate/', data=data, files=files)
            result = r.json()

            if 'predictions' not in result:
                return f'API没有返回检测结果，请稍后再来…_φ(･ω･` )\n{result.get("error")}'
            else:
                return '检测结果：\n' + '\n'.join([f'{k} {v:.4f}' for k, v in result['predictions'].items()])
    except Exception as e:
        print(f"处理图片失败 {img_url}: {e}")
        return f'检测失败了…_φ(･ω･` )'


async def _do_nailong_check(img_url: str) -> str:
    if nailongModel is None:
        return '奶龙模型未加载，暂无法使用…_φ(･ω･` )'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(img_url, timeout=25) as response:
                if response.status == 200:
                    content = await response.read()
                    img = Image.open(BytesIO(content)).convert('RGB')
                    img_tensor = img_transform(img).unsqueeze(0)

                    with torch.no_grad():
                        img_tensor = img_tensor.to(device)
                        outputs = nailongModel(img_tensor)
                        prob = nn.Softmax(dim=1)(outputs)
                        result = float(prob[0, 1]) * 100

                    return f'奶龙指数：{result:.4f}'
    except Exception as e:
        print(f"处理图片失败 {img_url}: {e}")
        return f'检测失败了…_φ(･ω･` )'


async def _get_nsfw_result_dict(img_url: str) -> Optional[dict]:
    moderate_content_api_key = plugin_config.get('web', {}).get('moderateContent', {}).get('key', '')
    if not moderate_content_api_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(img_url)
            image = Image.open(BytesIO(response.content))
            image = image.resize((600, 600), Image.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format='WEBP', quality=80)
            buffer.seek(0)

            files = {'file': ('image.webp', buffer, 'image/webp')}
            data = {'key': moderate_content_api_key}
            r = await client.post('https://api.moderatecontent.com/moderate/', data=data, files=files)
            result = r.json()
            if 'predictions' in result:
                return result['predictions']
    except:
        pass
    return None


async def _get_nailong_score(img_url: str) -> Optional[float]:
    if nailongModel is None:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(img_url, timeout=25) as response:
                if response.status == 200:
                    content = await response.read()
                    img = Image.open(BytesIO(content)).convert('RGB')
                    img_tensor = img_transform(img).unsqueeze(0)

                    with torch.no_grad():
                        img_tensor = img_tensor.to(device)
                        outputs = nailongModel(img_tensor)
                        prob = nn.Softmax(dim=1)(outputs)
                        return float(prob[0, 1]) * 100
    except:
        pass
    return None