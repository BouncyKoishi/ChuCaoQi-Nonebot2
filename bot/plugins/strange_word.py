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
- gh_auto_freeze - 启用/禁用自动怪话
- #怪话 - 说点怪话指令的回复版本
"""

import asyncio
import math
import random
import os
import re
import time
import traceback
from typing import Optional
from collections import deque
from nonebot import on_command, on_message, on_notice, get_bot
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, PokeNotifyEvent, Bot
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot import get_driver
from nonebot_plugin_apscheduler import scheduler

from kusa_base import plugin_config
from .reply_commands import reply_text_command
from services.chat_service import ChatService
from sensitive_filter import get_sensitive_filter
from utils import get_group_member_nickname

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

# 自动怪话配置（参考MaiBot的talk_value和willingness机制）
auto_reply_config = plugin_config.get('guaihua', {}).get('autoReply', {})
auto_reply_groups = auto_reply_config.get('groups', [])
auto_reply_talk_value = auto_reply_config.get('talkValue', 0.1)
auto_reply_min_msg = auto_reply_config.get('minMsgCount', 10)
auto_reply_cooldown = auto_reply_config.get('cooldown', 120)
auto_reply_max_context = auto_reply_config.get('maxContext', 10)
auto_reply_sample_size = auto_reply_config.get('sampleSize', 30)
auto_reply_enabled = True


class GroupChatBuffer:
    """群聊消息缓冲区，参考MaiBot的HeartFlow设计"""
    def __init__(self, max_size=30):
        self.messages = deque(maxlen=max_size)
        self.last_reply_time = 0
        self.msg_count_since_reply = 0
        self.willingness = auto_reply_talk_value

    def add(self, name, content, timestamp):
        self.messages.append({'name': name, 'content': content, 'time': timestamp})
        self.msg_count_since_reply += 1

    def on_replied(self):
        self.last_reply_time = time.time()
        self.msg_count_since_reply = 0
        self.willingness = max(0.05, self.willingness * 0.4)

    def recover_willingness(self):
        self.willingness = min(auto_reply_talk_value, self.willingness + 0.01)


group_buffers = {}
recent_used = deque(maxlen=20)


def update_poke_cache(group_num: int, text: str, timestamp: int):
    if group_num in poke_trigger_groups and text:
        poke_cache[group_num] = {'text': text, 'time': timestamp, 'msg_time': timestamp}
        poke_last_reply[group_num] = text


def get_sentence_list(group_num: int) -> list:
    return sentence_list_dict.get(group_num) or sentence_list_dict.get(default_group_num, [])


def get_random_sentence(group_num: int) -> str:
    sentence_list = get_sentence_list(group_num)
    if not sentence_list:
        return "目前还没有怪话库存^ ^"
    sf = get_sensitive_filter()
    for _ in range(min(len(sentence_list), 20)):
        sentence = random.choice(sentence_list)
        if not sf.contains(sentence):
            return sentence
    return "目前还没有怪话库存^ ^"


def is_valid_for_model(sentence: str) -> bool:
    if len(sentence) <= 2:
        return False
    if '[CQ:' in sentence:
        return False
    if re.match(r'^[\s!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|`~]*$', sentence):
        return False
    return True


def get_model_sentence_list(group_num: int) -> list:
    return [s for s in get_sentence_list(group_num) if is_valid_for_model(s)]


def is_valid_cache_message(event: GroupMessageEvent) -> tuple[bool, str, int]:
    for seg in event.get_message():
        if seg.type in ('image', 'at', 'face', 'share', 'music', 'video', 'record', 'file'):
            return False, '', 0
    msg = event.get_plaintext()
    if not msg or msg.startswith('!') or msg.startswith('#'):
        return False, '', 0
    return True, msg, event.time


def match_strange_word(reply: str, model_list: list) -> Optional[str]:
    """将LLM输出匹配到怪话库，失败返回None"""
    if reply in model_list:
        return reply
    # 模糊匹配
    reply_stripped = reply.strip('。！？~～，,')
    for s in model_list:
        if s == reply_stripped or reply_stripped in s or s in reply_stripped:
            return s
    return None


async def get_sentence_advance(group_num: int, input_str: str, exclude: str = '') -> str:
    """使用AI从怪话库中选择最合适的回复（基于单条输入）"""
    model_sentence_list = get_model_sentence_list(group_num)
    if not model_sentence_list:
        return get_random_sentence(group_num)

    available = [s for s in model_sentence_list if s != exclude] if exclude else model_sentence_list
    if len(available) < 10:
        available = model_sentence_list

    system_prompt = '你需要从以下怪话中选择一句语义最适宜的话来回答用户说的内容。你的回答内容只能是怪话列表中的某一句话，不包括任何其它内容。\n'
    user_prompt = f"用户发言：{input_str}\n\n怪话列表：\n"
    for _ in range(15):
        user_prompt += random.choice(available) + '\n'

    prompt = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    reply, _, _ = await ChatService.get_chat_reply("deepseek-chat", prompt)

    matched = match_strange_word(reply, model_sentence_list)
    if not matched:
        print(f'输出内容为:"{reply}" 匹配怪话库失败，输出随机怪话')
        return get_random_sentence(group_num)

    if get_sensitive_filter().contains(matched):
        print(f'[怪话] AI选中怪话含敏感词，替换为随机怪话')
        return get_random_sentence(group_num)

    return matched


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
                # 不足3句时用随机怪话补齐
                while len(reply_list) < 3:
                    reply_list.append(random.choice(model_sentence_list))
                return reply_list[:3]
        except Exception as e:
            print(f'解析输出内容失败，错误信息：{e}')

    print(f'输出内容为:"{reply}" 基本格式匹配失败，输出随机怪话')
    return [get_random_sentence(group_num) for _ in range(3)]


def should_auto_reply(group_id: int) -> bool:
    """判断是否应该自动回复怪话"""
    if not auto_reply_enabled:
        return False
    buf = group_buffers.get(group_id)
    if not buf:
        return False
    if buf.msg_count_since_reply < auto_reply_min_msg:
        return False
    if time.time() - buf.last_reply_time < auto_reply_cooldown:
        return False
    return random.random() < buf.willingness


async def pick_strange_word_by_context(group_id: int) -> Optional[str]:
    """基于群聊上下文，用AI从怪话库中选择最合适的怪话。返回怪话原文或None（沉默）"""
    buf = group_buffers.get(group_id)
    model_list = get_model_sentence_list(group_id)
    if not buf or not buf.messages or not model_list:
        return None

    available = [s for s in model_list if s not in recent_used]
    if len(available) < 10:
        available = model_list

    recent = list(buf.messages)[-auto_reply_max_context:]
    context_text = "\n".join(f"{m['name']}: {m['content']}" for m in recent)
    candidates = random.sample(available, min(auto_reply_sample_size, len(available)))
    candidate_text = "\n".join(f"- {s}" for s in candidates)

    system_prompt = (
        '你是一个群聊观察者。根据最近的群聊内容，从候选怪话中选一句最合适接话的。'
        '你的回答只能是候选怪话中的某一句原话，不包括任何其它内容。'
        '你不能复读群友说过的话，必须从候选怪话中选择。'
        '如果没有合适的怪话可以接，请回复"无"。'
    )
    prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"最近群聊：\n{context_text}\n\n候选怪话：\n{candidate_text}"}
    ]

    try:
        reply, _, _ = await ChatService.get_chat_reply("deepseek-chat", prompt)
    except Exception as e:
        print(f'[怪话] 自动选句API调用失败: {e}')
        return None

    reply = reply.strip()
    if reply == "无":
        print(f'[怪话] AI判断当前无合适怪话，选择沉默')
        return None

    matched = match_strange_word(reply, model_list)
    if not matched:
        print(f'[怪话] AI输出"{reply}"匹配怪话库失败，沉默')
        return None

    if get_sensitive_filter().contains(matched):
        print(f'[怪话] AI选中怪话含敏感词，沉默')
        return None

    return matched


async def send_auto_reply(bot: Bot, group_num: int, reply: str, poke_time: int = 0):
    """发送自动怪话回复并更新所有状态"""
    recent_used.append(reply)
    poke_last_reply[group_num] = reply
    update_poke_cache(group_num, reply, poke_time or int(time.time()))
    buf = group_buffers.get(group_num)
    if buf:
        buf.on_replied()
    await bot.send_group_msg(group_id=group_num, message=reply)


say_cmd = on_command("说点怪话", priority=5, block=True)
say_reverse_cmd = on_command("话怪点说", priority=5, block=True)
say_shuffle_cmd = on_command("说话怪点", aliases={"怪点说话"}, priority=5, block=True)
say_many_cmd = on_command("说些怪话", priority=5, block=True)
freeze_cmd = on_command("gh_receive_freeze", priority=5, block=True)
model_freeze_cmd = on_command("gh_model_freeze", priority=5, block=True)
auto_freeze_cmd = on_command("gh_auto_freeze", priority=5, block=True)


@reply_text_command('怪话')
async def 怪话_cmd(event, bot):
    if not hasattr(event, 'reply') or not event.reply:
        return 'Reply获取异常^ ^'
    text = event.reply.message.extract_plain_text().strip()
    if not text:
        return '暂不支持非文本格式怪话^ ^'
    group_num = getattr(event, 'group_id', default_group_num)
    if allow_model and random.random() < 0.8:
        reply = await get_sentence_advance(group_num, text)
    else:
        reply = get_random_sentence(group_num)
    update_poke_cache(group_num, reply, event.time)
    return reply


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
        if text in sentence_list_dict[group_num]:
            sentence_list_dict[group_num].remove(text)
            found = True
    if found:
        save_strange_words()
        return '已移除本句怪话'
    return '未查找到怪话'


@freeze_cmd.handle()
async def handle_freeze(event: MessageEvent):
    global receive_freeze
    receive_freeze = not receive_freeze
    await freeze_cmd.send(f'怪话接收已{"冻结" if receive_freeze else "解冻"}')


@model_freeze_cmd.handle()
async def handle_model_freeze(event: MessageEvent):
    global allow_model
    allow_model = not allow_model
    await model_freeze_cmd.send(f'大模型怪话已{"启用" if allow_model else "禁用"}')


@auto_freeze_cmd.handle()
async def handle_auto_freeze(event: MessageEvent):
    global auto_reply_enabled
    auto_reply_enabled = not auto_reply_enabled
    await auto_freeze_cmd.send(f'自动怪话已{"启用" if auto_reply_enabled else "禁用"}')


@say_cmd.handle()
async def handle_say(event: MessageEvent, args: Message = CommandArg()):
    group_num = getattr(event, 'group_id', default_group_num)
    stripped_text = args.extract_plain_text().strip()
    if stripped_text and allow_model and random.random() < 0.8:
        reply = await get_sentence_advance(group_num, stripped_text)
    else:
        reply = get_random_sentence(group_num)
    update_poke_cache(group_num, reply, event.time)
    await say_cmd.send(reply)


@say_reverse_cmd.handle()
async def handle_say_reverse(event: MessageEvent):
    msg = get_random_sentence(getattr(event, 'group_id', default_group_num))
    await say_reverse_cmd.send(msg if '[CQ:' in msg else msg[::-1])


@say_shuffle_cmd.handle()
async def handle_say_shuffle(event: MessageEvent):
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
    group_id = getattr(event, 'group_id', default_group_num)
    stripped_text = args.extract_plain_text().strip()
    if stripped_text and allow_model and random.random() < 0.8:
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
    if reply_list:
        update_poke_cache(group_id, reply_list[-1], event.time)


record_message_matcher = on_message(priority=5, block=False)


@record_message_matcher.handle()
async def record_message(event: MessageEvent):
    if not isinstance(event, GroupMessageEvent):
        return

    group_num = event.group_id
    user_id = event.user_id
    bot_self_id = int(bot_id) if (bot_id := getattr(event, 'self_id', None)) else None

    valid, msg, timestamp = is_valid_cache_message(event)

    # 拍一拍缓存更新
    if valid and group_num in poke_trigger_groups and user_id != bot_self_id:
        poke_cache[group_num] = {'text': msg, 'time': timestamp, 'msg_time': timestamp}
        print(f'[怪话] 缓存更新，群{group_num}: {msg[:30]}... (t={timestamp})')

    # 自动怪话触发
    if valid and group_num in auto_reply_groups and user_id != bot_self_id:
        if group_num not in group_buffers:
            group_buffers[group_num] = GroupChatBuffer()
        bot = get_bot()
        nickname = await get_group_member_nickname(bot, group_num, user_id)
        group_buffers[group_num].add(nickname, msg, timestamp)

        if should_auto_reply(group_num):
            try:
                reply = await pick_strange_word_by_context(group_num)
                if reply:
                    await send_auto_reply(bot, group_num, reply)
                    print(f'[怪话] 自动回复，群{group_num}: {reply[:30]}...')
                else:
                    group_buffers[group_num].msg_count_since_reply = max(
                        0, group_buffers[group_num].msg_count_since_reply - 3
                    )
            except Exception as e:
                print(f'[怪话] 自动回复失败: {e}')
                traceback.print_exc()

    # 怪话收集
    if group_num not in record_groups:
        return

    global sentence_list_dict

    for seg in event.get_message():
        if seg.type in ('image', 'at', 'face', 'share', 'music', 'video', 'record', 'file'):
            return

    if hasattr(event, 'reply') and event.reply:
        return
    if receive_freeze or not msg:
        return
    if msg in sentence_list_dict.get(group_num, []):
        return
    if '\n' in msg or user_id in not_record_members:
        return

    for word in not_record_words:
        if word in msg:
            return

    sf = get_sensitive_filter()
    if sf.contains(msg):
        hit = sf.find_first(msg)
        print(f'[怪话] 敏感词拦截，群{group_num}，来自{user_id}，命中:"{hit}"，原文:{msg[:30]}...')
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
    global sentence_list_dict
    folder_path = 'database/strangeWord'
    os.makedirs(folder_path, exist_ok=True)
    sf = get_sensitive_filter()

    for filename in os.listdir(folder_path):
        if not filename.endswith('.txt'):
            continue
        try:
            group_num = int(filename[:-4])
            sentence_list = []
            removed = 0
            with open(os.path.join(folder_path, filename), 'r', encoding='utf-8') as f:
                for sentence in f.readlines():
                    sentence = sentence.strip()
                    if sentence:
                        if sf.contains(sentence):
                            hit = sf.find_first(sentence)
                            print(f'[怪话] 启动清理敏感词，群{group_num}，命中:"{hit}"，原文:{sentence[:30]}...')
                            removed += 1
                        else:
                            sentence_list.append(sentence)
            if removed > 0:
                print(f'[怪话] 群{group_num}清理了 {removed} 条含敏感词的怪话')
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

    @scheduler.scheduled_job('interval', seconds=30)
    async def recover_willingness_task():
        for buf in group_buffers.values():
            buf.recover_willingness()


poke_notice = on_notice(priority=5, block=False)


@poke_notice.handle()
async def handle_poke(bot: Bot, event: PokeNotifyEvent):
    if event.sub_type != 'poke' or not event.group_id:
        return
    if event.group_id not in poke_trigger_groups:
        return
    if event.target_id != event.self_id:
        return

    group_num = event.group_id
    poke_time = event.time

    # 优先使用ChatBuffer上下文选句
    buf = group_buffers.get(group_num)
    if buf and buf.messages:
        last_respond_time = poke_last_respond_time.get(group_num, 0)
        if buf.last_reply_time > 0 and last_respond_time > buf.messages[-1]['time']:
            print(f'[怪话] 拍一拍触发，群 {group_num} 在上次响应后无新消息，跳过')
            return
        poke_last_respond_time[group_num] = poke_time
        try:
            reply = await pick_strange_word_by_context(group_num)
            if not reply:
                reply = get_random_sentence(group_num)
            await send_auto_reply(bot, group_num, reply, poke_time)
            print(f'[怪话] 拍一拍触发(ChatBuffer)，群 {group_num}: {reply[:30]}...')
        except Exception as e:
            print(f'[怪话] 拍一拍处理失败: {e}')
            traceback.print_exc()
        return

    # 回退到poke_cache单条消息
    cached = poke_cache.get(group_num)
    if not cached:
        print(f'[怪话] 拍一拍触发，群 {group_num} 没有缓存的消息')
        return

    last_respond_time = poke_last_respond_time.get(group_num, 0)
    if last_respond_time > cached.get('msg_time', 0):
        print(f'[怪话] 拍一拍触发，群 {group_num} 在上次响应后无新消息，跳过')
        return

    text = cached.get('text', '') or poke_last_reply.get(group_num, '')
    if not text:
        print(f'[怪话] 拍一拍触发，群 {group_num} 缓存消息为空')
        return

    poke_last_respond_time[group_num] = poke_time
    try:
        last_bot_reply = poke_last_reply.get(group_num, '')
        if allow_model and random.random() < 0.8:
            reply = await get_sentence_advance(group_num, text, exclude=last_bot_reply)
        else:
            reply = get_random_sentence(group_num)
        poke_last_reply[group_num] = reply
        update_poke_cache(group_num, reply, poke_time)
        await bot.send_group_msg(group_id=group_num, message=reply)
    except Exception as e:
        print(f'[怪话] 拍一拍处理失败: {e}')
        traceback.print_exc()
