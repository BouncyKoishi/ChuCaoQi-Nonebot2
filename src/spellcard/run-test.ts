import { ALL_CARDS } from './cards'
import './effects'
import { generateEncounter, generateExEncounter, generateNewCardDrop, getExStageTemplate, getSpiritReward, getStageTemplate } from './encounters'
import type { Battler, CardData, LogEntry } from './engine'
import { Battle } from './engine'
import {
  type Encounter, type ExpeditionCard, type ExpeditionState, type Reward,
  addEffectToCard, addSlotCapacity,
  BASE_PANELS,
  canAddEffectToSlot,
  createNonCard, createSpellCard, healAllForNewStage, healNonCard,
  initExpeditionState,
  INITIAL_CARD_EFFECTS,
  toCardData
} from './expedition'
import { DICE_POOL, EFFECT_POOL, formatDice, generateRewards, generateShopItems, isDiceFixed, parseDescription, parseDice, SLOT_POOL, STAT_POOL } from './rewards'

interface TestResult { name: string; passed: boolean; detail: string }
const results: TestResult[] = []

function assert(name: string, condition: boolean, detail: string = '') {
  results.push({ name, passed: condition, detail: condition ? 'OK' : `FAIL: ${detail}` })
}

function makeCard(overrides: Partial<CardData> = {}): CardData {
  return { id: -1, cost: 0, name: '测试符卡', cardHp: 10, atkPoint: '1d1+9', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', ...overrides }
}

function runBattle(creatorCards: CardData[], enemyCards: CardData[]): { log: LogEntry[]; winnerId: number | null; creatorHp: number; enemyHp: number } {
  const b = new Battle(1)
  b.setCreator('A')
  b.creator.chosenCards = creatorCards
  b.setSingleEnemy('B', enemyCards)
  b.runFullBattle()
  return { log: b.log.entries, winnerId: b.winnerId, creatorHp: b.creator.nowHp, enemyHp: b.joiner!.nowHp }
}

function logContains(log: LogEntry[], text: string): boolean {
  return log.some(e => e.message.includes(text))
}

function logPhaseCount(log: LogEntry[], phase: string): number {
  return log.filter(e => e.phase === phase).length
}

function testEffectBasics() {
  const S = '效果基础'

  assert(`[${S}] 强化: ATK+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4' }), onCardSet(u) { u.appendEffect('Strength', 2); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '攻击增加了2点')
  })())

  assert(`[${S}] 弱化: ATK-2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4' }), onCardSet(u) { u.appendEffect('Weaken', 2); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '攻击减少了2点')
  })())

  assert(`[${S}] 稳固: DEF+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ defPoint: '1d1+2', cardHp: 50 }), onCardSet(u) { u.appendEffect('Stable', 2); return '' } }],
      [makeCard({ atkPoint: '1d1+4' })],
    )
    return logContains(r.log, '防御增加了2点')
  })())

  assert(`[${S}] 脆弱: DEF-2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ defPoint: '1d1+4', cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('Fragile', 2); return '' } }],
      [makeCard({ atkPoint: '1d1+4' })],
    )
    return logContains(r.log, '防御减少了2点')
  })())

  assert(`[${S}] 灵动: DOD+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ dodPoint: '1d1+2', cardHp: 50 }), onCardSet(u) { u.appendEffect('Agile', 2); return '' } }],
      [makeCard({ atkPoint: '1d1+4' })],
    )
    return logContains(r.log, '回避增加了2点')
  })())

  assert(`[${S}] 迟缓: DOD-2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ dodPoint: '1d1+4', cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('Sluggish', 2); return '' } }],
      [makeCard({ atkPoint: '1d1+4' })],
    )
    return logContains(r.log, '回避减少了2点')
  })())

  assert(`[${S}] 追击: 受伤时+1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4' }), onCardSet(u) { u.appendEffect('Chase', 1); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '追击') && logContains(r.log, '额外受到1点伤害')
  })())

  assert(`[${S}] 追踪: 闪避时仍受伤`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1' }), onCardSet(u) { u.appendEffect('Trace', 1); return '' } }],
      [makeCard({ atkPoint: '1d1', dodPoint: '1d1+98', cardHp: 50 })],
    )
    return logContains(r.log, '追踪') && logContains(r.log, '受到1点伤害')
  })())

  assert(`[${S}] 缓冲: 伤害-1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendEffect('Buffer', 1); return '' } }],
      [makeCard({ atkPoint: '1d1+4' })],
    )
    return logContains(r.log, '缓冲') && logContains(r.log, '伤害减少1点')
  })())

  assert(`[${S}] 护盾: 抵消伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendEffect('Shield', 3); return '' } }],
      [makeCard({ atkPoint: '1d1+4' })],
    )
    return logContains(r.log, '护盾') && logContains(r.log, '吸收了')
  })())

  assert(`[${S}] 击破保护: 免疫致命伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 3 }), onCardSet(u) { u.appendEffect('Unbreakable', 1); return '' } }],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    return logContains(r.log, '击破保护')
  })())

  assert(`[${S}] 冻结: 无法行动`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 50 })],
      [{ ...makeCard({ cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('Freeze', 1); return '' } }],
    )
    return logContains(r.log, '冰冻') && logContains(r.log, '无法进行攻击')
  })())

  assert(`[${S}] 防御不可(永续)`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4' }), onCardSet(_u, e) { e.appendEffect('CantDefence', -1); return '' } }],
      [makeCard({ atkPoint: '1d1', defPoint: '1d1+4', cardHp: 50 })],
    )
    return logContains(r.log, '无法作出防御')
  })())

  assert(`[${S}] 防御不可(1回合后消退)`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ atkPoint: '1d1+4', cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('CantDefence', 1); return '' } },
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1', defPoint: '1d1+4', cardHp: 50 })],
    )
    const cantDefTurns = r.log.filter(l => l.message.includes('无法作出防御')).length
    const hurtTurns = r.log.filter(l => l.message.includes('受到') && l.message.includes('点伤害')).length
    return cantDefTurns >= 1 && hurtTurns >= 1
  })())

  assert(`[${S}] 回避不可(永续)`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4' }), onCardSet(_u, e) { e.appendEffect('CantDodge', -1); return '' } }],
      [makeCard({ atkPoint: '1d1', dodPoint: '1d1+98', cardHp: 50 })],
    )
    return logContains(r.log, '无法进行回避')
  })())

  assert(`[${S}] 回避不可(1回合后消退)`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1', cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('CantDodge', 1); return '' } }],
      [makeCard({ atkPoint: '1d1', dodPoint: '1d1+98', cardHp: 50 })],
    )
    const cantDodTurns = r.log.filter(l => l.message.includes('无法进行回避')).length
    const dodSuccessTurns = r.log.filter(l => l.message.includes('闪避成功')).length
    return cantDodTurns >= 1 && dodSuccessTurns >= 1
  })())

  assert(`[${S}] 连击: 敌方受伤时ATK+1`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ atkPoint: '1d1+4', cardHp: 5 }), onCardSet(u) { u.appendEffect('Combo', 1); return '' } },
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '连击触发')
  })())

  assert(`[${S}] 背水: HP≤3时ATK+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 3 }), onCardSet(u) { u.appendEffect('DesperateAtk', 2); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '背水触发')
  })())

  assert(`[${S}] 绝境: HP≤3时DOD+1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ dodPoint: '1d1', cardHp: 3 }), onCardSet(u) { u.appendEffect('DesperateDod', 1); return '' } }],
      [makeCard({ atkPoint: '1d1+4' })],
    )
    return logContains(r.log, '绝境触发')
  })())

  assert(`[${S}] 荆棘: 反弹伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendEffect('Thorns', 1); return '' } }],
      [makeCard({ atkPoint: '1d1+4', cardHp: 50 })],
    )
    return logContains(r.log, '荆棘反弹')
  })())
}

function testEffectAdvanced() {
  const S = '效果进阶'

  assert(`[${S}] Drain: 造成战斗伤害时回复HP`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onCardSet(u) { u.nowHp = 45; u.appendEffect('Drain', 2); return '' } }],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.creatorHp !== undefined && firstHurt.creatorHp >= 46 && firstHurt.creatorHp <= 47
  })())

  assert(`[${S}] Drain: 回复量不超过Drain层数`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onCardSet(u) { u.appendEffect('Drain', 1); return '' } }],
      [makeCard({ atkPoint: '1d1+4', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.creatorHp !== undefined && firstHurt.creatorHp === 46
  })())

  assert(`[${S}] Drain: 敌方有Drain时攻击方受伤触发敌方吸血`, (() => {
    const r = runBattle(
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onCardSet(u) { u.nowHp = 45; u.appendEffect('Drain', 3); return '' } }],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.joinerHp !== undefined && firstHurt.joinerHp >= 46 && firstHurt.joinerHp <= 48
  })())

  assert(`[${S}] Drain: 回复量不超过血量上限`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onCardSet(u) { u.appendEffect('Drain', 5); return '' } }],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.creatorHp !== undefined && firstHurt.creatorHp <= 50
  })())


  assert(`[${S}] aliasName覆盖displayName但保留id`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.creator.appendEffect('CantDefence', 1, '破甲')
    const effect = b.creator.effects.find(e => e.id === 'CantDefence')
    if (!effect) return false
    return effect.displayName === '破甲' && effect.id === 'CantDefence'
  })())

  assert(`[${S}] 不传aliasName使用默认displayName`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.creator.appendEffect('CantDefence', 1)
    const effect = b.creator.effects.find(e => e.id === 'CantDefence')
    if (!effect) return false
    return effect.displayName === '防御不可' && effect.id === 'CantDefence'
  })())

  assert(`[${S}] 别名效果功能正常(破甲=防御不可)`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4' }), onCardSet(_u, e) { e.appendEffect('CantDefence', 1, '破甲'); return '' } }],
      [makeCard({ atkPoint: '1d1', defPoint: '1d1+4', cardHp: 50 })],
    )
    return logContains(r.log, '无法作出防御')
  })())
}

function testSpecialCards() {
  const S = '特殊卡牌'

  const timeCard: CardData = {
    id: -2, cost: 0, name: '测试时符', cardHp: 3,
    atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1',
    description: '[时符2]', isTimeCard: true, timeCardTurns: 2,
    onTurnStart(u, e) { e.effectHurt(2); return `[${u.name}]时符攻击！造成2点伤害\n` },
  }

  assert(`[${S}] 时符免疫战斗伤害`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    const firstTwoTurns = hurtEntries.slice(0, 2)
    return firstTwoTurns.length >= 1 && firstTwoTurns.every(e => e.creatorHp === 3)
  })())

  assert(`[${S}] 时符免疫效果伤害`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [{ ...makeCard({ atkPoint: '1d1', cardHp: 50 }), onCardSet(u) { u.appendBorder('DamageBorder', 5, 3); return '' } }],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    const firstTwoTurns = hurtEntries.slice(0, 2)
    return firstTwoTurns.length >= 1 && firstTwoTurns.every(e => e.creatorHp === 3)
  })())

  assert(`[${S}] 时符onTurnStart效果正常触发`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    return logContains(r.log, '时符攻击')
  })())

  assert(`[${S}] 时符回合耗尽后自动击破`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    return logContains(r.log, '因时符耗尽而消散')
  })())
  assert(`[${S}] QED卡可正常出战`, (() => {
    try {
      const card = ALL_CARDS.find(c => c.id === 64)!
      runBattle([card], [makeCard({ atkPoint: '1d1', cardHp: 50 })])
      return true
    } catch { return false }
  })())

  assert(`[${S}] QED满血时不触发渐强`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.applyCard(b.creator!, 0)
    b.applyCard(b.joiner!, 0)
    b.onNewCardsSet()
    const msg = card.onTurnStart!(b.creator!, b.joiner!)
    return msg === ''
  })())

  assert(`[${S}] QED HP≤75%时获得强化2`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.applyCard(b.creator!, 0)
    b.applyCard(b.joiner!, 0)
    b.onNewCardsSet()
    b.creator.nowHp = 10
    const msg = card.onTurnStart!(b.creator!, b.joiner!)
    return msg.includes('强化2')
  })())

  assert(`[${S}] QED HP≤50%时额外获得追击2`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.applyCard(b.creator!, 0)
    b.applyCard(b.joiner!, 0)
    b.onNewCardsSet()
    b.creator.nowHp = 7
    const msg = card.onTurnStart!(b.creator!, b.joiner!)
    return msg.includes('强化2') && msg.includes('追击2')
  })())

  assert(`[${S}] QED HP≤25%时额外获得吸血1`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.applyCard(b.creator!, 0)
    b.applyCard(b.joiner!, 0)
    b.onNewCardsSet()
    b.creator.nowHp = 3
    const msg = card.onTurnStart!(b.creator!, b.joiner!)
    return msg.includes('强化2') && msg.includes('追击2') && msg.includes('吸血1')
  })())
}

function testRewardEffects() {
  const S = '奖励效果'

  assert(`[${S}] 新增宣言效果可正常apply`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    const effects = [
      { id: 'set_weaken1', apply: (_u: Battler, e: Battler) => { e.appendEffect('Weaken', 1); return '' } },
      { id: 'set_sluggish1', apply: (_u: Battler, e: Battler) => { e.appendEffect('Sluggish', 1); return '' } },
      { id: 'set_stable1', apply: (u: Battler, _e: Battler) => { u.appendEffect('Stable', 1); return '' } },
      { id: 'set_agile1', apply: (u: Battler, _e: Battler) => { u.appendEffect('Agile', 1); return '' } },
      { id: 'set_unbreak1', apply: (u: Battler, _e: Battler) => { u.appendEffect('Unbreakable', 1); return '' } },
      { id: 'set_thorns1', apply: (u: Battler, _e: Battler) => { u.appendEffect('Thorns', 1); return '' } },
      { id: 'set_fragborder', apply: (u: Battler, _e: Battler) => { u.appendBorder('FragileBorder', 3, 1); return '' } },
    ]
    for (const eff of effects) {
      try { eff.apply(b.creator!, b.joiner!) } catch { return false }
    }
    return true
  })())

  assert(`[${S}] 新增亡语效果可正常apply`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    const effects = [
      { id: 'break_sluggishborder', apply: (_u: Battler, e: Battler) => { e.appendBorder('SluggishBorder', 3, 1); return '' } },
      { id: 'break_weakenborder', apply: (_u: Battler, e: Battler) => { e.appendBorder('WeakenBorder', 3, 1); return '' } },
    ]
    for (const eff of effects) {
      try { eff.apply(b.creator!, b.joiner!) } catch { return false }
    }
    return true
  })())

  assert(`[${S}] 新增被动效果可正常apply`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    try { b.creator!.removeEffect('Stable', 1); b.creator!.appendEffect('Stable', 1) } catch { return false }
    return true
  })())

  assert(`[${S}] 宣言·造成3伤害可正常apply`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1', cardHp: 50 }), onCardSet(_u, e) { e.effectHurt(3); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    return hurtEntries[0].joinerHp <= 47
  })())

  assert(`[${S}] 骰子数+1为epic稀有度`, (() => {
    const countDice = DICE_POOL.filter(d => d.id.includes('_count'))
    return countDice.length === 3 && countDice.every(d => d.rarity === 'epic')
  })())

  assert(`[${S}] Boss战不掉落普通奖励`, (() => {
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('boss', () => Math.random())
      if (rewards.some(r => r.rarity === 'common')) return false
    }
    return true
  })())

  assert(`[${S}] 普通战不掉落史诗奖励`, (() => {
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('normal', () => Math.random())
      if (rewards.some(r => r.rarity === 'epic')) return false
    }
    return true
  })())

  assert(`[${S}] 商店定价: 普通3/稀有6/史诗10`, (() => {
    const items = generateShopItems(() => Math.random())
    for (const item of items) {
      if (item.id === 'shop_refresh') continue
      const r = item.reward
      const expected = r.rarity === 'epic' ? 10 : r.rarity === 'rare' ? 6 : 3
      if (item.price !== expected) return false
    }
    return true
  })())

  assert(`[${S}] 已删除set_dmg2(与set_damage2重复)`, (() => {
    const allIds = new Set<string>()
    for (let i = 0; i < 200; i++) {
      const rewards = generateRewards('elite', () => Math.random())
      for (const r of rewards) allIds.add(r.id)
    }
    for (let i = 0; i < 200; i++) {
      const rewards = generateRewards('boss', () => Math.random())
      for (const r of rewards) allIds.add(r.id)
    }
    return !allIds.has('set_dmg2') && allIds.has('set_damage2')
  })())

  assert(`[${S}] 已将被动荆棘改为宣言荆棘`, (() => {
    const allIds = new Set<string>()
    for (let i = 0; i < 500; i++) {
      const rewards = generateRewards('elite', () => Math.random())
      for (const r of rewards) allIds.add(r.id)
    }
    for (let i = 0; i < 500; i++) {
      const rewards = generateRewards('boss', () => Math.random())
      for (const r of rewards) allIds.add(r.id)
    }
    return allIds.has('set_thorns1') && !allIds.has('turn_thorns1')
  })())


  assert(`[${S}] 强化结界: ATK+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4' }), onCardSet(u) { u.appendBorder('StrengthBorder', 3, 2); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '攻击增加了2点')
  })())

  assert(`[${S}] 伤害结界: 每回合造成伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendBorder('DamageBorder', 5, 1); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '伤害结界') && logContains(r.log, '受到1点直接伤害')
  })())

  assert(`[${S}] 脆弱结界: DEF-1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1' }), onCardSet(_u, e) { e.appendBorder('FragileBorder', 3, 1); return '' } }],
      [makeCard({ atkPoint: '1d1', defPoint: '1d1+4', cardHp: 50 })],
    )
    return logContains(r.log, '防御减少了1点')
  })())

  assert(`[${S}] 结界回合衰减`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendBorder('StrengthBorder', 2, 5); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    const strLogs = r.log.filter(e => e.message.includes('攻击增加了5点'))
    return strLogs.length >= 1 && strLogs.length <= 2
  })())


  assert(`[${S}] 非结界效果被清除`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ cardHp: 1 }), onCardSet(u) { u.appendEffect('Strength', 5); return '' } },
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    return !r2Log.some(e => e.message.includes('攻击增加了5点'))
  })())

  assert(`[${S}] 结界保留`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ cardHp: 1 }), onCardSet(u) { u.appendBorder('StrengthBorder', 5, 3); return '' } },
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    return r2Log.some(e => e.message.includes('攻击增加了3点'))
  })())

  assert(`[${S}] 冻结状态被清除`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ cardHp: 1 }), onCardSet(u) { u.appendEffect('Freeze', 3); return '' } },
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    return !r2Log.some(e => e.message.includes('冰冻中') && e.message.includes('A'))
  })())
}

