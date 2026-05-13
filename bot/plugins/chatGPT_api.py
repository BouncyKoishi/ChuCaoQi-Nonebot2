import datetime
import re
import os
import time
import json

import dbConnection.chat as db
from kusa_base import is_super_admin, plugin_config, send_log
from reloader import db_command as on_command
from nonebot.adapters import Bot, Event
from nonebot.params import CommandArg
from nonebot.adapters import Message
from utils import nameDetailSplit, imgUrlTobase64
from services.chat_service import ChatService
from nonebot_plugin_apscheduler import scheduler
from multi_platform import (
    get_user_id,
    is_group_message,
    send_reply,
    send_finish,
)

HISTORY_PATH = u"chatHistory/"

from sensitive_filter import get_sensitive_filter


chat_cmd = on_command('chat', priority=5, block=True)

@chat_cmd.handle()
async def handle_chat(bot: Bot, event: Event, args: Message = CommandArg()):
    user_id = await get_user_id(event, auto_create=True)
    
    if not await permissionCheck(event, 'chat'):
        return
    
    content = await getChatContent(event, args)
    await send_reply(chat_cmd, "已开启新对话，等待回复……")
    reply = await chat(user_id, content, isNewConversation=True)
    await send_finish(chat_cmd, reply)


chat5_cmd = on_command('chat5', aliases={'chat4'}, priority=5, block=True)

