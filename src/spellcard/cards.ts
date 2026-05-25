import type { Battler, CardData } from './engine';
import { rollDice, SeededRandom } from './engine';

export const ALL_CARDS: CardData[] = [
  { id: 0, cost: 0, name: '非符', cardHp: 4, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2', description: '无' },
  { id: 1, cost: 2, name: '「妖怪破坏者」', cardHp: 3, atkPoint: '1d8', defPoint: '1d2', dodPoint: '1d2', description: '无' },
  { id: 2, cost: 1, name: '「扩散灵符」', cardHp: 4, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '无' },
  { id: 3, cost: 2, name: '「警醒阵」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2+2', dodPoint: '1d2', description: '无' },
  {
    id: 4, cost: 1, name: '「博丽护符」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '宣言时：获得[追踪1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendEffect('Trace', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Trace', 1); return '' },
  },
  {
    id: 5, cost: 1, name: '「弦月斩」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '宣言时：造成2点直接伤害',
    onCardSet(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡宣言效果：造成2点直接伤害\n` + info
    },
  },
  {
    id: 6, cost: 1, name: '「炯眼剑」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '被击破时：造成2点直接伤害',
    onCardBreak(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡终止效果：造成2点直接伤害\n` + info
    },
  },
  {
    id: 7, cost: 2, name: '「人偶振起」', cardHp: 4, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d2+1',
    description: '每回合开始时：获得[强化1]',
    onTurnStart(user: Battler, _enemy: Battler) { user.appendEffect('Strength', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Strength', 999); return '' },
  },
  {
    id: 8, cost: 1, name: '「人偶置操」', cardHp: 4, atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d2',
    description: '宣言时：获得[缓冲1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendEffect('Buffer', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Buffer', 1); return '' },
  },
  {
    id: 9, cost: 2, name: '「乾神招来 风」', cardHp: 7, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '宣言时：获得[追击1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendEffect('Chase', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Chase', 1); return '' },
  },
  {
    id: 10, cost: 1, name: '「坤神招来 盾」', cardHp: 1, atkPoint: '1d6', defPoint: '1d1-1', dodPoint: '1d1-1',
    description: '被击破时：获得永续的[护盾3]',
    onCardBreak(user: Battler, _enemy: Battler) { user.appendEffect('Shield', 3); return '下一张符卡获得3点护盾！\n' },
  },
  {
    id: 11, cost: 1, name: '「红寸劲」', cardHp: 4, atkPoint: '1d4', defPoint: '1d1', dodPoint: '1d2',
    description: '宣言时：对方获得[防御不可]',
    onCardSet(user: Battler, enemy: Battler) { enemy.appendEffect('CantDefence', -1); return `[${user.name}]本符卡对方无法防御！\n` },
    onCardBreak(_user: Battler, enemy: Battler) { enemy.removeEffect('CantDefence'); return '' },
  },
  {
    id: 12, cost: 2, name: '梦符「封魔阵」', cardHp: 6, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2',
    description: '宣言时：展开5回合的[伤害结界1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendBorder('DamageBorder', 5, 1); return `[${user.name}]展开了持续5回合的[伤害结界1]！\n` },
  },
  {
    id: 13, cost: 1, name: '暗符「境界线」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d3+1',
    description: '无',
  },
  {
    id: 14, cost: 3, name: '冻符「完美冻结」', cardHp: 9, atkPoint: '1d9', defPoint: '1d1-1', dodPoint: '1d1-1',
    description: '每回合开始时：获得[弱化1]；宣言时：赋予[冻结]',
    onCardSet(_user: Battler, enemy: Battler) { enemy.appendEffect('Freeze', 1); return '' },
    onTurnStart(user: Battler, _enemy: Battler) { user.appendEffect('Weaken', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Weaken', 999); return '' },
  },
  {
    id: 15, cost: 2, name: '虹符「彩虹的风铃」', cardHp: 6, atkPoint: '1d6', defPoint: '1d(2~2)', dodPoint: '1d2',
    description: '宣言时；被击破时：造成2点直接伤害',
    onCardSet(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡宣言效果：造成2点直接伤害\n` + info
    },
    onCardBreak(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡终止效果：造成2点直接伤害\n` + info
    },
  },
  { id: 16, cost: 4, name: '三华「崩山彩极炮」', cardHp: 8, atkPoint: '2d3+1d4', defPoint: '1d4', dodPoint: '1d2', description: '无' },
  {
    id: 17, cost: 2, name: '火符「火神之光」', cardHp: 7, atkPoint: '1d1-1', defPoint: '1d3', dodPoint: '1d2',
    description: '每回合开始时：造成2点直接伤害',
    onTurnStart(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡效果：造成2点直接伤害\n` + info
    },
  },
  {
    id: 18, cost: 2, name: '水符「水精公主」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2',
    description: '受到致命伤害时，免疫此次伤害（只能发动一次）',
    onCardSet(user: Battler, _enemy: Battler) { user.appendEffect('Unbreakable', 1); return '' },
  },
  {
    id: 19, cost: 2, name: '木符「风灵的角笛」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2',
    description: '偶数回合开始时：获得仅本回合生效的[灵动2]',
    onTurnStart(user: Battler, _enemy: Battler) {
      if (user.gameRound % 2 === 0) { user.appendEffect('Agile', 2) }
      return ''
    },
    onTurnEnd(user: Battler, _enemy: Battler) { user.removeEffect('Agile', 2); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Agile', 2); return '' },
  },
  {
    id: 20, cost: 2, name: '金符「金属疲劳」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2',
    description: '宣言时：展开5回合的[脆弱结界]',
    onCardSet(_user: Battler, enemy: Battler) { enemy.appendBorder('FragileBorder', 5, 1); return '' },
  },
  {
    id: 21, cost: 2, name: '土符「慵懒三石塔」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2',
    description: '宣言时：获得[缓冲1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendEffect('Buffer', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Buffer', 1); return '' },
  },
  { id: 22, cost: 4, name: '红符「深红射击」', cardHp: 2, atkPoint: '2d10', defPoint: '1d1', dodPoint: '1d1', description: '无' },
  {
    id: 23, cost: 2, name: '禁忌「笼中鸟」', cardHp: 6, atkPoint: '1d3', defPoint: '1d4', dodPoint: '1d3',
    description: '宣言时：对方获得[回避不可]',
    onCardSet(_user: Battler, enemy: Battler) { enemy.appendEffect('CantDodge', -1); return '' },
    onCardBreak(_user: Battler, enemy: Battler) { enemy.removeEffect('CantDodge'); return '' },
  },
  {
    id: 24, cost: 3, name: '禁忌「四重存在」', cardHp: 4, atkPoint: '1d4', defPoint: '1d4', dodPoint: '1d1-1',
    description: '被击破时：展开4回合的[强化结界1d4]',
    onCardBreak(user: Battler, _enemy: Battler) {
      const rng = new SeededRandom()
      const strength = rollDice('1d4', rng)
      user.appendBorder('StrengthBorder', 4, strength)
      return `${user.name}符卡破弃效果：展开4回合的[强化结界${strength}]！`
    },
  },
  {
    id: 25, cost: 4, name: '禁弹「星弧破碎」', cardHp: 10, atkPoint: '1d6', defPoint: '1d4', dodPoint: '1d2',
    description: '宣言时：造成x点伤害，x为你的剩余符卡数',
    onCardSet(user: Battler, enemy: Battler) {
      const hurtValue = 5 - user.usedCardIndices.length + 1
      const info = enemy.effectHurt(hurtValue)
      return `[${user.name}]符卡效果：造成${hurtValue}点直接伤害\n` + info
    },
  },
  // 红魔乡 - 露米娅
  { id: 26, cost: 1, name: '月符「Moonlight Ray」', cardHp: 4, atkPoint: '1d5', defPoint: '1d2', dodPoint: '1d2', description: '宣言时：对方获得[迟缓1]', character: 'rumia', onCardSet(_u, e) { e.appendEffect('Sluggish', 1); return `[${_u.name}]月光照射！对方获得迟缓1\n` }, onCardBreak(_u, e) { e.removeEffect('Sluggish', 1); return '' } },
  { id: 27, cost: 1, name: '夜符「Night Bird」', cardHp: 5, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d3', description: '无', character: 'rumia' },
  { id: 28, cost: 1, name: '暗符「Demarcation」', cardHp: 5, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2', description: '宣言时：对方获得[弱化1]', character: 'rumia', onCardSet(_u, e) { e.appendEffect('Weaken', 1); return `[${_u.name}]黑暗边界！对方获得弱化1\n` }, onCardBreak(_u, e) { e.removeEffect('Weaken', 1); return '' } },
  // 红魔乡 - 琪露诺
  { id: 29, cost: 1, name: '雹符「Hailstorm」', cardHp: 5, atkPoint: '1d7', defPoint: '1d1', dodPoint: '1d2', description: '宣言时：造成1点直接伤害', character: 'cirno', onCardSet(u, e) { const info = e.effectHurt(1); return `[${u.name}]冰雹暴风！造成1点直接伤害\n${info}` } },
  { id: 30, cost: 2, name: '雪符「Diamond Blizzard」', cardHp: 6, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d3', description: '宣言时：展开3回合的[迟缓结界1]', character: 'cirno', onCardSet(u, e) { e.appendBorder('SluggishBorder', 3, 1); return `[${u.name}]钻石风暴！\n` } },
  // 红魔乡 - 红美铃
  { id: 31, cost: 1, name: '华符「Selaginella 9」', cardHp: 6, atkPoint: '1d5', defPoint: '1d2', dodPoint: '1d2', description: '宣言时：获得[追击1]', character: 'meiling', onCardSet(u, _e) { u.appendEffect('Chase', 1); return `[${u.name}]卷柏之力！获得追击1\n` } },
  { id: 32, cost: 2, name: '幻符「华想梦葛」', cardHp: 7, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d3', description: '宣言时：获得[荆棘1]', character: 'meiling', onCardSet(u, _e) { u.appendEffect('Thorns', 1); return `[${u.name}]以柔克刚！获得荆棘1\n` } },
  { id: 33, cost: 2, name: '彩符「彩光乱舞」', cardHp: 6, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：获得[连击2]', character: 'meiling', onCardSet(u, _e) { u.appendEffect('Combo', 2); return `[${u.name}]弹幕乱舞！获得连击2\n` } },
  { id: 34, cost: 2, name: '彩符「极彩台风」', cardHp: 7, atkPoint: '2d4', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：对方获得[破甲]', character: 'meiling', onCardSet(_u, e) { e.appendEffect('CantDefence', -1, '破甲'); return `[${_u.name}]台风！对方获得破甲\n` }, onCardBreak(_u, e) { e.removeEffect('CantDefence'); return '' } },
  // 红魔乡 - 帕秋莉
  { id: 35, cost: 3, name: '火符「Agni Radiance」', cardHp: 6, atkPoint: '1d8', defPoint: '1d1', dodPoint: '1d2', description: '宣言时：造成3点直接伤害', character: 'patchouli', onCardSet(u, e) { const info = e.effectHurt(3); return `[${u.name}]火神的光辉！造成3点直接伤害\n${info}` } },
  { id: 36, cost: 3, name: '水符「Bury in Lake」', cardHp: 8, atkPoint: '1d4', defPoint: '1d4', dodPoint: '1d3', description: '宣言时：获得[击破保护1]', character: 'patchouli', onCardSet(u, _e) { u.appendEffect('Unbreakable', 1); return `[${u.name}]湖葬！获得击破保护1\n` } },
  { id: 37, cost: 3, name: '木符「Green Storm」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d3', description: '每回合开始时：展开2回合的[迟缓结界1]', character: 'patchouli', onTurnStart(u, e) { e.appendBorder('SluggishBorder', 2, 1); return `[${u.name}]绿色风暴！\n` } },
  { id: 38, cost: 3, name: '金符「Silver Dragon」', cardHp: 7, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：展开3回合的[脆弱结界1]', character: 'patchouli', onCardSet(u, _e) { u.appendBorder('FragileBorder', 3, 1); return `[${u.name}]银龙！\n` } },
  { id: 39, cost: 3, name: '土符「Trilithon Shake」', cardHp: 9, atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：获得[缓冲1]', character: 'patchouli', onCardSet(u, _e) { u.appendEffect('Buffer', 1); return `[${u.name}]三石塔震动！获得缓冲1\n` } },
  { id: 40, cost: 3, name: '火&土符「Lava Cromlech」', cardHp: 7, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：造成2点直接伤害；获得[缓冲1]', character: 'patchouli', onCardSet(u, _e) { const info = u.enemy!.effectHurt(2); u.appendEffect('Buffer', 1); return `[${u.name}]熔岩环石阵！\n${info}` } },
  { id: 41, cost: 3, name: '木&火符「Forest Blaze」', cardHp: 7, atkPoint: '1d7', defPoint: '1d2', dodPoint: '1d2', description: '宣言时：获得[追击2]', character: 'patchouli', onCardSet(u, _e) { u.appendEffect('Chase', 2); return `[${u.name}]森林大火！获得追击2\n` } },
  { id: 42, cost: 3, name: '水&木符「Water Elf」', cardHp: 8, atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d3', description: '每回合开始时：获得[灵动1]；回合结束时：失去[灵动1]', character: 'patchouli', onTurnStart(u, _e) { u.appendEffect('Agile', 1); return `[${u.name}]水精灵之舞！\n` }, onTurnEnd(u, _e) { u.removeEffect('Agile', 1); return '' } },
  { id: 43, cost: 4, name: '金&水符「Mercury Poison」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：展开5回合的[弱化结界1]；对方获得[迟缓1]', character: 'patchouli', onCardSet(u, e) { u.appendBorder('WeakenBorder', 5, 1); e.appendEffect('Sluggish', 1); return `[${u.name}]水银之毒！\n` } },
  { id: 44, cost: 4, name: '土&金符「Emerald Megalith」', cardHp: 9, atkPoint: '1d4', defPoint: '1d4+2', dodPoint: '1d2', description: '宣言时：获得[护盾3]', character: 'patchouli', onCardSet(u, _e) { u.appendEffect('Shield', 3); return `[${u.name}]祖母绿巨石！获得护盾3\n` } },
  { id: 45, cost: 4, name: '月符「Silent Selene」', cardHp: 9, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3', description: '宣言时：展开4回合的[伤害结界1d3]', character: 'patchouli', onCardSet(u, _e) { const rng = new SeededRandom(); const str = rollDice('1d3', rng); u.appendBorder('DamageBorder', 4, str); return `[${u.name}]沉静的月神！展开4回合的[伤害结界${str}]\n` } },
  { id: 46, cost: 5, name: '日符「Royal Flare」', cardHp: 7, atkPoint: '2d8', defPoint: '1d1', dodPoint: '1d1', description: '宣言时：造成4点直接伤害；每回合开始时：获得[弱化1]', character: 'patchouli', onCardSet(u, e) { const info = e.effectHurt(4); return `[${u.name}]皇家烈焰！造成4点直接伤害\n${info}` }, onTurnStart(u, _e) { u.appendEffect('Weaken', 1); return `[${u.name}]烈焰反噬！获得弱化1\n` } },
  { id: 47, cost: 5, name: '火水木金土符「贤者之石」', cardHp: 12, atkPoint: '1d6', defPoint: '1d4', dodPoint: '1d3', description: '每回合开始时：获得[强化1][稳固1]；回合结束时：获得[弱化1]', character: 'patchouli', onTurnStart(u, _e) { u.appendEffect('Strength', 1); u.appendEffect('Stable', 1); return `[${u.name}]贤者之石！获得强化1、稳固1\n` }, onTurnEnd(u, _e) { u.appendEffect('Weaken', 1); return `[${u.name}]贤者之石的代价！获得弱化1\n` } },
  // 红魔乡 - 咲夜
  { id: 48, cost: 3, name: '奇术「幻惑Misdirection」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d4+2', description: '宣言时：对方获得[迟缓2]', character: 'sakuya', onCardSet(_u, e) { e.appendEffect('Sluggish', 2); return `[${_u.name}]误导！对方获得迟缓2\n` }, onCardBreak(_u, e) { e.removeEffect('Sluggish', 2); return '' } },
  { id: 49, cost: 3, name: '幻幽「Jack the Ludo Bile」', cardHp: 7, atkPoint: '1d6', defPoint: '1d2', dodPoint: '1d3', description: '宣言时：获得[追踪2]', character: 'sakuya', onCardSet(u, _e) { u.appendEffect('Trace', 2); return `[${u.name}]迷幻的杰克！获得追踪2\n` } },
  { id: 50, cost: 4, name: '幻世「The World」', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：对方获得[时停1]；获得[强化2]', character: 'sakuya', onCardSet(u, e) { e.appendEffect('Freeze', 1, '时停'); u.appendEffect('Strength', 2); return `[${u.name}]THE WORLD！对方获得时停1，自身获得强化2\n` }, onCardBreak(_u, e) { e.removeEffect('Freeze'); return '' } },
  { id: 51, cost: 3, name: '女仆秘技「杀人玩偶」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2', description: '宣言时：获得[连击3]；每回合开始时：获得[强化1]', character: 'sakuya', onCardSet(u, _e) { u.appendEffect('Combo', 3); return `[${u.name}]杀人玩偶！获得连击3\n` }, onTurnStart(u, _e) { u.appendEffect('Strength', 1); return `[${u.name}]飞刀越打越痛！获得强化1\n` } },
  { id: 52, cost: 5, name: '奇术「Eternal Meek」', cardHp: 6, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d3', description: '每回合开始时：造成1d4点伤害；获得[追击1d3]', character: 'sakuya', onTurnStart(u, e) { const rng = new SeededRandom(); const dmg = rollDice('1d4', rng); const chaseAmt = rollDice('1d3', rng); const info = e.effectHurt(dmg); u.appendEffect('Chase', chaseAmt); return `[${u.name}]永恒的温柔！造成${dmg}点伤害，获得追击${chaseAmt}\n${info}` } },
  // 红魔乡 - 蕾米莉亚
  { id: 53, cost: 4, name: '神罚「年幼的恶魔之王」', cardHp: 9, atkPoint: '1d8', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：获得[吸血1]', character: 'remilia', onCardSet(u, _e) { u.appendEffect('Drain', 1); return `[${u.name}]恶魔之王！获得吸血1\n` } },
  { id: 54, cost: 4, name: '狱符「千根针的针山」', cardHp: 8, atkPoint: '2d4', defPoint: '1d2', dodPoint: '1d2', description: '宣言时：对方获得[迟缓2]；获得[追击2]', character: 'remilia', onCardSet(u, e) { e.appendEffect('Sluggish', 2); u.appendEffect('Chase', 2); return `[${u.name}]千根针！\n` }, onCardBreak(_u, e) { e.removeEffect('Sluggish', 2); return '' } },
  { id: 55, cost: 4, name: '神术「吸血鬼幻想」', cardHp: 9, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：获得[吸血1]；展开3回合的[强化结界2]', character: 'remilia', onCardSet(u, _e) { u.appendEffect('Drain', 1); u.appendBorder('StrengthBorder', 3, 2); return `[${u.name}]吸血鬼幻想！\n` } },
  { id: 56, cost: 5, name: '红符「Scarlet Meister」', cardHp: 8, atkPoint: '2d6', defPoint: '1d2', dodPoint: '1d1', description: '宣言时：获得[吸血2][追击2]', character: 'remilia', onCardSet(u, _e) { u.appendEffect('Drain', 2); u.appendEffect('Chase', 2); return `[${u.name}]绯红之主！获得吸血2、追击2\n` } },
  { id: 57, cost: 5, name: '「红色的幻想乡」', cardHp: 10, atkPoint: '1d8', defPoint: '1d3', dodPoint: '1d3', description: '宣言时：获得[吸血1]；展开5回合的[伤害结界1]', character: 'remilia', onCardSet(u, _e) { u.appendEffect('Drain', 1); u.appendBorder('DamageBorder', 5, 1); return `[${u.name}]红色的幻想乡！\n` } },
  // 红魔乡 - 芙兰朵露
  { id: 58, cost: 4, name: '禁忌「Cranberry Trap」', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：获得[荆棘1]', character: 'flandre', onCardSet(u, _e) { u.appendEffect('Thorns', 1); return `[${u.name}]蔓越莓陷阱！获得荆棘1\n` } },
  { id: 59, cost: 4, name: '禁忌「Laevatein」', cardHp: 6, atkPoint: '2d8', defPoint: '1d1-1', dodPoint: '1d1', description: '宣言时：对方获得[贯穿]', character: 'flandre', onCardSet(_u, e) { e.appendEffect('CantDefence', -1, '贯穿'); return `[${_u.name}]莱瓦汀！对方获得贯穿\n` }, onCardBreak(_u, e) { e.removeEffect('CantDefence'); return '' } },
  { id: 60, cost: 4, name: '禁忌「恋之迷宫」', cardHp: 8, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d3', description: '宣言时：对方获得[迟缓2][回避不可]', character: 'flandre', onCardSet(_u, e) { e.appendEffect('Sluggish', 2); e.appendEffect('CantDodge', -1); return `[${_u.name}]恋之迷宫！\n` }, onCardBreak(_u, e) { e.removeEffect('Sluggish', 2); e.removeEffect('CantDodge'); return '' } },
  { id: 61, cost: 4, name: '禁弹「Catadioptric」', cardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2', description: '宣言时：获得[荆棘1]；每回合开始时：获得[追踪1]', character: 'flandre', onCardSet(u, _e) { u.appendEffect('Thorns', 1); return `[${u.name}]折反射！获得荆棘1\n` }, onTurnStart(u, _e) { u.appendEffect('Trace', 1); return `[${u.name}]弹幕反射！获得追踪1\n` } },
  { id: 62, cost: 5, name: '禁弹「刻着过去的钟表」', cardHp: 9, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2', description: '每回合开始时：获得[强化1][稳固1]', character: 'flandre', onTurnStart(u, _e) { u.appendEffect('Strength', 1); u.appendEffect('Stable', 1); return `[${u.name}]时钟滴答！获得强化1、稳固1\n` } },
  { id: 63, cost: 5, name: '秘弹「之后就一个人都没有了吗？」', cardHp: 3, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d3', description: '[时符3]；每回合开始时：造成2点直接伤害', character: 'flandre', isTimeCard: true, timeCardTurns: 3, onTurnStart(u, e) { const info = e.effectHurt(2); return `[${u.name}]无人生还！造成2点直接伤害\n${info}` } },
  { id: 64, cost: 5, name: 'QED「495年的波纹」', cardHp: 14, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '渐强：HP≤75%获得[强化2]；≤50%额外[追击2]；≤25%额外[吸血1]', character: 'flandre', onTurnStart(u, _e) { const hp = u.nowHp; const maxHp = u.nowCard!.cardHp; const msgs: string[] = []; if (hp <= maxHp * 0.75) { u.appendEffect('Strength', 2); msgs.push('强化2'); } if (hp <= maxHp * 0.5) { u.appendEffect('Chase', 2); msgs.push('追击2'); } if (hp <= maxHp * 0.25) { u.appendEffect('Drain', 1); msgs.push('吸血1'); } return msgs.length > 0 ? `[${u.name}]495年的波纹！获得${msgs.join('、')}\n` : ''; } },
]

export function getRandomCards(count: number): CardData[] {
  const shuffled = [...ALL_CARDS].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, Math.min(count, shuffled.length))
}