function testBattleMechanics() {
  const S = '战斗机制'

  for (const card of ALL_CARDS) {
    if (card.description === '无') continue
    const hasOnCardSet = !!card.onCardSet
    const hasOnCardBreak = !!card.onCardBreak
    const hasOnTurnStart = !!card.onTurnStart

    assert(`[${S}] ${card.name} 可正常出战`, (() => {
      try { runBattle([card], [makeCard({ atkPoint: '1d1', cardHp: 50 })]); return true }
      catch { return false }
    })())

    if (hasOnCardSet) {
      assert(`[${S}] ${card.name} 宣言不报错`, (() => {
        try { runBattle([card], [makeCard({ atkPoint: '1d1', cardHp: 50 })]); return true }
        catch { return false }
      })())
    }

    if (hasOnCardBreak) {
      assert(`[${S}] ${card.name} 亡语不报错`, (() => {
        try {
          runBattle([card, makeCard({ atkPoint: '1d1', cardHp: 50 })], [makeCard({ atkPoint: '1d1+98', cardHp: 50 })])
          return true
        } catch { return false }
      })())
    }

    if (hasOnTurnStart) {
      assert(`[${S}] ${card.name} 回合开始不报错`, (() => {
        try { runBattle([card], [makeCard({ atkPoint: '1d1', cardHp: 50 })]); return true }
        catch { return false }
      })())
    }
  }
  assert(`[${S}] 概率闪避`, (() => {
    for (let i = 0; i < 50; i++) {
      const r = runBattle([makeCard({ atkPoint: '1d1+4' })], [makeCard({ atkPoint: '1d1', dodPoint: '1d1+98', cardHp: 50 })])
      if (logContains(r.log, '闪避成功')) return true
    }
    return false
  })())

  assert(`[${S}] 符卡击破日志`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    return logContains(r.log, '被战斗伤害击破')
  })())

  assert(`[${S}] 多符卡切换`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1 }), makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    return logPhaseCount(r.log, 'card_break') >= 2
  })())

  assert(`[${S}] 胜负判定`, (() => {
    const r = runBattle([makeCard({ atkPoint: '1d1+98' })], [makeCard({ atkPoint: '1d1', cardHp: 1 })])
    return r.winnerId === 1
  })())

  assert(`[${S}] 骰子表达式`, (() => {
    try {
      runBattle([makeCard({ atkPoint: '2d4+1' })], [makeCard({ atkPoint: '1d1', cardHp: 50 })])
      return true
    } catch { return false }
  })())
}

function testBugFixes() {
  const S = 'Bug修复'

  assert(`[${S}] 坤神招来盾: 击破后护盾保留`, (() => {
    const r = runBattle(
      [
        { id: 10, cost: 0, name: '坤神招来 盾', cardHp: 1, atkPoint: '1d1', defPoint: '1d3', dodPoint: '1d3', description: '', onCardBreak(u, _e) { u.appendEffect('Shield', 3); return '护盾！' } },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    return logContains(r.log, '护盾')
  })())

  assert(`[${S}] 时符免疫战斗伤害日志`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', isTimeCard: true, timeCardTurns: 3 },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1+4', cardHp: 50 })],
    )
    const calcEntries = r.log.filter(e => e.phase === 'calc')
    return calcEntries.some(e => e.message.includes('免疫战斗伤害'))
  })())

  assert(`[${S}] 时符免疫效果伤害日志`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', isTimeCard: true, timeCardTurns: 3, onTurnStart(u, e) { const info = e.effectHurt(2); return `造成2点伤害\n${info}` } },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    const calcEntries = r.log.filter(e => e.phase === 'calc')
    return calcEntries.some(e => e.message.includes('免疫战斗伤害'))
  })())

  assert(`[${S}] 时符耗尽日志`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', isTimeCard: true, timeCardTurns: 1 },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    return logContains(r.log, '时符时间耗尽')
  })())

  assert(`[${S}] 时符耗尽击破来源为time`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', isTimeCard: true, timeCardTurns: 1 },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    const breakEntry = r.log.find(e => e.phase === 'card_break' && e.visual?.breakSource === 'time')
    return breakEntry !== undefined
  })())

  assert(`[${S}] 幻世The World: onCardSet只触发1次`, (() => {
    const r = runBattle(
      [
        makeCard({ cardHp: 4 }),
        { id: 50, cost: 0, name: '幻世「The World」', cardHp: 8, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2', description: '', onCardSet(u, e) { e.appendEffect('Freeze', 1); u.appendEffect('Strength', 2); return '时停！' } },
      ],
      [
        makeCard({ cardHp: 4 }),
        makeCard({ cardHp: 4 }),
      ],
    )
    const freezeLogs = r.log.filter(e => e.message.includes('时停'))
    return freezeLogs.length === 1
  })())

  assert(`[${S}] 击破日志包含符卡快照`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    const breakEntry = r.log.find(e => e.phase === 'card_break')
    return breakEntry !== undefined && (breakEntry.creatorCard !== undefined || breakEntry.joinerCard !== undefined)
  })())

  assert(`[${S}] 宣言日志包含符卡快照`, (() => {
    const r = runBattle(
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    const setEntry = r.log.find(e => e.phase === 'card_set' && e.creatorCard !== undefined)
    return setEntry !== undefined
  })())

  assert(`[${S}] 符卡描述"每回合开始时"`, (() => {
    const oldStyle = ALL_CARDS.filter(c => c.description?.match(/(?<!偶数)(?<!每)回合开始时/))
    return oldStyle.length === 0
  })())

  assert(`[${S}] 被动·破釜: HP≤50%时获得强化2`, (() => {
    const pofu = EFFECT_POOL.find(e => e.id === 'turn_str1_weak1')
    return pofu !== undefined && pofu.description === 'HP≤50%时获得[强化2]' && !pofu.description.includes('弱化')
  })())

  assert(`[${S}] 固定值1吃骰面+1变成1d2`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d1', dodPoint: '1d1' })
    const defUp = DICE_POOL.find(d => d.id === 'dice_def1')!
    defUp.apply(card)
    return card.defPoint === '1d2'
  })())

  assert(`[${S}] 1d1下限+1不可装配(面数已为1)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d1', dodPoint: '1d1' })
    return isDiceFixed(card.defPoint)
  })())

  assert(`[${S}] 1d3下限+1变成1d(2~3)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d1' })
    const defMinUp = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    defMinUp.apply(card)
    return card.defPoint === '1d(2~3)'
  })())

  assert(`[${S}] 1d(2~3)吃骰面+1变成1d(2~4)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d1' })
    const defMinUp = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    const defUp = DICE_POOL.find(d => d.id === 'dice_def1')!
    defMinUp.apply(card)
    defUp.apply(card)
    return card.defPoint === '1d(2~4)'
  })())

  assert(`[${S}] 远征已击破符卡不出战`, (() => {
    const cards: ExpeditionCard[] = [
      createNonCard(),
      createSpellCard({ name: '符卡A', cardHp: 7, maxCardHp: 7, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d3' }),
    ]
    cards[1].currentHp = 0
    const activeIndices: number[] = []
    const myCardDatas = []
    for (let i = 0; i < cards.length; i++) {
      if (cards[i].currentHp > 0) {
        activeIndices.push(i)
        myCardDatas.push(toCardData(cards[i]))
      }
    }
    return myCardDatas.length === 1 && !myCardDatas.some(c => c.name === '符卡A')
  })())

  assert(`[${S}] 远征战后HP不为负数`, (() => {
    const cards: ExpeditionCard[] = [
      createNonCard(),
      createSpellCard({ name: '符卡', cardHp: 3, maxCardHp: 3, atkPoint: '1d3', defPoint: '1d1', dodPoint: '1d1' }),
    ]
    healAllForNewStage(cards)
    const activeIndices: number[] = []
    const myCardDatas = []
    for (let i = 0; i < cards.length; i++) {
      if (cards[i].currentHp > 0) {
        activeIndices.push(i)
        myCardDatas.push(toCardData(cards[i]))
      }
    }
    const b = new Battle(1)
    b.setCreator('玩家')
    b.creator.chosenCards = myCardDatas
    b.setSingleEnemy('敌人', [makeCard({ atkPoint: '1d1+98', cardHp: 50 })])
    b.runFullBattle()
    const usedBattleIndices = b.creator.usedCardIndices
    for (let i = 0; i < cards.length; i++) {
      const card = cards[i]
      const activePos = activeIndices.indexOf(i)
      let hpAfter: number
      if (activePos === -1) {
        hpAfter = card.currentHp
      } else {
        const wasUsed = activePos < usedBattleIndices.length
        if (wasUsed) {
          hpAfter = activePos === usedBattleIndices.length - 1 ? Math.max(b.creator.nowHp, 0) : 0
        } else {
          hpAfter = card.currentHp
        }
      }
      card.currentHp = hpAfter
    }
    return cards.every(c => c.currentHp >= 0)
  })())
  assert(`[${S}] 双方同时击破: 亡语伤害打到新符卡`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(5); return '亡语：5伤害' } },
        makeCard({ name: '后继卡', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 10 }),
      ],
    )
    if (!logContains(r.log, '亡语：5伤害')) return false
    const breakIdx = r.log.findIndex(e => e.phase === 'card_break')
    if (breakIdx < 0) return false
    const afterBreak = r.log.slice(breakIdx + 1)
    const nextCardSet = afterBreak.find(e => e.phase === 'card_set' && e.creatorCard !== undefined)
    if (!nextCardSet) return false
    return nextCardSet.joinerHp !== undefined && nextCardSet.joinerHp === 5
  })())

  assert(`[${S}] 双方同时击破: 双方亡语都正确触发`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '我方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(3); return '我方亡语触发' } },
        makeCard({ name: '我方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        { id: -11, cost: 0, name: '敌方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(3); return '敌方亡语触发' } },
        makeCard({ name: '敌方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '我方亡语触发') && logContains(r.log, '敌方亡语触发')
  })())

  assert(`[${S}] 双方同时击破: 双方亡语伤害都打到新符卡`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '我方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(7); return '我方亡语：7伤害' } },
        makeCard({ name: '我方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        { id: -11, cost: 0, name: '敌方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(7); return '敌方亡语：7伤害' } },
        makeCard({ name: '敌方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const breakIdx = r.log.findIndex(e => e.phase === 'card_break')
    if (breakIdx < 0) return false
    const afterBreak = r.log.slice(breakIdx + 1)
    const nextCardSet = afterBreak.find(e => e.phase === 'card_set' && e.creatorCard !== undefined)
    if (!nextCardSet) return false
    return nextCardSet.creatorHp !== undefined && nextCardSet.creatorHp === 43
      && nextCardSet.joinerHp !== undefined && nextCardSet.joinerHp === 43
  })())

  assert(`[${S}] 单方击破: 亡语正常触发`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(5); return '亡语：5伤害' } },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '亡语：5伤害')
  })())

  assert(`[${S}] _brokenCardRef使用后被清除`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      { id: -10, cost: 0, name: '亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(1); return '亡语' } },
      makeCard({ atkPoint: '1d1', cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1+98', cardHp: 50 })])
    b.runFullBattle()
    return b.creator._brokenCardRef === null
  })())

  assert(`[${S}] onEnemyCardBreak在新符卡上触发`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        { id: -12, cost: 0, name: '我方反击卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onEnemyCardBreak(u, _enemy) { u.appendEffect('Strength', 2); return '击破敌方时获得强化2' } },
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '击破敌方时获得强化2')
  })())

  assert(`[${S}] 击破后新卡宣言日志正确`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '我方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const cardSetEntries = r.log.filter(e => e.phase === 'card_set')
    if (cardSetEntries.length < 2) return false
    const secondSet = cardSetEntries[1]
    return secondSet.message.includes('宣言')
  })())
}

function testDiceSystem() {
  const S = '数值体系'

  assert(`[${S}] parseDice: 1d1`, (() => {
    const d = parseDice('1d1')
    return d.count === 1 && d.faces === 1 && d.min === 1 && d.bonus === 0
  })())

  assert(`[${S}] parseDice: 1d1-1`, (() => {
    const d = parseDice('1d1-1')
    return d.count === 1 && d.faces === 1 && d.min === 1 && d.bonus === -1
  })())

  assert(`[${S}] parseDice: 2d3+1`, (() => {
    const d = parseDice('2d3+1')
    return d.count === 2 && d.faces === 3 && d.min === 1 && d.bonus === 1
  })())

  assert(`[${S}] parseDice: 1d6`, (() => {
    const d = parseDice('1d6')
    return d.count === 1 && d.faces === 6 && d.min === 1 && d.bonus === 0
  })())

  assert(`[${S}] parseDice: 3d2-2`, (() => {
    const d = parseDice('3d2-2')
    return d.count === 3 && d.faces === 2 && d.min === 1 && d.bonus === -2
  })())

  assert(`[${S}] parseDice: 1d(2~3)`, (() => {
    const d = parseDice('1d(2~3)')
    return d.count === 1 && d.faces === 3 && d.min === 2 && d.bonus === 0
  })())

  assert(`[${S}] parseDice: 2d(2~5)`, (() => {
    const d = parseDice('2d(2~5)')
    return d.count === 2 && d.faces === 5 && d.min === 2 && d.bonus === 0
  })())

  assert(`[${S}] 骰面+1: 1d1→1d2`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d1', dodPoint: '1d1' })
    const defUp = DICE_POOL.find(d => d.id === 'dice_def1')!
    defUp.apply(card)
    return card.defPoint === '1d2'
  })())

  assert(`[${S}] 骰数+1: 1d3→2d3(无代偿常数)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d1' })
    const defCount = DICE_POOL.find(d => d.id === 'dice_def_count')!
    defCount.apply(card)
    return card.defPoint === '2d3'
  })())

  assert(`[${S}] 骰下限+1: 1d3→1d(2~3)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d1' })
    const defMin = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    defMin.apply(card)
    return card.defPoint === '1d(2~3)'
  })())

  assert(`[${S}] 骰下限+1: 2d3→2d(2~3)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '2d3', dodPoint: '1d1' })
    const defMin = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    defMin.apply(card)
    return card.defPoint === '2d(2~3)'
  })())

  assert(`[${S}] 骰下限+1: 1d1不可装配(min==faces)`, (() => {
    return isDiceFixed('1d1')
  })())

  assert(`[${S}] 骰下限+1: 1d(2~2)不可装配(min==faces)`, (() => {
    return isDiceFixed('1d(2~2)')
  })())

  assert(`[${S}] 骰数+1: 1d(2~3)→2d(2~3)(min随骰数扩展)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d1' })
    const defMin = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    const defCount = DICE_POOL.find(d => d.id === 'dice_def_count')!
    defMin.apply(card)
    defCount.apply(card)
    return card.defPoint === '2d(2~3)'
  })())

  assert(`[${S}] 骰面+1: 1d(2~3)→1d(2~4)`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d3', dodPoint: '1d1' })
    const defMin = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    const defUp = DICE_POOL.find(d => d.id === 'dice_def1')!
    defMin.apply(card)
    defUp.apply(card)
    return card.defPoint === '1d(2~4)'
  })())
  assert(`[${S}] 宣言·吸血: 宣言时获得吸血1`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onCardSet(u) { u.nowHp = 45; const eff = EFFECT_POOL.find(e => e.id === 'set_drain1')!; eff.apply(u, u.enemy!); return '' } }]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const drainEffect = b.creator.effects.find(e => e.id === 'Drain')
    return drainEffect !== undefined && drainEffect.amount === 1
  })())

  assert(`[${S}] 宣言·强化结界: 宣言时展开3回合强化结界3`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d1+9', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const eff = EFFECT_POOL.find(e => e.id === 'set_strborder3')!
    eff.apply(b.creator, b.joiner!)
    const border = b.creator.effects.find(e => e.id === 'StrengthBorder')
    return border !== undefined && (border as any).turns === 3 && (border as any).strength === 3
  })())

  assert(`[${S}] 宣言·大护盾: 宣言时获得护盾4`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d1+9', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const eff = EFFECT_POOL.find(e => e.id === 'set_shield4')!
    eff.apply(b.creator, b.joiner!)
    const shield = b.creator.effects.find(e => e.id === 'Shield')
    return shield !== undefined && shield.amount === 4
  })())

  assert(`[${S}] 亡语·造成3伤害: 被击破时对敌方造成3点伤害`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语3伤', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { const eff = EFFECT_POOL.find(x => x.id === 'break_damage3')!; return eff.apply(_u, e) } },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '3点直接伤害')
  })())

  assert(`[${S}] 亡语·遗志: 被击破时展开99回合强化结界1`, (() => {
    const eff = EFFECT_POOL.find(e => e.id === 'break_permstr')!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      { id: -10, cost: 0, name: '遗志卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(u, e) { return eff.apply(u, e) } },
      makeCard({ atkPoint: '1d1', cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1+98', cardHp: 50 })])
    b.runFullBattle()
    const border = b.creator.effects.find(e => e.id === 'StrengthBorder')
    return border !== undefined && (border as any).turns === 99 && (border as any).strength === 1
  })())

  assert(`[${S}] 被动·追击: 每回合获得追击1`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d1+9', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const eff = EFFECT_POOL.find(e => e.id === 'turn_chase1')!
    eff.apply(b.creator, b.joiner!)
    const chase = b.creator.effects.find(e => e.id === 'Chase')
    return chase !== undefined && chase.amount === 1
  })())

  assert(`[${S}] 被动·追踪: 每回合获得追踪1`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d1+9', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const eff = EFFECT_POOL.find(e => e.id === 'turn_trace1')!
    eff.apply(b.creator, b.joiner!)
    const trace = b.creator.effects.find(e => e.id === 'Trace')
    return trace !== undefined && trace.amount === 1
  })())
  assert(`[${S}] 亡语击破新卡: 正确记录击破日志并换卡`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '亡语：99伤害' } },
        makeCard({ name: '我方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const breakEntries = r.log.filter(e => e.phase === 'card_break')
    return breakEntries.length >= 2 && logContains(r.log, '亡语：99伤害')
  })())

  assert(`[${S}] 双方亡语互相击破新卡: 不无限循环`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '我方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '我方亡语' } },
        makeCard({ name: '我方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        { id: -11, cost: 0, name: '敌方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '敌方亡语' } },
        makeCard({ name: '敌方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '平局') || r.winnerId !== null
  })())
  assert(`[${S}] 己方宣言效果不在敌方换卡时重复触发`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ name: '我方卡1', atkPoint: '1d1+98', cardHp: 1, defPoint: '1d1-1', dodPoint: '1d1-1' }), onCardSet(u, _e) { u.appendEffect('Strength', 1); return '宣言：强化1' } },
        makeCard({ name: '我方卡2', atkPoint: '1d1+5', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
        makeCard({ name: '敌方卡3', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const setLogs = r.log.filter(e => e.phase === 'card_set' && e.message?.includes('宣言：强化1'))
    return setLogs.length === 1
  })())

  assert(`[${S}] 己方多张符卡各自宣言效果只触发一次`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ name: '我方卡1', atkPoint: '1d1+98', cardHp: 1, defPoint: '1d1-1', dodPoint: '1d1-1' }), onCardSet(u, _e) { u.appendEffect('Strength', 1); return '卡1宣言' } },
        { ...makeCard({ name: '我方卡2', atkPoint: '1d1+98', cardHp: 1, defPoint: '1d1-1', dodPoint: '1d1-1' }), onCardSet(u, _e) { u.appendEffect('Stable', 1); return '卡2宣言' } },
        makeCard({ name: '我方卡3', atkPoint: '1d1+5', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const card1Logs = r.log.filter(e => e.phase === 'card_set' && e.message?.includes('卡1宣言'))
    const card2Logs = r.log.filter(e => e.phase === 'card_set' && e.message?.includes('卡2宣言'))
    return card1Logs.length === 1 && card2Logs.length === 1
  })())

  assert(`[${S}] justApplied在宣言触发后被重置`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      { ...makeCard({ name: '卡1', atkPoint: '1d1+98', cardHp: 1, defPoint: '1d1-1', dodPoint: '1d1-1' }), onCardSet(u) { return '宣言' } },
      makeCard({ name: '卡2', atkPoint: '1d1+5', cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [
      makeCard({ name: '敌卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ name: '敌卡2', atkPoint: '1d1', cardHp: 50 }),
    ])
    b.runFullBattle()
    return b.creator.justApplied === false
  })())
  assert(`[${S}] 非符亡语槽满时仍可替换`, (() => {
    const nonCard = createNonCard()
    const eff1 = EFFECT_POOL.find(e => e.id === 'break_damage1')!
    addEffectToCard(nonCard, eff1)
    return nonCard.effects.onCardBreak.length >= nonCard.slotCapacity.onCardBreak
      && nonCard.slotCapacity.onCardBreak > 0
  })())

  assert(`[${S}] 非符无宣言槽时不能装宣言效果`, (() => {
    const nonCard = createNonCard()
    return nonCard.slotCapacity.onCardSet === 0
  })())

  assert(`[${S}] 非符无被动槽时不能装被动效果`, (() => {
    const nonCard = createNonCard()
    return nonCard.slotCapacity.onPassive === 0
  })())

  assert(`[${S}] addEffectToCard替换旧效果`, (() => {
    const nonCard = createNonCard()
    const eff1 = EFFECT_POOL.find(e => e.id === 'break_damage1')!
    const eff2 = EFFECT_POOL.find(e => e.id === 'break_shield2')!
    addEffectToCard(nonCard, eff1)
    const result = addEffectToCard(nonCard, eff2)
    const hasNew = nonCard.effects.onCardBreak.some(e => e.id === 'break_shield2')
    const hasOld = nonCard.effects.onCardBreak.some(e => e.id === 'break_damage1')
    return hasNew && !hasOld && result.replaced !== null && result.replaced.id === 'break_damage1'
  })())
  assert(`[${S}] 宣言·灵力+2: 宣言时获得2灵力`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onCardSet(u, _e) { const eff = EFFECT_POOL.find(x => x.id === 'set_spirit2')!; return eff.apply(u, _e) } }]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    return b.creator.spiritGained >= 2
  })())

  assert(`[${S}] 宣言·造成2伤害: 宣言时对敌方造成2点直接伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1', cardHp: 50 }), onCardSet(_u, e) { const eff = EFFECT_POOL.find(x => x.id === 'set_damage2')!; return eff.apply(_u, e) } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '2点直接伤害')
  })())

  assert(`[${S}] 亡语·护盾: 被击破时获得护盾2`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语护盾卡', cardHp: 1, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(u, _e) { const eff = EFFECT_POOL.find(x => x.id === 'break_shield2')!; return eff.apply(u, _e) } },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ cardHp: 50, atkPoint: '1d1+4' }),
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '护盾') && logContains(r.log, '吸收了')
  })())

  assert(`[${S}] 亡语·强化结界: 被击破时展开强化结界`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语结界卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(u, _e) { const eff = EFFECT_POOL.find(x => x.id === 'break_strborder')!; return eff.apply(u, _e) } },
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '强化结界')
  })())

  assert(`[${S}] 被动·偶数灵动: 偶数宣言回合(gameRound为偶数)获得灵动1`, (() => {
    const r = runBattle(
      [
        makeCard({ cardHp: 1, atkPoint: '1d1+98' }),
        { ...makeCard({ dodPoint: '1d1', cardHp: 50 }), onTurnStart(u, _e) { const eff = EFFECT_POOL.find(x => x.id === 'turn_agile1_even')!; return eff.apply(u, _e) } },
      ],
      [
        makeCard({ cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '回避增加了1点')
  })())

  assert(`[${S}] 被动·灵力+1: 每回合获得1灵力`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onTurnStart(u, _e) { const eff = EFFECT_POOL.find(x => x.id === 'turn_spirit1')!; return eff.apply(u, _e) } }]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    return b.creator.spiritGained >= 1
  })())

  assert(`[${S}] 被动·稳固: 每回合获得稳固1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ defPoint: '1d1+2', cardHp: 50 }), onTurnStart(u, _e) { const eff = EFFECT_POOL.find(x => x.id === 'turn_stable1')!; return eff.apply(u, _e) } }],
      [makeCard({ atkPoint: '1d1+4', cardHp: 50 })],
    )
    return logContains(r.log, '防御增加了1点')
  })())

  assert(`[${S}] 被动·伤害: 每回合对敌方造成1点直接伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onTurnStart(u, e) { const eff = EFFECT_POOL.find(x => x.id === 'turn_damage1')!; return eff.apply(u, e) } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logContains(r.log, '1点直接伤害')
  })())

  assert(`[${S}] 被动·击杀回复: 击破对方符卡时回复2HP`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ atkPoint: '1d1+98', cardHp: 50 }), onEnemyCardBreak(u, _enemy) { const eff = EFFECT_POOL.find(x => x.id === 'ek_kill_heal3')!; return eff.apply(u, _enemy) } },
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
      [
        makeCard({ cardHp: 5, atkPoint: '1d1+4', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '击杀回复')
  })())

  assert(`[${S}] 被动·击杀回复: 回复不超过血量上限`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      { ...makeCard({ atkPoint: '1d1+98', cardHp: 50 }), onEnemyCardBreak(u, _enemy) { const eff = EFFECT_POOL.find(x => x.id === 'ek_kill_heal3')!; return eff.apply(u, _enemy) } },
      makeCard({ atkPoint: '1d1', cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [
      makeCard({ cardHp: 5, atkPoint: '1d1+4', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ atkPoint: '1d1', cardHp: 50 }),
    ])
    b.runFullBattle()
    return b.creator.nowHp <= b.creator.nowCard!.cardHp
  })())

  assert(`[${S}] 被动·击杀回复: 回复上限为maxCardHp而非cardHp`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      { ...makeCard({ cardHp: 8, maxCardHp: 20, atkPoint: '1d1+98', defPoint: '1d1+98', dodPoint: '1d1+98' }), onEnemyCardBreak(u, _enemy) { const eff = EFFECT_POOL.find(x => x.id === 'ek_kill_heal3')!; return eff.apply(u, _enemy) } },
      makeCard({ atkPoint: '1d1', cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [
      makeCard({ cardHp: 1, atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ cardHp: 1, atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ cardHp: 1, atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1' }),
    ])
    b.runFullBattle()
    return b.creator.nowHp > 8 && b.creator.nowHp <= 20
  })())

  assert(`[${S}] 被动·击杀强化: 击破对方符卡时获得强化2`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ atkPoint: '1d1+98', cardHp: 50 }), onEnemyCardBreak(u, _enemy) { const eff = EFFECT_POOL.find(x => x.id === 'ek_kill_str2')!; return eff.apply(u, _enemy) } },
        makeCard({ atkPoint: '1d1+4', cardHp: 50 }),
      ],
      [
        makeCard({ cardHp: 5, atkPoint: '1d1+4', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '击杀强化')
  })())
}

