export interface CommandTag {
  text: string
  type?: '' | 'success' | 'warning' | 'danger' | 'info'
}

export interface Command {
  name: string
  aliases?: string[]
  params?: string
  description: string
  details?: string[]
  tags?: CommandTag[]
  category: string
  subcategory: string
}

export const commands: Command[] = [
  {
    name: '生草',
    params: '[草种名称]',
    description: '开始种植草，可指定草种（不填则使用默认草种）。生草需要消耗承载力，生草完成后可获得草和草之精华。',
    details: [
      '不指定草种时使用默认草种（可通过"默认草种"指令设置）',
      '正在生草时不可重复生草，土地过载时也无法生草',
      '承载力不足（<=0，若土壤保护装置启用则为<=10）将禁止生草',
      '生草完成后会获得草和草之精华，满足一定条件可触发喜报与围殴'
    ],
    tags: [{ text: '消耗承载力', type: 'warning' }],
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '过载生草',
    params: '[草种名称]',
    description: '使用过载魔法进行生草，收获时额外获得草之精华，但土地将进入过载状态无法生草。',
    details: [
      '需要拥有"奈奈的过载魔法"才能使用',
      '过载生草收获时，根据生草量中不同数字的个数，每个不同数字获得2个额外草之精华',
      '过载时间为基础3小时×不同数字个数，拥有"祝福之色赠予结缘之人"称号可缩减为2小时×不同数字个数'
    ],
    tags: [{ text: '需奈奈的过载魔法', type: 'warning' }],
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '除草',
    params: '',
    description: '清除当前正在生长的草，需要拥有除草机。除草不会获得任何产出，但会清除灵性标记和休耕标记。',
    details: [
      '需要拥有"除草机"才能使用',
      '除草会清除当前正在生长的草，不会获得草和草之精华',
      '除草后会清除灵性标记和休耕标记',
      '如果配置中开启了"除草后自动生草"，除草后会自动开始新一轮生草'
    ],
    tags: [{ text: '需除草机', type: 'warning' }],
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '百草园',
    params: '',
    description: '查看农田状态，包括当前生草进度、预估产量、默认草种、土壤承载力等信息。',
    details: [
      '显示当前生草状态：正在生草时显示剩余时间和预估产量，未生草时显示是否过载',
      '显示默认草种、当前土壤承载力和可用后备承载力',
      '如果配置中开启"生草预估详情展示"，会额外显示生草数量的详细计算过程'
    ],
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '默认草种',
    params: '[草种名称]',
    description: '设置生草时的默认草种，不指定草种名称时默认设为普通草。',
    details: [
      '设置后，使用"生草"指令不指定草种时将自动使用此默认草种',
      '不传参数时默认设为"草"（普通草）',
      '默认草种仅对Bot端生草指令有效，对Web端无效'
    ],
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '承载力补充',
    aliases: ['补充承载力'],
    params: '[补充数量]',
    description: '消耗后备承载力补充土壤承载力，不指定数量则补充到满。',
    details: [
      '消耗"后备承载力"来恢复土壤承载力，承载力上限为25',
      '不指定数量时自动补充到满',
      '指定数量时补充指定点数（受后备承载力限制）',
      '承载力已满时无法补充'
    ],
    tags: [{ text: '消耗后备承载力', type: 'warning' }],
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '生草简报',
    params: '',
    description: '查看最近24小时的生草统计，包括生草次数、总草量、草之精华及各自平均值。',
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '生草日报',
    params: '',
    description: '查看昨日的生草统计，包括生草次数、总草量、草之精华及各自平均值。',
    category: '生草系统',
    subcategory: '生草'
  },
  {
    name: '生草周报',
    params: '',
    description: '查看上周的生草统计，包括生草次数、总草量、草之精华及各自平均值。',
    category: '生草系统',
    subcategory: '生草'
  },

  {
    name: '仓库',
    params: '[qq=QQ号]',
    description: '查看仓库信息，包括草、草之精华、财产和道具。不带参数查看自己的仓库，带qq参数可查看他人仓库（需要消耗侦察凭证）。',
    details: [
      '不带参数时查看自己的仓库，显示等级、称号、名称、草/草之精华数量及财产和道具',
      '带qq=QQ号参数时查看他人仓库，需要拥有侦察凭证道具，每次查看消耗1个',
      '查看他人仓库时显示前缀为[侦察卫星使用中]'
    ],
    tags: [{ text: '消耗1个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '能力',
    params: '',
    description: '查看自己当前拥有的能力和图纸列表。',
    details: [
      '分别列出拥有的能力（类型为"能力"的物品）和图纸（类型为"图纸"的物品）',
      '仅显示拥有数量不为0的能力和图纸名称'
    ],
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '改名',
    params: '新名字',
    description: '修改自己在生草系统中的显示名称，名字长度不能超过25个字符。',
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '称号',
    params: '',
    description: '查看自己当前可用的称号列表。',
    details: [
      '可使用"修改称号"指令来更改当前展示的称号'
    ],
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '修改称号',
    params: '[称号名称]',
    description: '修改当前在仓库指令下展示的称号。不带参数则清除当前称号，带称号名称则设置为指定称号。',
    details: [
      '不带参数时清除当前称号，仓库中的称号展示位改为展示当前信息员等级名称',
      '带称号名称时，会验证该称号是否存在，以及自己是否拥有该称号'
    ],
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '配置列表',
    params: '',
    description: '查看所有可用的配置项及其当前开关状态（on/off）。',
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '配置',
    params: '配置名 on/off',
    description: '设置指定配置项的开关状态，使用on开启或off关闭。',
    details: [
      '不带参数时会显示使用帮助',
      '配置名必须是系统中已存在的公共配置项，否则会报错',
      '可使用"配置列表"指令查看当前所有可用的配置项'
    ],
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '草压缩',
    params: '[数量]',
    description: '将草压缩为草之精华，每1个草之精华需要消耗1,000,000草。需要拥有草压缩基地才能使用。',
    details: [
      '需要拥有"草压缩基地"道具才能使用',
      '不带参数时默认产出1个草之精华（消耗1,000,000草）',
      '带数量参数时产出指定数量的草之精华',
      '草不足时提示所需数量'
    ],
    tags: [{ text: '消耗草', type: 'warning' }],
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '信息员升级',
    params: '',
    description: '消耗草来提升信息员等级（Lv0~Lv4），升级费用为50×10^新等级的草。',
    details: [
      '当前等级达到Lv4（后浪信息员）时无法使用本指令，需使用"进阶信息员升级"',
      '升级费用：Lv1=500草、Lv2=5000草、Lv3=50000草、Lv4=500000草',
      '等级对应：Lv0用户、Lv1信息员、Lv2高级信息员、Lv3特级信息员、Lv4后浪信息员'
    ],
    tags: [{ text: '消耗草', type: 'warning' }],
    category: '生草系统',
    subcategory: '仓库与能力'
  },
  {
    name: '进阶信息员升级',
    params: '',
    description: '消耗草之精华来提升进阶信息员等级（Lv5~Lv8），升级费用为10^(新等级-4)个草之精华。',
    details: [
      '当前等级低于Lv4时无法使用，需先使用"信息员升级"达到Lv4',
      '当前等级达到Lv8（天琴信息网络）时为最高级，无法继续升级',
      '升级费用：Lv5=10、Lv6=100、Lv7=1000、Lv8=10000个草之精华',
      '等级对应：Lv5天琴信息员、Lv6天琴信息节点、Lv7天琴信息矩阵、Lv8天琴信息网络'
    ],
    tags: [{ text: '消耗草之精华', type: 'warning' }],
    category: '生草系统',
    subcategory: '仓库与能力'
  },

  {
    name: '商店',
    params: '[全部]',
    description: '查看以草为货币的商店物品列表。',
    details: [
      '默认只显示满足前置购买条件且未达数量上限的物品',
      '输入"全部"或"all"参数可查看商店全部物品',
      '物品按价格升序排列'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '进阶商店',
    params: '[全部]',
    description: '查看以草之精华为货币的商店物品列表。',
    details: [
      '默认只显示满足前置购买条件且未达数量上限的物品',
      '输入"全部"或"all"参数可查看商店全部物品',
      '物品按价格升序排列'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '建筑商店',
    aliases: ['核心商店'],
    params: '[全部]',
    description: '查看以自动化核心为货币的商店物品列表，包含生草工厂等建筑类物品。',
    details: [
      '默认只显示满足前置购买条件且未达数量上限的物品',
      '输入"全部"或"all"参数可查看商店全部物品',
      '物品按价格升序排列'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '商店帮助',
    params: '',
    description: '查看商店与道具系统的帮助说明。',
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '查询',
    aliases: ['道具详情'],
    params: '物品名',
    description: '查询指定生草系统物品的详细信息，包括拥有数量、商店价格、购买前置条件、可转让/可禁用属性等。',
    details: [
      '显示物品的拥有数量（如有上限则显示 当前/上限）',
      '显示基础价格，若为浮动价格则额外显示当前价格和价格倍率',
      '显示是否可转让、是否可禁用（及当前启用/禁用状态）',
      '显示前置购买条件（如有）和物品说明（如有）',
      '此命令仅查询生草系统物品信息，抽奖物品请使用"物品详情"命令'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '购买',
    params: '物品名 [数量]',
    description: '从商店购买指定物品，数量默认为1。',
    details: [
      '购买前会检查前置条件、数量上限和货币是否充足',
      '浮动价格物品（如生草工厂）购买时会显示总价并需要输入y确认',
      '数量支持k/m/b后缀，如10k表示10000',
      '如果是可控制的物品，购买后会自动启用'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '出售',
    params: '物品名 [数量]',
    description: '将指定物品出售给商店，获得对应货币，数量默认为1。',
    details: [
      '只有设有出售价的物品才能出售',
      '浮动价格物品不可通过商店出售',
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '转让',
    aliases: ['道具转让'],
    params: '物品名 [数量] qq=目标QQ号',
    description: '将指定物品转让给其他用户，仅可转让标记为可转让的物品。',
    details: [
      '需要通过qq=指定接收者，接收者必须拥有生草系统账户',
      '只有标记为可转让的物品才能转让',
      '转让成功后，若接收方开启了"物品转让提示"配置，会私聊通知接收方',
      '未指定数量时数量默认为1，数量支持k/m/b后缀',
      '仅支持转让生草系统物品，不支持转让抽奖物品'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '启用',
    aliases: ['道具启用'],
    params: '物品名',
    description: '启用指定物品的效果，仅对可控制的物品有效。',
    details: [
      '只有标记为可控制的物品才能手动启用',
      '必须拥有该物品才能启用'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '禁用',
    aliases: ['道具禁用'],
    params: '物品名',
    description: '禁用指定物品的效果，仅对可控制的物品有效。',
    details: [
      '只有标记为可控制的物品才能手动禁用',
      '必须拥有该物品才能禁用'
    ],
    category: '生草系统',
    subcategory: '商店与道具'
  },
  {
    name: '合成',
    params: '目标物品名 [数量]',
    description: '使用奖券合成机将低级奖券合成为高级奖券。',
    details: [
      '需要拥有"奖券合成机"才能进行合成',
      '合成配方：10个十连券 → 1个高级十连券',
      '合成配方：10个高级十连券 → 1个特级十连券',
      '合成配方：10个特级十连券 → 1个天琴十连券',
      '数量默认为1，表示合成几个目标物品（消耗10倍数量的源材料）'
    ],
    tags: [{ text: '需奖券合成机', type: 'warning' }],
    category: '生草系统',
    subcategory: '商店与道具'
  },

  {
    name: '发草包',
    params: 'num=个数 kusa=总草数',
    description: '发放一个草包，指定人数和总草数，其他玩家可抢草包获取随机草。',
    details: [
      '只能在除草器主群中使用',
      'num为草包个数（即最多多少人可以抢），kusa为草包总额',
      'kusa参数支持k/m/b单位后缀（如kusa=1k表示1000草）',
      '草包1小时后超时，未抢完的草将退回给发放者',
      '草包抢完后会公布手气王（抢到最多草的玩家）'
    ],
    tags: [{ text: '主群限定', type: 'warning' }],
    category: '生草系统',
    subcategory: '用户交互'
  },
  {
    name: '抢草包',
    params: '',
    description: '抢当前所有可抢的草包，随机获得一定数量的草。',
    details: [
      '只能在除草器主群中使用',
      '每个草包只能抢一次，已抢过的草包不会重复发放',
      '抢到的草数随机，有1%的概率只获得1草'
    ],
    tags: [{ text: '主群限定', type: 'warning' }],
    category: '生草系统',
    subcategory: '用户交互'
  },
  {
    name: '围殴',
    params: '',
    description: '围殴当前可围殴的所有玩家，随机从对方身上抢走一定数量的草。',
    details: [
      '只能在群聊中使用',
      '围殴对象为生草结算时触发喜报的对象',
      '每次围殴随机抢走目标4%~15%上限的草',
      '每个围殴对象只能参与一次',
      '不能围殴自己，机械臂用户不能参与围殴',
      '若围殴对象持有"除草器的共享魔法"且参与者VIP等级>=5，额外获得1草之精华',
      '围殴持续2~5分钟后自动结束，累计损失超过上限也会提前结束'
    ],
    tags: [{ text: '群聊', type: 'warning' }],
    category: '生草系统',
    subcategory: '用户交互'
  },
  {
    name: '草转让',
    params: 'qq=QQ号 kusa=草数',
    description: '将自己的草转让给指定玩家，需要通过QQ号指定接收者。',
    details: [
      'kusa参数支持k/m/b单位后缀（如kusa=1k表示1000草），支持逗号分隔数字',
      '目标用户必须拥有生草账户',
      '转让>=10000草时会私聊通知被转让者'
    ],
    category: '生草系统',
    subcategory: '用户交互'
  },

  {
    name: '测G',
    params: '',
    description: '查看当前各校区G值及自己的G持仓。',
    details: [
      '显示东、南、北、珠海、深圳五个校区的当前G值及对比上一期的涨跌幅百分比',
      '同时显示用户在各校区持有的G数量',
      '末尾提示使用G市帮助查看交易指令'
    ],
    category: '生草系统',
    subcategory: 'G市'
  },
  {
    name: 'G市帮助',
    params: '',
    description: '查看G市交易相关指令帮助。',
    category: '生草系统',
    subcategory: 'G市'
  },
  {
    name: '交易总结',
    params: '',
    description: '查看本周期的G市交易总结，包括持仓估值、投入/取出草数和盈亏。',
    details: [
      '显示当前持仓折合草数、本周期总投入草数、总取出草数',
      '计算本周期盈亏估值 = 当前持仓估值 + 已取出草数 - 已投入草数',
      '列出各校区持仓详情：数量 × 当前G值 = 折合草数',
      '结算时间无法查询'
    ],
    category: '生草系统',
    subcategory: 'G市'
  },
  {
    name: '上期交易总结',
    params: '',
    description: '查看上一周期的G市交易总结，包括投入、取出和总盈亏。',
    details: [
      '显示上周期总投入草数、总取出草数、总盈亏（取出 - 投入）',
      '结算时间无法查询'
    ],
    category: '生草系统',
    subcategory: 'G市'
  },
  {
    name: '交易记录',
    params: '',
    description: '查看本周期的G市交易记录，支持翻页浏览。',
    details: [
      '每页显示10条记录，按时间倒序排列',
      '每条记录显示时间、买入/卖出、G数量、G名称、花费/获得草数、等效单价',
      '多页时可通过!下一页/!上一页翻页'
    ],
    category: '生草系统',
    subcategory: 'G市'
  },
  {
    name: 'G买入',
    params: '<数量|all> <校区>[校区比例]',
    description: '买入指定校区的G，可用草兑换G。',
    details: [
      '数量参数：指定买入数量，或用all表示用全部草买入',
      '校区参数：东/南/北/珠/深，可同时指定多个校区并附带比例',
      '示例：!G买入 100 东 = 买入100个东校区G',
      '示例：!G买入 100 东2南1 = 按东:南=2:1比例，各买入200和100个',
      '示例：!G买入 all 东 = 用全部草买入东校区G',
      '买入价格 = 数量 × 当前G值',
      '结算时间无法交易'
    ],
    category: '生草系统',
    subcategory: 'G市'
  },
  {
    name: 'G卖出',
    params: '<数量|all> <校区>[校区比例]',
    description: '卖出指定校区的G，兑换为草。',
    details: [
      '数量参数：指定卖出数量，或用all表示卖出全部持仓',
      '校区参数：东/南/北/珠/深，可同时指定多个校区并附带比例',
      '示例：!G卖出 100 东 = 卖出100个东校区G',
      '示例：!G卖出 all 东 = 卖出全部东校区G',
      '示例：!G卖出 all = 卖出所有校区的G',
      '卖出收取0.05%手续费',
      '结算时间无法交易'
    ],
    category: '生草系统',
    subcategory: 'G市'
  },
  {
    name: 'G线图',
    params: '[校区]',
    description: '查看本周期G值走势图。',
    details: [
      '可选参数：东/南/北/珠/深，指定查看某校区G线图',
      '不指定校区时，显示所有校区对比图（归一化后对数坐标）'
    ],
    category: '生草系统',
    subcategory: 'G市'
  },

  {
    name: '每日产量',
    params: '',
    description: '查看自己的每日工业期望产量，包括草、草之精华、自动化核心的产量。',
    details: [
      '产量基于当前拥有的生草机器、生草工厂、流动生草工厂、草精炼厂、核心装配工厂、红茶池等工业设施计算',
      '草精炼厂运作会消耗5000草/厂',
      '蕾米球的生产魔法根据当前草地承载力显示额外加成'
    ],
    category: '生草系统',
    subcategory: '统计'
  },
  {
    name: 'KUSA_RANK',
    params: '',
    description: '查看草排行榜，显示草数最多的前25名用户（排除机器人用户）。',
    tags: [{ text: '消耗1个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '统计'
  },
  {
    name: 'FACTORY_RANK',
    params: '',
    description: '查看工厂数排行榜，显示拥有工厂数量最多的用户排名。',
    tags: [{ text: '消耗1个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '统计'
  },
  {
    name: 'KUSA_ADV',
    params: '[userId]',
    description: '查看指定用户的草精统计详情，包括现有草精、信息员等级消费草精、道具消费草精和总计草精。不传userId时查看自己。',
    details: [
      '消耗1个侦察凭证（超管免费）',
      '总计草精 = 现有草精 + 信息员等级消费 + 道具消费'
    ],
    tags: [{ text: '消耗1个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '统计'
  },
  {
    name: '草精排行榜',
    params: '',
    description: '查看总草精排行榜，显示草精数最多的前25名用户，并展示自己的排名和与前后名的差距。',
    details: [
      '消耗10个侦察凭证（超管免费）',
      '仅显示拥有生草工业园区蓝图的用户',
      '仅显示90天内有活跃记录的用户'
    ],
    tags: [{ text: '消耗10个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '统计'
  },
  {
    name: '草精新星榜',
    params: '',
    description: '查看草精新星排行榜，仅显示信息员等级不超过6的用户，相当于新手的草精排行榜。',
    details: [
      '消耗10个侦察凭证（超管免费）',
      '仅显示拥有生草工业园区蓝图的用户',
      '仅显示90天内有活跃记录的用户',
      '仅显示信息员等级不超过6的用户'
    ],
    tags: [{ text: '消耗10个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '统计'
  },
  {
    name: '生草打分榜',
    params: '[-self]',
    description: '查看单次生草最高记录排行榜，按单次生草结果降序排列。',
    details: [
      '消耗5个侦察凭证（超管免费）',
      '添加 -self 参数可查看自己的单次生草最高记录排行',
      '不添加 -self 则查看全服排行'
    ],
    tags: [{ text: '消耗5个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '统计'
  },
  {
    name: '草精打分榜',
    params: '[-self]',
    description: '查看单次生草草精最高记录排行榜，按单次草精结果降序排列。',
    details: [
      '消耗5个侦察凭证（超管免费）',
      '添加 -self 参数可查看自己的单次草精最高记录排行',
      '不添加 -self 则查看全服排行'
    ],
    tags: [{ text: '消耗5个侦察凭证', type: 'warning' }],
    category: '生草系统',
    subcategory: '统计'
  },

  {
    name: '抽奖',
    params: '[奖池名/等级名]',
    description: '从抽奖池中随机抽取一件物品。仅在允许抽奖的群组中可用，不支持私聊。',
    details: [
      '参数可指定奖池名或等级名（Easy/Normal/Hard/Lunatic），也可同时指定两者',
      '不传参数则从所有奖池中随机抽取',
      '抽奖有概率被口球（禁言），持有量子护盾可大幅降低禁言概率',
      '持有量子护盾时，每次抽奖固定消耗一个量子护盾',
      '持有骰子碎片时，若抽到已有物品会自动重roll，每次重roll消耗1个碎片，单次抽奖最多重roll50次',
      '首次抽到的物品会标记(New!)'
    ],
    tags: [{ text: '群聊限定', type: 'warning' }],
    category: '抽奖系统',
    subcategory: '基础指令'
  },
  {
    name: '十连抽',
    params: '[等级名/奖池名]',
    description: '消耗一张十连券进行十连抽，一次获得10件物品。根据指定的等级消耗不同类型的十连券。',
    details: [
      '参数可指定等级名或奖池名，也可同时指定两者',
      '不传参数默认等级为Easy，使用普通十连券',
      '不同等级对应的十连券：Easy→十连券, Normal→高级十连券, Hard→特级十连券, Lunatic→天琴十连券',
      '抽出的物品等级必然大于等于用户所指定等级，除此以外没有保底机制',
      '不会抽到口球（禁言），没有重roll机制，不会消耗量子护盾或骰子碎片',
      '首次抽到的物品会标记(New!)'
    ],
    tags: [{ text: '群聊限定', type: 'warning' }, { text: '消耗十连券', type: 'danger' }],
    category: '抽奖系统',
    subcategory: '基础指令'
  },
  {
    name: '物品仓库',
    params: '[等级名/奖池名]',
    description: '查看自己在抽奖系统中已拥有的物品。不传参数时按稀有度分组显示所有已拥有物品及数量。',
    details: [
      '指定等级时显示该等级下所有已拥有物品，支持翻页浏览',
      '当某等级物品数量超过配置阈值时，该等级列表会被隐藏',
      '指定等级时物品数量超过100会启用分页'
    ],
    tags: [{ text: '支持翻页', type: 'info' }],
    category: '抽奖系统',
    subcategory: '基础指令'
  },
  {
    name: '物品详情',
    params: '物品名',
    description: '查看指定抽奖物品的详细信息，包括稀有度、持有数量、物品说明、创作者、所属奖池以及被抽中的统计。若物品名不存在，会自动转为物品搜索。',
    details: [
      '仅用于查看抽奖系统物品详细信息。生草系统物品请使用 !查询 指令',
    ],
    category: '抽奖系统',
    subcategory: '基础指令'
  },
  {
    name: '物品搜索',
    params: '关键词',
    description: '根据关键词模糊搜索抽奖物品，显示匹配的物品列表（含稀有度标注）。结果超过12件时支持翻页浏览。',
    tags: [{ text: '支持翻页', type: 'info' }],
    category: '抽奖系统',
    subcategory: '基础指令'
  },
  {
    name: '奖池列表',
    aliases: ['物品池列表'],
    params: '',
    description: '查看当前抽奖系统中所有可用的奖池名称列表。',
    category: '抽奖系统',
    subcategory: '基础指令'
  },
  {
    name: '最新物品',
    params: '',
    description: '查看抽奖系统中最新添加的5件物品（按添加时间倒序）。每次使用消耗1个侦察凭证。',
    tags: [{ text: '消耗1个侦察凭证', type: 'warning' }],
    category: '抽奖系统',
    subcategory: '基础指令'
  },

  {
    name: '添加-Easy',
    aliases: ['物品添加-Easy'],
    params: '物品名[:物品简介]',
    description: '添加一件Easy稀有度的自制物品到抽奖池。消耗1000草。物品名最长32字，物品简介最长1024字。提交后会进行内容审核。',
    details: [
      '参数格式：物品名 或 物品名:物品简介（冒号支持中英文）',
      '物品名和简介会经过敏感词检查和AI内容审核',
      '同名物品不可重复添加'
    ],
    tags: [{ text: '消耗1000草', type: 'danger' }],
    category: '抽奖系统',
    subcategory: '自制物品'
  },
  {
    name: '添加-Normal',
    aliases: ['物品添加-Normal'],
    params: '物品名[:物品简介]',
    description: '添加一件Normal稀有度的自制物品到抽奖池。消耗8000草。物品名最长32字，物品简介最长1024字。提交后会进行内容审核。',
    details: [
      '参数格式：物品名 或 物品名:物品简介（冒号支持中英文）',
      '物品名和简介会经过敏感词检查和AI内容审核',
      '同名物品不可重复添加'
    ],
    tags: [{ text: '消耗8000草', type: 'danger' }],
    category: '抽奖系统',
    subcategory: '自制物品'
  },
  {
    name: '添加-Hard',
    aliases: ['物品添加-Hard'],
    params: '物品名[:物品简介]',
    description: '添加一件Hard稀有度的自制物品到抽奖池。消耗64000草。物品名最长32字，物品简介最长1024字。提交后会进行内容审核。',
    details: [
      '参数格式：物品名 或 物品名:物品简介（冒号支持中英文）',
      '物品名和简介会经过敏感词检查和AI内容审核',
      '同名物品不可重复添加'
    ],
    tags: [{ text: '消耗64000草', type: 'danger' }],
    category: '抽奖系统',
    subcategory: '自制物品'
  },
  {
    name: '添加-Lunatic',
    aliases: ['物品添加-Lunatic'],
    params: '物品名[:物品简介]',
    description: '添加一件Lunatic稀有度的自制物品到抽奖池。消耗512000草。物品名最长32字，物品简介最长1024字。提交后会进行内容审核。',
    details: [
      '参数格式：物品名 或 物品名:物品简介（冒号支持中英文）',
      '物品名和简介会经过敏感词检查和AI内容审核',
      '同名物品不可重复添加'
    ],
    tags: [{ text: '消耗512000草', type: 'danger' }],
    category: '抽奖系统',
    subcategory: '自制物品'
  },
  {
    name: '自制物品列表',
    params: '[等级名/奖池名]',
    description: '查看自己添加的所有自制物品。不传参数时按稀有度分组显示；指定等级时显示该等级下的所有自制物品，支持翻页浏览。',
    tags: [{ text: '支持翻页', type: 'info' }],
    category: '抽奖系统',
    subcategory: '自制物品'
  },
  {
    name: '物品修改',
    params: '物品名:新物品简介',
    description: '修改自己创建的抽奖物品的简介说明。只有物品的作者才能修改。修改后的内容会经过AI审核。',
    details: [
      '参数格式：物品名:新物品简介（冒号支持中英文）',
      '只有该物品的作者才能修改物品简介',
      '修改内容会经过AI内容审核，审核不通过则修改失败'
    ],
    category: '抽奖系统',
    subcategory: '自制物品'
  },
  {
    name: '物品删除',
    params: '物品名',
    description: '删除自己创建的抽奖物品。只有物品的作者才能删除。删除操作不可逆。',
    category: '抽奖系统',
    subcategory: '自制物品'
  },

  {
    name: '说点怪话',
    params: '[文本]',
    description: '输出随机一条怪话。怪话库来源于群聊聊天记录。传入文本时有一定概率使用AI从怪话库中选择语义最适宜的怪话回复。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '怪话'
  },
  {
    name: '说些怪话',
    params: '[文本]',
    description: '输出三条怪话。传入文本时有一定概率使用AI从怪话库中选择三句语义连贯的怪话组合回复，否则随机选择三条不重复的纯文本怪话。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '怪话'
  },
  {
    name: '话怪点说',
    params: '',
    description: '输出一条怪话，如果怪话是纯文本则逆序输出（反转文字顺序）。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '怪话'
  },
  {
    name: '说话怪点',
    aliases: ['怪点说话'],
    params: '',
    description: '输出一条怪话，如果怪话是纯文本则打乱文字顺序输出。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '怪话'
  },
  {
    name: '#怪话',
    params: '',
    description: '回复一条消息，以该消息内容为输入获取怪话回复。有一定概率使用AI从怪话库中选择语义最适宜的怪话回复。',
    details: [
      '仅支持回复纯文本消息',
      '此指令为说点怪话的回复触发版本，功能等价于 !说点怪话 [回复内容]'
    ],
    tags: [{ text: '回复触发', type: 'info' }, { text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '怪话'
  },

  {
    name: '晚安',
    params: '',
    description: '获取一个平均400分钟（标准差50分钟）的大口球（群内禁言）。仅在管理员授权群中生效。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '口球与睡眠'
  },
  {
    name: '午睡',
    params: '',
    description: '获取一个平均60分钟（标准差10分钟）的中型口球（群内禁言）。仅在管理员授权群中生效。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '口球与睡眠'
  },
  {
    name: '醒了',
    params: '',
    description: '获取一个平均60分钟（标准差10分钟）的中型口球（群内禁言）。仅在管理员授权群中生效。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '口球与睡眠'
  },
  {
    name: '口球',
    params: 'qq=QQ号 sec=秒数',
    description: '消耗草（1草/秒）给指定用户设置口球（群内禁言）。sec=0时为解除口球。',
    details: [
      '费用为秒数对应的草量，如sec=60则消耗60草',
      'sec=0时为解除禁言，不消耗草'
    ],
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '口球与睡眠'
  },

  {
    name: 'rolllj',
    params: '',
    description: '从罗俊图库中随机获取一张艺术处理过的罗俊图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rollpurelj',
    params: '',
    description: '从纯净罗俊图库中随机获取一张未经艺术处理的罗俊原图。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rollzh5',
    params: '',
    description: '从zh5图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rolltd',
    params: '',
    description: '从土豆图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rolljdm',
    aliases: ['rollzdm', 'rollmd'],
    params: '',
    description: '从俊达萌图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rollpurejdm',
    aliases: ['rollpurezdm', 'rollpuremd'],
    params: '',
    description: '从俊达萌美图图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rollmmc',
    aliases: ['rolllg'],
    params: '',
    description: '从猫猫虫图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rollgm',
    params: '',
    description: '从怪猫图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'roll251',
    params: '',
    description: '从251图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'rollxb',
    params: '',
    description: '从西八兔图库中随机获取一张图片。',
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },
  {
    name: 'commitpic',
    params: '[图片]',
    description: '向图库上传图片，图片将进入待分类目录等待管理员分类。',
    details: [
      '可直接附带图片发送，也可先发指令再在后续消息中上传图片',
      '上传的图片先存入待分类目录，需管理员分类后才会进入正式图库',
      '通过MD5校验自动检测并拦截图库中已有的图片'
    ],
    tags: [{ text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '图库'
  },

  {
    name: '爆柠檬',
    params: '',
    description: '发送一个柠檬emoji。',
    category: '群聊互动',
    subcategory: '其他互动'
  },
  {
    name: '#nsfw',
    params: '',
    description: '回复一张图片，检测该图片是否包含NSFW内容，返回adult/teen/everyone三个分类的概率值。回复他人图片时有1/8概率触发黑暗决斗机制。',
    details: [
      '使用ModerateContent API进行NSFW检测',
      '在特定群中有3小时冷却时间',
      '黑暗决斗：如果图片是色图，发图者被口球；否则检测者被口球',
      '无法被口球的目标会收到除草器的一拳（emoji反应）'
    ],
    tags: [{ text: '回复触发', type: 'info' }, { text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '其他互动'
  },
  {
    name: '#nailong',
    params: '',
    description: '回复一张图片，检测该图片的奶龙指数（0-100），大于50判定为奶龙图。回复他人图片时有1/8概率触发奶龙决斗机制。',
    details: [
      '使用本地ResNet50模型进行奶龙检测',
      '在特定群中有3小时冷却时间',
      '奶龙决斗：如果奶龙指数>50，发图者被口球；否则检测者被口球',
      '无法被口球的目标会收到除草器的一拳（emoji反应）'
    ],
    tags: [{ text: '回复触发', type: 'info' }, { text: '群聊', type: 'warning' }],
    category: '群聊互动',
    subcategory: '其他互动'
  },

  {
    name: 'roll',
    params: 'XdY 或 XdY-Z',
    description: '掷骰子，返回骰子点数之和。',
    details: [
      '格式 XdY：投X个1~Y面的骰子，返回总和',
      '格式 XdY-Z：投X个Y~Z面的骰子，返回总和',
      'X为1~4位数字，Y/Z为1~12位数字',
      '示例：!roll 1d100 表示投1个1~100的骰子'
    ],
    category: '实用功能',
    subcategory: 'Roll点'
  },
  {
    name: 'rollx',
    params: 'XdY 或 XdY-Z',
    description: '掷骰子（详细模式），返回每次骰子结果及总和。',
    details: [
      '与roll类似，但会显示每个骰子的具体点数',
      'X为单个数字（1~9）',
      '示例：!rollx 5d100 返回如 23+45+67+12+89=236'
    ],
    category: '实用功能',
    subcategory: 'Roll点'
  },
  {
    name: 'rollf',
    params: 'XdY 或 XdY-Z',
    description: '掷浮点数骰子，返回带2位小数的结果。',
    details: [
      '支持浮点数面数，最小值为0（而非1）',
      'Y/Z可为小数，如5.5',
      '结果保留2位小数',
      '话说都浮点数了真的能算骰子吗'
    ],
    category: '实用功能',
    subcategory: 'Roll点'
  },
  {
    name: '选择',
    params: '选项1 选项2 选项3 ...',
    description: '从给定选项中随机选择一个。同一天同一用户相同选项结果不变。',
    details: [
      '选项需要以空格分隔',
      '结果基于用户ID、选项和日期的哈希值确定',
      '示例：!选择 火锅 烧烤 麻辣烫'
    ],
    category: '实用功能',
    subcategory: 'Roll点'
  },
  {
    name: '判断',
    params: '判断内容',
    description: '对输入内容进行是/否判断。同一天同一用户相同问题结果不变。',
    category: '实用功能',
    subcategory: 'Roll点'
  },

  {
    name: '起卦',
    params: '[问题或关键词]',
    description: '周易占卜，通过掷币法生成卦象。',
    details: [
      '可选输入问题或关键词（不超过100字），不输入则直接占卜',
      '使用三硬币法模拟，生成六爻卦象',
      '输出包含：爻名（含动爻标记）、八卦符号、本卦、之卦、卦辞',
      '结果基于用户ID、输入内容和当前小时的哈希值确定',
      '起卦后可使用 !解卦 获取AI解析'
    ],
    category: '实用功能',
    subcategory: '占卜'
  },
  {
    name: '解卦',
    params: '',
    description: '使用AI对最近的起卦结果进行解卦。每日限10次。',
    details: [
      '需先使用 !起卦 命令进行占卜',
      '使用 deepseek-v4-flash 模型生成解卦内容',
      '每日解卦次数上限为10次',
      '解卦内容由AI生成，仅供参考'
    ],
    category: '实用功能',
    subcategory: '占卜'
  },

  {
    name: '公告',
    params: '',
    description: '查看Bot公告信息。',
    category: '实用功能',
    subcategory: '信息查询'
  },
  {
    name: 'news',
    params: '',
    description: '获取每日60秒读懂世界新闻图片。',
    details: [
      '数据来源：api.2xb.cn/zaob',
      '返回当日新闻概览图片',
      '每日9:00自动向配置的群推送'
    ],
    category: '实用功能',
    subcategory: '信息查询'
  },
  {
    name: '台风',
    params: '[prev 或 prevN]',
    description: '查询中央气象台台风信息。',
    details: [
      '无参数时查询当前最新台风报文',
      '输入 prev 查看上一条台风报文',
      '输入 prev2、prev3 等查看更早的报文'
    ],
    category: '实用功能',
    subcategory: '信息查询'
  },
  {
    name: '雷达回波',
    aliases: ['雷达'],
    params: '<地区> [-gif]',
    description: '查询气象雷达回波图，支持生成动态GIF。',
    details: [
      '无参数时展示使用说明与所有支持的站点',
      '正常使用必须指定地区或站点，如：全国、广州、深圳、北京等',
      '添加 -gif 参数可生成过去1小时的动态GIF图',
      '支持全国、华北、东北、华东、华中、华南、西南、西北等区域',
      '支持各省会雷达站和东南沿海主要雷达站',
      '示例：!雷达回波 全国、!雷达回波 广州 -gif'
    ],
    category: '实用功能',
    subcategory: '信息查询'
  },
  {
    name: '降雨',
    aliases: ['降水'],
    params: '',
    description: '查询中山大学各校区未来6小时降雨预报。',
    details: [
      '覆盖校区：南校园、北校园、东校园、珠海校区、深圳校区',
      '返回图片包含：各校区逐小时降水概率表 + 有降雨校区的降雨量柱状图',
      '数据来源：Open-Meteo API'
    ],
    category: '实用功能',
    subcategory: '信息查询'
  },
  {
    name: '校园网',
    params: '',
    description: '查看中山大学校园网最新公告。',
    details: [
      '数据来源：i.akarin.dev 校园网公告同步',
      '每日8:00-23:00每小时自动检测并推送新公告'
    ],
    category: '实用功能',
    subcategory: '信息查询'
  },
  {
    name: 'THANKS',
    params: '[年份]',
    description: '查看为除草器提供捐助的信息和排行榜。',
    details: [
      '可选输入年份（2020-2099）查看该年度捐助信息',
      '不输入年份则显示累计捐助信息',
      '十分感谢您对除草器的支持~'
    ],
    category: '实用功能',
    subcategory: '信息查询'
  },
  {
    name: '捐助记录',
    aliases: ['捐赠记录'],
    params: '',
    description: '查看个人的所有捐助记录。',
    details: [
      '显示每笔捐助的日期和金额',
      '十分感谢您对除草器的支持~'
    ],
    category: '实用功能',
    subcategory: '信息查询'
  },

  {
    name: '搜图',
    aliases: ['picsearch'],
    params: '[图片]',
    description: '以图搜图，使用SauceNAO、Bing、Ascii2D多引擎搜索。',
    details: [
      '直接附带图片发送指令，或先发送指令再在后续消息中上传图片',
      '搜索结果包含缩略图、标题、相似度、来源链接',
      '回复搜索结果消息并输入编号可提取对应图片URL'
    ],
    category: '实用功能',
    subcategory: '图片搜索'
  },
  {
    name: '#搜图',
    aliases: ['#picsearch'],
    params: '',
    description: '回复一张图片消息进行以图搜图，使用SauceNAO、Bing、Ascii2D多引擎搜索。',
    details: [
      '回复一张图片消息，回复内容输入 #搜图 或 #picsearch',
      '搜索结果包含缩略图、标题、相似度、来源链接',
      '回复搜索结果消息并输入编号可提取对应图片URL'
    ],
    tags: [{ text: '回复触发', type: 'info' }],
    category: '实用功能',
    subcategory: '图片搜索'
  },
  {
    name: '#picurl',
    aliases: ['#url'],
    params: '',
    description: '回复图片消息提取其原始URL。',
    tags: [{ text: '回复触发', type: 'info' }],
    category: '实用功能',
    subcategory: '图片搜索'
  },

  {
    name: 'music',
    params: '搜索关键词',
    description: '搜索网易云音乐歌曲，返回第一条搜索结果。',
    details: [
      '输出包含：歌曲链接、曲名、艺术家、专辑',
      '数据来源：网易云音乐API'
    ],
    category: '实用功能',
    subcategory: '其他'
  },
  {
    name: '点餐',
    aliases: ['saizeriya'],
    params: '预算 或 最低预算-最高预算',
    description: '根据预算随机生成萨莉亚点餐方案。',
    details: [
      '输入单个数字表示固定预算，如 !点餐 50',
      '输入范围表示预算区间，如 !点餐 30-50',
      '预算上限为500元',
      '尽可能在菜单中匹配恰好等于预算的组合',
      '输出包含菜品编号、名称、单价及总消费'
    ],
    category: '实用功能',
    subcategory: '其他'
  },
  {
    name: 'timestamp',
    params: '',
    description: '获取当前时间的Unix时间戳。',
    category: '实用功能',
    subcategory: '其他'
  },

  {
    name: 'chat',
    params: '对话内容',
    description: '开启新对话，使用当前设定的角色和模型与大模型进行对话。',
    details: [
      '开启一个全新的对话，会自动保存上一轮对话并初始化新的对话历史',
      '使用当前选择的角色设定作为系统提示词',
      '使用当前选择的模型（默认 deepseek-v4-flash）',
      '群聊中无需额外权限即可使用，私聊需要私聊权限',
      '每日有 token 用量限制，超出后无法使用'
    ],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chat5',
    aliases: ['chat4'],
    params: '对话内容',
    description: '开启新对话，强制使用 GPT-5 模型进行对话。',
    details: [
      '与 chat 类似，但强制使用 gpt-5 模型',
      '需要进阶模型权限（allowAdvancedModel）才能使用',
      'GPT-5 的 token 用量会乘以5计算'
    ],
    tags: [{ text: '需进阶模型权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chatn',
    params: '对话内容',
    description: '开启新对话，无视当前角色设定，使用默认角色进行对话。',
    details: [
      '与 chat 类似，但忽略用户当前选择的角色，使用默认角色',
      '群聊中无需额外权限即可使用，私聊需要私聊权限'
    ],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chatn5',
    aliases: ['chatn4'],
    params: '对话内容',
    description: '开启新对话，无视当前角色设定并强制使用 GPT-5 模型进行对话。',
    details: [
      '同时具备 chatn（使用默认角色）和 chat5（使用GPT-5模型）的特性',
      '需要进阶模型权限'
    ],
    tags: [{ text: '需进阶模型权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chatc',
    params: '对话内容',
    description: '继续上一轮对话，在当前对话历史中追加消息。',
    details: [
      '不会创建新对话，而是在已有的对话历史基础上继续对话',
      '保留先前对话历史中的角色设定和上下文'
    ],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chatc5',
    aliases: ['chatc4'],
    params: '对话内容',
    description: '继续上一轮对话，强制使用 GPT-5 模型。',
    details: [
      '与 chatc 类似，但强制使用 gpt-5 模型',
      '需要进阶模型权限（allowAdvancedModel）'
    ],
    tags: [{ text: '需进阶模型权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chatb',
    params: '',
    description: '撤回最后一轮对话（包括用户消息和AI回复）。',
    details: [
      '撤回对话历史中最后一组用户消息和AI回复',
      '如果对话历史不足2条消息，则提示没有可撤回的对话'
    ],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chatr',
    params: '[新内容]',
    description: '撤回最后一轮对话并重新生成回复。',
    details: [
      '先撤回最后一轮对话（用户消息+AI回复），然后重新发送消息获取新回复',
      '如果提供了新内容参数，则使用新内容替代原消息重新生成；否则使用原用户消息重新生成'
    ],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chatr5',
    aliases: ['chatr4'],
    params: '[新内容]',
    description: '撤回最后一轮对话并使用 GPT-5 模型重新生成回复。',
    details: [
      '与 chatr 类似，但强制使用 gpt-5 模型重新生成',
      '需要进阶模型权限（allowAdvancedModel）'
    ],
    tags: [{ text: '需进阶模型权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '基础对话'
  },
  {
    name: 'chat_help',
    params: '',
    description: '查看 ChatBot 对话功能的帮助信息。',
    details: [
      '显示所有可用的 chat 指令及其简要说明',
      '根据用户权限动态显示可用指令'
    ],
    category: 'ChatBot',
    subcategory: '基础对话'
  },

  {
    name: 'role_update',
    params: '[-p] 角色名称[:角色描述]',
    description: '新增或更新角色描述信息。添加 -p 或 -public 前缀可将角色设为公共角色。',
    details: [
      '使用冒号（中英文均可）分隔角色名称和角色描述',
      '如果角色名称已存在则更新描述，否则创建新角色',
      '添加 -p 或 -public 前缀可将角色设为公共角色（所有用户可见）',
      '公共角色名称不能与已有公共角色重名',
      '需要角色权限（allowRole）'
    ],
    tags: [{ text: '需角色权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '角色设定'
  },
  {
    name: 'role_delete',
    params: '角色名称',
    description: '删除指定角色。只能删除自己创建的角色。',
    details: [
      '只能删除自己创建的角色',
      '删除角色后，正在使用该角色的用户会被自动切换回默认角色',
      '需要角色权限（allowRole）'
    ],
    tags: [{ text: '需角色权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '角色设定'
  },
  {
    name: 'role_detail',
    params: '角色名称',
    description: '查看指定角色的描述信息。只能查看自己创建的角色或公共角色。',
    tags: [{ text: '需角色权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '角色设定'
  },
  {
    name: 'role_change',
    params: '[角色名称]',
    description: '切换当前使用的角色。不提供角色名称时切换到默认角色。',
    details: [
      '可以切换到自己创建的角色或公共角色',
      '无法切换到他人的私人角色',
      '需要角色权限（allowRole）'
    ],
    tags: [{ text: '需角色权限', type: 'warning' }],
    category: 'ChatBot',
    subcategory: '角色设定'
  },

  {
    name: 'model_change',
    params: '[模型名称]',
    description: '切换对话使用的语言模型。不提供参数时默认切换到 deepseek-chat。',
    details: [
      '支持的预设模型：deepseek-chat、deepseek-r（映射为 deepseek-reasoner）、gpt-5-mini、gpt-5（需进阶模型权限）、gemini-2.5-flash、gemini-2.5-pro（需管理员权限）',
      '也可以输入自定义模型名称，但会提示可能报错'
    ],
    category: 'ChatBot',
    subcategory: '模型与存档'
  },
  {
    name: 'chat_save',
    aliases: ['save_conversation'],
    params: '[存档名称]',
    description: '手动保存当前对话记录。',
    details: [
      '将当前对话历史保存为 JSON 文件',
      '不提供名称时自动生成：如果有角色名则使用"角色名_时间戳"，否则仅使用时间戳'
    ],
    category: 'ChatBot',
    subcategory: '模型与存档'
  },
  {
    name: 'chat_load',
    aliases: ['load_conversation'],
    params: '[序号]',
    description: '加载已保存的对话记录。',
    details: [
      '不提供参数时显示可加载的对话记录列表（按修改时间倒序，最多显示10条）',
      '提供序号时加载对应的对话记录并替换当前对话',
      '加载后会显示对话记录名称和上一轮对话内容预览'
    ],
    category: 'ChatBot',
    subcategory: '模型与存档'
  },
  {
    name: 'chat_user',
    params: '',
    description: '查看当前用户的 ChatBot 权限和使用信息。',
    details: [
      '显示总 token 用量、当日 token 用量/限额',
      '显示当前拥有的权限：私聊、角色切换、进阶模型',
      '显示当前使用的模型名称',
      '有角色权限时额外显示当前角色、自建角色列表和公共角色列表'
    ],
    category: 'ChatBot',
    subcategory: '模型与存档'
  },

  {
    name: 'help',
    params: '',
    description: '查看除草器功能说明。',
    category: '杂项',
    subcategory: '杂项'
  },
  {
    name: '生草系统',
    params: '',
    description: '查看生草系统指令帮助。',
    category: '杂项',
    subcategory: '杂项'
  },
  {
    name: '提交工单',
    params: '标题[:详情]',
    description: '向开发者提交工单反馈问题或建议。',
    details: [
      '使用冒号（中英文均可）分隔标题和详情',
      '标题最多128字，详情最多1024字',
      '至少需要提供标题'
    ],
    category: '杂项',
    subcategory: '杂项'
  },
  {
    name: '下一页',
    aliases: ['next', 'n'],
    params: '',
    description: '在分页内容中翻到下一页。适用于所有支持分页的功能。',
    details: [
      '全局翻页命令，适用于仓库、搜索、交易记录等分页展示的指令',
      '需要先使用带分页功能的命令建立翻页状态',
      '已经是最后一页时会提示'
    ],
    category: '杂项',
    subcategory: '杂项'
  },
  {
    name: '上一页',
    aliases: ['prev', 'p', 'previous'],
    params: '',
    description: '在分页内容中翻到上一页。适用于所有支持分页的功能。',
    details: [
      '全局翻页命令，适用于所有支持分页的功能',
      '已经是第一页时会提示'
    ],
    category: '杂项',
    subcategory: '杂项'
  }
]

export const categories = [
  { name: '生草系统', subcategories: ['生草', '仓库与能力', '商店与道具', '用户交互', 'G市', '统计'] },
  { name: '抽奖系统', subcategories: ['基础指令', '自制物品'] },
  { name: '群聊互动', subcategories: ['怪话', '口球与睡眠', '图库', '其他互动'] },
  { name: '实用功能', subcategories: ['Roll点', '占卜', '信息查询', '图片搜索', '其他'] },
  { name: 'ChatBot', subcategories: ['基础对话', '角色设定', '模型与存档'] },
  { name: '杂项', subcategories: ['杂项'] }
]
