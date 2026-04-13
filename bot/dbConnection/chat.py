from .models import ChatUser, ChatRole
from . import user as user_db


async def getChatUser(userId) -> ChatUser:
    return await ChatUser.filter(user_id=userId).first()


async def getChatRoleById(roleId: int) -> ChatRole:
    return await ChatRole.filter(id=roleId).first()


async def getChatUserListByNowRoleId(roleId: int):
    return await ChatUser.filter(chosenRoleId=roleId).all()


async def getChatRole(userId, roleName: str, allowPublic: bool) -> ChatRole:
    role = await ChatRole.filter(user_id=userId).filter(name=roleName).first()
    if role or not allowPublic:
        return role
    return await ChatRole.filter(isPublic=True).filter(name=roleName).first()


async def getChatRoleList(userId):
    return await ChatRole.filter(user_id=userId).all()


async def getPublicRoleList():
    return await ChatRole.filter(isPublic=True).all()


async def updateChatUser(userId, userMode: str):
    allowPrivate = True if 'p' in userMode else False
    allowRole = True if 'r' in userMode else False
    allowAdvancedModel = True if 'm' in userMode else False
    dailyTokenLimit = -1 if 'u' in userMode else (1000000 if 'v' in userMode else 10000)
    unifiedUser = await user_db.getUnifiedUser(userId)
    await ChatUser.update_or_create(user=unifiedUser, defaults={
        'allowPrivate': allowPrivate, 'allowRole': allowRole,
        'allowAdvancedModel': allowAdvancedModel, 'dailyTokenLimit': dailyTokenLimit
    })


async def updateUsingModel(userId, newModel):
    chatUser = await getChatUser(userId)
    chatUser.chosenModel = newModel
    await chatUser.save()


async def changeUsingRole(userId, roleName):
    chatUser = await getChatUser(userId)
    if not roleName:
        chatUser.chosenRoleId = 1
        await chatUser.save()
        return True
    role = await getChatRole(userId, roleName, True)
    if role:
        chatUser.chosenRoleId = role.id
        await chatUser.save()
        return True
    return False


async def updateRoleDetail(userId, roleName, detail, isPublic: bool):
    role = await getChatRole(userId, roleName, False)
    if role:
        role.detail = detail
        role.isPublic = isPublic
        await role.save()
    else:
        unifiedUser = await user_db.getUnifiedUser(userId)
        await ChatRole.create(user=unifiedUser, name=roleName, detail=detail, isPublic=isPublic)


async def deleteRole(role: ChatRole):
    await role.delete()


async def addTokenUsage(chatUser: ChatUser, model: str, tokenUse: int):
    tokenUse *= 5 if model == "gpt-5" else 1
    tokenUse = tokenUse // 5 if model == "gpt-5-nano" else tokenUse
    chatUser.tokenUse += tokenUse
    chatUser.todayTokenUse += tokenUse
    await chatUser.save()


async def resetTodayTokenUse():
    await ChatUser.all().update(todayTokenUse=0)