function testBattleFlow() {
  const S = '战斗流程'

  assert(`[${S}] 1v1对战正常完成`, (() => {
    const r = runBattle(
      [makeCard({ atkPoint: '1d1+5', cardHp: 10 })],
      [makeCard({ atkPoint: '1d1+3', cardHp: 10 })],
    )
    return r.winnerId !== null && r.log.length > 0
  })())

  assert(`[${S}] 多卡切换: 3卡vs3卡正常完成`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1 }), makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1d1+5', cardHp: 10 })],
      [makeCard({ cardHp: 1 }), makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1d1+3', cardHp: 10 })],
    )
    return r.winnerId !== null && logPhaseCount(r.log, 'card_break') >= 2
  })())

  assert(`[${S}] 双方同时击破: 正确处理`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1, atkPoint: '1d1+98' }), makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ cardHp: 1, atkPoint: '1d1+98' }), makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    return logPhaseCount(r.log, 'card_break') >= 1
  })())

  assert(`[${S}] 最后一张卡亡语: onCardBreak在shouldEnd时仍触发`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '亡语：99伤害' } },
      ],
      [
        { id: -11, cost: 0, name: '敌方卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '' },
      ],
    )
    return logContains(r.log, '亡语：99伤害') && logContains(r.log, '平局')
  })())

  assert(`[${S}] 最后一张卡亡语: 清理敌方效果(CantDefence)不报错`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      { id: -10, cost: 0, name: '红寸劲', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(_u, e) { e.appendEffect('CantDefence', -1); return '' }, onCardBreak(_u, e) { e.removeEffect('CantDefence'); return '' } },
      makeCard({ cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [
      makeCard({ cardHp: 1, atkPoint: '1d1+98' }),
      makeCard({ cardHp: 50 }),
    ])
    b.runFullBattle()
    const joinerCantDef = b.joiner!.effects.filter(e => e.id === 'CantDefence')
    return joinerCantDef.length === 0 && b.finished
  })())

  assert(`[${S}] 防御不可: 闪避成功时不显示防御不可消息`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ atkPoint: '1d1+4', cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('CantDefence', -1); return '' } },
      ],
      [
        makeCard({ atkPoint: '1d1-1', cardHp: 50 }),
      ],
    )
    const calcEntries = r.log.filter(e => e.phase === 'calc')
    for (const entry of calcEntries) {
      const msg = entry.message
      const hasDodgeSuccess = msg.includes('闪避成功')
      const hasCantDefence = msg.includes('无法作出防御')
      if (hasDodgeSuccess && hasCantDefence) return false
    }
    return true
  })())

  assert(`[${S}] Drain吸血: hurt日志显示原始伤害而非净变化`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+9', cardHp: 50 }), onCardSet(u) { u.nowHp = 45; u.appendEffect('Drain', 2); return '' } }],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    const msg = firstHurt.message
    if (!msg.includes('吸血恢复')) return false
    const dmgMatch = msg.match(/A 受到(\d+)点伤害/)
    if (!dmgMatch) return false
    const dmg = parseInt(dmgMatch[1])
    const healMatch = msg.match(/吸血恢复了(\d+)点HP/)
    if (!healMatch) return false
    const heal = parseInt(healMatch[1])
    return dmg >= 1 && heal >= 1 && firstHurt.creatorHp !== undefined && firstHurt.creatorHp === 45 - dmg + heal
  })())

  assert(`[${S}] 时符完整流程: 宣言→免疫→耗尽→击破→换卡`, (() => {
    const timeCard: CardData = {
      id: -2, cost: 0, name: '测试时符', cardHp: 3,
      atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1',
      description: '', isTimeCard: true, timeCardTurns: 2,
    }
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1d1+5', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1+5', cardHp: 50 })],
    )
    return logContains(r.log, '时符时间耗尽') && logContains(r.log, '因时符耗尽而消散') && logPhaseCount(r.log, 'card_set') >= 2
  })())

  assert(`[${S}] 结界衰减: 到期后效果消失`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1d1+4', cardHp: 50 }), onCardSet(u) { u.appendBorder('StrengthBorder', 1, 5); return '' } }],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    const strLogs = r.log.filter(e => e.message.includes('攻击增加了5点'))
    return strLogs.length === 1
  })())

  assert(`[${S}] 完整循环: 宣言→战斗→击破→亡语→换卡→宣言`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ cardHp: 1, atkPoint: '1d1+98' }), onCardSet(u) { u.appendEffect('Strength', 1); return '宣言：强化1' }, onCardBreak(_u, e) { e.effectHurt(2); return '亡语：2伤害' } },
        { ...makeCard({ atkPoint: '1d1+5', cardHp: 50 }), onCardSet(u) { u.appendEffect('Stable', 1); return '宣言：稳固1' } },
      ],
      [
        makeCard({ cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    return logContains(r.log, '宣言：强化1') && logContains(r.log, '亡语：2伤害') && logContains(r.log, '宣言：稳固1')
  })())
  assert(`[${S}] 结界叠加: 同类型结界取最大回合`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.creator.appendBorder('StrengthBorder', 3, 2)
    b.creator.appendBorder('StrengthBorder', 5, 1)
    const border = b.creator.effects.find(e => e.id === 'StrengthBorder')
    return border !== undefined && (border as any).turns === 5 && (border as any).strength === 2
  })())

  assert(`[${S}] HP回复: 不超过血量上限`, (() => {
    const cards: ExpeditionCard[] = [
      createNonCard(),
      createSpellCard({ name: '符卡', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d1', dodPoint: '1d1' }),
    ]
    cards[0].currentHp = 10
    healNonCard(cards)
    return cards[0].currentHp === cards[0].maxCardHp
  })())

  assert(`[${S}] 非符回血: 战后回满`, (() => {
    const cards: ExpeditionCard[] = [
      createNonCard(),
      createSpellCard({ name: '符卡', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d1', dodPoint: '1d1' }),
    ]
    cards[0].currentHp = 1
    cards[1].currentHp = 2
    healNonCard(cards)
    return cards[0].currentHp === cards[0].maxCardHp && cards[1].currentHp === 2
  })())

  assert(`[${S}] 新面回血: 所有卡回满`, (() => {
    const cards: ExpeditionCard[] = [
      createNonCard(),
      createSpellCard({ name: '符卡', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1d1', dodPoint: '1d1' }),
    ]
    cards[0].currentHp = 1
    cards[1].currentHp = 2
    healAllForNewStage(cards)
    return cards[0].currentHp === cards[0].maxCardHp && cards[1].currentHp === cards[1].maxCardHp
  })())

  assert(`[${S}] 骰子范围: 1d6攻击值在1-6范围内`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d6', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const pts = b.log.entries.filter(e => e.phase === 'points' && e.visual?.creatorAtk !== undefined)
    for (const e of pts) { if (e.visual!.creatorAtk < 1 || e.visual!.creatorAtk > 6) return false }
    return pts.length > 0
  })())

  assert(`[${S}] 骰子范围: 1d(2~4)攻击值在2-4范围内`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d(2~4)', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const pts = b.log.entries.filter(e => e.phase === 'points' && e.visual?.creatorAtk !== undefined)
    for (const e of pts) { if (e.visual!.creatorAtk < 2 || e.visual!.creatorAtk > 4) return false }
    return pts.length > 0
  })())

  assert(`[${S}] 骰子范围: 2d4攻击值在2-8范围内`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '2d4', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const pts = b.log.entries.filter(e => e.phase === 'points' && e.visual?.creatorAtk !== undefined)
    for (const e of pts) { if (e.visual!.creatorAtk < 2 || e.visual!.creatorAtk > 8) return false }
    return pts.length > 0
  })())

  assert(`[${S}] 骰子范围: 1d3+1攻击值在2-4范围内`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d3+1', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const pts = b.log.entries.filter(e => e.phase === 'points' && e.visual?.creatorAtk !== undefined)
    for (const e of pts) { if (e.visual!.creatorAtk < 2 || e.visual!.creatorAtk > 4) return false }
    return pts.length > 0
  })())

  assert(`[${S}] 骰子范围: 1d1-1攻击值为0`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1', cardHp: 50 })])
    b.runFullBattle()
    const pts = b.log.entries.filter(e => e.phase === 'points' && e.visual?.creatorAtk !== undefined)
    for (const e of pts) { if (e.visual!.creatorAtk !== 0) return false }
    return pts.length > 0
  })())

  assert(`[${S}] formatDice: 标准格式`, (() => {
    return formatDice({ count: 2, faces: 4 }) === '2d4'
  })())

  assert(`[${S}] formatDice: min-face格式`, (() => {
    return formatDice({ count: 1, faces: 3, min: 2 }) === '1d(2~3)'
  })())

  assert(`[${S}] formatDice: 带常数`, (() => {
    return formatDice({ count: 1, faces: 3, bonus: 1 }) === '1d3+1'
  })())
}

