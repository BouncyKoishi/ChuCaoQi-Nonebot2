"""
萨莉亚菜单插件 - NoneBot2 版本
根据预算随机生成萨莉亚点餐方案
"""

from __future__ import annotations
import random
import typing
from nonebot import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.typing import T_State

from multi_platform import send_finish


class SaizeriyaMenuItem(typing.NamedTuple):
    id: int
    name: str
    price: int


saizeriyaGDMenu = (
    SaizeriyaMenuItem(id=1977, name='蓝布鲁斯科气泡', price=36),
    SaizeriyaMenuItem(id=1733, name='草莓千层蛋糕配薄脆巧克力酱冰激凌', price=22),
    SaizeriyaMenuItem(id=1732, name='薄脆巧克力酱冰激凌', price=9),
    SaizeriyaMenuItem(id=1731, name='薄脆树莓果酱冰激凌', price=9),
    SaizeriyaMenuItem(id=1726, name='草莓千层蛋糕', price=16),
    SaizeriyaMenuItem(id=1717, name='激情果粒', price=8),
    SaizeriyaMenuItem(id=1713, name='芒果布丁', price=8),
    SaizeriyaMenuItem(id=1719, name='焦糖布丁', price=16),
    SaizeriyaMenuItem(id=1907, name='麒麟啤酒', price=10),
    SaizeriyaMenuItem(id=1921, name='赤霞珠干红葡萄酒（750ml）', price=36),
    SaizeriyaMenuItem(id=1924, name='霞多丽干白葡萄酒（750ml）', price=36),
    SaizeriyaMenuItem(id=1969, name='蒂安诺干红葡萄酒（750ml）', price=58),
    SaizeriyaMenuItem(id=1245, name='意式小吃拼盘', price=32),
    SaizeriyaMenuItem(id=1218, name='蒜香佛卡夏', price=9),
    SaizeriyaMenuItem(id=1607, name='鸡翅鸡排牛肉粒拼盘', price=49),
    SaizeriyaMenuItem(id=1509, name='番茄海鲜意面', price=22),
    SaizeriyaMenuItem(id=1011, name='金枪鱼沙拉（萨莉亚沙拉酱）', price=12),
    SaizeriyaMenuItem(id=1235, name='鱿鱼花蛤拼盘', price=26),
    SaizeriyaMenuItem(id=1116, name='蘑菇汤', price=9),
    SaizeriyaMenuItem(id=1513, name='黑椒牛柳意面', price=18),
    SaizeriyaMenuItem(id=1387, name='榴莲小匹萨', price=21),
    SaizeriyaMenuItem(id=1613, name='烘烤羊排', price=49),
    SaizeriyaMenuItem(id=1231, name='人气小吃拼盘②', price=27),
    SaizeriyaMenuItem(id=1208, name='意式茄红鸡翅', price=26),
    SaizeriyaMenuItem(id=1117, name='田园蔬菜汤', price=9),
    SaizeriyaMenuItem(id=1115, name='玉米汤', price=9),
    SaizeriyaMenuItem(id=1012, name='水果沙拉', price=9),
    SaizeriyaMenuItem(id=1013, name='海带丝沙拉（萨莉亚沙拉酱）', price=9),
    SaizeriyaMenuItem(id=1014, name='甜玉米沙拉（萨莉亚沙拉酱）', price=9),
    SaizeriyaMenuItem(id=1114, name='花蛤裙菜海鲜汤', price=9),
    SaizeriyaMenuItem(id=1290, name='蒜香花椰菜', price=9),
    SaizeriyaMenuItem(id=1289, name='什锦鲜蔬', price=12),
    SaizeriyaMenuItem(id=1288, name='白糖烤饼', price=5),
    SaizeriyaMenuItem(id=1286, name='原味烤饼', price=5),
    SaizeriyaMenuItem(id=1246, name='椒盐鸡腿排', price=16),
    SaizeriyaMenuItem(id=1242, name='蒜香烤面包片', price=7),
    SaizeriyaMenuItem(id=1241, name='原味烤面包片', price=5),
    SaizeriyaMenuItem(id=1233, name='黑椒烤肠', price=16),
    SaizeriyaMenuItem(id=1226, name='烤甜玉米', price=7),
    SaizeriyaMenuItem(id=1204, name='QQ薯角', price=7),
    SaizeriyaMenuItem(id=1224, name='烤菠菜', price=7),
    SaizeriyaMenuItem(id=1229, name='芝士烤玉米', price=9),
    SaizeriyaMenuItem(id=1240, name='海带丝', price=9),
    SaizeriyaMenuItem(id=1232, name='盐酥鸡肉粒', price=13),
    SaizeriyaMenuItem(id=1275, name='芝士奶汁土豆泥', price=13),
    SaizeriyaMenuItem(id=1234, name='五目烤肠', price=16),
    SaizeriyaMenuItem(id=1209, name='本色烤全鱿', price=22),
    SaizeriyaMenuItem(id=1393, name='肉酱培根小匹萨（6英寸含酸菜）', price=14),
    SaizeriyaMenuItem(id=1389, name='香肠小匹萨（6英寸）', price=14),
    SaizeriyaMenuItem(id=1382, name='水果小匹萨（6英寸）', price=14),
    SaizeriyaMenuItem(id=1380, name='培根菠萝小匹萨（6英寸）', price=14),
    SaizeriyaMenuItem(id=1307, name='榴莲匹萨（8英寸）', price=39),
    SaizeriyaMenuItem(id=1305, name='培根菠萝匹萨（8英寸）', price=22),
    SaizeriyaMenuItem(id=1420, name='金枪鱼焗意面', price=18),
    SaizeriyaMenuItem(id=1419, name='肉酱香肠芝士烤饭（含酸菜）', price=18),
    SaizeriyaMenuItem(id=1416, name='香烤鸡肉焗饭', price=18),
    SaizeriyaMenuItem(id=1410, name='海鲜焗意面', price=18),
    SaizeriyaMenuItem(id=1409, name='米饭', price=2),
    SaizeriyaMenuItem(id=1408, name='肉酱焗意面', price=18),
    SaizeriyaMenuItem(id=1404, name='鸡排烤饭', price=20),
    SaizeriyaMenuItem(id=1403, name='肉酱焗饭', price=19),
    SaizeriyaMenuItem(id=1402, name='芝士肉酱焗饭', price=23),
    SaizeriyaMenuItem(id=1415, name='芝士香烤鸡肉焗饭', price=22),
    SaizeriyaMenuItem(id=1405, name='鸡肉芝士培根烤饭', price=18),
    SaizeriyaMenuItem(id=1401, name='番茄海鲜烩饭', price=19),
    SaizeriyaMenuItem(id=1535, name='酸菜培根意面', price=12),
    SaizeriyaMenuItem(id=1523, name='蒜香茄汁鲜菇金枪鱼意面', price=18),
    SaizeriyaMenuItem(id=1512, name='墨鱼汁意面', price=15),
    SaizeriyaMenuItem(id=1505, name='青酱汁意面', price=14),
    SaizeriyaMenuItem(id=1617, name='烤肠鸡排牛肉粒拼盘', price=49),
    SaizeriyaMenuItem(id=1612, name='烤肠鸡排羊排拼盘', price=49),
    SaizeriyaMenuItem(id=1608, name='黑椒烤肠配黑椒鸡排', price=23),
    SaizeriyaMenuItem(id=1605, name='香烤鸡排（蒜香酱）', price=19),
    SaizeriyaMenuItem(id=1606, name='香烤鸡排（黑椒酱）', price=19),
    SaizeriyaMenuItem(id=1615, name='五目肠配香烤鸡排（蒜香酱）', price=24),
    SaizeriyaMenuItem(id=1603, name='牛排（黑椒风味）', price=49),
    SaizeriyaMenuItem(id=1602, name='牛排（蒜香风味）', price=49),
    SaizeriyaMenuItem(id=1601, name='鱿鱼配香烤鸡排', price=37),
    SaizeriyaMenuItem(id=1987, name='索阿维干白葡萄酒（750ml）', price=38),
    SaizeriyaMenuItem(id=1979, name='蓝布鲁斯科气泡酒（750ml）', price=38),
    SaizeriyaMenuItem(id=1911, name='莫斯卡托甜型高泡葡萄酒（750ml）', price=58),
    SaizeriyaMenuItem(id=1573, name='橄榄油什锦海鲜酱意面（辣味）', price=15),
    SaizeriyaMenuItem(id=1572, name='高原茄子肉酱意面（辣味）', price=18),
    SaizeriyaMenuItem(id=1571, name='高原茄子肉酱意面（原味）', price=18),
    SaizeriyaMenuItem(id=1570, name='橄榄油什锦海鲜酱意面（原味）', price=15),
    SaizeriyaMenuItem(id=1655, name='什锦菌菇汉堡', price=26),
    SaizeriyaMenuItem(id=1438, name='罗勒酱鸡肉烩饭', price=15),
    SaizeriyaMenuItem(id=1437, name='戈贡佐拉芝士肉酱饭', price=13),
    SaizeriyaMenuItem(id=1267, name='奶汁局鹌鹑蛋配甜豌豆', price=16),
    SaizeriyaMenuItem(id=1213, name='香烤鸡肉丁配意式香芹酱', price=13),
    SaizeriyaMenuItem(id=1212, name='意式炸南瓜', price=5),
    SaizeriyaMenuItem(id=1203, name='德国酸青瓜', price=5),
    SaizeriyaMenuItem(id=1989, name='桑娇维塞干红葡萄酒（750ml）', price=38),
    SaizeriyaMenuItem(id=1121, name='那不勒斯风味婚礼汤', price=12),
    SaizeriyaMenuItem(id=1982, name='泰兰努斯普拉米蒂沃干红（750ml）', price=136),
    SaizeriyaMenuItem(id=1027, name='牛油果火腿片沙拉（橄榄油香醋汁）', price=15),
    SaizeriyaMenuItem(id=1903, name='柠檬利口酒（杯）', price=5),
    SaizeriyaMenuItem(id=1902, name='索阿维干白葡萄酒（杯）', price=5),
    SaizeriyaMenuItem(id=1901, name='桑娇维塞干红葡萄酒（杯）', price=5),
    SaizeriyaMenuItem(id=1749, name='柠檬芝士蛋糕', price=12),
    SaizeriyaMenuItem(id=1217, name='佛卡夏', price=7),
    SaizeriyaMenuItem(id=1704, name='肉桂糖佛卡夏配香草冰淇淋', price=13),
    SaizeriyaMenuItem(id=1566, name='博洛尼亚肉酱意面（辣味）', price=13),
    SaizeriyaMenuItem(id=1645, name='原切安格斯眼肉牛排（7分熟）', price=59),
    SaizeriyaMenuItem(id=1565, name='博洛尼亚肉酱意面（原味）', price=13),
    SaizeriyaMenuItem(id=1270, name='蒜香黄油蜗牛配焦香小面包', price=19),
    SaizeriyaMenuItem(id=1433, name='牛肝菌酱鸡肉芝士烤饭', price=21),
    SaizeriyaMenuItem(id=1221, name='人气小吃拼盘', price=29),
    SaizeriyaMenuItem(id=1120, name='南瓜汤（无添加糖）', price=9),
    SaizeriyaMenuItem(id=1118, name='蘑菇汤', price=9),
    SaizeriyaMenuItem(id=1112, name='玉米汤', price=9),
    SaizeriyaMenuItem(id=1030, name='牛油果酸奶沙拉', price=15),
    SaizeriyaMenuItem(id=1023, name='甜玉米沙拉（橄榄油香醋汁）', price=9),
    SaizeriyaMenuItem(id=1022, name='海带丝沙拉（橄榄油香醋汁）', price=9),
    SaizeriyaMenuItem(id=1020, name='金枪鱼沙拉（橄榄油香醋汁）', price=12),
    SaizeriyaMenuItem(id=1287, name='意式小吃拼盘配意式香芹酱', price=29),
    SaizeriyaMenuItem(id=1284, name='斯特拉恰特拉芝士', price=13),
    SaizeriyaMenuItem(id=1260, name='牛油果芝香恰巴塔', price=15),
    SaizeriyaMenuItem(id=1223, name='白葡萄酒贻贝', price=18),
    SaizeriyaMenuItem(id=1222, name='香烤鳕鱼排', price=15),
    SaizeriyaMenuItem(id=1215, name='盐酥鸡肉粒', price=13),
    SaizeriyaMenuItem(id=1239, name='温泉蛋', price=4),
    SaizeriyaMenuItem(id=1294, name='甜豌豆配温泉蛋', price=11),
    SaizeriyaMenuItem(id=1291, name='芝士肉酱烤茄子', price=13),
    SaizeriyaMenuItem(id=1265, name='原味煮花蛤', price=13),
    SaizeriyaMenuItem(id=1201, name='原制芝士（马苏里拉切达）', price=5),
    SaizeriyaMenuItem(id=1253, name='芝士烤菠菜', price=9),
    SaizeriyaMenuItem(id=1250, name='蒜香黄油炒菜心', price=9),
    SaizeriyaMenuItem(id=1205, name='蒜香黄油什锦菌菇', price=10),
    SaizeriyaMenuItem(id=3374, name='卡拉布里亚风味小匹萨加芝士', price=22),
    SaizeriyaMenuItem(id=3377, name='四喜芝士小匹萨加芝士', price=19),
    SaizeriyaMenuItem(id=1377, name='四喜芝士小匹萨', price=15),
    SaizeriyaMenuItem(id=3370, name='鸡肉培根小匹萨加芝士', price=19),
    SaizeriyaMenuItem(id=3387, name='榴莲小匹萨加芝士', price=25),
    SaizeriyaMenuItem(id=3369, name='罗勒酱鸡肉小匹萨加芝士', price=22),
    SaizeriyaMenuItem(id=1374, name='卡拉布里亚风味小匹萨', price=18),
    SaizeriyaMenuItem(id=1370, name='鸡肉培根小匹萨', price=15),
    SaizeriyaMenuItem(id=1369, name='罗勒酱鸡肉小匹萨', price=18),
    SaizeriyaMenuItem(id=1436, name='曙光女神酱甜豌豆烩饭', price=17),
    SaizeriyaMenuItem(id=1435, name='芝士香烤鸡肉焗饭', price=23),
    SaizeriyaMenuItem(id=1434, name='蒜香鸡肉培根芝士烤饭', price=19),
    SaizeriyaMenuItem(id=1499, name='米饭（五常大米）', price=3),
    SaizeriyaMenuItem(id=1423, name='海鲜烩饭', price=17),
    SaizeriyaMenuItem(id=1268, name='焦香小面包', price=5),
    SaizeriyaMenuItem(id=1269, name='蒜香小面包', price=7),
    SaizeriyaMenuItem(id=1569, name='蒜香贻贝意面', price=24),
    SaizeriyaMenuItem(id=1567, name='斯特拉恰特拉芝士意面', price=18),
    SaizeriyaMenuItem(id=1558, name='蒜香花蛤菜心辣味意面', price=15),
    SaizeriyaMenuItem(id=1549, name='番茄海鲜意面', price=22),
    SaizeriyaMenuItem(id=1547, name='肉酱意面', price=18),
    SaizeriyaMenuItem(id=1546, name='芝士番茄培根意面', price=15),
    SaizeriyaMenuItem(id=1564, name='牛肝菌酱培根奶汁意面', price=22),
    SaizeriyaMenuItem(id=1502, name='热那亚风味罗勒酱意面', price=15),
    SaizeriyaMenuItem(id=1656, name='芝芝多多微辣辣汉堡（不辣）', price=30),
    SaizeriyaMenuItem(id=1653, name='芝芝多多微辣辣汉堡', price=30),
    SaizeriyaMenuItem(id=1652, name='卡拉布里亚风味五花肉', price=22),
    SaizeriyaMenuItem(id=1643, name='安格斯焦香牛肉汉堡', price=24),
    SaizeriyaMenuItem(id=1630, name='五目肠配香烤鸡排（黑椒酱）', price=24),
    SaizeriyaMenuItem(id=1641, name='芝芝多多微辣辣鸡排', price=24),
    SaizeriyaMenuItem(id=1647, name='芝芝多多微辣辣鸡排（不辣）', price=24),
    SaizeriyaMenuItem(id=1744, name='意式酸奶树莓果酱', price=9),
    SaizeriyaMenuItem(id=1748, name='浓郁巧克力配清爽薄荷冰淇淋', price=15),
    SaizeriyaMenuItem(id=1752, name='坚果树莓果酱冰淇淋', price=9),
    SaizeriyaMenuItem(id=1754, name='蓝莓芝士蛋糕', price=12),
    SaizeriyaMenuItem(id=1756, name='斯特拉恰特拉', price=13),
    SaizeriyaMenuItem(id=1757, name='提拉米苏蛋糕', price=16),
    SaizeriyaMenuItem(id=1918, name='朝日啤酒（500ml）', price=10),
    SaizeriyaMenuItem(id=1914, name='阿佩罗柠檬斯普里茨', price=15),
    SaizeriyaMenuItem(id=1917, name='莫斯卡托干白葡萄酒（187ml）', price=16),
    SaizeriyaMenuItem(id=1992, name='朝日超爽3.5啤酒', price=9),
    SaizeriyaMenuItem(id=1986, name='阿肯塔维蒙蒂诺白葡萄酒（750ml）', price=128),
    SaizeriyaMenuItem(id=1985, name='龙虾维蒙蒂诺白葡萄酒（750ml）', price=88),
    SaizeriyaMenuItem(id=1984, name='维德凡干白葡萄酒（750ml）', price=88),
    SaizeriyaMenuItem(id=1983, name='尼格马罗桃红葡萄酒（750ml）', price=78),
    SaizeriyaMenuItem(id=1981, name='普拉米蒂沃干红葡萄酒（750ml）', price=88),
    SaizeriyaMenuItem(id=1980, name='尼格马罗干红葡萄酒（750ml）', price=88),
)

