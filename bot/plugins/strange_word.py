"""
怪话插件 - NoneBot2 版本

支持怪话收集、随机怪话、AI 怪话等功能。

指令：
- 说点怪话 - 随机怪话或AI生成怪话
- 话怪点说 - 随机怪话（反转）
- 说话怪点 - 随机怪话（打乱）
- 说些怪话 - 多条随机怪话
- gh_receive_freeze - 冻结/解冻怪话接收
- gh_model_freeze - 启用/禁用AI怪话
- #怪话 - 说点怪话指令的回复版本
"""

import math
import random
import os
import re
import asyncio
from nonebot import on_command, on_message, on_notice
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, PokeNotifyEvent, Bot
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot import get_driver
from nonebot_plugin_apscheduler import scheduler

from kusa_base import plugin_config
from .reply_commands import reply_text_command
from services.chat_service import ChatService

sentence_list_dict = {}

poke_cache = {}

poke_last_respond_time = {}

poke_last_reply = {}

receive_freeze = False
allow_model = True

not_record_words = []
not_record_members = []
record_groups = []
poke_trigger_groups = []
default_group_num = 0

try:
    not_record_words = plugin_config.get('guaihua', {}).get('notRecordWords', [])
    not_record_members = plugin_config.get('guaihua', {}).get('notRecordMembers', [])
    record_groups = plugin_config.get('guaihua', {}).get('recordGroups', [])
    poke_trigger_groups = plugin_config.get('guaihua', {}).get('pokeTriggerGroups', [])
    default_group_num = plugin_config.get('group', {}).get('sysu', 0)
except Exception as e:
    print(f"[怪话] 加载配置失败: {e}")


def get_sentence_list(group_num: int) -> list:
    return sentence_list_dict.get(group_num) or sentence_list_dict.get(default_group_num, [])


def get_random_sentence(group_num: int) -> str:
    sentence_list = get_sentence_list(group_num)
    if not sentence_list:
        return "目前还没有怪话库存^ ^"
    return random.choice(sentence_list)


def is_valid_for_model(sentence: str) -> bool:
    if len(sentence) <= 2:
        return False
    if '[CQ:' in sentence:
        return False
    if re.match(r'^[\s!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|`~]*$', sentence):
        return False
    return True


def get_model_sentence_list(group_num: int) -> list:
    sentence_list = get_sentence_list(group_num)
    return [s for s in sentence_list if is_valid_for_model(s)]


def is_valid_cache_message(event: GroupMessageEvent) -> tuple[bool, str, int]:
    """检查消息是否符合缓存规则"""
    message = event.get_message()
    
    for seg in message:
        if seg.type in ('image', 'at', 'face', 'share', 'music', 'video', 'record', 'file'):
            return False, '', 0
    
    msg = event.get_plaintext()
    if not msg:
        return False, '', 0
    
    if msg.startswith('!') or msg.startswith('#'):
        return False, '', 0
    
    return True, msg, event.time


async def get_sentence_advance(group_num: int, input_str: str, exclude: str = '') -> str:
    """使用AI从怪话库中选择最合适的回复"""
    model_sentence_list = get_model_sentence_list(group_num)
    if not model_sentence_list:
        return get_random_sentence(group_num)
    
    system_prompt = '你需要从以下怪话中选择一句语义最适宜的话来回答用户说的内容。你的回答内容只能是怪话列表中的某一句话，不包括任何其它内容。\n'
    user_prompt = f"用户发言：{input_str}\n\n怪话列表：\n"
    
    available_sentences = [s for s in model_sentence_list if s != exclude] if exclude else model_sentence_list
    if len(available_sentences) < 10:
        available_sentences = model_sentence_list
    
    for _ in range(10):
        user_prompt += random.choice(available_sentences) + '\n'
    
    prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    reply, _, _ = await ChatService.get_chat_reply("deepseek-chat", prompt)
    
    if reply not in model_sentence_list:
        print(f'输出内容为:"{reply}" 匹配怪话库失败，输出随机怪话')
        reply = random.choice(model_sentence_list) if model_sentence_list else "目前还没有怪话库存awa"
    
    return reply