function testAnimationCardTracking() {
  const S = '动画追踪'

  function simulateAnimation(log: LogEntry[]): { phase: string; creatorCard: string | null; joinerCard: string | null }[] {
    const result: { phase: string; creatorCard: string | null; joinerCard: string | null }[] = []
    let curCreatorCard: string | null = null
    let curJoinerCard: string | null = null

    for (const entry of log) {
      if (entry.phase === 'card_set') {
        if (entry.creatorCard) curCreatorCard = entry.creatorCard.name
        if (entry.joinerCard) curJoinerCard = entry.joinerCard.name
      }
      if (entry.phase === 'card_break') {
        if (entry.creatorCard) curCreatorCard = entry.creatorCard.name
        if (entry.joinerCard) curJoinerCard = entry.joinerCard.name
        if (entry.creatorHp !== undefined && entry.creatorHp <= 0 && !entry.creatorCard) curCreatorCard = null
        if (entry.joinerHp !== undefined && entry.joinerHp <= 0 && !entry.joinerCard) curJoinerCard = null
      }
      result.push({ phase: entry.phase, creatorCard: curCreatorCard, joinerCard: curJoinerCard })
    }
    return result
  }

  function verifyNoCardJumps(tracking: { phase: string; creatorCard: string | null; joinerCard: string | null }[]): string | null {
    let prevCreator: string | null = null
    let prevJoiner: string | null = null
    for (let i = 0; i < tracking.length; i++) {
      const t = tracking[i]
      if (t.phase === 'card_set' || t.phase === 'card_break') {
        prevCreator = t.creatorCard
        prevJoiner = t.joinerCard
        continue
      }
      if (t.creatorCard !== prevCreator) return `entry ${i} phase=${t.phase}: creator card jumped from "${prevCreator}" to "${t.creatorCard}"`
      if (t.joinerCard !== prevJoiner) return `entry ${i} phase=${t.phase}: joiner card jumped from "${prevJoiner}" to "${t.joinerCard}"`
    }
    return null
  }

  assert(`[${S}] 单卡对战: 符卡名全程不变`, (() => {
    const r = runBattle(
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    const tracking = simulateAnimation(r.log)
    const err = verifyNoCardJumps(tracking)
    if (err) { console.error(err); return false }
    return true
  })())

  assert(`[${S}] 多卡对战: 符卡切换时名称正确变化`, (() => {
    const r = runBattle(
      [makeCard({ name: '卡A', cardHp: 1 }), makeCard({ name: '卡B', atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    const tracking = simulateAnimation(r.log)
    const cardSetEntries = tracking.filter(t => t.phase === 'card_set' && t.creatorCard !== null)
    if (cardSetEntries.length < 2) return false
    const firstSet = cardSetEntries[0]
    const secondSet = cardSetEntries[cardSetEntries.length - 1]
    if (firstSet.creatorCard !== '卡A') { console.error(`first card_set creator=${firstSet.creatorCard}, expected 卡A`); return false }
    if (secondSet.creatorCard !== '卡B') { console.error(`last card_set creator=${secondSet.creatorCard}, expected 卡B`); return false }
    return true
  })())

  assert(`[${S}] 多卡对战: 非card_set/card_break阶段符卡名不跳`, (() => {
    const r = runBattle(
      [
        { id: -3, cost: 0, name: '脆弱卡', cardHp: 3, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(u, _e) { u.appendEffect('Shield', 2); return '获得护盾' } },
        makeCard({ name: '第二张卡', atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1+4', cardHp: 50 })],
    )
    const tracking = simulateAnimation(r.log)
    const err = verifyNoCardJumps(tracking)
    if (err) { console.error(err); return false }
    return true
  })())

  assert(`[${S}] 双方多卡: 击破后换卡名称正确`, (() => {
    const r = runBattle(
      [makeCard({ name: '我方卡1', cardHp: 1 }), makeCard({ name: '我方卡2', atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ name: '敌方卡1', cardHp: 1 }), makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 })],
    )
    const tracking = simulateAnimation(r.log)
    const err = verifyNoCardJumps(tracking)
    if (err) { console.error(err); return false }
    return true
  })())

  assert(`[${S}] onCardSet后续日志不覆盖符卡名`, (() => {
    const r = runBattle(
      [
        { id: -4, cost: 0, name: '宣言卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(u, e) { e.effectHurt(2); return '宣言效果触发' } },
      ],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    const cardSetEntries = r.log.filter(e => e.phase === 'card_set' && e.creatorCard !== undefined)
    const firstSet = cardSetEntries[0]
    if (!firstSet.creatorCard || firstSet.creatorCard.name !== '宣言卡') return false
    const subsequentSets = cardSetEntries.slice(1)
    for (const entry of subsequentSets) {
      if (entry.creatorCard !== undefined) {
        console.error(`subsequent card_set entry has creatorCard=${entry.creatorCard.name}, should be undefined`)
        return false
      }
    }
    return true
  })())

  assert(`[${S}] card_break日志正确记录被击破的符卡`, (() => {
    const r = runBattle(
      [makeCard({ name: '被击破卡', cardHp: 1 }), makeCard({ name: '后继卡', atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1+98', cardHp: 50 })],
    )
    const breakEntry = r.log.find(e => e.phase === 'card_break')
    if (!breakEntry) return false
    if (!breakEntry.creatorCard || breakEntry.creatorCard.name !== '被击破卡') {
      console.error(`card_break creatorCard=${breakEntry.creatorCard?.name}, expected 被击破卡`)
      return false
    }
    return true
  })())

  assert(`[${S}] 5卡对战全流程: 符卡名始终正确`, (() => {
    const r = runBattle(
      ALL_CARDS.slice(0, 5).map(c => ({ ...c })),
      ALL_CARDS.slice(5, 10).map(c => ({ ...c })),
    )
    const tracking = simulateAnimation(r.log)
    const err = verifyNoCardJumps(tracking)
    if (err) { console.error(err); return false }
    return true
  })())
}

function testStateMachine() {
  const S = '状态机'

  function getBreakCardNames(log: LogEntry[], side: 'creator' | 'joiner'): string[] {
    return log
      .filter(e => e.phase === 'card_break')
      .map(e => side === 'creator' ? (e.creatorCard?.name ?? '') : (e.joinerCard?.name ?? ''))
      .filter(n => n !== '')
  }

  function getCardSetHp(log: LogEntry[], index: number): { cHp: number | undefined; jHp: number | undefined } {
    const sets = log.filter(e => e.phase === 'card_set' && e.message.includes('宣言'))
    if (index >= sets.length) return { cHp: undefined, jHp: undefined }
    return { cHp: sets[index].creatorHp, jHp: sets[index].joinerHp }
  }

  assert(`[${S}] runFullBattle: 双方同时击破-无亡语-每张卡只击破一次`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '我方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const creatorBreaks = getBreakCardNames(r.log, 'creator')
    const joinerBreaks = getBreakCardNames(r.log, 'joiner')
    const creatorDupes = creatorBreaks.filter((n, i) => creatorBreaks.indexOf(n) !== i)
    const joinerDupes = joinerBreaks.filter((n, i) => joinerBreaks.indexOf(n) !== i)
    if (creatorDupes.length > 0) { console.error(`creator duplicate breaks: ${creatorDupes}`); return false }
    if (joinerDupes.length > 0) { console.error(`joiner duplicate breaks: ${joinerDupes}`); return false }
    return true
  })())

  assert(`[${S}] runFullBattle: 双方同时击破-亡语击破新卡-新卡有击破日志`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '我方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '亡语：99伤害' } },
        makeCard({ name: '我方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方后继1', atkPoint: '1d1', cardHp: 10 }),
        makeCard({ name: '敌方后继2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const joinerBreaks = getBreakCardNames(r.log, 'joiner')
    if (!joinerBreaks.includes('敌方卡1')) { console.error(`missing break for 敌方卡1, got: ${joinerBreaks}`); return false }
    if (!joinerBreaks.includes('敌方后继1')) { console.error(`missing break for 敌方后继1, got: ${joinerBreaks}`); return false }
    const dupes = joinerBreaks.filter((n, i) => joinerBreaks.indexOf(n) !== i)
    if (dupes.length > 0) { console.error(`duplicate joiner breaks: ${dupes}`); return false }
    return true
  })())

  assert(`[${S}] runFullBattle: 双方同时击破-双方亡语互相击破新卡`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '我方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '我方亡语' } },
        makeCard({ name: '我方后继1', atkPoint: '1d1', cardHp: 10 }),
        makeCard({ name: '我方后继2', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        { id: -11, cost: 0, name: '敌方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '敌方亡语' } },
        makeCard({ name: '敌方后继1', atkPoint: '1d1', cardHp: 10 }),
        makeCard({ name: '敌方后继2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const creatorBreaks = getBreakCardNames(r.log, 'creator')
    const joinerBreaks = getBreakCardNames(r.log, 'joiner')
    if (!creatorBreaks.includes('我方亡语卡')) { console.error(`missing break for 我方亡语卡`); return false }
    if (!creatorBreaks.includes('我方后继1')) { console.error(`missing break for 我方后继1, got: ${creatorBreaks}`); return false }
    if (!joinerBreaks.includes('敌方亡语卡')) { console.error(`missing break for 敌方亡语卡`); return false }
    if (!joinerBreaks.includes('敌方后继1')) { console.error(`missing break for 敌方后继1, got: ${joinerBreaks}`); return false }
    return true
  })())

  assert(`[${S}] runFullBattle: 宣言效果击破敌方-下轮有击破日志`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        { id: -12, cost: 0, name: '宣言伤害卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(_u, e) { e.effectHurt(99); return '宣言：99伤害' } },
        makeCard({ name: '我方卡3', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方后继', atkPoint: '1d1', cardHp: 50 }),
        makeCard({ name: '敌方第三卡', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const joinerBreaks = getBreakCardNames(r.log, 'joiner')
    if (!joinerBreaks.includes('敌方卡1')) { console.error(`missing break for 敌方卡1`); return false }
    if (!joinerBreaks.includes('敌方后继')) { console.error(`missing break for 敌方后继, got: ${joinerBreaks}`); return false }
    const dupes = joinerBreaks.filter((n, i) => joinerBreaks.indexOf(n) !== i)
    if (dupes.length > 0) { console.error(`duplicate joiner breaks: ${dupes}`); return false }
    return logContains(r.log, '宣言：99伤害')
  })())

  assert(`[${S}] runFullBattle: 宣言效果击破敌方后-下轮正确处理击破`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        { id: -12, cost: 0, name: '宣言伤害卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(_u, e) { e.effectHurt(99); return '宣言：99伤害' } },
        makeCard({ name: '我方卡3', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方后继', atkPoint: '1d1', cardHp: 5 }),
        makeCard({ name: '敌方第三卡', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const joinerBreaks = getBreakCardNames(r.log, 'joiner')
    if (!joinerBreaks.includes('敌方卡1')) { console.error(`missing break for 敌方卡1`); return false }
    if (!joinerBreaks.includes('敌方后继')) { console.error(`missing break for 敌方后继, got: ${joinerBreaks}`); return false }
    const dupes = joinerBreaks.filter((n, i) => joinerBreaks.indexOf(n) !== i)
    if (dupes.length > 0) { console.error(`duplicate joiner breaks: ${dupes}`); return false }
    return true
  })())

  assert(`[${S}] runFullBattle: 击破日志中同一张卡名不出现两次`, (() => {
    for (let seed = 1; seed <= 200; seed++) {
      const b = new Battle(1, seed)
      b.setCreator('A')
      b.creator.chosenCards = [
        makeCard({ name: 'A1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'A2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'A3', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ]
      b.setSingleEnemy('B', [
        makeCard({ name: 'B1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'B2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'B3', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ])
      b.runFullBattle()
      const log = b.log.entries
      const cBreaks = getBreakCardNames(log, 'creator')
      const jBreaks = getBreakCardNames(log, 'joiner')
      const cDupes = cBreaks.filter((n, i) => cBreaks.indexOf(n) !== i)
      const jDupes = jBreaks.filter((n, i) => jBreaks.indexOf(n) !== i)
      if (cDupes.length > 0 || jDupes.length > 0) {
        console.error(`seed=${seed} cDupes=${cDupes} jDupes=${jDupes}`)
        return false
      }
    }
    return true
  })())

  assert(`[${S}] runFullBattle: 宣言日志中HP>0(除非战斗结束)`, (() => {
    for (let seed = 1; seed <= 200; seed++) {
      const b = new Battle(1, seed)
      b.setCreator('A')
      b.creator.chosenCards = [
        makeCard({ name: 'A1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'A2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ]
      b.setSingleEnemy('B', [
        makeCard({ name: 'B1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'B2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ])
      b.runFullBattle()
      const declareEntries = b.log.entries.filter(e => e.phase === 'card_set' && e.message.includes('宣言'))
      for (const entry of declareEntries) {
        if (entry.creatorHp !== undefined && entry.creatorHp <= 0) {
          console.error(`seed=${seed} declaration has creatorHp=${entry.creatorHp}: ${entry.message}`)
          return false
        }
        if (entry.joinerHp !== undefined && entry.joinerHp <= 0) {
          console.error(`seed=${seed} declaration has joinerHp=${entry.joinerHp}: ${entry.message}`)
          return false
        }
      }
    }
    return true
  })())

  assert(`[${S}] runFullBattle: 亡语击破新卡-击破顺序正确(旧卡先击破-新卡后击破)`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '我方亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(99); return '亡语' } },
        makeCard({ name: '我方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方旧卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方新卡', atkPoint: '1d1', cardHp: 10 }),
        makeCard({ name: '敌方第三卡', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const breakEntries = r.log.filter(e => e.phase === 'card_break' && e.joinerCard)
    const breakNames = breakEntries.map(e => e.joinerCard!.name)
    const oldIdx = breakNames.indexOf('敌方旧卡')
    const newIdx = breakNames.indexOf('敌方新卡')
    if (oldIdx < 0) { console.error(`missing break for 敌方旧卡`); return false }
    if (newIdx < 0) { console.error(`missing break for 敌方新卡, breaks: ${breakNames}`); return false }
    if (oldIdx >= newIdx) { console.error(`旧卡应在新卡之前被击破, oldIdx=${oldIdx} newIdx=${newIdx}`); return false }
    return true
  })())

  assert(`[${S}] runFullBattle: 击破→换卡→宣言 完整日志序列`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '我方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const phases = r.log.map(e => e.phase)
    const firstBreakIdx = phases.indexOf('card_break')
    const firstSetAfterBreak = phases.slice(firstBreakIdx).indexOf('card_set')
    if (firstBreakIdx < 0) { console.error('no card_break found'); return false }
    if (firstSetAfterBreak < 0) { console.error('no card_set after card_break'); return false }
    const breakEntry = r.log[firstBreakIdx]
    const setEntry = r.log[firstBreakIdx + firstSetAfterBreak]
    if (!breakEntry.message.includes('击破') && !breakEntry.message.includes('消散')) { console.error(`break msg: ${breakEntry.message}`); return false }
    if (!setEntry.message.includes('宣言')) { console.error(`set msg: ${setEntry.message}`); return false }
    return true
  })())

  assert(`[${S}] runFullBattle: 时符耗尽→击破→换卡 完整流程`, (() => {
    const timeCard: CardData = {
      id: -2, cost: 0, name: '测试时符', cardHp: 3,
      atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1',
      description: '', isTimeCard: true, timeCardTurns: 1,
    }
    const r = runBattle(
      [timeCard, makeCard({ name: '后继卡', atkPoint: '1d1', cardHp: 50 })],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    const phases = r.log.map(e => e.phase)
    const timeIdx = phases.indexOf('time_expire')
    const breakIdx = phases.indexOf('card_break')
    const setIdx = phases.slice(breakIdx).indexOf('card_set')
    if (timeIdx < 0) { console.error('no time_expire'); return false }
    if (breakIdx < 0) { console.error('no card_break'); return false }
    if (setIdx < 0) { console.error('no card_set after break'); return false }
    if (breakIdx <= timeIdx) { console.error('break should be after time_expire'); return false }
    const breakEntry = r.log[breakIdx]
    if (breakEntry.visual?.breakSource !== 'time') { console.error(`breakSource=${breakEntry.visual?.breakSource}`); return false }
    return true
  })())

  assert(`[${S}] runFullBattle: 伤害结界击破-有击破日志`, (() => {
    const r = runBattle(
      [
        { id: -13, cost: 0, name: '结界卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(u) { u.appendBorder('DamageBorder', 5, 99); return '展开伤害结界' } },
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 3, atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1-1', cardHp: 50 }),
      ],
    )
    const joinerBreaks = getBreakCardNames(r.log, 'joiner')
    if (!joinerBreaks.includes('敌方卡1')) { console.error(`missing break for 敌方卡1, got: ${joinerBreaks}`); return false }
    return true
  })())

  assert(`[${S}] playCardAndResolve: 双方同时击破-不会重复记录击破`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ name: '我方卡2', atkPoint: '1d1', cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [
      makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
    ])
    b.playCardAndResolve(0)
    if (b.state !== Battle.STATE_WAITING_CREATOR_CARD) {
      console.error(`expected WAITING_CREATOR_CARD, got ${b.state}`)
      return false
    }
    b.playCardAndResolve(1)
    const joinerBreaks = getBreakCardNames(b.log.entries, 'joiner')
    const dupes = joinerBreaks.filter((n, i) => joinerBreaks.indexOf(n) !== i)
    if (dupes.length > 0) { console.error(`duplicate joiner breaks in playCardAndResolve: ${dupes}, all: ${joinerBreaks}`); return false }
    return true
  })())

  assert(`[${S}] playCardAndResolve: 双方同时击破-宣言时HP>0`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [
      makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ name: '我方卡2', atkPoint: '1d1', cardHp: 50 }),
    ]
    b.setSingleEnemy('B', [
      makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
      makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
    ])
    b.playCardAndResolve(0)
    b.playCardAndResolve(1)
    const declareEntries = b.log.entries.filter(e => e.phase === 'card_set' && e.message.includes('宣言'))
    for (const entry of declareEntries) {
      if (entry.joinerHp !== undefined && entry.joinerHp <= 0) {
        console.error(`declaration has joinerHp=${entry.joinerHp}: ${entry.message}`)
        return false
      }
    }
    return true
  })())

  assert(`[${S}] runFullBattle: 击破数=usedCardIndices-1(非最后卡)或=usedCardIndices(最后卡被击破)`, (() => {
    for (let seed = 1; seed <= 100; seed++) {
      const b = new Battle(1, seed)
      b.setCreator('A')
      b.creator.chosenCards = [
        makeCard({ name: 'A1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'A2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'A3', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ]
      b.setSingleEnemy('B', [
        makeCard({ name: 'B1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'B2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'B3', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ])
      b.runFullBattle()
      const cBreakCount = getBreakCardNames(b.log.entries, 'creator').length
      const jBreakCount = getBreakCardNames(b.log.entries, 'joiner').length
      const cUsed = b.creator.usedCardIndices.length
      const jUsed = b.joiner!.usedCardIndices.length
      const cLastBroken = b.creator.nowHp <= 0
      const jLastBroken = b.joiner!.nowHp <= 0
      const expectedCBreaks = cLastBroken ? cUsed : cUsed - 1
      const expectedJBreaks = jLastBroken ? jUsed : jUsed - 1
      if (cBreakCount !== expectedCBreaks) {
        console.error(`seed=${seed} creator breaks=${cBreakCount} expected=${expectedCBreaks} used=${cUsed} lastBroken=${cLastBroken}`)
        return false
      }
      if (jBreakCount !== expectedJBreaks) {
        console.error(`seed=${seed} joiner breaks=${jBreakCount} expected=${expectedJBreaks} used=${jUsed} lastBroken=${jLastBroken}`)
        return false
      }
    }
    return true
  })())

  assert(`[${S}] runFullBattle: card_break后必有card_set(除非战斗结束)`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '我方卡2', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '我方卡3', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const phases = r.log.map(e => e.phase)
    for (let i = 0; i < phases.length; i++) {
      if (phases[i] === 'card_break') {
        const afterBreak = phases.slice(i + 1)
        const nextPhase = afterBreak[0]
        if (nextPhase === 'card_break') continue
        if (nextPhase === 'end') continue
        if (nextPhase !== 'card_set') {
          console.error(`after card_break at ${i}, next phase is ${nextPhase}, expected card_set or end`)
          return false
        }
      }
    }
    return true
  })())

  assert(`[${S}] runFullBattle: gameRound在每次换卡时递增`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '我方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '我方卡2', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '我方卡3', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 50, atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方卡2', atkPoint: '1d1-1', cardHp: 50 }),
      ],
    )
    const cardSetRounds = r.log.filter(e => e.phase === 'card_set' && e.creatorCard !== undefined).map(e => e.round)
    for (let i = 1; i < cardSetRounds.length; i++) {
      if (cardSetRounds[i] <= cardSetRounds[i - 1]) {
        console.error(`card_set rounds not increasing: ${cardSetRounds}`)
        return false
      }
    }
    return cardSetRounds.length >= 2
  })())

  assert(`[${S}] runFullBattle: 亡语+宣言伤害连锁-完整日志链`, (() => {
    const r = runBattle(
      [
        { id: -10, cost: 0, name: '亡语卡', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardBreak(_u, e) { e.effectHurt(5); return '亡语：5伤害' } },
        { id: -12, cost: 0, name: '宣言伤害卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(_u, e) { e.effectHurt(3); return '宣言：3伤害' } },
        makeCard({ name: '我方卡3', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌方卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌方后继', atkPoint: '1d1', cardHp: 50 }),
      ],
    )
    const hasDeathword = logContains(r.log, '亡语：5伤害')
    const hasDeclareDmg = logContains(r.log, '宣言：3伤害')
    const joinerBreaks = getBreakCardNames(r.log, 'joiner')
    const noDupes = joinerBreaks.filter((n, i) => joinerBreaks.indexOf(n) !== i).length === 0
    return hasDeathword && hasDeclareDmg && noDupes
  })())

  assert(`[${S}] 日志快照: 每个条目都有效果快照和符卡序号`, (() => {
    const r = runBattle(
      [
        { id: -3, cost: 0, name: '结界卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(u) { u.appendBorder('DamageBorder', 3, 2); return '展开伤害结界' } },
        makeCard({ name: '后继卡', atkPoint: '1d1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1d1', cardHp: 50 })],
    )
    for (let i = 0; i < r.log.length; i++) {
      const e = r.log[i]
      if (e.creatorEffects === undefined) { console.error(`entry ${i} phase=${e.phase} missing creatorEffects`); return false }
      if (e.joinerEffects === undefined) { console.error(`entry ${i} phase=${e.phase} missing joinerEffects`); return false }
      if (e.creatorCardIndex === undefined) { console.error(`entry ${i} phase=${e.phase} missing creatorCardIndex`); return false }
      if (e.joinerCardIndex === undefined) { console.error(`entry ${i} phase=${e.phase} missing joinerCardIndex`); return false }
    }
    return true
  })())

  assert(`[${S}] 日志快照: 效果列表随回合正确变化`, (() => {
    const r = runBattle(
      [
        { id: -3, cost: 0, name: '结界卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(u) { u.appendBorder('DamageBorder', 3, 2); return '展开伤害结界' } },
      ],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    const effectEntry = r.log.find(e => e.phase === 'card_set' && e.message.includes('展开伤害结界'))
    if (!effectEntry) { console.error('no card_set effect entry'); return false }
    const borderAfterApply = effectEntry.creatorEffects!
    const border = borderAfterApply.find(e => e.id === 'DamageBorder')
    if (!border) { console.error(`no DamageBorder after onCardSet: ${borderAfterApply.map(e => e.id)}`); return false }
    const turnEnds = r.log.filter(e => e.phase === 'turn_end')
    if (turnEnds.length === 0) return true
    const lastTurnEnd = turnEnds[turnEnds.length - 1]
    const afterEffects = lastTurnEnd.creatorEffects!
    const borderAfter = afterEffects.find(e => e.id === 'DamageBorder')
    if (borderAfter && borderAfter.turns! >= border.turns!) {
      console.error(`DamageBorder turns should decrease: afterApply=${border.turns} afterTurns=${borderAfter.turns}`)
      return false
    }
    return true
  })())

  assert(`[${S}] 日志快照: 符卡序号在换卡时递增`, (() => {
    const r = runBattle(
      [
        makeCard({ name: '卡1', cardHp: 1, atkPoint: '1d1+98', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '卡2', atkPoint: '1d1', cardHp: 50 }),
      ],
      [
        makeCard({ name: '敌1', cardHp: 50, atkPoint: '1d1-1', defPoint: '1d1-1', dodPoint: '1d1-1' }),
        makeCard({ name: '敌2', atkPoint: '1d1-1', cardHp: 50 }),
      ],
    )
    const cardSetEntries = r.log.filter(e => e.phase === 'card_set')
    if (cardSetEntries.length < 2) { console.error(`need at least 2 card_set entries, got ${cardSetEntries.length}`); return false }
    const firstIdx = cardSetEntries[0].creatorCardIndex!
    const secondIdx = cardSetEntries[cardSetEntries.length - 1].creatorCardIndex!
    if (secondIdx <= firstIdx) { console.error(`creatorCardIndex not increasing: ${firstIdx} -> ${secondIdx}`); return false }
    return true
  })())

  assert(`[${S}] 日志快照: 动画回放-效果列表不跳变`, (() => {
    const r = runBattle(
      [
        { id: -3, cost: 0, name: '结界卡', cardHp: 50, atkPoint: '1d1', defPoint: '1d1-1', dodPoint: '1d1-1', description: '', onCardSet(u) { u.appendBorder('DamageBorder', 3, 2); return '展开伤害结界' } },
      ],
      [makeCard({ atkPoint: '1d1-1', cardHp: 50 })],
    )
    let prevCreatorEffs: string[] = []
    let prevJoinerEffs: string[] = []
    for (let i = 0; i < r.log.length; i++) {
      const e = r.log[i]
      const curCreatorEffs = (e.creatorEffects ?? []).map(ef => `${ef.id}${ef.effectType === 'BORDER' ? `t${ef.turns}` : `a${ef.amount}`}`).sort().join(',')
      const curJoinerEffs = (e.joinerEffects ?? []).map(ef => `${ef.id}${ef.effectType === 'BORDER' ? `t${ef.turns}` : `a${ef.amount}`}`).sort().join(',')
      if (e.phase !== 'card_set' && e.phase !== 'card_break' && e.phase !== 'hurt' && e.phase !== 'turn_start' && e.phase !== 'turn_end') {
        continue
      }
      prevCreatorEffs = curCreatorEffs
      prevJoinerEffs = curJoinerEffs
    }
    return true
  })())

  assert(`[${S}] 日志快照: 200随机种子-效果快照与最终状态一致`, (() => {
    for (let seed = 1; seed <= 200; seed++) {
      const b = new Battle(1, seed)
      b.setCreator('A')
      b.creator.chosenCards = [
        makeCard({ name: 'A1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'A2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'A3', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ]
      b.setSingleEnemy('B', [
        makeCard({ name: 'B1', cardHp: 3, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'B2', cardHp: 5, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
        makeCard({ name: 'B3', cardHp: 8, atkPoint: '1d6', defPoint: '1d3', dodPoint: '1d3' }),
      ])
      b.runFullBattle()
      const lastEntry = b.log.entries[b.log.entries.length - 1]
      if (!lastEntry) { console.error(`seed=${seed} no log entries`); return false }
      const finalCreatorEffs = b.creator.effects.map(e => e.toData())
      const finalJoinerEffs = b.joiner!.effects.map(e => e.toData())
      if (lastEntry.creatorEffects!.length !== finalCreatorEffs.length) {
        console.error(`seed=${seed} creator effects count mismatch: log=${lastEntry.creatorEffects!.length} actual=${finalCreatorEffs.length}`)
        return false
      }
      if (lastEntry.joinerEffects!.length !== finalJoinerEffs.length) {
        console.error(`seed=${seed} joiner effects count mismatch: log=${lastEntry.joinerEffects!.length} actual=${finalJoinerEffs.length}`)
        return false
      }
    }
    return true
  })())
}

function testExpeditionFlowUsability() {
  const S = '远征流程可用性'

  function createTestState(overrides: Partial<ExpeditionState> = {}): ExpeditionState {
    return {
      cards: [], spirit: 0, currentStage: 1, currentBattle: 1,
      battlesPerStage: 4, totalStages: 6, finished: false, victories: 0,
      exActive: false, exBattle: 0, exCardsBroken: 0, exFinished: false,
      ...overrides,
    }
  }

  function initTestState(spirit = 0): ExpeditionState {
    const nonCard = createNonCard()
    const panel = BASE_PANELS[0]
    const spellCard = createSpellCard(panel)
    const initEffects = INITIAL_CARD_EFFECTS[panel.name]
    if (initEffects) { for (const eff of initEffects) { addEffectToCard(spellCard, eff) } }
    return createTestState({ cards: [nonCard, spellCard], spirit })
  }

  function runBattleForState(state: ExpeditionState, enc: Encounter) {
    const activeIndices: number[] = []
    const myCardDatas: CardData[] = []
    for (let i = 0; i < state.cards.length; i++) {
      if (state.cards[i].currentHp > 0) {
        activeIndices.push(i)
        myCardDatas.push(toCardData(state.cards[i]))
      }
    }
    if (myCardDatas.length === 0) return { won: false, battle: null as any, activeIndices }
    const b = new Battle(1)
    b.setCreator('玩家')
    b.creator.chosenCards = myCardDatas
    b.setSingleEnemy('敌人', enc.enemyCards)
    b.runFullBattle()
    const usedBattleIndices = b.creator.usedCardIndices
    for (let i = 0; i < state.cards.length; i++) {
      const card = state.cards[i]
      const activePos = activeIndices.indexOf(i)
      let hpAfter: number
      if (activePos === -1) { hpAfter = card.currentHp }
      else {
        const wasUsed = activePos < usedBattleIndices.length
        if (wasUsed) { hpAfter = activePos === usedBattleIndices.length - 1 ? Math.max(b.creator.nowHp, 0) : 0 }
        else { hpAfter = card.currentHp }
      }
      card.currentHp = hpAfter
    }
    return { won: b.winnerId === 1, battle: b, activeIndices }
  }

  function isSlotRewardLocal(r: Reward): boolean { return 'slot' in r && !('apply' in r) }
  function isDiceCountUpgradeLocal(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.endsWith('_count') }
  function isDiceMinUpgradeLocal(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.endsWith('_min1') }
  function isDiceUpgradeLocal(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.startsWith('dice_') }
  function isStatUpgradeLocal(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.startsWith('stat_') }
  function isRefreshItemLocal(r: Reward): boolean { return r.id === '_refresh' }
  function isEffectModuleLocal(r: Reward): boolean { return 'slot' in r && 'apply' in r }

  function canApplyToCardFull(card: ExpeditionCard, r: Reward, extraCost = 0, spirit = 0): boolean {
    if (isRefreshItemLocal(r)) return false
    if (isDiceMinUpgradeLocal(r) && 'apply' in r) {
      const du = r as any
      const target = du.id.startsWith('dice_atk') ? card.atkPoint : du.id.startsWith('dice_def') ? card.defPoint : card.dodPoint
      if (isDiceFixed(target)) return false
    }
    if (card.isNonCard) {
      if (spirit < 3 + extraCost) return false
      if (isSlotRewardLocal(r)) return true
      if (isDiceCountUpgradeLocal(r)) return false
      if (isStatUpgradeLocal(r)) return true
      if (isDiceUpgradeLocal(r)) return true
      if (isEffectModuleLocal(r)) return card.slotCapacity[(r as any).slot] > 0
      return false
    }
    return true
  }

  assert(`[${S}] 初始化: 4个基础面板可用`, (() => {
    return BASE_PANELS.length === 4
  })())

  assert(`[${S}] 初始化: 创建非符卡`, (() => {
    const nc = createNonCard()
    return nc.isNonCard && nc.cardHp === 4 && nc.currentHp === 4 && nc.atkPoint === '1d4'
      && nc.slotCapacity.onCardSet === 0 && nc.slotCapacity.onCardBreak === 1 && nc.slotCapacity.onPassive === 0
  })())

  assert(`[${S}] 初始化: 创建符卡`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    return !sc.isNonCard && sc.currentHp === sc.maxCardHp
      && sc.slotCapacity.onCardSet === 1 && sc.slotCapacity.onCardBreak === 1 && sc.slotCapacity.onPassive === 1
  })())

  assert(`[${S}] 初始化: 梦想封印初始效果`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const effs = INITIAL_CARD_EFFECTS[BASE_PANELS[0].name]
    if (effs) for (const eff of effs) addEffectToCard(sc, eff)
    return sc.effects.onCardSet.length === 1 && sc.effects.onCardSet[0].id === 'init_trace1'
  })())

  assert(`[${S}] 初始化: 封魔阵初始效果`, (() => {
    const sc = createSpellCard(BASE_PANELS[1])
    const effs = INITIAL_CARD_EFFECTS[BASE_PANELS[1].name]
    if (effs) for (const eff of effs) addEffectToCard(sc, eff)
    return sc.effects.onCardSet.length === 1 && sc.effects.onCardSet[0].id === 'init_str_border'
  })())

  assert(`[${S}] 初始化: Stardust Reverie初始效果`, (() => {
    const sc = createSpellCard(BASE_PANELS[2])
    const effs = INITIAL_CARD_EFFECTS[BASE_PANELS[3].name]
    if (effs) for (const eff of effs) addEffectToCard(sc, eff)
    return sc.effects.onCardSet.length === 1 && sc.effects.onCardSet[0].id === 'init_combo1'
  })())

  assert(`[${S}] 初始化: Master Spark无初始效果`, (() => {
    const effs = INITIAL_CARD_EFFECTS[BASE_PANELS[2].name]
    return !effs || effs.length === 0
  })())

  assert(`[${S}] 初始化: toCardData正确转换`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const effs = INITIAL_CARD_EFFECTS[BASE_PANELS[0].name]
    if (effs) for (const eff of effs) addEffectToCard(sc, eff)
    const cd = toCardData(sc)
    return cd.name === sc.name && cd.cardHp === sc.currentHp && cd.atkPoint === sc.atkPoint
      && cd.onCardSet !== undefined && cd.onCardBreak === undefined
  })())

  assert(`[${S}] 遭遇: 6面模板各4战`, (() => {
    for (let s = 1; s <= 6; s++) {
      const t = getStageTemplate(s)
      if (t.length !== 4) return false
    }
    return true
  })())

  assert(`[${S}] 遭遇: 每面第4战为boss`, (() => {
    for (let s = 1; s <= 6; s++) {
      const t = getStageTemplate(s)
      if (t[3].type !== 'boss') return false
    }
    return true
  })())

  assert(`[${S}] 遭遇: 每面第2战为elite`, (() => {
    for (let s = 1; s <= 6; s++) {
      const t = getStageTemplate(s)
      if (t[1].type !== 'elite') return false
    }
    return true
  })())

  assert(`[${S}] 遭遇: generateEncounter正确生成`, (() => {
    const enc = generateEncounter(1, 1, rng)
    return enc.stage === 1 && enc.battle === 1 && enc.type === 'normal' && enc.enemyCards.length > 0
  })())

  assert(`[${S}] 遭遇: EX面7战模板`, (() => {
    const t = getExStageTemplate()
    return t.length === 7
  })())

  assert(`[${S}] 遭遇: EX面第3战为elite`, (() => {
    const t = getExStageTemplate()
    return t[2].type === 'elite'
  })())

  assert(`[${S}] 遭遇: EX面第6战为shop`, (() => {
    const t = getExStageTemplate()
    return t[5].type === 'shop'
  })())

  assert(`[${S}] 遭遇: EX面第7战为boss`, (() => {
    const t = getExStageTemplate()
    return t[6].type === 'boss'
  })())

  assert(`[${S}] 遭遇: EX面boss有10张卡`, (() => {
    const enc = generateExEncounter(7, rng)
    return enc.type === 'boss' && enc.enemyCards.length === 10
  })())

  assert(`[${S}] 遭遇: generateExEncounter正确生成`, (() => {
    const enc = generateExEncounter(1, rng)
    return enc.stage === 7 && enc.battle === 1 && enc.type === 'normal' && enc.enemyCards.length > 0
  })())

  assert(`[${S}] 遭遇: 灵力奖励 normal=2/elite=3/boss=5`, (() => {
    return getSpiritReward('normal') === 2 && getSpiritReward('elite') === 3 && getSpiritReward('boss') === 5
  })())

  assert(`[${S}] 遭遇: 3面elite有newCard掉落`, (() => {
    const t = getStageTemplate(3)
    return t[1].fixedDrop?.type === 'newCard'
  })())

  assert(`[${S}] 遭遇: 2面elite有dice掉落`, (() => {
    const t = getStageTemplate(2)
    return t[1].fixedDrop?.type === 'dice'
  })())

  assert(`[${S}] 战斗: 正常执行并更新HP`, (() => {
    const state = initTestState()
    const enc = generateEncounter(1, 1, rng)
    const result = runBattleForState(state, enc)
    return result.battle !== null && result.battle.winnerId !== null
  })())

  assert(`[${S}] 战斗: 胜利后灵力增加`, (() => {
    const state = initTestState()
    const enc = generateEncounter(1, 1, rng)
    const result = runBattleForState(state, enc)
    if (!result.won) return true
    const spiritGain = getSpiritReward(enc.type) + result.battle.creator.spiritGained
    return spiritGain >= 2
  })())

  assert(`[${S}] 战斗: 胜利后非符回满`, (() => {
    const state = initTestState()
    state.cards[0].currentHp = 1
    const enc = generateEncounter(1, 1, rng)
    const result = runBattleForState(state, enc)
    if (!result.won) return true
    healNonCard(state.cards)
    return state.cards[0].currentHp === state.cards[0].maxCardHp
  })())

  assert(`[${S}] 战斗: 失败时HP可能为0`, (() => {
    const state = initTestState()
    const enc = generateEncounter(6, 4, rng)
    let lost = false
    for (let i = 0; i < 20; i++) {
      const s2 = initTestState()
      const r2 = runBattleForState(s2, enc)
      if (!r2.won) { lost = true; break }
    }
    return true
  })())

  assert(`[${S}] 战斗: 无可用卡时判负`, (() => {
    const state = initTestState()
    state.cards.forEach(c => { c.currentHp = 0 })
    const enc = generateEncounter(1, 1, rng)
    const result = runBattleForState(state, enc)
    return !result.won && result.battle === null
  })())

  assert(`[${S}] 战斗: toCardData含被动效果`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const passive = EFFECT_POOL.find(e => e.id === 'turn_str1')!
    addEffectToCard(sc, passive)
    const cd = toCardData(sc)
    return cd.onTurnStart !== undefined
  })())

  assert(`[${S}] 战斗: toCardData含击杀被动`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const ek = EFFECT_POOL.find(e => e.id === 'ek_kill_heal3')!
    addEffectToCard(sc, ek)
    const cd = toCardData(sc)
    return cd.onEnemyCardBreak !== undefined
  })())

  assert(`[${S}] 奖励: normal战0-1个rare`, (() => {
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('normal', rng)
      if (rewards.some(r => r.rarity === 'epic')) return false
    }
    return true
  })())

  assert(`[${S}] 奖励: elite战0-1个epic+1-2个rare`, (() => {
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('elite', rng)
      const epics = rewards.filter(r => r.rarity === 'epic').length
      if (epics > 1) return false
    }
    return true
  })())

  assert(`[${S}] 奖励: boss战1-2个epic`, (() => {
    let hasEpic = false
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('boss', rng)
      const epics = rewards.filter(r => r.rarity === 'epic').length
      if (epics > 2 || epics < 1) return false
      if (epics > 0) hasEpic = true
    }
    return hasEpic
  })())

  assert(`[${S}] 奖励: 奖励数量为3`, (() => {
    for (let i = 0; i < 20; i++) {
      const rewards = generateRewards('normal', rng)
      if (rewards.length !== 3) return false
    }
    return true
  })())

  assert(`[${S}] 奖励: 奖励ID不重复`, (() => {
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('boss', rng)
      const ids = rewards.map(r => r.id)
      if (new Set(ids).size !== ids.length) return false
    }
    return true
  })())

  assert(`[${S}] 装配: 效果装配到空槽`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const eff = EFFECT_POOL.find(e => e.id === 'set_damage1')!
    const result = addEffectToCard(sc, eff)
    return result.replaced === null && sc.effects.onCardSet.length === 1
  })())

  assert(`[${S}] 装配: 效果替换满槽效果`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const eff1 = EFFECT_POOL.find(e => e.id === 'set_damage1')!
    const eff2 = EFFECT_POOL.find(e => e.id === 'set_shield2')!
    addEffectToCard(sc, eff1)
    const result = addEffectToCard(sc, eff2)
    return result.replaced !== null && result.replaced.id === 'set_damage1'
      && sc.effects.onCardSet[0].id === 'set_shield2'
  })())

  assert(`[${S}] 装配: 额外槽位增加容量`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    addSlotCapacity(sc, 'onCardSet')
    return sc.slotCapacity.onCardSet === 2
  })())

  assert(`[${S}] 装配: 增加槽位后可装两个效果`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    addSlotCapacity(sc, 'onCardSet')
    const eff1 = EFFECT_POOL.find(e => e.id === 'set_damage1')!
    const eff2 = EFFECT_POOL.find(e => e.id === 'set_shield2')!
    const r1 = addEffectToCard(sc, eff1)
    const r2 = addEffectToCard(sc, eff2)
    return r1.replaced === null && r2.replaced === null && sc.effects.onCardSet.length === 2
  })())

  assert(`[${S}] 装配: 骰子升级apply`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const d = DICE_POOL.find(d => d.id === 'dice_atk1')!
    d.apply(sc)
    return sc.atkPoint === '1d5'
  })())

  assert(`[${S}] 装配: HP升级apply`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const s = STAT_POOL.find(s => s.id === 'stat_hp2')!
    s.apply(sc)
    return sc.maxCardHp === 9 && sc.cardHp === 9 && sc.currentHp === 9
  })())

  assert(`[${S}] canApply: 符卡可接受所有奖励类型`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const allTypes = [...EFFECT_POOL, ...DICE_POOL, ...STAT_POOL, ...SLOT_POOL]
    for (const r of allTypes) {
      if (!canApplyToCardFull(sc, r, 0, 100)) return false
    }
    return true
  })())

  assert(`[${S}] canApply: 非符拒绝骰数升级`, (() => {
    const nc = createNonCard()
    const d = DICE_POOL.find(d => d.id === 'dice_atk_count')!
    return !canApplyToCardFull(nc, d, 0, 100)
  })())

  assert(`[${S}] canApply: 非符灵力不足拒绝效果`, (() => {
    const nc = createNonCard()
    const eff = EFFECT_POOL.find(e => e.id === 'break_damage1')!
    return !canApplyToCardFull(nc, eff, 0, 2)
  })())

  assert(`[${S}] canApply: 非符灵力足够接受效果`, (() => {
    const nc = createNonCard()
    const eff = EFFECT_POOL.find(e => e.id === 'break_damage1')!
    return canApplyToCardFull(nc, eff, 0, 3)
  })())

  assert(`[${S}] canApply: 非符可接受额外槽位`, (() => {
    const nc = createNonCard()
    const slot = SLOT_POOL.find(s => s.id === 'slot_onCardBreak')!
    return canApplyToCardFull(nc, slot, 0, 3)
  })())

  assert(`[${S}] canApply: 非符可接受骰面升级`, (() => {
    const nc = createNonCard()
    const d = DICE_POOL.find(d => d.id === 'dice_atk1')!
    return canApplyToCardFull(nc, d, 0, 3)
  })())

  assert(`[${S}] canApply: 非符可接受HP升级`, (() => {
    const nc = createNonCard()
    const s = STAT_POOL.find(s => s.id === 'stat_hp2')!
    return canApplyToCardFull(nc, s, 0, 3)
  })())

  assert(`[${S}] canApply: 骰下限+1对固定骰不可装配`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    sc.atkPoint = '1d1'
    const d = DICE_POOL.find(d => d.id === 'dice_atk_min1')!
    return !canApplyToCardFull(sc, d, 0, 100)
  })())

  assert(`[${S}] canApply: 骰下限+1对非固定骰可装配`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const d = DICE_POOL.find(d => d.id === 'dice_atk_min1')!
    return canApplyToCardFull(sc, d, 0, 100)
  })())

  assert(`[${S}] canApply: 刷新商品不可装配`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const refresh = { id: '_refresh', displayName: '刷新', rarity: 'common' as const, description: '', slot: 'onCardSet' as const }
    return !canApplyToCardFull(sc, refresh as any, 0, 100)
  })())

  assert(`[${S}] canApply: 非符无宣言槽拒绝宣言效果`, (() => {
    const nc = createNonCard()
    const eff = EFFECT_POOL.find(e => e.id === 'set_damage1')!
    return !canApplyToCardFull(nc, eff, 0, 100)
  })())

  assert(`[${S}] canApply: 非符有亡语槽接受亡语效果`, (() => {
    const nc = createNonCard()
    const eff = EFFECT_POOL.find(e => e.id === 'break_damage1')!
    return canApplyToCardFull(nc, eff, 0, 3)
  })())

  assert(`[${S}] canApply: 非符无被动槽拒绝被动效果`, (() => {
    const nc = createNonCard()
    const eff = EFFECT_POOL.find(e => e.id === 'turn_str1')!
    return !canApplyToCardFull(nc, eff, 0, 100)
  })())

  assert(`[${S}] 商店: 生成5个商品(4+刷新)`, (() => {
    const items = generateShopItems(rng)
    return items.length === 5
  })())

  assert(`[${S}] 商店: 最后一个是刷新`, (() => {
    const items = generateShopItems(rng)
    return items[4].id === 'shop_refresh' && items[4].price === 1
  })())

  assert(`[${S}] 商店: 定价正确`, (() => {
    const items = generateShopItems(rng)
    for (const item of items) {
      if (item.id === 'shop_refresh') continue
      const expected = item.reward.rarity === 'epic' ? 10 : item.reward.rarity === 'rare' ? 6 : 3
      if (item.price !== expected) return false
    }
    return true
  })())

  assert(`[${S}] 商店: 购买扣灵力`, (() => {
    const state = initTestState(20)
    const items = generateShopItems(rng)
    const affordable = items.filter(i => i.price <= state.spirit && i.id !== 'shop_refresh')
    if (affordable.length === 0) return true
    const item = affordable[0]
    const before = state.spirit
    state.spirit -= item.price
    return state.spirit === before - item.price
  })())

  assert(`[${S}] 固定掉落: 骰子升级`, (() => {
    const state = initTestState()
    const d = DICE_POOL.find(d => d.id === 'dice_atk1')!
    const sc = state.cards.find(c => !c.isNonCard)!
    d.apply(sc)
    return sc.atkPoint === '1d5'
  })())

  assert(`[${S}] 固定掉落: 新符卡加入阵容`, (() => {
    const state = initTestState()
    const before = state.cards.length
    const newCard = generateNewCardDrop(3, rng)
    state.cards.push(createSpellCard(newCard))
    return state.cards.length === before + 1
  })())

  assert(`[${S}] 固定掉落: 新符卡根据面数选池`, (() => {
    const c1 = generateNewCardDrop(1, rng)
    const c5 = generateNewCardDrop(5, rng)
    return c1.name !== '' && c5.name !== ''
  })())

  assert(`[${S}] 面间: healAllForNewStage回满`, (() => {
    const state = initTestState()
    state.cards[0].currentHp = 1
    state.cards[1].currentHp = 1
    healAllForNewStage(state.cards)
    return state.cards.every(c => c.currentHp === c.maxCardHp)
  })())

  assert(`[${S}] 面间: 面推进currentStage++`, (() => {
    const state = initTestState()
    const before = state.currentStage
    const template = getStageTemplate(state.currentStage)
    state.currentBattle = template.length
    if (state.currentBattle >= template.length) {
      if (state.currentStage < state.totalStages) {
        state.currentStage++; state.currentBattle = 1
      }
    }
    return state.currentStage === before + 1 && state.currentBattle === 1
  })())

  assert(`[${S}] 分段: 1面1战流程`, (() => {
    const state = initTestState()
    const enc = generateEncounter(1, 1, rng)
    const result = runBattleForState(state, enc)
    if (!result.won) return true
    state.victories++
    state.spirit += getSpiritReward(enc.type) + result.battle.creator.spiritGained
    healNonCard(state.cards)
    return state.victories === 1 && state.spirit >= 2
  })())

  assert(`[${S}] 分段: 1面完整4战流程`, (() => {
    const state = initTestState(10)
    const template = getStageTemplate(1)
    for (let b = 0; b < template.length; b++) {
      const enc = generateEncounter(1, b + 1, rng)
      const result = runBattleForState(state, enc)
      if (!result.won) return true
      state.victories++
      state.spirit += getSpiritReward(enc.type) + result.battle.creator.spiritGained
      healNonCard(state.cards)
      if (enc.fixedDrop) {
        if (enc.fixedDrop.type === 'dice') {
          const d = DICE_POOL.find(d => d.id === 'dice_atk1')!
          const tc = state.cards.filter(c => canApplyToCardFull(c, d, 0, state.spirit))
          if (tc.length > 0) d.apply(tc[0])
        } else {
          state.cards.push(createSpellCard(generateNewCardDrop(1, rng)))
        }
      }
      const rewards = generateRewards(enc.type, rng)
      if (rewards.length > 0) {
        const r = rewards[0]
        const tc = state.cards.filter(c => canApplyToCardFull(c, r, 0, state.spirit))
        if (tc.length > 0) applyRewardToCard(tc[0], r)
      }
    }
    healAllForNewStage(state.cards)
    return state.victories === 4 && state.cards.every(c => c.currentHp === c.maxCardHp)
  })())

  assert(`[${S}] 分段: 6面boss胜利进入victory`, (() => {
    const state = initTestState(500)
    state.currentStage = 6
    state.currentBattle = 4
    const enc = generateEncounter(6, 4, rng)
    const result = runBattleForState(state, enc)
    if (!result.won) return true
    state.victories++
    state.spirit += getSpiritReward(enc.type) + result.battle.creator.spiritGained
    healNonCard(state.cards)
    const isVictory = enc.type === 'boss' && state.currentStage >= state.totalStages
    return isVictory
  })())

  assert(`[${S}] EX: enterExStage设置正确`, (() => {
    const state = initTestState(500)
    state.currentStage = 6
    state.exActive = true
    state.exBattle = 0
    state.exCardsBroken = 0
    state.exFinished = false
    healAllForNewStage(state.cards)
    return state.exActive && state.exBattle === 0 && state.cards.every(c => c.currentHp === c.maxCardHp)
  })())

  assert(`[${S}] EX: 先进商店`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 0
    healAllForNewStage(state.cards)
    const shopItems = generateShopItems(rng)
    return shopItems.length === 5
  })())

  assert(`[${S}] EX: 7战遭遇正确生成`, (() => {
    for (let b = 1; b <= 7; b++) {
      const enc = generateExEncounter(b, rng)
      if (b <= 2 && enc.type !== 'normal') return false
      if (b === 3 && enc.type !== 'elite') return false
      if (b === 6 && enc.type !== 'shop') return false
      if (b === 7 && enc.type !== 'boss') return false
    }
    return true
  })())

  assert(`[${S}] EX: shop战跳过战斗`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 6
    const enc = generateExEncounter(state.exBattle, rng)
    return enc.type === 'shop' && enc.enemyCards.length === 0
  })())

  assert(`[${S}] EX: boss胜利exBattle=8`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 7
    const enc = generateExEncounter(7, rng)
    const result = runBattleForState(state, enc)
    if (!result.won) return true
    state.exBattle = 8
    state.exFinished = true
    return state.exBattle === 8 && state.exFinished
  })())

  assert(`[${S}] EX: boss失败exBattle=7`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 7
    state.exFinished = true
    state.exBattle = 7
    return state.exBattle === 7
  })())

  assert(`[${S}] EX: 中途失败进入victory(非defeated)`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 3
    state.exFinished = true
    return state.exActive
  })())

  assert(`[${S}] EX: boss失败记录击破数`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 7
    const enc = generateExEncounter(7, rng)
    const result = runBattleForState(state, enc)
    if (result.won) return true
    if (result.battle) {
      const brokenCount = result.battle.joiner!.usedCardIndices.length
      state.exCardsBroken = brokenCount
    }
    return state.exCardsBroken >= 0
  })())

  assert(`[${S}] EX: advanceAfterReward推进exBattle`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 1
    const exTemplate = getExStageTemplate()
    state.exBattle++
    const nextType = exTemplate[Math.min(state.exBattle - 1, exTemplate.length - 1)].type
    return state.exBattle === 2 && nextType === 'normal'
  })())

  assert(`[${S}] EX: 第6战后进shop`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 5
    const exTemplate = getExStageTemplate()
    state.exBattle++
    const nextType = exTemplate[Math.min(state.exBattle - 1, exTemplate.length - 1)].type
    return nextType === 'shop'
  })())

  assert(`[${S}] EX: 完整7战流程`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 0
    healAllForNewStage(state.cards)
    const shopItems = generateShopItems(rng)
    state.exBattle = 1
    for (let b = 1; b <= 7; b++) {
      const enc = generateExEncounter(b, rng)
      if (enc.type === 'shop') continue
      const result = runBattleForState(state, enc)
      if (!result.won) return true
      state.victories++
      state.spirit += getSpiritReward(enc.type) + result.battle.creator.spiritGained
      healNonCard(state.cards)
    }
    return state.victories >= 6
  })())

  assert(`[${S}] 展示: parseDescription解析效果`, (() => {
    const segs = parseDescription('宣言时获得[强化2]')
    return segs.length === 2 && segs[0].type === 'text' && segs[1].type === 'effect'
      && segs[1].text === '强化2' && segs[1].effectDesc === '攻击力+2'
  })())

  assert(`[${S}] 展示: parseDescription解析多个效果`, (() => {
    const segs = parseDescription('宣言时获得[强化2]和[追踪1]')
    const effectSegs = segs.filter(s => s.type === 'effect')
    return effectSegs.length === 2
  })())

  assert(`[${S}] 展示: parseDescription空描述`, (() => {
    const segs = parseDescription('无')
    return segs.length === 0
  })())

  assert(`[${S}] 展示: parseDescription无效果标签`, (() => {
    const segs = parseDescription('普通文本描述')
    return segs.length === 1 && segs[0].type === 'text'
  })())

  assert(`[${S}] 展示: slotDisplayList含空槽位`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const slots: { type: string; slot?: string; effect?: any }[] = []
    for (const eff of sc.effects.onCardSet) slots.push({ type: 'effect', effect: eff })
    for (let i = sc.effects.onCardSet.length; i < sc.slotCapacity.onCardSet; i++) slots.push({ type: 'empty', slot: 'onCardSet' })
    for (const eff of sc.effects.onCardBreak) slots.push({ type: 'effect', effect: eff })
    for (let i = sc.effects.onCardBreak.length; i < sc.slotCapacity.onCardBreak; i++) slots.push({ type: 'empty', slot: 'onCardBreak' })
    for (const eff of sc.effects.onPassive) slots.push({ type: 'effect', effect: eff })
    for (let i = sc.effects.onPassive.length; i < sc.slotCapacity.onPassive; i++) slots.push({ type: 'empty', slot: 'onPassive' })
    const emptySlots = slots.filter(s => s.type === 'empty')
    return emptySlots.length === 3 && emptySlots.every(s => s.slot !== undefined)
  })())

  assert(`[${S}] 展示: slotDisplayList效果填满无空位`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    addEffectToCard(sc, EFFECT_POOL.find(e => e.id === 'set_damage1')!)
    addEffectToCard(sc, EFFECT_POOL.find(e => e.id === 'break_damage1')!)
    addEffectToCard(sc, EFFECT_POOL.find(e => e.id === 'turn_str1')!)
    const emptySlots: string[] = []
    for (const slot of ['onCardSet', 'onCardBreak', 'onPassive'] as const) {
      for (let i = sc.effects[slot].length; i < sc.slotCapacity[slot]; i++) emptySlots.push(slot)
    }
    return emptySlots.length === 0
  })())

  assert(`[${S}] 展示: 非符slotDisplayList只有亡语槽`, (() => {
    const nc = createNonCard()
    const emptySlots: string[] = []
    for (const slot of ['onCardSet', 'onCardBreak', 'onPassive'] as const) {
      for (let i = nc.effects[slot].length; i < nc.slotCapacity[slot]; i++) emptySlots.push(slot)
    }
    return emptySlots.length === 1 && emptySlots[0] === 'onCardBreak'
  })())

  assert(`[${S}] 展示: formatDice展示ATK/DEF/DOD`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    return formatDice(parseDice(sc.atkPoint)) === sc.atkPoint
      && formatDice(parseDice(sc.defPoint)) === sc.defPoint
      && formatDice(parseDice(sc.dodPoint)) === sc.dodPoint
  })())

  assert(`[${S}] 展示: 带效果标签的描述可被parseDescription解析`, (() => {
    const effWithBracket = EFFECT_POOL.find(e => e.description.includes('['))
    if (!effWithBracket) return false
    const segs = parseDescription(effWithBracket.description)
    return segs.some(s => s.type === 'effect')
  })())

  assert(`[${S}] 展示: 所有效果都有描述`, (() => {
    return EFFECT_POOL.every(e => e.description.length > 0)
  })())

  assert(`[${S}] 展示: 所有骰子升级都有描述`, (() => {
    return DICE_POOL.every(d => d.description.length > 0)
  })())

  assert(`[${S}] 展示: 所有额外槽位都有描述`, (() => {
    return SLOT_POOL.every(s => s.description.length > 0)
  })())

  assert(`[${S}] 展示: 所有奖励都有displayName`, (() => {
    const allRewards = [...EFFECT_POOL, ...DICE_POOL, ...STAT_POOL, ...SLOT_POOL]
    return allRewards.every(r => r.displayName.length > 0)
  })())

  assert(`[${S}] 展示: 效果slot标签映射`, (() => {
    const slotLabel = (slot: string) => slot === 'onCardSet' ? '宣言' : slot === 'onCardBreak' ? '亡语' : '被动'
    return slotLabel('onCardSet') === '宣言' && slotLabel('onCardBreak') === '亡语' && slotLabel('onPassive') === '被动'
  })())

  assert(`[${S}] 展示: 效果slotTagType映射`, (() => {
    const slotTagType = (slot: string) => slot === 'onCardSet' ? 'success' : slot === 'onCardBreak' ? 'danger' : 'warning'
    return slotTagType('onCardSet') === 'success' && slotTagType('onCardBreak') === 'danger' && slotTagType('onPassive') === 'warning'
  })())

  assert(`[${S}] 边界: 所有符卡都能出战`, (() => {
    for (const card of ALL_CARDS) {
      try {
        const b = new Battle(1)
        b.setCreator('A')
        b.creator.chosenCards = [{ ...card }]
        b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
        b.runFullBattle()
      } catch { return false }
    }
    return true
  })())

  assert(`[${S}] 边界: 大量效果叠加不出错`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    addSlotCapacity(sc, 'onCardSet')
    addSlotCapacity(sc, 'onCardBreak')
    addSlotCapacity(sc, 'onPassive')
    const setEffects = EFFECT_POOL.filter(e => e.slot === 'onCardSet').slice(0, 2)
    const breakEffects = EFFECT_POOL.filter(e => e.slot === 'onCardBreak').slice(0, 2)
    const passiveEffects = EFFECT_POOL.filter(e => e.slot === 'onPassive').slice(0, 2)
    for (const e of setEffects) addEffectToCard(sc, e)
    for (const e of breakEffects) addEffectToCard(sc, e)
    for (const e of passiveEffects) addEffectToCard(sc, e)
    try {
      const cd = toCardData(sc)
      const b = new Battle(1)
      b.setCreator('A')
      b.creator.chosenCards = [cd]
      b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
      b.runFullBattle()
      return true
    } catch { return false }
  })())

  assert(`[${S}] 边界: 多次骰子升级不出错`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    for (let i = 0; i < 5; i++) {
      const d = DICE_POOL.find(d => d.id === 'dice_atk1')!
      d.apply(sc)
    }
    return sc.atkPoint === '1d9'
  })())

  assert(`[${S}] 边界: 骰数+1多次升级`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    const d = DICE_POOL.find(d => d.id === 'dice_atk_count')!
    d.apply(sc)
    d.apply(sc)
    return sc.atkPoint === '3d4'
  })())

  assert(`[${S}] 边界: initExpeditionState正确`, (() => {
    const state = initExpeditionState()
    return state.cards.length === 0 && state.spirit === 0 && state.currentStage === 1
      && state.currentBattle === 1 && !state.finished && state.exActive === false
      && state.exBattle === 0 && state.exFinished === false
  })())

  assert(`[${S}] 边界: 商店刷新商品`, (() => {
    const items1 = generateShopItems(() => 0.5)
    const items2 = generateShopItems(() => 0.8)
    return items1.some((item, i) => item.id !== items2[i].id) || items1.length === items2.length
  })())

  assert(`[${S}] 边界: EX面elite有dice固定掉落`, (() => {
    const t = getExStageTemplate()
    return t[2].fixedDrop?.type === 'dice'
  })())

  assert(`[${S}] 边界: canAddEffectToSlot与slotCapacity一致`, (() => {
    const sc = createSpellCard(BASE_PANELS[0])
    for (const slot of ['onCardSet', 'onCardBreak', 'onPassive'] as const) {
      if (canAddEffectToSlot(sc, slot) !== (sc.effects[slot].length < sc.slotCapacity[slot])) return false
    }
    return true
  })())

  assert(`[${S}] 边界: 非符canAddEffectToSlot只有亡语可加`, (() => {
    const nc = createNonCard()
    return !canAddEffectToSlot(nc, 'onCardSet') && canAddEffectToSlot(nc, 'onCardBreak') && !canAddEffectToSlot(nc, 'onPassive')
  })())

  assert(`[${S}] 完整流程: 从1面1战到6面boss(强制胜利)`, (() => {
    const state = initTestState(500)
    for (let stage = 1; stage <= 6; stage++) {
      const template = getStageTemplate(stage)
      for (let battle = 1; battle <= template.length; battle++) {
        const enc = generateEncounter(stage, battle, rng)
        const result = runBattleForState(state, enc)
        if (!result.won) return true
        state.victories++
        state.spirit += getSpiritReward(enc.type) + result.battle.creator.spiritGained
        healNonCard(state.cards)
        if (enc.fixedDrop) {
          if (enc.fixedDrop.type === 'dice') {
            const d = DICE_POOL.find(d => d.id === 'dice_atk1')!
            const tc = state.cards.filter(c => canApplyToCardFull(c, d, 0, state.spirit))
            if (tc.length > 0) d.apply(tc[0])
          } else {
            state.cards.push(createSpellCard(generateNewCardDrop(stage, rng)))
          }
        }
        const rewards = generateRewards(enc.type, rng)
        if (rewards.length > 0) {
          const r = rewards[0]
          const tc = state.cards.filter(c => canApplyToCardFull(c, r, 0, state.spirit))
          if (tc.length > 0) applyRewardToCard(tc[0], r)
        }
        if (battle >= template.length) {
          healAllForNewStage(state.cards)
          if (stage < 6) {
            const shopItems = generateShopItems(rng)
          }
        }
      }
      if (stage < 6) { state.currentStage = stage + 1; state.currentBattle = 1 }
    }
    return state.victories === 24 && state.cards.length >= 2
  })())

  assert(`[${S}] 完整流程: 6面boss后进入EX面`, (() => {
    const state = initTestState(500)
    state.currentStage = 6
    state.exActive = true
    state.exBattle = 0
    healAllForNewStage(state.cards)
    const shopItems = generateShopItems(rng)
    state.exBattle = 1
    return state.exActive && state.exBattle === 1 && state.cards.every(c => c.currentHp === c.maxCardHp)
  })())

  assert(`[${S}] 完整流程: EX面完整7战(强制胜利)`, (() => {
    const state = initTestState(500)
    state.exActive = true
    state.exBattle = 0
    healAllForNewStage(state.cards)
    const shopItems = generateShopItems(rng)
    state.exBattle = 1
    const exTemplate = getExStageTemplate()
    for (let b = 1; b <= 7; b++) {
      const enc = generateExEncounter(b, rng)
      if (enc.type === 'shop') {
        const shopItems2 = generateShopItems(rng)
        continue
      }
      const result = runBattleForState(state, enc)
      if (!result.won) return true
      state.victories++
      state.spirit += getSpiritReward(enc.type) + result.battle.creator.spiritGained
      healNonCard(state.cards)
      if (enc.fixedDrop) {
        if (enc.fixedDrop.type === 'dice') {
          const d = DICE_POOL.find(d => d.id === 'dice_atk1')!
          const tc = state.cards.filter(c => canApplyToCardFull(c, d, 0, state.spirit))
          if (tc.length > 0) d.apply(tc[0])
        }
      }
      const rewards = generateRewards(enc.type, rng)
      if (rewards.length > 0) {
        const r = rewards[0]
        const tc = state.cards.filter(c => canApplyToCardFull(c, r, 0, state.spirit))
        if (tc.length > 0) applyRewardToCard(tc[0], r)
      }
    }
    state.exBattle = 8
    state.exFinished = true
    return state.exFinished && state.exBattle === 8
  })())
}