saizeriyaGDMenuPriceTotal = sum(x.price for x in saizeriyaGDMenu)


def rollMenu(budgetMin: int, budgetMax: int | None = None) -> str:
    if budgetMax is None:
        budgetMax = budgetMin
    if budgetMin < 1:
        budgetMin = 1
    if budgetMax < 1:
        budgetMax = 1
    if budgetMin > budgetMax:
        budgetMin, budgetMax = budgetMax, budgetMin
    if budgetMax > 500:
        budgetMax = 500
    if budgetMin > 500:
        return '吃这么多，你是幽幽子吗 ( ｡╹ω╹｡ )'
    if budgetMax < min(x.price for x in saizeriyaGDMenu):
        return '这么点钱能吃啥啊 …_φ(･ω･` )'

    randomizedMenu = list(saizeriyaGDMenu)
    random.shuffle(randomizedMenu)

    budgetTried: set[int] = set()
    result: list[SaizeriyaMenuItem] = []

    for _ in range(64):
        if len(budgetTried) >= (budgetMax - budgetMin + 1) or len(result):
            break
        result = []

        while True:
            budget = random.randint(budgetMin, budgetMax)
            if budget not in budgetTried:
                break
        budgetTried.add(budget)

        if budget == saizeriyaGDMenuPriceTotal:
            result = randomizedMenu
        else:
            subset = [
                [False for _ in range(budget + 1)]
                for _ in range(len(randomizedMenu) + 1)
            ]

            for i in range(budget + 1):
                subset[0][i] = False
            for i in range(len(randomizedMenu) + 1):
                subset[i][0] = True
            for i in range(1, len(randomizedMenu) + 1):
                for j in range(1, budget + 1):
                    subset[i][j] = (
                        subset[i - 1][j]
                        if j < randomizedMenu[i - 1].price else
                        (subset[i - 1][j] or subset[i - 1][j - randomizedMenu[i - 1].price])
                    )
            if subset[len(randomizedMenu)][budget]:
                for i in range(len(randomizedMenu), -1, -1):
                    if subset[i][budget] and not subset[i - 1][budget]:
                        result.append(randomizedMenu[i - 1])
                        budget -= randomizedMenu[i - 1].price
                    if not budget:
                        break

    if not result:
        return '居然找不到符合要求的点餐方案……( >﹏<。)'
    result.sort(key=lambda x: x.id)
    return '\n'.join((
        f'你点了{len(result)}份菜',
        *(f'{x.id} {x.name} {x.price}元' for x in result),
        f'总消费：{sum(x.price for x in result)}元',
    ))


saizeriya_cmd = on_command("点餐", aliases={"saizeriya"}, priority=5, block=True)


@saizeriya_cmd.handle()
async def handle_saizeriya(args: Message = CommandArg()):
    strippedText = args.extract_plain_text().strip()
    if not strippedText:
        await saizeriya_cmd.finish('没有输入预算或预算范围^ ^')
    try:
        if '-' in strippedText:
            budgetMin, budgetMax = map(int, strippedText.split('-'))
        else:
            budgetMin = budgetMax = int(strippedText)
    except ValueError:
        await saizeriya_cmd.finish('输入的预算格式不正确^ ^')
    result = rollMenu(budgetMin, budgetMax)
    await saizeriya_cmd.finish(result)