async def get_sentence_list_advance(group_num: int, input_str: str) -> list:
    """使用AI生成多条怪话"""
    model_sentence_list = get_model_sentence_list(group_num)
    if not model_sentence_list:
        return [get_random_sentence(group_num) for _ in range(3)]
    
    system_prompt = ('你需要从以下怪话中选择三句话，组成一个尽可能语义适宜且内容连贯的段落来回答用户说的内容。'
                    '你的回答内容按以下格式输出：["A", "B", "C"]'
                    '其中A、B、C只能是怪话列表中的某一句话，不包括任何其它内容。')
    user_prompt = f"用户发言：{input_str}\n\n怪话列表：\n"
    for _ in range(40):
        user_prompt += random.choice(model_sentence_list) + '\n'
    
    prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    reply, _, _ = await ChatService.get_chat_reply("deepseek-chat", prompt)
    
    if reply.startswith('[') and reply.endswith(']'):
        reply = reply.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        reply = reply.replace('，', ',').replace('。', '.').replace('：', ':').replace('；', ';')
        try:
            reply_list = eval(reply)
            if isinstance(reply_list, list):
                for i in range(len(reply_list)):
                    if not isinstance(reply_list[i], str):
                        print(f'输出内容为:"{reply}" 匹配怪话库失败，输出随机怪话')
                        reply_list[i] = random.choice(model_sentence_list)
                return reply_list
        except Exception as e:
            print(f'解析输出内容失败，错误信息：{e}')
    
    print(f'输出内容为:"{reply}" 基本格式匹配失败，输出随机怪话')
    sentence_list = get_sentence_list(group_num)
    return [random.choice(sentence_list) if sentence_list else "目前还没有怪话库存awa" for _ in range(3)]


say_cmd = on_command("说点怪话", priority=5, block=True)
say_reverse_cmd = on_command("话怪点说", priority=5, block=True)
say_shuffle_cmd = on_command("说话怪点", aliases={"怪点说话"}, priority=5, block=True)
say_many_cmd = on_command("说些怪话", priority=5, block=True)
freeze_cmd = on_command("gh_receive_freeze", priority=5, block=True)
model_freeze_cmd = on_command("gh_model_freeze", priority=5, block=True)


@reply_text_command('怪话')
async def 怪话_cmd(event, bot):
    """回复消息作为说点怪话的参数"""
    if not hasattr(event, 'reply') or not event.reply:
        return 'Reply获取异常^ ^'

    text = event.reply.message.extract_plain_text().strip()
    if not text:
        return '暂不支持非文本格式怪话^ ^'

    group_num = getattr(event, 'group_id', default_group_num)

    if allow_model and random.random() < 0.5:
        reply = await get_sentence_advance(group_num, text)
        return reply
    else:
        return get_random_sentence(group_num)


@reply_text_command('remove')
async def remove_cmd(event, bot):
    from multi_platform import get_user_id
    from kusa_base import is_super_admin

    user_id = await get_user_id(event)
    if not user_id or not await is_super_admin(user_id):
        return

    text = str(event.reply.message).strip()
    if not text:
        return

    global sentence_list_dict

    found = False
    for group_num in list(sentence_list_dict.keys()):
        sentence_list = sentence_list_dict[group_num]
        if text in sentence_list:
            sentence_list.remove(text)
            found = True

    if found:
        save_strange_words()
        return '已移除本句怪话'
    else:
        return '未查找到怪话'


@freeze_cmd.handle()
async def handle_freeze(event: MessageEvent):
    """冻结/解冻怪话接收"""
    global receive_freeze
    receive_freeze = not receive_freeze
    await freeze_cmd.send(f'怪话接收已{"冻结" if receive_freeze else "解冻"}')