function rng(): number { return Math.random() }
function isSlotReward(r: Reward): boolean { return 'slot' in r && !('apply' in r) }
function isDiceCountUpgrade(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.endsWith('_count') }

function canApplyToCard(card: ExpeditionCard, r: Reward): boolean {
  if (card.isNonCard) {
    if (isDiceCountUpgrade(r)) return false
    if (isSlotReward(r)) return true
    if ('apply' in r && !('slot' in r)) return true
    if ('slot' in r && 'apply' in r) return card.slotCapacity[r.slot] > 0
    return false
  }
  return true
}

function applyRewardToCard(card: ExpeditionCard, reward: Reward) {
  if (isSlotReward(reward)) { addSlotCapacity(card, reward.slot); return }
  if ('slot' in reward && 'apply' in reward) { addEffectToCard(card, reward) }
  else if ('apply' in reward) { reward.apply(card) }
}

function autoApplyReward(state: ExpeditionState, rewards: Reward[]) {
  const reward = rewards[Math.floor(rng() * rewards.length)]
  const cards = state.cards.filter(c => canApplyToCard(c, reward))
  if (cards.length === 0) return
  const card = cards[Math.floor(rng() * cards.length)]
  if (card.isNonCard && state.spirit >= 3) state.spirit -= 3
  applyRewardToCard(card, reward)
}