@chat5_cmd.handle()
async def handle_chat5(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    if not await permissionCheck(event, 'model'):
        return
    user_id = await get_user_id(event, auto_create=True)
    content = await getChatContent(event, args)
    await send_reply(chat5_cmd, "已开启新对话，等待回复……")
    reply = await chat(user_id, content, isNewConversation=True, useGPT5=True)
    await send_finish(chat5_cmd, reply)


chatn_cmd = on_command('chatn', priority=5, block=True)

@chatn_cmd.handle()
async def handle_chatn(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    user_id = await get_user_id(event, auto_create=True)
    content = await getChatContent(event, args)
    await send_reply(chatn_cmd, "已开启新对话，等待回复……")
    reply = await chat(user_id, content, isNewConversation=True, useDefaultRole=True)
    await send_finish(chatn_cmd, reply)


chatn5_cmd = on_command('chatn5', aliases={'chatn4'}, priority=5, block=True)

@chatn5_cmd.handle()
async def handle_chatn5(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    if not await permissionCheck(event, 'model'):
        return
    user_id = await get_user_id(event, auto_create=True)
    content = await getChatContent(event, args)
    await send_reply(chatn5_cmd, "已开启新对话，等待回复……")
    reply = await chat(user_id, content, isNewConversation=True, useDefaultRole=True, useGPT5=True)
    await send_finish(chatn5_cmd, reply)


chatc_cmd = on_command('chatc', priority=5, block=True)

@chatc_cmd.handle()
async def handle_chatc(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    user_id = await get_user_id(event, auto_create=True)
    content = await getChatContent(event, args)
    await send_reply(chatc_cmd, "继续进行对话，等待回复……")
    reply = await chat(user_id, content, isNewConversation=False)
    await send_finish(chatc_cmd, reply)


chatc5_cmd = on_command('chatc5', aliases={'chatc4'}, priority=5, block=True)

@chatc5_cmd.handle()
async def handle_chatc5(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    if not await permissionCheck(event, 'model'):
        return
    user_id = await get_user_id(event, auto_create=True)
    content = await getChatContent(event, args)
    await send_reply(chatc5_cmd, "继续进行对话，等待回复……")
    reply = await chat(user_id, content, isNewConversation=False, useGPT5=True)
    await send_finish(chatc5_cmd, reply)


chatb_cmd = on_command('chatb', priority=5, block=True)

@chatb_cmd.handle()
async def handle_chatb(bot: Bot, event: Event):
    if not await permissionCheck(event, 'chat'):
        return
    user_id = await get_user_id(event, auto_create=True)
    lastMessage = await undo(user_id)
    if lastMessage is None:
        await send_finish(chatb_cmd, "没有可撤回的对话。")
        return
    await send_finish(chatb_cmd, "已撤回最后一轮对话。")


chatr_cmd = on_command('chatr', priority=5, block=True)

@chatr_cmd.handle()
async def handle_chatr(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    user_id = await get_user_id(event, auto_create=True)
    content = await getChatContent(event, args)
    lastMessage = await undo(user_id)
    if lastMessage is None:
        await send_finish(chatr_cmd, "没有可撤回的对话，无法重新生成。")
        return
    inputContent = content if args.extract_plain_text() else lastMessage['content']
    await send_reply(chatr_cmd, "已撤回最后一轮对话，重新生成回复中……")
    reply = await chat(user_id, inputContent, isNewConversation=False)
    await send_finish(chatr_cmd, reply)


chatr5_cmd = on_command('chatr5', aliases={'chatr4'}, priority=5, block=True)

@chatr5_cmd.handle()
async def handle_chatr5(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    if not await permissionCheck(event, 'model'):
        return
    user_id = await get_user_id(event, auto_create=True)
    content = await getChatContent(event, args)
    lastMessage = await undo(user_id)
    if lastMessage is None:
        await send_finish(chatr5_cmd, "没有可撤回的对话，无法重新生成。")
        return
    inputContent = content if args.extract_plain_text() else lastMessage['content']
    await send_reply(chatr5_cmd, "已撤回最后一轮对话，重新生成回复中……")
    reply = await chat(user_id, inputContent, isNewConversation=False, useGPT5=True)
    await send_finish(chatr5_cmd, reply)


chat_user_cmd = on_command('chat_user', priority=5, block=True)

@chat_user_cmd.handle()
async def handle_chat_user(bot: Bot, event: Event):
    user_id = await get_user_id(event, auto_create=True)
    chatUser = await db.getChatUser(user_id)
    if chatUser is None:
        await send_finish(chat_user_cmd, "你尚未激活大模型对话功能。")
        return

    output = f"你总计使用的token量: {chatUser.tokenUse}\n"
    output += f"当日token用量：{chatUser.todayTokenUse} / {int(chatUser.dailyTokenLimit)}\n"
    output += "在群聊内进行大模型对话无需权限。\n"
    output += f"你的进阶chat功能使用权限："
    output += f"私聊 " if chatUser.allowPrivate else ""
    output += f"角色切换 " if chatUser.allowRole else ""
    output += f"进阶模型 " if chatUser.allowAdvancedModel else ""
    output += f"\n当前使用模型：{chatUser.chosenModel}\n"

    if chatUser.allowRole:
        nowRole = await db.getChatRoleById(chatUser.chosenRoleId)
        createdRoleList = await db.getChatRoleList(user_id)
        publicRoleList = await db.getPublicRoleList()
        if nowRole:
            output += f"\n当前使用角色：{nowRole.name}"
        if createdRoleList:
            output += f"\n当前可选择的自建角色列表："
            for role in createdRoleList:
                output += f"{role.name} "
        if publicRoleList:
            output += f"\n当前可选择的公共角色列表："
            for role in publicRoleList:
                output += f"{role.name} "
    await send_finish(chat_user_cmd, output)


chat_user_update_cmd = on_command('chat_user_update', priority=5, block=True)

@chat_user_update_cmd.handle()
async def handle_chat_user_update(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'admin'):
        return
    strippedText = args.extract_plain_text().strip()
    if strippedText is None or strippedText == "":
        await send_finish(chat_user_update_cmd, '需要指定用户标识！')
        return
    
    # 提取数字标识符
    identifier = int(''.join([c for c in strippedText if c.isdigit()]))
    params = strippedText.split('-')[1] if '-' in strippedText else ""
    
    # 使用通用函数解析用户标识符
    from kusa_base import parse_user_identifier
    target_user_id = await parse_user_identifier(identifier)
    
    if target_user_id:
        await db.updateChatUser(target_user_id, params)
        await send_finish(chat_user_update_cmd, f"已更新用户{identifier}的chat权限")
    else:
        await send_finish(chat_user_update_cmd, f"未找到用户{identifier}")


role_detail_cmd = on_command('role_detail', priority=5, block=True)

@role_detail_cmd.handle()
async def handle_role_detail(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, "role"):
        return
    user_id = await get_user_id(event, auto_create=True)
    strippedText = args.extract_plain_text().strip()
    
    role = await db.getChatRole(user_id, strippedText, True)
    if role is None:
        await send_finish(role_detail_cmd, "无相关该角色信息（无法查看他人的私人角色）。")
        return
    await send_finish(role_detail_cmd, role.detail)


role_change_cmd = on_command('role_change', priority=5, block=True)

@role_change_cmd.handle()
async def handle_role_change(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, "role"):
        return
    user_id = await get_user_id(event, auto_create=True)
    strippedText = args.extract_plain_text().strip()
    
    success = await db.changeUsingRole(user_id, strippedText)
    if not success:
        await send_finish(role_change_cmd, "无相关角色信息（无法切换到他人的私人角色）。")
    else:
        strippedText = "default" if not strippedText else strippedText
        await send_finish(role_change_cmd, f"已切换到{strippedText}角色")


role_update_cmd = on_command('role_update', priority=5, block=True)

@role_update_cmd.handle()
async def handle_role_update(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, "role"):
        return
    user_id = await get_user_id(event, auto_create=True)
    strippedText = args.extract_plain_text().strip()
    
    isPublicRole = strippedText.startswith("-p ") or strippedText.startswith("-public ")
    strippedText = re.sub("^(-p|-public) ", "", strippedText)
    name, detail = nameDetailSplit(strippedText)
    if not name:
        await send_finish(role_update_cmd, '至少需要一个角色名称！')
        return
    if isPublicRole:
        publicRoleList = await db.getPublicRoleList()
        for role in publicRoleList:
            if role.name == name:
                await send_finish(role_update_cmd, "已经有一个公共角色叫这个名称了！")
                return
    await db.updateRoleDetail(user_id, name, detail, isPublicRole)
    await send_finish(role_update_cmd, f"已更新角色 {name} 的描述信息")


role_delete_cmd = on_command('role_delete', priority=5, block=True)

@role_delete_cmd.handle()
async def handle_role_delete(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, "role"):
        return
    user_id = await get_user_id(event, auto_create=True)
    strippedText = args.extract_plain_text().strip()
    
    if not strippedText:
        await send_finish(role_delete_cmd, '需要角色名称！')
        return
    role = await db.getChatRole(user_id, strippedText, False)
    if role is None:
        await send_finish(role_delete_cmd, "无相关角色信息，或者你没有权限删除该角色。")
        return
    chatUsersUsingThisRole = await db.getChatUserListByNowRoleId(role.id)
    for chatUser in chatUsersUsingThisRole:
        if chatUser.user:
            await db.changeUsingRole(chatUser.user_id, None)
    await db.deleteRole(role)
    await send_finish(role_delete_cmd, f"已删除角色 {strippedText}")


model_change_cmd = on_command('model_change', priority=5, block=True)

@model_change_cmd.handle()
async def handle_model_change(bot: Bot, event: Event, args: Message = CommandArg()):
    user_id = await get_user_id(event, auto_create=True)
    strippedText = args.extract_plain_text().strip()
    
    if strippedText:
        if "gpt" in strippedText:
            if strippedText in ["gpt-5", "gpt5"]:
                if not await permissionCheck(event, "model"):
                    await send_finish(model_change_cmd, "需要高级模型权限！")
                    return
                newModel = "gpt-5"
            else:
                newModel = "gpt-5-mini"
        elif "gemini" in strippedText:
            if not await permissionCheck(event, "admin"):
                return
            if "pro" in strippedText:
                newModel = "gemini-2.5-pro"
            else:
                newModel = "gemini-2.5-flash"
        elif "deepseek-r" in strippedText:
            newModel = "deepseek-reasoner"
        elif "deepseek" in strippedText:
            newModel = "deepseek-chat"
        else:
            newModel = strippedText
            await send_reply(model_change_cmd, "注意，你定义的模型名称不在预设列表，chat可能报错！")
    else:
        newModel = "deepseek-chat"
    
    await db.updateUsingModel(user_id, newModel)
    output = f"已切换到{newModel}模型"
    await send_finish(model_change_cmd, output)


chat_save_cmd = on_command('chat_save', aliases={'save_conversation'}, priority=5, block=True)

@chat_save_cmd.handle()
async def handle_chat_save(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    user_id = await get_user_id(event, auto_create=True)
    strippedArg = args.extract_plain_text().strip()
    history = await readDefaultConversation(user_id)
    fileName = re.sub(r'[\\/:*?"<>|]', '', strippedArg)
    if fileName == "":
        timeStr = time.strftime('%Y%m%d%H%M', time.localtime())
        systemPrompt = history[0] if history and len(history) > 0 and history[0]['role'] == 'system' else None
        roleName = systemPrompt.get('botRoleName', '') if systemPrompt else ''
        fileName = f"{roleName}_{timeStr}" if roleName else timeStr
    saveConversation(user_id, fileName, history)
    await send_finish(chat_save_cmd, f"已保存当前对话记录，记录名称为 {fileName} ")


chat_load_cmd = on_command('chat_load', aliases={'load_conversation'}, priority=5, block=True)

@chat_load_cmd.handle()
async def handle_chat_load(bot: Bot, event: Event, args: Message = CommandArg()):
    if not await permissionCheck(event, 'chat'):
        return
    user_id = await get_user_id(event, auto_create=True)
    arg_text = args.extract_plain_text().strip()

    loadableFiles = []
    for file in os.listdir(HISTORY_PATH):
        if file.startswith(f"{user_id}_") and file.endswith(".json"):
            file_path = os.path.join(HISTORY_PATH, file)
            display_name = file[len(f"{user_id}_"):-5]
            mtime = os.path.getmtime(file_path)
            loadableFiles.append((display_name, mtime))
    if not loadableFiles:
        await send_finish(chat_load_cmd, "没有可加载的对话记录。")
        return
    loadableFiles.sort(key=lambda x: x[1], reverse=True)

    loadableFileNames = [file[0] for file in loadableFiles]

    if arg_text.isdigit():
        idx = int(arg_text) - 1
        if 0 <= idx < len(loadableFileNames):
            fileName = loadableFileNames[idx]
            history = readConversation(user_id, fileName)
            if history:
                saveDefaultConversation(user_id, history)
                
                preview = f"已加载对话记录：{fileName}\n\n"
                
                conversation_messages = [msg for msg in history if msg['role'] != 'system']
                
                if len(conversation_messages) >= 2:
                    preview += "上一轮对话内容：\n"
                    for msg in conversation_messages[-2:]:
                        role_display = "你" if msg['role'] == 'user' else "AI"
                        content = msg['content']
                        
                        if isinstance(content, list):
                            content_text = ""
                            for item in content:
                                if isinstance(item, dict) and 'text' in item:
                                    content_text += item['text']
                        else:
                            content_text = str(content)
                        
                        if len(content_text) > 200:
                            content_text = content_text[:200] + "..."
                        
                        preview += f"{role_display}：{content_text}\n"
                elif len(conversation_messages) == 1:
                    msg = conversation_messages[0]
                    content = msg['content']
                    if isinstance(content, list):
                        content_text = ""
                        for item in content:
                            if isinstance(item, dict) and 'text' in item:
                                content_text += item['text']
                    else:
                        content_text = str(content)
                    
                    if len(content_text) > 200:
                        content_text = content_text[:200] + "..."
                    
                    preview += f"对话内容：{content_text}"
                else:
                    preview += "（对话记录为空）"
                
                await send_finish(chat_load_cmd, preview)
            else:
                await send_finish(chat_load_cmd, f"无法加载对话记录：{fileName}")
        else:
            await send_finish(chat_load_cmd, f"序号无效，请输入 1-{len(loadableFileNames)} 之间的数字")
        return

    selectListStr = "请选择要加载的对话记录(输入序号)：\n"
    for idx, fileName in enumerate(loadableFiles):
        selectListStr += f"{idx + 1}. {fileName}\n"
        if idx >= 9:
            break

    await send_finish(chat_load_cmd, selectListStr + "\n(请使用 !chat_load [序号] 来选择)")


chat_help_cmd = on_command('chat_help', priority=5, block=True)

@chat_help_cmd.handle()
async def handle_chat_help(bot: Bot, event: Event):
    user_id = await get_user_id(event, auto_create=True)
    chatUser = await db.getChatUser(user_id)
    if chatUser is None:
        await send_finish(chat_help_cmd, "你尚未激活大模型对话功能。可使用!chat开启一个对话以激活。")
        return

    output = "chat_user: 查看chat权限等相关信息\nchat: 开始一个新对话"
    output += "\nchatc: 继续上一轮对话\nchatb: 撤回上一轮对话\nchatr: 撤回上一轮对话并重新生成"
    output += "\nchat_save: 手动保存当前对话记录"
    output += "\nchat_load: 加载已保存的对话记录文件"
    if chatUser.allowRole:
        output += "\nchatn: 无视当前角色设定，开始一个新对话"
        output += ("\nrole_change: 切换当前角色\nrole_detail: 查看角色描述信息\n"
                   "role_update: 新增/更新角色描述信息(-g 设置为全局角色)\nrole_delete: 删除角色")
    if chatUser.allowAdvancedModel:
        output += "\nmodel_change: 切换语言模型（deepseek/deepseek-r/gpt-5/gpt-5-mini）"
    else:
        output += "\nmodel_change: 切换语言模型（deepseek/deepseek-r/gpt-5-mini）"
    if await is_super_admin(user_id):
        output += "\nchat_user_update: 更改指定人员chat权限(-p私聊 -r角色 -m进阶模型 -v更高上限 -u无限使用)"
    output += "\n\n当前默认使用的模型：deepseek-chat\n对话使用的是收费api，请勿滥用！"
    await send_finish(chat_help_cmd, output)


async def getChatContent(event: Event, args: Message):
    inputText = args.extract_plain_text()
    userContent = [{"type": "text", "text": inputText}]
    return userContent


async def chat(user_id, content, isNewConversation: bool, useDefaultRole=False, useGPT5=False, retryCount=0):
    chatUser = await db.getChatUser(user_id)
    
    model = "gpt-5" if useGPT5 else chatUser.chosenModel
    roleId = 0 if useDefaultRole else chatUser.chosenRoleId
    history = await getNewConversation(user_id, roleId) if isNewConversation else await readDefaultConversation(user_id)
    history.append({"role": "user", "content": content})

    try:
        reply, tokenUsage = await getChatReply(model, history)
        reply = get_sensitive_filter().filter(reply)
        await db.addTokenUsage(chatUser, model, tokenUsage)
        saveDefaultConversation(user_id, history)

        if isNewConversation:
            role = await db.getChatRoleById(roleId)
            roleName = role.name if role and roleId != 0 else ""
        else:
            systemPrompt = history[0] if history and len(history) > 0 and history[0]['role'] == 'system' else None
            roleName = systemPrompt.get('botRoleName', '') if systemPrompt else ""
        roleSign = f"\nRole: {roleName}" if roleName else ""
        modelSign = "(GPT-5)" if model == "gpt-5" else ("(deepseek)" if "deepseek" in model else "")
        tokenSign = f"\nTokens{modelSign}: {tokenUsage}"
        return reply + "\n" + roleSign + tokenSign
    except Exception as e:
        reason = str(e) if str(e) else "Timeout"
        await send_log(f"user: {user_id} 的 {model} api调用出现异常，异常原因为：{reason}\nRetry次数：{retryCount}")
        print(f"Catch Time: {datetime.datetime.now().timestamp()}")
        if retryCount < 1:
            return await chat(user_id, content, isNewConversation, useDefaultRole, useGPT5, retryCount + 1)
        else:
            return "对话出错了，请稍后再试。"


async def getChatReply(model, history):
    startTimeStamp = datetime.datetime.now().timestamp()
    print(f"Start Time: {startTimeStamp}")
    reply, tokenUsage, response_dict = await ChatService.get_chat_reply(model, history)
    endTimeStamp = datetime.datetime.now().timestamp()
    print(f"Response Time: {endTimeStamp}, Used Time: {endTimeStamp - startTimeStamp}")
    print(f"Response: {reply}")
    history.append({"role": "assistant", "content": reply})
    if "deepseek" in model and 'reasoning_content' in response_dict['choices'][0]['message']:
        print(f"Reasoning Content:{response_dict['choices'][0]['message']['reasoning_content']}")
    finishReason = response_dict['choices'][0]['finish_reason']
    if finishReason != "stop":
        print(f"Finish Reason: {finishReason}")
    return reply, tokenUsage


async def undo(user_id):
    history = await readDefaultConversation(user_id)
    if len(history) < 2:
        return None
    history.pop()
    latestWord = history.pop()
    saveDefaultConversation(user_id, history)
    return latestWord


async def getNewConversation(user_id, roleId):
    history = await readDefaultConversation(user_id, forceToGetResult=False)
    if history and len(history) > 0:
        saveConversation(user_id, '[上个对话自动存档]', history)
    role = await db.getChatRoleById(roleId)
    if not role:
        return []
    if roleId == 0:
        if not role.detail:
            return []
        return [{"role": "system", "content": [{"type": "text", "text": role.detail}]}]
    return [{"role": "system", "botRoleName": role.name, "content": [{"type": "text", "text": role.detail}]}]


async def readDefaultConversation(user_id, forceToGetResult=True):
    result = readConversation(user_id, None)
    if result is None and forceToGetResult:
        chatUser = await db.getChatUser(user_id)
        return await getNewConversation(user_id, chatUser.chosenRoleId)
    return result


def saveDefaultConversation(user_id, history):
    saveConversation(user_id, None, history)


def readConversation(user_id, fileName):
    fullFileName = f"{user_id}_{fileName}" if fileName else f"{user_id}"
    savePath = HISTORY_PATH + fullFileName + ".json"
    if not os.path.exists(savePath):
        return None
    with open(savePath, encoding="utf-8") as f:
        return json.load(f)


def saveConversation(user_id, fileName, history):
    fullFileName = f"{user_id}_{fileName}" if fileName else f"{user_id}"
    savePath = HISTORY_PATH + fullFileName + ".json"
    with open(savePath, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)


async def permissionCheck(event: Event, checker: str):
    user_id = await get_user_id(event, auto_create=True)
    
    if checker == 'admin':
        return await is_super_admin(user_id)

    isGroupCall = is_group_message(event)
    chatUser = await db.getChatUser(user_id)
    
    if chatUser is None:
        await db.updateChatUser(user_id, '')
        chatUser = await db.getChatUser(user_id)

    if checker == 'chat':
        if 0 < chatUser.dailyTokenLimit <= chatUser.todayTokenUse:
            return False
        if not isGroupCall:
            return chatUser.allowPrivate
        return True
    if checker == 'role':
        return chatUser.allowRole
    if checker == 'model':
        return chatUser.allowAdvancedModel
    return False


if scheduler:
    @scheduler.scheduled_job('cron', hour=3, minute=1, misfire_grace_time=None)
    async def resetTodayTokenUseRunner():
        await db.resetTodayTokenUse()
        print("已重置所有用户的todayTokenUse")
