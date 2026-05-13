from tortoise.models import Model
from tortoise.fields import CharField, IntField, BooleanField, FloatField, DatetimeField, ForeignKeyField, CASCADE


class UnifiedUser(Model):
    id = IntField(pk=True)
    realQQ = CharField(max_length=12, unique=True, null=True)
    qqbotOpenid = CharField(max_length=128, unique=True, null=True)
    webToken = CharField(max_length=64, unique=True, null=True)
    webTokenCreatedAt = DatetimeField(null=True)
    sessionToken = CharField(max_length=64, unique=True, null=True)
    sessionTokenExpiresAt = DatetimeField(null=True)
    isSuperAdmin = BooleanField(default=False)
    isRobot = BooleanField(default=False)
    relatedUserId = IntField(null=True)
    createdAt = DatetimeField(auto_now_add=True)
    updatedAt = DatetimeField(auto_now=True)


# class GroupMapping(Model):
#     """群组映射表 - 用于 OneBot + 官方QQ Bot 双平台运行场景，目前已禁用"""
#     id = IntField(pk=True)
#     onebotGroupId = CharField(max_length=12, unique=True, null=True)
#     qqbotGroupOpenid = CharField(max_length=128, unique=True, null=True)
#     groupName = CharField(max_length=64, null=True)
#     allowAutoBind = BooleanField(default=False)
#     createdAt = DatetimeField(auto_now_add=True)


class KusaBase(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="kusa_bases", null=True, source_field="userId", unique=True)
    name = CharField(max_length=32, null=True)
    title = CharField(max_length=32, null=True)
    kusa = IntField(default=0)
    advKusa = IntField(default=0)
    vipLevel = IntField(default=0)
    lastUseTime = DatetimeField(null=True)

    class Meta:
        table = "kusabase"


class KusaField(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="kusa_fields", null=True, source_field="userId", unique=True)
    kusaFinishTs = IntField(default=None, null=True)
    isUsingKela = BooleanField(default=False)
    isPrescient = BooleanField(default=False)
    isMirroring = BooleanField(default=False)
    overloadOnHarvest = BooleanField(default=False)
    biogasEffect = FloatField(default=1)
    soilCapacity = IntField(default=25)
    weedCosting = IntField(default=0)
    kusaResult = IntField(default=0)
    advKusaResult = IntField(default=0)
    kusaType = CharField(max_length=8, default=None, null=True)
    defaultKusaType = CharField(max_length=8, default="草")
    lastUseTime = DatetimeField(null=True)


class KusaHistory(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="kusa_histories", null=True, source_field="userId")
    kusaType = CharField(max_length=8, default="")
    kusaResult = IntField(default=0)
    advKusaResult = IntField(default=0)
    createTimeTs = IntField()


class DrawItemList(Model):
    id = IntField(pk=True)
    name = CharField(max_length=64)
    pool = CharField(max_length=32)
    rareRank = IntField()
    detail = CharField(max_length=1024)
    authorId = IntField(null=True)


class DrawItemStorage(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="draw_item_storages", null=True, source_field="userId")
    item = ForeignKeyField("models.DrawItemList", on_delete=CASCADE, related_name="draw_item_storage")
    amount = IntField()


class KusaItemList(Model):
    name = CharField(max_length=64, pk=True)
    detail = CharField(max_length=1024, null=True)
    type = CharField(max_length=32, null=True)
    isControllable = BooleanField(default=True)
    isTransferable = BooleanField(default=True)
    shopPrice = IntField(null=True)
    sellingPrice = IntField(null=True)
    priceRate = FloatField(null=True)
    priceType = CharField(max_length=32, null=True)
    amountLimit = IntField(null=True)
    shopPreItems = CharField(max_length=128, null=True)


class KusaItemStorage(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="kusa_item_storages", null=True, source_field="userId")
    item = ForeignKeyField("models.KusaItemList", on_delete=CASCADE, related_name="kusa_item_storage")
    amount = IntField()
    allowUse = BooleanField(default=True)
    timeLimitTs = IntField(null=True)

    class Meta:
        unique_together = (("user", "item"),)


class GValue(Model):
    cycle = IntField()
    turn = IntField()
    eastValue = FloatField()
    southValue = FloatField()
    northValue = FloatField()
    zhuhaiValue = FloatField()
    shenzhenValue = FloatField()
    createTime = DatetimeField()


class WorkOrder(Model):
    id = IntField(pk=True)
    title = CharField(max_length=128)
    authorId = IntField(null=True)
    detail = CharField(max_length=1024, null=True)
    reply = CharField(max_length=512, null=True)


class ChatUser(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="chat_users", null=True, source_field="userId")
    allowPrivate = BooleanField(default=False)
    allowRole = BooleanField(default=False)
    allowAdvancedModel = BooleanField(default=False)
    chosenModel = CharField(max_length=32, default="deepseek-chat")
    tokenUse = IntField(default=0)
    todayTokenUse = IntField(default=0)
    dailyTokenLimit = IntField(default=10000)
    chosenRoleId = IntField(default=0)
    createTime = DatetimeField(auto_now_add=True)


class ChatRole(Model):
    id = IntField(pk=True)
    name = CharField(max_length=32)
    detail = CharField(max_length=10240)
    isPublic = BooleanField(default=False)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="chat_roles", null=True, source_field="userId")
    createTime = DatetimeField(auto_now_add=True)


class Flag(Model):
    id = IntField(pk=True)
    name = CharField(max_length=32)
    value = BooleanField(default=False)
    forAll = BooleanField(default=True)
    ownerId = IntField(null=True)


class DonateRecord(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="donate_records", null=True, source_field="userId")
    amount = FloatField()
    donateDate = CharField(max_length=16)
    source = CharField(max_length=12)
    remark = CharField(max_length=128, null=True)


class TradeRecord(Model):
    id = IntField(pk=True)
    user = ForeignKeyField("models.UnifiedUser", on_delete=CASCADE, related_name="trade_records", null=True, source_field="userId")
    tradeType = CharField(max_length=16)
    gainItemAmount = IntField(null=True)
    gainItemName = CharField(max_length=64, null=True)
    costItemAmount = IntField(null=True)
    costItemName = CharField(max_length=64, null=True)
    detail = CharField(max_length=128, null=True)
    timestamp = IntField()


class PageView(Model):
    id = IntField(pk=True)
    userId = IntField(null=True)
    path = CharField(max_length=128)
    pageName = CharField(max_length=64, null=True)
    createdAt = DatetimeField(auto_now_add=True)