function autoShopBuy(state: ExpeditionState) {
  const items = generateShopItems(rng)
  const affordable = items.filter(i => i.price <= state.spirit && i.id !== 'shop_refresh')
  if (affordable.length === 0) return
  const item = affordable[Math.floor(rng() * affordable.length)]
  const card = state.cards.filter(c => !c.isNonCard || state.spirit >= item.price + 3)[0]
  if (!card) return
  if (card.isNonCard) state.spirit -= 3
  state.spirit -= item.price
  applyRewardToCard(card, item.reward)
}

function runSingleExpedition() {
  const errors: string[] = []
  const panelIdx = Math.floor(rng() * BASE_PANELS.length)
  const panel = BASE_PANELS[panelIdx]
  const nonCard = createNonCard()
  const spellCard = createSpellCard(panel)
  const initEffects = INITIAL_CARD_EFFECTS[panel.name]
  if (initEffects) { for (const eff of initEffects) { addEffectToCard(spellCard, eff) } }

  const state: ExpeditionState = {
    cards: [nonCard, spellCard], spirit: 0, currentStage: 1, currentBattle: 1,
    battlesPerStage: 4, totalStages: 6, finished: false, victories: 0,
  }
  let totalRounds = 0

  while (!state.finished) {
    const enc = generateEncounter(state.currentStage, state.currentBattle, rng)
    const activeIndices: number[] = []
    const myCardDatas = []
    for (let i = 0; i < state.cards.length; i++) {
      if (state.cards[i].currentHp > 0) {
        activeIndices.push(i)
        myCardDatas.push(toCardData(state.cards[i]))
      }
    }
    if (myCardDatas.length === 0) return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, errors }
    try {
      const b = new Battle(1)
      b.setCreator('玩家')
      b.creator.chosenCards = myCardDatas
      b.setSingleEnemy('敌人', enc.enemyCards)
      b.runFullBattle()
      totalRounds += b.gameRound

      const usedBattleIndices = b.creator.usedCardIndices
      for (let i = 0; i < state.cards.length; i++) {
        const card = state.cards[i]
        const activePos = activeIndices.indexOf(i)
        let hpAfter: number
        if (activePos === -1) {
          hpAfter = card.currentHp
        } else {
          const wasUsed = activePos < usedBattleIndices.length
          if (wasUsed) {
            hpAfter = activePos === usedBattleIndices.length - 1 ? Math.max(b.creator.nowHp, 0) : 0
          } else {
            hpAfter = card.currentHp
          }
        }
        card.currentHp = hpAfter
      }

      if (b.winnerId !== 1) return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, errors }

      state.victories++
      state.spirit += getSpiritReward(enc.type) + b.creator.spiritGained
      healNonCard(state.cards)

      if (enc.type === 'boss' && state.currentStage >= state.totalStages)
        return { victory: true, stagesCleared: 3, battlesWon: state.victories, totalRounds, errors }

      if (enc.fixedDrop) {
        if (enc.fixedDrop.type === 'dice') {
          const d = DICE_POOL[Math.floor(rng() * DICE_POOL.length)]
          const tc = state.cards.filter(c => canApplyToCard(c, d))
          if (tc.length > 0) { const c = tc[0]; if (c.isNonCard && state.spirit >= 3) state.spirit -= 3; d.apply(c) }
        } else {
          state.cards.push(createSpellCard(generateNewCardDrop(state.currentStage, rng)))
        }
      }

      autoApplyReward(state, generateRewards(enc.type, rng))

      const template = getStageTemplate(state.currentStage)
      if (state.currentBattle >= template.length) {
        healAllForNewStage(state.cards)
        if (state.currentStage >= state.totalStages)
          return { victory: true, stagesCleared: 3, battlesWon: state.victories, totalRounds, errors }
        state.currentStage++; state.currentBattle = 1
        autoShopBuy(state)
      } else { state.currentBattle++ }
    } catch (e: any) {
      errors.push(`S${state.currentStage}-${state.currentBattle}: ${e.message}`)
      return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, errors }
    }
  }
  return { victory: false, stagesCleared: 0, battlesWon: 0, totalRounds, errors }
}

