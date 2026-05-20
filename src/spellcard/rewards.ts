import type { Battler } from './engine'
import { rollDice, SeededRandom } from './engine'
import type { DiceUpgrade, EffectModule, ExtraSlotReward, Reward, ShopItem, StatUpgrade } from './expedition'

const EFFECT_POOL: EffectModule[] = [
  {
    id: 'set_damage1', displayName: '宣言·造成1伤害', slot: 'onCardSet', rarity: 'common',
    description: '宣言时对敌方造成1点直接伤害',
    apply(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(1)
      return `[${user.name}]宣言效果：造成1点直接伤害\n` + info
    },
  },
  {
    id: 'set_shield2', displayName: '宣言·护盾', slot: 'onCardSet', rarity: 'common',
    description: '宣言时获得[护盾2]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Shield', 2); return '' },
  },
  {
    id: 'set_buffer1', displayName: '宣言·缓冲', slot: 'onCardSet', rarity: 'common',
    description: '宣言时获得[缓冲1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Buffer', 1); return '' },
  },
  {
    id: 'set_spirit2', displayName: '宣言·灵力+2', slot: 'onCardSet', rarity: 'common',
    description: '宣言时获得2灵力',
    apply(user: Battler, _enemy: Battler) { user.spiritGained += 2; return `[${user.name}]获得2灵力！\n` },
  },
  {
    id: 'set_stable1', displayName: '宣言·稳固', slot: 'onCardSet', rarity: 'common',
    description: '宣言时获得[稳固1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Stable', 1); return '' },
  },
  {
    id: 'set_agile1', displayName: '宣言·灵动', slot: 'onCardSet', rarity: 'common',
    description: '宣言时获得[灵动1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Agile', 1); return '' },
  },
  {
    id: 'set_damage2', displayName: '宣言·造成2伤害', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时对敌方造成2点直接伤害',
    apply(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]宣言效果：造成2点直接伤害\n` + info
    },
  },
  {
    id: 'set_chase1', displayName: '宣言·追击', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时获得[追击1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Chase', 1); return '' },
  },
  {
    id: 'set_trace1', displayName: '宣言·追踪', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时获得[追踪1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Trace', 1); return '' },
  },
  {
    id: 'set_combo1', displayName: '宣言·连击', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时获得[连击1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Combo', 1); return '' },
  },
  {
    id: 'set_thorns1', displayName: '宣言·荆棘', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时获得[荆棘1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Thorns', 1); return '' },
  },
  {
    id: 'set_dmgborder', displayName: '宣言·伤害结界', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时展开3回合[伤害结界1]',
    apply(user: Battler, _enemy: Battler) { user.appendBorder('DamageBorder', 3, 1); return '' },
  },
  {
    id: 'set_fragborder', displayName: '宣言·脆弱结界', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时展开3回合[脆弱结界1]',
    apply(user: Battler, _enemy: Battler) { user.appendBorder('FragileBorder', 3, 1); return '' },
  },
  {
    id: 'set_weaken1', displayName: '宣言·弱化', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时对方获得[弱化1]',
    apply(_user: Battler, enemy: Battler) { enemy.appendEffect('Weaken', 1); return '' },
  },
  {
    id: 'set_sluggish1', displayName: '宣言·迟缓', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时对方获得[迟缓1]',
    apply(_user: Battler, enemy: Battler) { enemy.appendEffect('Sluggish', 1); return '' },
  },
  {
    id: 'set_unbreak1', displayName: '宣言·击破保护', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时获得[击破保护1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Unbreakable', 1); return '' },
  },
  {
    id: 'set_damage3', displayName: '宣言·造成3伤害', slot: 'onCardSet', rarity: 'epic',
    description: '宣言时对敌方造成3点直接伤害',
    apply(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(3)
      return `[${user.name}]宣言效果：造成3点直接伤害\n` + info
    },
  },
  {
    id: 'set_freeze', displayName: '宣言·冻结', slot: 'onCardSet', rarity: 'epic',
    description: '宣言时对方获得[冻结1]',
    apply(_user: Battler, enemy: Battler) { enemy.appendEffect('Freeze', 1); return '' },
  },
  {
    id: 'set_cantdef', displayName: '宣言·防御不可', slot: 'onCardSet', rarity: 'epic',
    description: '宣言时对方获得[防御不可]',
    apply(_user: Battler, enemy: Battler) { enemy.appendEffect('CantDefence', -1); return '' },
  },
  {
    id: 'set_cantdod', displayName: '宣言·回避不可', slot: 'onCardSet', rarity: 'epic',
    description: '宣言时对方获得[回避不可]',
    apply(_user: Battler, enemy: Battler) { enemy.appendEffect('CantDodge', -1); return '' },
  },
  {
    id: 'set_drain1', displayName: '宣言·吸血', slot: 'onCardSet', rarity: 'epic',
    description: '宣言时获得[吸血1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Drain', 1); return '' },
  },
  {
    id: 'set_strborder3', displayName: '宣言·强化结界', slot: 'onCardSet', rarity: 'epic',
    description: '宣言时展开3回合[强化结界3]',
    apply(user: Battler, _enemy: Battler) { user.appendBorder('StrengthBorder', 3, 3); return '' },
  },
  {
    id: 'set_shield4', displayName: '宣言·大护盾', slot: 'onCardSet', rarity: 'epic',
    description: '宣言时获得[护盾4]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Shield', 4); return '' },
  },
  {
    id: 'break_damage3', displayName: '亡语·造成3伤害', slot: 'onCardBreak', rarity: 'epic',
    description: '被击破时对敌方造成3点直接伤害',
    apply(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(3)
      return `[${user.name}]亡语效果：造成3点直接伤害\n` + info
    },
  },
  {
    id: 'break_permstr', displayName: '亡语·遗志', slot: 'onCardBreak', rarity: 'epic',
    description: '被击破时展开99回合[强化结界1]',
    apply(user: Battler, _enemy: Battler) { user.appendBorder('StrengthBorder', 99, 1); return '' },
  },
  {
    id: 'turn_chase1', displayName: '被动·追击', slot: 'onPassive', rarity: 'epic',
    description: '每回合获得[追击1]',
    apply(user: Battler, _enemy: Battler) { user.removeEffect('Chase', 1); user.appendEffect('Chase', 1); return '' },
  },
  {
    id: 'turn_trace1', displayName: '被动·追踪', slot: 'onPassive', rarity: 'epic',
    description: '每回合获得[追踪1]',
    apply(user: Battler, _enemy: Battler) { user.removeEffect('Trace', 1); user.appendEffect('Trace', 1); return '' },
  },
  {
    id: 'break_damage1', displayName: '亡语·造成1伤害', slot: 'onCardBreak', rarity: 'common',
    description: '被击破时对敌方造成1点直接伤害',
    apply(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(1)
      return `[${user.name}]亡语效果：造成1点直接伤害\n` + info
    },
  },
  {
    id: 'break_shield2', displayName: '亡语·护盾', slot: 'onCardBreak', rarity: 'common',
    description: '被击破时获得[护盾2]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Shield', 2); return '' },
  },
  {
    id: 'break_damage2', displayName: '亡语·造成2伤害', slot: 'onCardBreak', rarity: 'rare',
    description: '被击破时对敌方造成2点直接伤害',
    apply(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(2)
      return `[${user.name}]亡语效果：造成2点直接伤害\n` + info
    },
  },
  {
    id: 'break_strborder', displayName: '亡语·强化结界', slot: 'onCardBreak', rarity: 'rare',
    description: '被击破时展开3回合[强化结界1d3]',
    apply(user: Battler, _enemy: Battler) {
      const rng = new SeededRandom()
      const str = rollDice('1d3', rng)
      user.appendBorder('StrengthBorder', 3, str)
      return `${user.name}亡语效果：展开3回合的[强化结界${str}]！`
    },
  },
  {
    id: 'break_fragborder', displayName: '亡语·脆弱结界', slot: 'onCardBreak', rarity: 'rare',
    description: '被击破时对敌方展开3回合[脆弱结界1]',
    apply(_user: Battler, enemy: Battler) { enemy.appendBorder('FragileBorder', 3, 1); return '' },
  },
  {
    id: 'break_sluggishborder', displayName: '亡语·迟缓结界', slot: 'onCardBreak', rarity: 'rare',
    description: '被击破时对敌方展开3回合[迟缓结界1]',
    apply(_user: Battler, enemy: Battler) { enemy.appendBorder('SluggishBorder', 3, 1); return '' },
  },
  {
    id: 'break_weakenborder', displayName: '亡语·弱化结界', slot: 'onCardBreak', rarity: 'rare',
    description: '被击破时对敌方展开3回合[弱化结界1]',
    apply(_user: Battler, enemy: Battler) { enemy.appendBorder('WeakenBorder', 3, 1); return '' },
  },
  {
    id: 'turn_str1', displayName: '被动·强化', slot: 'onPassive', rarity: 'common',
    description: '每回合获得[强化1]',
    apply(user: Battler, _enemy: Battler) { user.removeEffect('Strength', 1); user.appendEffect('Strength', 1); return '' },
  },
  {
    id: 'turn_damage1', displayName: '被动·伤害', slot: 'onPassive', rarity: 'common',
    description: '每回合对敌方造成1点直接伤害',
    apply(user: Battler, enemy: Battler) {
      const info = enemy.effectHurt(1)
      return `[${user.name}]被动效果：造成1点直接伤害\n` + info
    },
  },
  {
    id: 'turn_agile1_even', displayName: '被动·偶数灵动', slot: 'onPassive', rarity: 'common',
    description: '偶数回合获得[灵动1]',
    apply(user: Battler, _enemy: Battler) {
      if (user.gameRound % 2 === 0) { user.removeEffect('Agile', 1); user.appendEffect('Agile', 1) }
      return ''
    },
  },
  {
    id: 'turn_spirit1', displayName: '被动·灵力+1', slot: 'onPassive', rarity: 'common',
    description: '每回合获得1灵力',
    apply(user: Battler, _enemy: Battler) { user.spiritGained += 1; return `[${user.name}]获得1灵力！\n` },
  },
  {
    id: 'turn_desperate_dod1', displayName: '被动·绝境', slot: 'onPassive', rarity: 'common',
    description: 'HP≤3时闪避+1',
    apply(user: Battler, _enemy: Battler) { user.removeEffect('DesperateDod', 1); user.appendEffect('DesperateDod', 1); return '' },
  },
  {
    id: 'turn_stable1', displayName: '被动·稳固', slot: 'onPassive', rarity: 'common',
    description: '每回合获得[稳固1]',
    apply(user: Battler, _enemy: Battler) { user.removeEffect('Stable', 1); user.appendEffect('Stable', 1); return '' },
  },
  {
    id: 'turn_str1_weak1', displayName: '被动·破釜', slot: 'onPassive', rarity: 'rare',
    description: 'HP≤50%时获得[强化2]',
    apply(user: Battler, _enemy: Battler) {
      if (user.nowHp <= user.nowCard!.cardHp * 0.5) {
        user.removeEffect('Strength', 2); user.appendEffect('Strength', 2)
      } else {
        user.removeEffect('Strength', 2)
      }
      return ''
    },
  },
  {
    id: 'turn_desperate_atk2', displayName: '被动·背水', slot: 'onPassive', rarity: 'rare',
    description: 'HP≤3时攻击力+2',
    apply(user: Battler, _enemy: Battler) { user.removeEffect('DesperateAtk', 2); user.appendEffect('DesperateAtk', 2); return '' },
  },
  {
    id: 'ek_kill_heal3', displayName: '被动·击杀回复', slot: 'onPassive', rarity: 'rare', trigger: 'enemyCardBreak',
    description: '击破对方符卡时回复3HP',
    apply(user: Battler, _enemy: Battler) {
      const heal = Math.min(3, user.nowCard!.cardHp - user.nowHp)
      if (heal > 0) { user.nowHp += heal; return `[${user.name}]击杀回复，恢复${heal}HP！\n` }
      return ''
    },
  },
  {
    id: 'ek_kill_str2', displayName: '被动·击杀强化', slot: 'onPassive', rarity: 'rare', trigger: 'enemyCardBreak',
    description: '击破对方符卡时获得[强化2]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Strength', 2); return `[${user.name}]击杀强化，攻击力+2！\n` },
  },
]

const DICE_POOL: DiceUpgrade[] = [
  {
    id: 'dice_atk1', displayName: 'ATK骰面+1', rarity: 'common',
    description: '攻击骰面+1（如1d4→1d5）',
    apply(card) { card.atkPoint = upgradeDice(card.atkPoint) },
  },
  {
    id: 'dice_def1', displayName: 'DEF骰面+1', rarity: 'common',
    description: '防御骰面+1',
    apply(card) { card.defPoint = upgradeDice(card.defPoint) },
  },
  {
    id: 'dice_dod1', displayName: 'DOD骰面+1', rarity: 'common',
    description: '回避骰面+1',
    apply(card) { card.dodPoint = upgradeDice(card.dodPoint) },
  },
  {
    id: 'dice_atk2', displayName: 'ATK骰面+2', rarity: 'rare',
    description: '攻击骰面+2',
    apply(card) { card.atkPoint = upgradeDice(upgradeDice(card.atkPoint)) },
  },
  {
    id: 'dice_atk_min1', displayName: 'ATK下限+1', rarity: 'rare',
    description: '攻击骰下限+1',
    apply(card) { card.atkPoint = upgradeDiceMin(card.atkPoint) },
  },
  {
    id: 'dice_def_min1', displayName: 'DEF下限+1', rarity: 'rare',
    description: '防御骰下限+1',
    apply(card) { card.defPoint = upgradeDiceMin(card.defPoint) },
  },
  {
    id: 'dice_dod_min1', displayName: 'DOD下限+1', rarity: 'rare',
    description: '回避骰下限+1',
    apply(card) { card.dodPoint = upgradeDiceMin(card.dodPoint) },
  },
  {
    id: 'dice_atk_count', displayName: 'ATK骰数+1', rarity: 'epic',
    description: '攻击骰数+1（如1d4→2d4）',
    apply(card) { card.atkPoint = upgradeDiceCount(card.atkPoint) },
  },
  {
    id: 'dice_def_count', displayName: 'DEF骰数+1', rarity: 'epic',
    description: '防御骰数+1',
    apply(card) { card.defPoint = upgradeDiceCount(card.defPoint) },
  },
  {
    id: 'dice_dod_count', displayName: 'DOD骰数+1', rarity: 'epic',
    description: '回避骰数+1',
    apply(card) { card.dodPoint = upgradeDiceCount(card.dodPoint) },
  },
]

const STAT_POOL: StatUpgrade[] = [
  {
    id: 'stat_hp2', displayName: 'HP+2', rarity: 'common',
    description: '最大HP+2',
    apply(card) { card.maxCardHp += 2; card.cardHp += 2; card.currentHp += 2 },
  },
  {
    id: 'stat_hp3', displayName: 'HP+3', rarity: 'rare',
    description: '最大HP+3',
    apply(card) { card.maxCardHp += 3; card.cardHp += 3; card.currentHp += 3 },
  },
]

export function parseDice(diceStr: string): { count: number; faces: number; min: number; bonus: number } {
  const minMatch = diceStr.match(/^(\d+)d\((\d+)~(\d+)\)([+-]\d+)?$/)
  if (minMatch) {
    return { count: parseInt(minMatch[1]), min: parseInt(minMatch[2]), faces: parseInt(minMatch[3]), bonus: minMatch[4] ? parseInt(minMatch[4]) : 0 }
  }
  const match = diceStr.match(/^(\d+)d(\d+)([+-]\d+)?$/)
  if (!match) return { count: 1, faces: 1, min: 1, bonus: 0 }
  return { count: parseInt(match[1]), min: 1, faces: parseInt(match[2]), bonus: match[3] ? parseInt(match[3]) : 0 }
}

export function formatDice(d: { count: number; faces: number; min?: number; bonus?: number }): string {
  const min = d.min ?? 1
  const bonus = d.bonus ?? 0
  if (min > 1) {
    const base = `${d.count}d(${min}~${d.faces})`
    if (bonus > 0) return `${base}+${bonus}`
    if (bonus < 0) return `${base}${bonus}`
    return base
  }
  const base = `${d.count}d${d.faces}`
  if (bonus > 0) return `${base}+${bonus}`
  if (bonus < 0) return `${base}${bonus}`
  return base
}

export function isDiceFixed(diceStr: string): boolean {
  const d = parseDice(diceStr)
  return d.min >= d.faces
}

function upgradeDice(diceStr: string): string {
  const d = parseDice(diceStr)
  return formatDice({ ...d, faces: d.faces + 1 })
}

function upgradeDiceCount(diceStr: string): string {
  const d = parseDice(diceStr)
  return formatDice({ ...d, count: d.count + 1 })
}

function upgradeDiceMin(diceStr: string): string {
  const d = parseDice(diceStr)
  return formatDice({ ...d, min: d.min + 1 })
}

const SLOT_POOL: ExtraSlotReward[] = [
  { id: 'slot_onCardSet', displayName: '额外宣言槽', rarity: 'rare', description: '为一张符卡添加额外的宣言时效果槽', slot: 'onCardSet' },
  { id: 'slot_onCardBreak', displayName: '额外亡语槽', rarity: 'rare', description: '为一张符卡添加额外的被击破时效果槽', slot: 'onCardBreak' },
  { id: 'slot_onPassive', displayName: '额外被动槽', rarity: 'rare', description: '为一张符卡添加额外的被动效果槽', slot: 'onPassive' },
]

function pickRandom<T>(arr: T[], count: number, rng: () => number): T[] {
  const shuffled = [...arr].sort(() => rng() - 0.5)
  return shuffled.slice(0, count)
}

export function generateRewards(
  battleType: 'normal' | 'elite' | 'boss',
  rng: () => number,
): Reward[] {
  let epicCount: number
  let rareCount: number
  if (battleType === 'boss') {
    const roll = rng()
    epicCount = roll < 0.5 ? 1 : 2
    rareCount = 3 - epicCount
  } else if (battleType === 'elite') {
    const roll = rng()
    if (roll < 0.2) { epicCount = 1; rareCount = 1 }
    else if (roll < 0.55) { epicCount = 0; rareCount = 2 }
    else { epicCount = 0; rareCount = 1 }
  } else {
    const roll = rng()
    epicCount = 0
    rareCount = roll < 0.05 ? 2 : roll < 0.2 ? 1 : 0
  }
  const commonCount = 3 - epicCount - rareCount

  const rewards: Reward[] = []
  const usedIds = new Set<string>()

  const epicEffects = EFFECT_POOL.filter(e => e.rarity === 'epic')
  const rareEffects = EFFECT_POOL.filter(e => e.rarity === 'rare')
  const commonEffects = EFFECT_POOL.filter(e => e.rarity === 'common')
  const epicDice = DICE_POOL.filter(d => d.rarity === 'epic')
  const rareDice = DICE_POOL.filter(d => d.rarity === 'rare')
  const commonDice = DICE_POOL.filter(d => d.rarity === 'common')
  const rareStats = STAT_POOL.filter(s => s.rarity === 'rare')
  const commonStats = STAT_POOL.filter(s => s.rarity === 'common')

  const epicPool = [epicEffects, epicDice]
  const rarePool = [rareEffects, rareDice, rareStats, SLOT_POOL]
  const commonPool = [commonEffects, commonDice, commonStats]

  for (let i = 0; i < epicCount; i++) {
    let attempts = 0
    while (attempts < 20) {
      const chosen = epicPool[Math.floor(rng() * epicPool.length)]
      if (chosen.length === 0) { attempts++; continue }
      const item = chosen[Math.floor(rng() * chosen.length)]
      if (!usedIds.has(item.id)) { usedIds.add(item.id); rewards.push(item); break }
      attempts++
    }
  }

  for (let i = 0; i < rareCount; i++) {
    let attempts = 0
    while (attempts < 20) {
      const chosen = rarePool[Math.floor(rng() * rarePool.length)]
      if (chosen.length === 0) { attempts++; continue }
      const item = chosen[Math.floor(rng() * chosen.length)]
      if (!usedIds.has(item.id)) { usedIds.add(item.id); rewards.push(item); break }
      attempts++
    }
  }

  for (let i = 0; i < commonCount; i++) {
    let attempts = 0
    while (attempts < 20) {
      const chosen = commonPool[Math.floor(rng() * commonPool.length)]
      if (chosen.length === 0) { attempts++; continue }
      const item = chosen[Math.floor(rng() * chosen.length)]
      if (!usedIds.has(item.id)) { usedIds.add(item.id); rewards.push(item); break }
      attempts++
    }
  }

  return rewards.slice(0, 3)
}

export function generateShopItems(rng: () => number): ShopItem[] {
  const items: ShopItem[] = []
  const allRewards: Reward[] = [...EFFECT_POOL, ...DICE_POOL, ...STAT_POOL, ...SLOT_POOL]

  const picked = pickRandom(allRewards, 4, rng)
  for (const r of picked) {
    const price = r.rarity === 'epic' ? 10 : r.rarity === 'rare' ? 6 : 3
    items.push({
      id: `shop_${r.id}`,
      name: r.displayName,
      description: r.description,
      price,
      reward: r,
    })
  }

  items.push({
    id: 'shop_refresh',
    name: '刷新商品',
    description: '重新随机生成商品',
    price: 1,
    reward: { id: '_refresh', displayName: '刷新', rarity: 'common', description: '', slot: 'onCardSet' } as any,
  })

  return items
}

const EFFECT_DESCRIPTIONS: Record<string, string> = {
  '追击': '对方受伤时额外+X伤害',
  '追踪': '对方闪避成功时仍受X点伤害',
  '强化': '攻击力+X',
  '弱化': '攻击力-X',
  '稳固': '防御力+X',
  '脆弱': '防御力-X',
  '灵动': '闪避+X',
  '迟缓': '闪避-X',
  '缓冲': '受到的伤害-X',
  '护盾': '抵消X点伤害',
  '击破保护': '免疫一次致命伤害',
  '冻结': '无法攻击/防御/闪避',
  '防御不可': '受伤=攻击力，无减伤',
  '回避不可': '闪避率归零',
  '伤害结界': '每回合对对方造成X点伤害',
  '强化结界': '攻击力+X',
  '弱化结界': '攻击力-X',
  '稳固结界': '防御力+X',
  '脆弱结界': '对方防御力-X',
  '灵动结界': '闪避+X',
  '迟缓结界': '闪避-X',
  '连击': '对方符卡已受伤时攻击力+X',
  '背水': 'HP≤3时攻击力+X',
  '绝境': 'HP≤3时闪避+X',
  '荆棘': '受到战斗伤害时反弹X点伤害',
  '灵力获取': '每回合获得X灵力',
  '吸血': '造成战斗伤害时，回复最多X点HP',
  '时符': 'X回合内免疫一切伤害，回合耗尽后符卡自动被击破',
  '破甲': 'X回合内对方无法防御',
  '贯穿': 'X回合内对方无法防御',
  '时停': '对方无法行动X回合',
}

const SORTED_EFFECT_BASES = Object.keys(EFFECT_DESCRIPTIONS).sort((a, b) => b.length - a.length)

export interface DescSegment {
  type: 'text' | 'effect'
  text: string
  effectDesc?: string
}

export function parseDescription(desc: string): DescSegment[] {
  if (!desc || desc === '无') return []
  const segments: DescSegment[] = []
  const regex = /\[([^\]]+)\]/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(desc)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', text: desc.slice(lastIndex, match.index) })
    }

    const effectName = match[1]
    let foundBase = ''
    let suffix = ''
    for (const base of SORTED_EFFECT_BASES) {
      if (effectName.startsWith(base)) {
        foundBase = base
        suffix = effectName.slice(base.length)
        break
      }
    }

    let effectDesc = effectName
    if (foundBase && EFFECT_DESCRIPTIONS[foundBase]) {
      effectDesc = EFFECT_DESCRIPTIONS[foundBase].replace(/X/g, suffix || '1')
    }

    segments.push({ type: 'effect', text: effectName, effectDesc })
    lastIndex = regex.lastIndex
  }

  if (lastIndex < desc.length) {
    segments.push({ type: 'text', text: desc.slice(lastIndex) })
  }

  return segments
}

export { DICE_POOL, EFFECT_POOL, SLOT_POOL, STAT_POOL }