@model_freeze_cmd.handle()
async def handle_model_freeze(event: MessageEvent):
    """启用/禁用AI怪话"""
    global allow_model
    allow_model = not allow_model
    await model_freeze_cmd.send(f'大模型怪话已{"启用" if allow_model else "禁用"}')


@say_cmd.handle()
async def handle_say(event: MessageEvent, args: Message = CommandArg()):
    """处理说点怪话指令"""
    group_num = getattr(event, 'group_id', default_group_num)
    stripped_text = args.extract_plain_text().strip()
    
    if stripped_text and allow_model and random.random() < 0.5:
        reply = await get_sentence_advance(group_num, stripped_text)
        await say_cmd.send(reply)
    else:
        await say_cmd.send(get_random_sentence(group_num))


@say_reverse_cmd.handle()
async def handle_say_reverse(event: MessageEvent):
    """处理话怪点说指令（反转）"""
    msg = get_random_sentence(getattr(event, 'group_id', default_group_num))
    await say_reverse_cmd.send(msg if '[CQ:' in msg else msg[::-1])


@say_shuffle_cmd.handle()
async def handle_say_shuffle(event: MessageEvent):
    """处理说话怪点指令（打乱）"""
    group_id = getattr(event, 'group_id', default_group_num)
    msg = get_random_sentence(group_id)
    if '[CQ:' in msg:
        await say_shuffle_cmd.send(msg)
    else:
        msg_list = list(msg)
        random.shuffle(msg_list)
        await say_shuffle_cmd.send(''.join(msg_list))


@say_many_cmd.handle()
async def handle_say_many(event: MessageEvent, args: Message = CommandArg()):
    """处理说些怪话指令"""
    group_id = getattr(event, 'group_id', default_group_num)
    stripped_text = args.extract_plain_text().strip()
    
    if stripped_text and allow_model and random.random() < 0.35:
        reply_list = await get_sentence_list_advance(group_id, stripped_text)
    else:
        reply_list = []
        while len(reply_list) < 3:
            msg = get_random_sentence(group_id)
            if '[CQ:' not in msg and msg not in reply_list:
                reply_list.append(msg)
    
    for msg in reply_list:
        await say_many_cmd.send(msg)
        await asyncio.sleep(1)


record_message_matcher = on_message(priority=5, block=False)


@record_message_matcher.handle()
async def record_message(event: MessageEvent):
    """记录群聊消息到怪话库，并更新拍一拍缓存"""
    if not isinstance(event, GroupMessageEvent):
        return

    group_num = event.group_id
    user_id = event.user_id
    bot_self_id = int(bot_id) if (bot_id := getattr(event, 'self_id', None)) else None
    
    valid, msg, timestamp = is_valid_cache_message(event)
    
    if valid and group_num in poke_trigger_groups and user_id != bot_self_id:
        poke_cache[group_num] = {'text': msg, 'time': timestamp, 'msg_time': timestamp}
        print(f'[怪话] 缓存更新，群{group_num}: {msg[:30]}... (t={timestamp})')

    if group_num not in record_groups:
        return

    global sentence_list_dict

    message = event.get_message()

    for seg in message:
        if seg.type in ('image', 'at', 'face', 'share', 'music', 'video', 'record', 'file'):
            return

    if hasattr(event, 'reply') and event.reply:
        return

    if receive_freeze:
        return
    if not msg:
        return
    if msg in sentence_list_dict.get(group_num, []):
        return
    if '\n' in msg:
        return
    if user_id in not_record_members:
        return

    for word in not_record_words:
        if word in msg:
            return

    sentence_list = sentence_list_dict.get(group_num, [])
    list_len = len(sentence_list)

    record_risk = 175 - (list_len / 4)
    msg_length = len(msg.replace(' ', ''))
    record_risk /= (0.12 * msg_length + 1.5 / msg_length)

    if random.random() * 100 <= record_risk:
        sentence_list.append(msg)
        print(f'群聊{group_num}录入了来自{user_id}的怪话：{msg[:30]}...')
        if list_len >= 600:
            del_msg_index = math.floor(1.1 ** (random.random() * 66) - 1)
            del_msg = sentence_list[del_msg_index]
            print(f'DelMsgIndex={del_msg_index}, Delete:{del_msg}')
            del sentence_list[del_msg_index]
        sentence_list_dict[group_num] = sentence_list


