import type { Battler, CardData } from './engine';
import { rollDice, SeededRandom } from './engine';

export const ALL_CARDS: CardData[] = [
  { id: 0, cost: 0, name: '非符', cardHp: 4, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2', description: '无' },
  { id: 1, cost: 1, name: '「妖怪破坏者」', cardHp: 3, atkPoint: '1d8', defPoint: '1d2', dodPoint: '1d2', description: '无' },
  { id: 2, cost: 1, name: '「扩散灵符」', cardHp: 4, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d2', description: '无' },
  { id: 3, cost: 1, name: '「警醒阵」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2+2', dodPoint: '1d2', description: '无' },
  {
    id: 4, cost: 1, name: '「博丽护符」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '宣言时：获得[追踪1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendEffect('Trace', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Trace', 1); return '' },
  },
  {
    id: 5, cost: 1, name: '「弦月斩」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '宣言时：造成2点伤害',
    onCardSet(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡宣言效果：造成2点直接伤害\n` + info
    },
  },
  {
    id: 6, cost: 1, name: '「炯眼剑」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '破弃时：造成2点伤害',
    onCardBreak(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡终止效果：造成2点直接伤害\n` + info
    },
  },
  {
    id: 7, cost: 1, name: '「人偶振起」', cardHp: 4, atkPoint: '1', defPoint: '0', dodPoint: '1d2+1',
    description: '回合开始时：获得[强化1]',
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
    id: 9, cost: 1, name: '「乾神招来 风」', cardHp: 7, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
    description: '宣言时：获得[追击1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendEffect('Chase', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Chase', 1); return '' },
  },
  {
    id: 10, cost: 1, name: '「坤神招来 盾」', cardHp: 1, atkPoint: '1d6', defPoint: '0', dodPoint: '0',
    description: '破弃时：获得永续的[护盾3]',
    onCardBreak(user: Battler, _enemy: Battler) { user.appendEffect('Shield', 3); return '下一张符卡获得3点护盾！\n' },
  },
  {
    id: 11, cost: 1, name: '「红寸劲」', cardHp: 4, atkPoint: '1d4', defPoint: '1', dodPoint: '1d2',
    description: '宣言时：对方[防御不可]',
    onCardSet(user: Battler, enemy: Battler) { enemy.appendEffect('CantDefence', 1); return `[${user.name}]本符卡对方无法防御！\n` },
    onCardBreak(_user: Battler, enemy: Battler) { enemy.removeEffect('CantDefence', 1); return '' },
  },
  {
    id: 12, cost: 2, name: '梦符「封魔阵」', cardHp: 6, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2',
    description: '宣言时：展开5回合的[伤害结界1]',
    onCardSet(user: Battler, _enemy: Battler) { user.appendBorder('DamageBorder', 5, 1); return `[${user.name}]展开了持续5回合的[伤害结界1]！\n` },
  },
  {
    id: 13, cost: 2, name: '暗符「境界线」', cardHp: 6, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d3+1',
    description: '无',
  },
  {
    id: 14, cost: 3, name: '冻符「完美冻结」', cardHp: 9, atkPoint: '1d9', defPoint: '0', dodPoint: '0',
    description: '回合开始时：获得[弱化1]；宣言时：赋予[冻结]',
    onCardSet(_user: Battler, enemy: Battler) { enemy.appendEffect('Freeze', 1); return '' },
    onTurnStart(user: Battler, _enemy: Battler) { user.appendEffect('Weaken', 1); return '' },
    onCardBreak(user: Battler, _enemy: Battler) { user.removeEffect('Weaken', 999); return '' },
  },
  {
    id: 15, cost: 2, name: '虹符「彩虹的风铃」', cardHp: 6, atkPoint: '1d6', defPoint: '2', dodPoint: '1d2',
    description: '宣言时，破弃时：造成2点伤害',
    onCardSet(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡宣言效果：造成2点直接伤害\n` + info
    },
    onCardBreak(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]符卡终止效果：造成2点直接伤害\n` + info
    },
  },
  { id: 16, cost: 3, name: '三华「崩山彩极炮」', cardHp: 8, atkPoint: '2d3+1d4', defPoint: '1d4', dodPoint: '1d2', description: '无' },
  {
    id: 17, cost: 2, name: '火符「火神之光」', cardHp: 7, atkPoint: '0', defPoint: '1d3', dodPoint: '1d2',
    description: '回合开始时：造成2点伤害',
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
  { id: 22, cost: 3, name: '红符「深红射击」', cardHp: 2, atkPoint: '2d10', defPoint: '1', dodPoint: '1', description: '无' },
  {
    id: 23, cost: 2, name: '禁忌「笼中鸟」', cardHp: 6, atkPoint: '1d3', defPoint: '1d4', dodPoint: '1d3',
    description: '宣言时：对方[回避不可]',
    onCardSet(_user: Battler, enemy: Battler) { enemy.appendEffect('CantDodge', 1); return '' },
    onCardBreak(_user: Battler, enemy: Battler) { enemy.removeEffect('CantDodge', 1); return '' },
  },
  {
    id: 24, cost: 3, name: '禁忌「四重存在」', cardHp: 4, atkPoint: '1d4', defPoint: '1d4', dodPoint: '0',
    description: '破弃时：展开4回合的[强化结界1d4]',
    onCardBreak(user: Battler, _enemy: Battler) {
      const rng = new SeededRandom()
      const strength = rollDice('1d4', rng)
      user.appendBorder('StrengthBorder', 4, strength)
      return `${user.name}符卡破弃效果：展开4回合的[强化结界${strength}]！`
    },
  },
  {
    id: 25, cost: 3, name: '禁弹「星弧破碎」', cardHp: 10, atkPoint: '1d6', defPoint: '1d4', dodPoint: '1d2',
    description: '宣言时：造成x点伤害，x为你的剩余符卡数',
    onCardSet(user: Battler, enemy: Battler) {
      const hurtValue = 5 - user.usedCardIndices.length + 1
      const info = enemy.effectHurt(hurtValue)
      return `[${user.name}]符卡效果：造成${hurtValue}点直接伤害\n` + info
    },
  },
]

export function getRandomCards(count: number): CardData[] {
  const shuffled = [...ALL_CARDS].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, Math.min(count, shuffled.length))
}