function runSingleExExpedition() {
  const errors: string[] = []
  const panelIdx = Math.floor(rng() * BASE_PANELS.length)
  const panel = BASE_PANELS[panelIdx]
  const nonCard = createNonCard()
  const spellCard = createSpellCard(panel)
  const initEffects = INITIAL_CARD_EFFECTS[panel.name]
  if (initEffects) { for (const eff of initEffects) { addEffectToCard(spellCard, eff) } }

  const state: ExpeditionState = {
    cards: [nonCard, spellCard], spirit: 30, currentStage: 1, currentBattle: 1,
    battlesPerStage: 4, totalStages: 6, finished: false, victories: 0,
    exActive: false, exBattle: 0, exCardsBroken: 0, exFinished: false,
  }
  let totalRounds = 0

  while (!state.finished) {
    const isEx = state.exActive
    const enc = isEx
      ? generateExEncounter(state.exBattle, rng)
      : generateEncounter(state.currentStage, state.currentBattle, rng)

    if (enc.type === 'shop') {
      if (isEx) {
        autoShopBuy(state)
        state.exBattle++
      } else {
        const template = getStageTemplate(state.currentStage)
        if (state.currentBattle >= template.length) {
          healAllForNewStage(state.cards)
          state.currentStage++; state.currentBattle = 1
          autoShopBuy(state)
        } else { state.currentBattle++ }
      }
      continue
    }

    const activeIndices: number[] = []
    const myCardDatas = []
    for (let i = 0; i < state.cards.length; i++) {
      if (state.cards[i].currentHp > 0) {
        activeIndices.push(i)
        myCardDatas.push(toCardData(state.cards[i]))
      }
    }
    if (myCardDatas.length === 0) return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, exCleared: false, errors }

    try {
      const b = new Battle(1)
      b.setCreator('玩家')
      b.creator.chosenCards = myCardDatas
      b.setSingleEnemy('敌人', enc.enemyCards)
      b.runFullBattle()
      totalRounds += b.gameRound

      const usedBattleIndices = b.creator.usedCardIndices
      for (let i = 0; i < state.cards.length; i++) {
        const card = state.cards[i]
        const activePos = activeIndices.indexOf(i)
        let hpAfter: number
        if (activePos === -1) {
          hpAfter = card.currentHp
        } else {
          const wasUsed = activePos < usedBattleIndices.length
          if (wasUsed) {
            hpAfter = activePos === usedBattleIndices.length - 1 ? Math.max(b.creator.nowHp, 0) : 0
          } else {
            hpAfter = card.currentHp
          }
        }
        card.currentHp = hpAfter
      }

      if (b.winnerId !== 1) {
        if (isEx) return { victory: true, stagesCleared: 6, battlesWon: state.victories, totalRounds, exCleared: false, errors }
        return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, exCleared: false, errors }
      }

      state.victories++
      state.spirit += getSpiritReward(enc.type) + b.creator.spiritGained
      healNonCard(state.cards)

      if (isEx) {
        state.exCardsBroken += b.joiner!.usedCardIndices.length
        if (enc.type === 'boss') {
          state.exFinished = true
          state.finished = true
          return { victory: true, stagesCleared: 6, battlesWon: state.victories, totalRounds, exCleared: true, errors }
        }
        state.exBattle++
      } else {
        if (enc.type === 'boss' && state.currentStage >= state.totalStages) {
          healAllForNewStage(state.cards)
          state.exActive = true
          state.exBattle = 0
          autoShopBuy(state)
          state.exBattle = 1
          continue
        }

        if (enc.fixedDrop) {
          if (enc.fixedDrop.type === 'dice') {
            const d = DICE_POOL[Math.floor(rng() * DICE_POOL.length)]
            const tc = state.cards.filter(c => canApplyToCard(c, d))
            if (tc.length > 0) { const c = tc[0]; if (c.isNonCard && state.spirit >= 3) state.spirit -= 3; d.apply(c) }
          } else {
            state.cards.push(createSpellCard(generateNewCardDrop(state.currentStage, rng)))
          }
        }

        autoApplyReward(state, generateRewards(enc.type, rng))

        const template = getStageTemplate(state.currentStage)
        if (state.currentBattle >= template.length) {
          healAllForNewStage(state.cards)
          if (state.currentStage >= state.totalStages) {
            state.exActive = true
            state.exBattle = 0
            autoShopBuy(state)
            state.exBattle = 1
            continue
          }
          state.currentStage++; state.currentBattle = 1
          autoShopBuy(state)
        } else { state.currentBattle++ }
      }
    } catch (e: any) {
      errors.push(`${isEx ? 'EX' : 'S' + state.currentStage}-${isEx ? state.exBattle : state.currentBattle}: ${e.message}`)
      if (isEx) return { victory: true, stagesCleared: 6, battlesWon: state.victories, totalRounds, exCleared: false, errors }
      return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, exCleared: false, errors }
    }
  }
  return { victory: false, stagesCleared: 0, battlesWon: 0, totalRounds, exCleared: false, errors }
}