driver = get_driver()


@driver.on_startup
async def load_strange_words():
    """启动时加载怪话数据"""
    global sentence_list_dict
    folder_path = 'database/strangeWord'
    os.makedirs(folder_path, exist_ok=True)
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.txt'):
            try:
                group_num = int(filename[:-4])
                sentence_list = []
                with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                    for sentence in f.readlines():
                        sentence = sentence.strip()
                        if sentence:
                            sentence_list.append(sentence)
                print(f'群聊{group_num}当前怪话条目数：{len(sentence_list)}')
                sentence_list_dict[group_num] = sentence_list
            except Exception as e:
                print(f'加载怪话文件 {filename} 失败: {e}')
    
    for group_num in poke_trigger_groups:
        last_sentence = ''
        if group_num in sentence_list_dict and sentence_list_dict[group_num]:
            last_sentence = sentence_list_dict[group_num][-1]
        poke_cache[group_num] = {'text': last_sentence, 'time': 0, 'msg_time': 0}
        print(f'[怪话] 拍一拍缓存初始化，群 {group_num}，初始消息: {last_sentence[:20] if last_sentence else "(空)"}...')


def save_strange_words():
    """保存怪话数据"""
    os.makedirs('database/strangeWord', exist_ok=True)
    for group_num in sentence_list_dict:
        with open(f'database/strangeWord/{group_num}.txt', 'w', encoding='utf-8') as f:
            for sentence in sentence_list_dict[group_num]:
                f.write(sentence + '\n')
    print(f'[怪话] 已保存怪话数据，共 {len(sentence_list_dict)} 个群')


if scheduler:
    @scheduler.scheduled_job('cron', minute='15,45', misfire_grace_time=None)
    async def save_strange_words_task():
        save_strange_words()


poke_notice = on_notice(priority=5, block=False)


@poke_notice.handle()
async def handle_poke(bot: Bot, event: PokeNotifyEvent):
    """处理拍一拍事件，触发怪话回复"""
    if event.sub_type != 'poke':
        return
    
    if not event.group_id:
        return
    
    if event.group_id not in poke_trigger_groups:
        return
    
    if event.target_id != event.self_id:
        return
    
    group_num = event.group_id
    poke_time = event.time
    
    cached = poke_cache.get(group_num)
    if not cached:
        print(f'[怪话] 拍一拍触发，群 {group_num} 没有缓存的消息')
        return
    
    last_msg_time = cached.get('msg_time', 0)
    last_respond_time = poke_last_respond_time.get(group_num, 0)
    
    if last_respond_time > last_msg_time:
        print(f'[怪话] 拍一拍触发，群 {group_num} 在上次响应后无新消息，跳过')
        return
    
    text = cached.get('text', '')
    if not text:
        text = poke_last_reply.get(group_num, '')
        if not text:
            print(f'[怪话] 拍一拍触发，群 {group_num} 缓存消息为空')
            return
        print(f'[怪话] 拍一拍触发，使用上一句回复: {text[:50]}...')
    else:
        print(f'[怪话] 拍一拍触发，获取到消息: {text[:50]}...')
    
    poke_last_respond_time[group_num] = poke_time
    
    try:
        last_bot_reply = poke_last_reply.get(group_num, '')
        if allow_model and random.random() < 0.5:
            reply = await get_sentence_advance(group_num, text, exclude=last_bot_reply)
        else:
            reply = get_random_sentence(group_num)
        
        poke_last_reply[group_num] = reply
        poke_cache[group_num] = {'text': reply, 'time': poke_time, 'msg_time': poke_time}
        
        await bot.send_group_msg(group_id=group_num, message=reply)
        
    except Exception as e:
        import traceback
        print(f'[怪话] 拍一拍处理失败: {e}')
        traceback.print_exc()
