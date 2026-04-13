"""
随机化功能插件 - NoneBot2 版本
支持 Roll 点、选择、判断等功能
"""

import re
import time
import random
from functools import reduce
from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters import Message
from nonebot.typing import T_State

from multi_platform import get_platform_user_id


roll_cmd = on_command("roll", priority=5, block=True)
rollx_cmd = on_command("rollx", priority=5, block=True)
rollf_cmd = on_command("rollf", priority=5, block=True)
choose_cmd = on_command("选择", priority=5, block=True)
judge_cmd = on_command("判断", priority=5, block=True)


@roll_cmd.handle()
async def handle_roll(args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    dice_info = re.search(r'(\d{1,4})d((\d{1,12})-(\d{1,12})|\d{1,12})', stripped_arg)
    if dice_info:
        result, _ = run_dice(dice_info, 'n')
        await roll_cmd.finish(f'Roll点结果为：{result}')
    else:
        await roll_cmd.finish('Roll点格式不正确^ ^\n示例：!roll 1d100')


@rollx_cmd.handle()
async def handle_rollx(args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    dice_info = re.search(r'(\d)d((\d{1,12})-(\d{1,12})|\d{1,12})', stripped_arg)
    if dice_info:
        result, num_list = run_dice(dice_info, 'n')
        if num_list:
            num_list_str = reduce(lambda a, b: str(a) + '+' + str(b), num_list)
            await rollx_cmd.finish(f'Roll点结果为：{num_list_str}={result}')
        else:
            await rollx_cmd.finish(f'Roll点结果为：{result}')
    else:
        await rollx_cmd.finish('Rollx格式不正确^ ^\n示例：!rollx 5d100')


@rollf_cmd.handle()
async def handle_rollf(args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip()
    regex = r'(\d{1,4})d((\d{1,12}\.\d{1,12}|\d{1,12})-(\d{1,12}\.\d{1,12}|\d{1,12})|(\d{1,12}\.\d{1,12}|\d{1,12}))'
    dice_info = re.search(regex, stripped_arg)
    if dice_info:
        result, _ = run_dice(dice_info, 'f')
        await rollf_cmd.finish(f'Roll点结果为：{result:.2f}')
    else:
        await rollf_cmd.finish('Rollf格式不正确^ ^\n示例：!rollf 2d5.5')


def run_dice(dice_info, stage):
    amount = int(dice_info.group(1))
    point_range = dice_info.group(2)
    min_point = 1
    result = 0
    num_list = []

    if stage == 'f':
        min_point = 0
        if '-' in point_range:
            min_point = float(dice_info.group(3))
            max_point = float(dice_info.group(4))
            if max_point - min_point < 0:
                return result, num_list
        else:
            max_point = float(dice_info.group(2))

        while amount:
            result += random.uniform(min_point, max_point)
            amount -= 1

        return result, num_list

    else:
        if '-' in point_range:
            min_point = int(dice_info.group(3))
            max_point = int(dice_info.group(4))
            if max_point - min_point < 0:
                return 0, num_list
        else:
            max_point = int(dice_info.group(2))

        while amount:
            num = random.randint(min_point, max_point)
            result += num
            if amount <= 9:
                num_list.append(num)
            amount -= 1

        return result, num_list


@choose_cmd.handle()
async def handle_choose(state: T_State, args: Message = CommandArg()):
    arg_list = args.extract_plain_text().strip().split(' ')
    if not arg_list or not arg_list[0]:
        await choose_cmd.finish('未输入选项^ ^')
        return
    
    user_id = state.get('_user_id') or 'unknown'
    hashing_str = str(arg_list) + str(user_id) + time.strftime("%Y-%m-%d", time.localtime()) + 'confounding'
    chosen = arg_list[hash(hashing_str) % len(arg_list)]
    await choose_cmd.finish(f'选择：{chosen}')


@judge_cmd.handle()
async def handle_judge(state: T_State, args: Message = CommandArg()):
    stripped_arg = args.extract_plain_text().strip().replace('\n', '')
    if not stripped_arg:
        await judge_cmd.finish('未输入判断内容^ ^')
        return
    
    answer = ['是', '否']
    user_id = state.get('_user_id') or 'unknown'
    hashing_str = stripped_arg + str(user_id) + time.strftime("%Y-%m-%d", time.localtime()) + 'confounding'
    result = answer[hash(hashing_str) % 2]
    await judge_cmd.finish(f'{stripped_arg}\n判断：{result}')