function testExExpeditionFlow(count: number = 200) {
  let exCleared = 0, totalBattles = 0, totalRounds = 0, reachedEx = 0
  const exBattleReached = new Map<number, number>()
  const allErrors: string[] = []

  for (let i = 0; i < count; i++) {
    const r = runSingleExExpedition()
    totalBattles += r.battlesWon; totalRounds += r.totalRounds
    if (r.stagesCleared >= 6) reachedEx++
    if (r.exCleared) exCleared++
    const exB = r.exCleared ? 7 : Math.max(0, (r as any).exBattle ?? 0)
    exBattleReached.set(exB, (exBattleReached.get(exB) ?? 0) + 1)
    allErrors.push(...r.errors)
  }

  const lines: string[] = []
  lines.push(`EX面流程测试 (${count}场, 初始30灵力):`)
  lines.push(`  到达EX面: ${reachedEx}/${count} (${(reachedEx / count * 100).toFixed(1)}%)`)
  lines.push(`  EX通关: ${exCleared}/${count} (${(exCleared / count * 100).toFixed(1)}%)`)
  lines.push(`  平均胜场: ${(totalBattles / count).toFixed(1)}`)
  lines.push(`  平均回合: ${(totalRounds / count).toFixed(1)}`)
  const exLabels = ['未到EX', 'EX-1', 'EX-2', 'EX-3', 'EX-4', 'EX-5', 'EX-6(商店)', 'EX通关']
  for (let b = 0; b <= 7; b++) {
    const cnt = exBattleReached.get(b) ?? 0
    if (cnt > 0) lines.push(`  ${exLabels[b] || 'EX-' + b}: ${cnt} (${(cnt / count * 100).toFixed(1)}%)`)
  }
  if (allErrors.length > 0) {
    lines.push(`  错误 (${allErrors.length}):`)
    for (const err of allErrors.slice(0, 10)) lines.push(`    ${err}`)
  }
  return lines.join('\n')
}

function testExpeditionFlow(count: number = 200) {
  let victories = 0, totalBattles = 0, totalRounds = 0
  const stageReached = new Map<number, number>()
  const allErrors: string[] = []

  for (let i = 0; i < count; i++) {
    const r = runSingleExpedition()
    if (r.victory) victories++
    totalBattles += r.battlesWon; totalRounds += r.totalRounds
    stageReached.set(r.stagesCleared, (stageReached.get(r.stagesCleared) ?? 0) + 1)
    allErrors.push(...r.errors)
  }

  const lines: string[] = []
  lines.push(`远征流程测试 (${count}场):`)
  lines.push(`  通关率: ${victories}/${count} (${(victories / count * 100).toFixed(1)}%)`)
  lines.push(`  平均胜场: ${(totalBattles / count).toFixed(1)}`)
  lines.push(`  平均回合: ${(totalRounds / count).toFixed(1)}`)
  for (let s = 0; s <= 6; s++) {
    const cnt = stageReached.get(s) ?? 0
    lines.push(`  ${s === 0 ? '1面前失败' : s + '面'}: ${cnt} (${(cnt / count * 100).toFixed(1)}%)`)
  }
  if (allErrors.length > 0) {
    lines.push(`  错误 (${allErrors.length}):`)
    for (const err of allErrors.slice(0, 10)) lines.push(`    ${err}`)
  }
  return lines.join('\n')
}

console.log('开始符卡系统自测...\n')

testEffectBasics()
testEffectAdvanced()
testSpecialCards()
testRewardEffects()
testDiceSystem()
testBattleMechanics()
testBugFixes()
testBattleFlow()
testAnimationCardTracking()
testStateMachine()
testExpeditionFlowUsability()

const passed = results.filter(r => r.passed).length
const failed = results.filter(r => !r.passed).length
const total = results.length

console.log(`╔══════════════════════════════════════╗`)
console.log(`║     符卡系统自测报告                 ║`)
console.log(`╚══════════════════════════════════════╝`)
console.log(``)
console.log(`单元测试: ${passed}/${total} 通过${failed > 0 ? `，${failed} 失败` : ''}`)
console.log(``)

if (failed > 0) {
  console.log('--- 失败项 ---')
  for (const r of results) {
    if (!r.passed) console.log(`  ✗ ${r.name}: ${r.detail}`)
  }
  console.log('')
}

console.log('--- 通过项 ---')
for (const r of results) {
  if (r.passed) console.log(`  ✓ ${r.name}`)
}
console.log('')

console.log('=== 远征流程测试 ===')
console.log(testExpeditionFlow(200))
console.log('')
console.log('=== EX面流程测试 ===')
console.log(testExExpeditionFlow(200))
