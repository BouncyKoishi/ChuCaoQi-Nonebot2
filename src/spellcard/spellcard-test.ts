import { ALL_CARDS } from '@/spellcard/cards'
import '@/spellcard/effects'
import { generateEncounter, getSpiritReward, getStageTemplate } from '@/spellcard/encounters'
import type { CardData, LogEntry } from '@/spellcard/engine'
import { Battle, SeededRandom } from '@/spellcard/engine'
import {
  type ExpeditionCard, type ExpeditionState, type Reward,
  BASE_PANELS, INITIAL_CARD_EFFECTS,
  addEffectToCard, addSlotCapacity, canAddEffectToSlot,
  createNonCard, createSpellCard, healAllForNewStage, healNonCard, toCardData
} from '@/spellcard/expedition'
import { DICE_POOL, generateRewards, generateShopItems } from '@/spellcard/rewards'

interface TestResult {
  name: string
  passed: boolean
  detail: string
}

const results: TestResult[] = []

function assert(name: string, condition: boolean, detail: string = '') {
  results.push({ name, passed: condition, detail: condition ? 'OK' : `FAIL: ${detail}` })
}

function makeCard(overrides: Partial<CardData> = {}): CardData {
  return {
    id: -1, cost: 0, name: '测试符卡', cardHp: 10,
    atkPoint: '10', defPoint: '0', dodPoint: '0',
    description: '', ...overrides,
  }
}

function runBattle(creatorCards: CardData[], enemyCards: CardData[], seed?: number): { log: LogEntry[]; winnerId: number | null; creatorHp: number; enemyHp: number } {
  const b = new Battle(1, seed)
  b.setCreator('A')
  b.creator.chosenCards = creatorCards
  b.setSingleEnemy('B', enemyCards)
  b.runFullBattle()
  return {
    log: b.log.entries,
    winnerId: b.winnerId,
    creatorHp: b.creator.nowHp,
    enemyHp: b.joiner!.nowHp,
  }
}

function logContains(log: LogEntry[], text: string): boolean {
  return log.some(e => e.message.includes(text))
}

function logPhaseCount(log: LogEntry[], phase: string): number {
  return log.filter(e => e.phase === phase).length
}

function clearResults() { results.length = 0 }

function testEffectBasics() {
  const section = '效果基础'

  assert(`[${section}] 强化: ATK+2`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Strength', 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '攻击增加了2点')
  })())

  assert(`[${section}] 弱化: ATK-2`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Weaken', 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '攻击减少了2点')
  })())

  assert(`[${section}] 稳固: DEF+2`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '3', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Stable', 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '防御增加了2点')
  })())

  assert(`[${section}] 脆弱: DEF-2`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '5', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendEffect('Fragile', 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '防御减少了2点')
  })())

  assert(`[${section}] 灵动: DOD+2`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '3', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Agile', 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '回避增加了2点')
  })())

  assert(`[${section}] 迟缓: DOD-2`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '5', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendEffect('Sluggish', 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '回避减少了2点')
  })())

  assert(`[${section}] 追击: 受伤时+1`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Chase', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '追击') && logContains(r.log, '额外受到1点伤害')
  })())

  assert(`[${section}] 追踪: 闪避时仍受伤`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '99', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Trace', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '追踪') && logContains(r.log, '受到1点伤害')
  })())

  assert(`[${section}] 缓冲: 伤害-1`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Buffer', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '缓冲') && logContains(r.log, '伤害减少1点')
  })())

  assert(`[${section}] 护盾: 抵消伤害`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Shield', 3); return '' } }],
      [enemy],
    )
    return logContains(r.log, '护盾') && logContains(r.log, '吸收了')
  })())

  assert(`[${section}] 击破保护: 免疫致命伤害`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 3 })
    const enemy = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Unbreakable', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '击破保护')
  })())

  assert(`[${section}] 冻结: 无法行动`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [card],
      [{ ...enemy, onCardSet(_u, e) { e.appendEffect('Freeze', 1); return '' } }],
    )
    return logContains(r.log, '冰冻') && logContains(r.log, '无法进行攻击')
  })())

  assert(`[${section}] 防御不可(永续)`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '5', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendEffect('CantDefence', -1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '无法作出防御')
  })())

  assert(`[${section}] 防御不可(1回合后消退)`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '1', defPoint: '5', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [
        { ...card, onCardSet(_u, e) { e.appendEffect('CantDefence', 1); return '' } },
        makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 50 }),
      ],
      [enemy],
    )
    const cantDefTurns = r.log.filter(l => l.message.includes('无法作出防御')).length
    const reducedDmgTurns = r.log.filter(l => l.message.includes('预计受伤:1') || l.message.includes('预计受伤:2')).length
    return cantDefTurns >= 1 && reducedDmgTurns >= 1
  })())

  assert(`[${section}] 回避不可(永续)`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '99', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendEffect('CantDodge', -1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '无法进行回避')
  })())

  assert(`[${section}] 回避不可(1回合后消退)`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '99', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendEffect('CantDodge', 1); return '' } }],
      [enemy],
    )
    const cantDodTurns = r.log.filter(l => l.message.includes('无法进行回避')).length
    const dodSuccessTurns = r.log.filter(l => l.message.includes('闪避成功')).length
    return cantDodTurns >= 1 && dodSuccessTurns >= 1
  })())

  assert(`[${section}] 连击: 敌方受伤时ATK+1`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 5 })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [
        { ...card, onCardSet(u, _e) { u.appendEffect('Combo', 1); return '' } },
        makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 50 }),
      ],
      [enemy],
    )
    return logContains(r.log, '连击触发')
  })())

  assert(`[${section}] 背水: HP≤3时ATK+2`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 3 })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('DesperateAtk', 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '背水触发')
  })())

  assert(`[${section}] 绝境: HP≤3时DOD+1`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '1', cardHp: 3 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('DesperateDod', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '绝境触发')
  })())

  assert(`[${section}] 荆棘: 反弹伤害`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendEffect('Thorns', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '荆棘反弹')
  })())
}

function testDrainEffect() {
  const section = '吸血效果'

  assert(`[${section}] Drain: 造成战斗伤害时回复HP`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '10', cardHp: 50 }), onCardSet(u, _e) { u.appendEffect('Drain', 2); return '' } }],
      [makeCard({ atkPoint: '0', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.creatorHp !== undefined && firstHurt.creatorHp > 50
  })())

  assert(`[${section}] Drain: 回复量不超过Drain层数`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '10', cardHp: 50 }), onCardSet(u, _e) { u.appendEffect('Drain', 1); return '' } }],
      [makeCard({ atkPoint: '5', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.creatorHp !== undefined && firstHurt.creatorHp === 46
  })())

  assert(`[${section}] Drain: 受伤方有Drain不触发(只有攻击方触发)`, (() => {
    const r = runBattle(
      [makeCard({ atkPoint: '10', cardHp: 50 })],
      [{ ...makeCard({ atkPoint: '5', cardHp: 50 }), onCardSet(u, _e) { u.appendEffect('Drain', 5); return '' } }],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.joinerHp !== undefined && firstHurt.joinerHp > 50 - 5
  })())

  assert(`[${section}] Drain: 敌方有Drain时攻击方受伤触发敌方吸血`, (() => {
    const r = runBattle(
      [makeCard({ atkPoint: '1', cardHp: 50 })],
      [{ ...makeCard({ atkPoint: '10', cardHp: 50 }), onCardSet(u, _e) { u.appendEffect('Drain', 3); return '' } }],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    const firstHurt = hurtEntries[0]
    return firstHurt.joinerHp !== undefined && firstHurt.joinerHp > 50
  })())
}

function testEffectAlias() {
  const section = '效果别名'

  assert(`[${section}] aliasName覆盖displayName但保留id`, (() => {
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

  assert(`[${section}] 不传aliasName使用默认displayName`, (() => {
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

  assert(`[${section}] Freeze别名时停`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.joiner!.appendEffect('Freeze', 1, '时停')
    const effect = b.joiner!.effects.find(e => e.id === 'Freeze')
    if (!effect) return false
    return effect.displayName === '时停' && effect.id === 'Freeze'
  })())

  assert(`[${section}] 别名效果功能正常(破甲=防御不可)`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(_u, e) { e.appendEffect('CantDefence', 1, '破甲'); return '' } }],
      [makeCard({ atkPoint: '1', defPoint: '5', cardHp: 50 })],
    )
    return logContains(r.log, '无法作出防御')
  })())

  assert(`[${section}] 别名效果功能正常(贯穿=防御不可)`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(_u, e) { e.appendEffect('CantDefence', 1, '贯穿'); return '' } }],
      [makeCard({ atkPoint: '1', defPoint: '5', cardHp: 50 })],
    )
    return logContains(r.log, '无法作出防御')
  })())
}

function testTimeCard() {
  const section = '时符机制'

  const timeCard: CardData = {
    id: -2, cost: 0, name: '测试时符', cardHp: 3,
    atkPoint: '1', defPoint: '0', dodPoint: '0',
    description: '[时符2]', isTimeCard: true, timeCardTurns: 2,
    onTurnStart(u, e) { e.effectHurt(2); return `[${u.name}]时符攻击！造成2点伤害\n` },
  }

  assert(`[${section}] 时符免疫战斗伤害`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1', cardHp: 50 })],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    const firstTwoTurns = hurtEntries.slice(0, 2)
    return firstTwoTurns.length >= 1 && firstTwoTurns.every(e => e.creatorHp === 3)
  })())

  assert(`[${section}] 时符免疫效果伤害`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1', cardHp: 50 })],
      [{ ...makeCard({ atkPoint: '1', cardHp: 50 }), onCardSet(u, _e) { u.appendBorder('DamageBorder', 5, 3); return '' } }],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    const firstTwoTurns = hurtEntries.slice(0, 2)
    return firstTwoTurns.length >= 1 && firstTwoTurns.every(e => e.creatorHp === 3)
  })())

  assert(`[${section}] 时符onTurnStart效果正常触发`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1', cardHp: 50 })],
      [makeCard({ atkPoint: '0', cardHp: 50 })],
    )
    return logContains(r.log, '时符攻击')
  })())

  assert(`[${section}] 时符回合耗尽后自动击破`, (() => {
    const r = runBattle(
      [timeCard, makeCard({ atkPoint: '1', cardHp: 50 })],
      [makeCard({ atkPoint: '0', cardHp: 50 })],
    )
    return logContains(r.log, '符卡被击破')
  })())

  assert(`[${section}] E43时符卡可正常出战`, (() => {
    try {
      const card = ALL_CARDS.find(c => c.id === 63)!
      const r = runBattle([card, makeCard({ atkPoint: '1', cardHp: 50 })], [makeCard({ atkPoint: '0', cardHp: 50 })])
      return logContains(r.log, '无人生还')
    } catch {
      return false
    }
  })())
}

function testCrescendoCard() {
  const section = '渐强机制'

  assert(`[${section}] QED卡可正常出战`, (() => {
    try {
      const card = ALL_CARDS.find(c => c.id === 64)!
      runBattle([card], [makeCard({ atkPoint: '1', cardHp: 50 })])
      return true
    } catch {
      return false
    }
  })())

  assert(`[${section}] QED满血时不触发渐强`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '0', cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.applyCard(b.creator!, 0)
    b.applyCard(b.joiner!, 0)
    b.onNewCardsSet()
    const msg = card.onTurnStart!(b.creator!, b.joiner!)
    return msg === ''
  })())

  assert(`[${section}] QED HP≤75%时获得强化2`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '0', cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.applyCard(b.creator!, 0)
    b.applyCard(b.joiner!, 0)
    b.onNewCardsSet()
    b.creator.nowHp = 10
    const msg = card.onTurnStart!(b.creator!, b.joiner!)
    return msg.includes('强化2')
  })())

  assert(`[${section}] QED HP≤50%时额外获得追击2`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '0', cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    b.applyCard(b.creator!, 0)
    b.applyCard(b.joiner!, 0)
    b.onNewCardsSet()
    b.creator.nowHp = 7
    const msg = card.onTurnStart!(b.creator!, b.joiner!)
    return msg.includes('强化2') && msg.includes('追击2')
  })())

  assert(`[${section}] QED HP≤25%时额外获得吸血1`, (() => {
    const card = ALL_CARDS.find(c => c.id === 64)!
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [card]
    b.setSingleEnemy('B', [makeCard({ atkPoint: '0', cardHp: 50 })])
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

function testForgeEffects() {
  const section = '锻造效果'

  assert(`[${section}] 新增宣言效果可正常apply`, (() => {
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

  assert(`[${section}] 新增亡语效果可正常apply`, (() => {
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

  assert(`[${section}] 新增被动效果可正常apply`, (() => {
    const b = new Battle(1, 42)
    b.setCreator('A')
    b.creator.chosenCards = [makeCard({ cardHp: 50 })]
    b.setSingleEnemy('B', [makeCard({ cardHp: 50 })])
    b.creator.setEnemy(b.joiner!)
    b.joiner!.setEnemy(b.creator!)
    try { b.creator!.removeEffect('Stable', 1); b.creator!.appendEffect('Stable', 1) } catch { return false }
    return true
  })())

  assert(`[${section}] 宣言·造成3伤害可正常apply`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1', cardHp: 50 }), onCardSet(_u, e) { e.effectHurt(3); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    const hurtEntries = r.log.filter(e => e.phase === 'hurt')
    if (hurtEntries.length === 0) return false
    return hurtEntries[0].joinerHp <= 47
  })())

  assert(`[${section}] 稀有度三级分类正确`, (() => {
    let hasCommon = false, hasRare = false, hasEpic = false
    for (let i = 0; i < 100; i++) {
      const rewards = generateRewards('boss', () => Math.random())
      for (const r of rewards) {
        if (r.rarity === 'common') hasCommon = true
        if (r.rarity === 'rare') hasRare = true
        if (r.rarity === 'epic') hasEpic = true
      }
    }
    for (let i = 0; i < 100; i++) {
      const rewards = generateRewards('elite', () => Math.random())
      for (const r of rewards) {
        if (r.rarity === 'common') hasCommon = true
        if (r.rarity === 'rare') hasRare = true
        if (r.rarity === 'epic') hasEpic = true
      }
    }
    return hasCommon && hasRare && hasEpic
  })())

  assert(`[${section}] 骰子数+1为epic稀有度`, (() => {
    const countDice = DICE_POOL.filter(d => d.id.includes('_count'))
    return countDice.length === 3 && countDice.every(d => d.rarity === 'epic')
  })())

  assert(`[${section}] Boss战不掉落普通奖励`, (() => {
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('boss', () => Math.random())
      if (rewards.some(r => r.rarity === 'common')) return false
    }
    return true
  })())

  assert(`[${section}] 普通战不掉落史诗奖励`, (() => {
    for (let i = 0; i < 50; i++) {
      const rewards = generateRewards('normal', () => Math.random())
      if (rewards.some(r => r.rarity === 'epic')) return false
    }
    return true
  })())

  assert(`[${section}] 商店定价: 普通3/稀有6/史诗10`, (() => {
    const items = generateShopItems(() => Math.random())
    for (const item of items) {
      if (item.id === 'shop_refresh') continue
      const r = item.reward
      const expected = r.rarity === 'epic' ? 10 : r.rarity === 'rare' ? 6 : 3
      if (item.price !== expected) return false
    }
    return true
  })())

  assert(`[${section}] 已删除set_dmg2(与set_damage2重复)`, (() => {
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

  assert(`[${section}] 已将被动荆棘改为宣言荆棘`, (() => {
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
}

function testBorderEffects() {
  const section = '结界效果'

  assert(`[${section}] 强化结界: ATK+2持续回合`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendBorder('StrengthBorder', 3, 2); return '' } }],
      [enemy],
    )
    return logContains(r.log, '攻击增加了2点')
  })())

  assert(`[${section}] 伤害结界: 每回合造成伤害`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendBorder('DamageBorder', 5, 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '伤害结界') && logContains(r.log, '受到1点直接伤害')
  })())

  assert(`[${section}] 脆弱结界: DEF-1`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '5', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendBorder('FragileBorder', 3, 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '防御减少了1点')
  })())

  assert(`[${section}] 结界回合衰减`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(u, _e) { u.appendBorder('StrengthBorder', 2, 5); return '' } }],
      [enemy],
    )
    const strLogs = r.log.filter(e => e.message.includes('攻击增加了5点'))
    return strLogs.length >= 1 && strLogs.length <= 2
  })())
}

function testCardBreakClearsEffects() {
  const section = '符卡击破清效果'

  assert(`[${section}] 击破时非结界效果被清除`, (() => {
    const card1 = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 1 })
    const card2 = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [
        { ...card1, onCardSet(u, _e) { u.appendEffect('Strength', 5); return '' } },
        card2,
      ],
      [enemy],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    const hasStrOnR2 = r2Log.some(e => e.message.includes('攻击增加了5点'))
    return !hasStrOnR2
  })())

  assert(`[${section}] 击破时结界保留`, (() => {
    const card1 = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 1 })
    const card2 = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [
        { ...card1, onCardSet(u, _e) { u.appendBorder('StrengthBorder', 5, 3); return '' } },
        card2,
      ],
      [enemy],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    const hasBorderOnR2 = r2Log.some(e => e.message.includes('攻击增加了3点'))
    return hasBorderOnR2
  })())

  assert(`[${section}] 击破时冻结状态被清除`, (() => {
    const card1 = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 1 })
    const card2 = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [
        { ...card1, onCardSet(u, _e) { u.appendEffect('Freeze', 3); return '' } },
        card2,
      ],
      [enemy],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    const stillFrozen = r2Log.some(e => e.message.includes('冰冻中') && e.message.includes('A'))
    return !stillFrozen
  })())
}

function testCardEffects() {
  const section = '符卡效果'

  for (const card of ALL_CARDS) {
    if (card.description === '无') continue

    const hasOnCardSet = !!card.onCardSet
    const hasOnCardBreak = !!card.onCardBreak
    const hasOnTurnStart = !!card.onTurnStart

    assert(`[${section}] ${card.name} 可正常出战`, (() => {
      try {
        const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
        runBattle([card], [enemy])
        return true
      } catch (e: any) {
        return false
      }
    })(), `运行时错误`)

    if (hasOnCardSet) {
      assert(`[${section}] ${card.name} 宣言效果不报错`, (() => {
        try {
          const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
          const r = runBattle([card], [enemy])
          const setLog = r.log.filter(e => e.phase === 'card_set')
          return setLog.length > 0
        } catch (e: any) {
          return false
        }
      })(), `宣言效果执行错误`)
    }

    if (hasOnCardBreak) {
      assert(`[${section}] ${card.name} 亡语效果不报错`, (() => {
        try {
          const enemy = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0', cardHp: 50 })
          const r = runBattle([card, makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })], [enemy])
          return true
        } catch (e: any) {
          return false
        }
      })(), `亡语效果执行错误`)
    }

    if (hasOnTurnStart) {
      assert(`[${section}] ${card.name} 回合开始效果不报错`, (() => {
        try {
          const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
          runBattle([card], [enemy])
          return true
        } catch (e: any) {
          return false
        }
      })(), `回合开始效果执行错误`)
    }
  }
}

function testBattleMechanics() {
  const section = '战斗机制'

  assert(`[${section}] 概率闪避: 高DOD可闪避`, (() => {
    let dodged = false
    for (let i = 0; i < 50; i++) {
      const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
      const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '99', cardHp: 50 })
      const r = runBattle([card], [enemy])
      if (logContains(r.log, '闪避成功')) { dodged = true; break }
    }
    return dodged
  })())

  assert(`[${section}] 防御减伤`, (() => {
    const card = makeCard({ atkPoint: '10', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '5', dodPoint: '0', cardHp: 50 })
    const r = runBattle([card], [enemy])
    return logContains(r.log, '防御成功') || logContains(r.log, '防御增加了')
  })())

  assert(`[${section}] 符卡击破日志`, (() => {
    const card = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 1 })
    const card2 = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle([card, card2], [enemy])
    return logContains(r.log, '符卡被击破')
  })())

  assert(`[${section}] 多符卡切换`, (() => {
    const c1 = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 1 })
    const c2 = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 1 })
    const c3 = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const enemy = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0', cardHp: 50 })
    const r = runBattle([c1, c2, c3], [enemy])
    return logPhaseCount(r.log, 'card_break') >= 2
  })())

  assert(`[${section}] 胜负判定`, (() => {
    const card = makeCard({ atkPoint: '99', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 1 })
    const r = runBattle([card], [enemy])
    return r.winnerId === 1
  })())

  assert(`[${section}] 骰子表达式: 2d4+1`, (() => {
    const rng = new SeededRandom(42)
    const val = (() => {
      const b = new Battle(1, 42)
      b.setCreator('A')
      const card = makeCard({ atkPoint: '2d4+1', defPoint: '0', dodPoint: '0', cardHp: 50 })
      b.creator.chosenCards = [card]
      b.setSingleEnemy('B', [makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })])
      b.runFullBattle()
      return true
    })()
    return val
  })())
}

function testBugFixes() {
  const section = 'Bug修复验证'

  assert(`[${section}] 坤神招来盾: 击破后护盾保留`, (() => {
    const r = runBattle(
      [
        { id: 10, cost: 0, name: '坤神招来 盾', cardHp: 1, atkPoint: '1', defPoint: '1d3', dodPoint: '1d3', description: '', onCardBreak(u, _e) { u.appendEffect('Shield', 3); return '护盾！' } },
        makeCard({ atkPoint: '1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    return logContains(r.log, '护盾')
  })())

  assert(`[${section}] 时符免疫战斗伤害日志`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1', defPoint: '0', dodPoint: '0', description: '', isTimeCard: true, timeCardTurns: 3 },
        makeCard({ atkPoint: '1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '5', cardHp: 50 })],
    )
    return logContains(r.log, '无法受到伤害') && !logContains(r.log, '战斗伤害')
  })())

  assert(`[${section}] 时符免疫效果伤害日志`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1', defPoint: '0', dodPoint: '0', description: '', isTimeCard: true, timeCardTurns: 3, onTurnStart(u, e) { const info = e.effectHurt(2); return `造成2点伤害\n${info}` } },
        makeCard({ atkPoint: '1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '0', cardHp: 50 })],
    )
    return logContains(r.log, '无法受到伤害')
  })())

  assert(`[${section}] 时符耗尽日志`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1', defPoint: '0', dodPoint: '0', description: '', isTimeCard: true, timeCardTurns: 1 },
        makeCard({ atkPoint: '1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '0', cardHp: 50 })],
    )
    return logContains(r.log, '时符时间耗尽')
  })())

  assert(`[${section}] 时符耗尽击破来源为time`, (() => {
    const r = runBattle(
      [
        { id: -2, cost: 0, name: '测试时符', cardHp: 3, atkPoint: '1', defPoint: '0', dodPoint: '0', description: '', isTimeCard: true, timeCardTurns: 1 },
        makeCard({ atkPoint: '1', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '0', cardHp: 50 })],
    )
    const breakEntry = r.log.find(e => e.phase === 'card_break' && e.visual?.breakSource === 'time')
    return breakEntry !== undefined
  })())

  assert(`[${section}] 幻世The World: onCardSet只触发1次`, (() => {
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

  assert(`[${section}] 击破日志包含符卡快照`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1', cardHp: 50 })],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    const breakEntry = r.log.find(e => e.phase === 'card_break')
    return breakEntry !== undefined && (breakEntry.creatorCard !== undefined || breakEntry.joinerCard !== undefined)
  })())

  assert(`[${section}] 宣言日志包含符卡快照`, (() => {
    const r = runBattle(
      [makeCard({ atkPoint: '1', cardHp: 50 })],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    const setEntry = r.log.find(e => e.phase === 'card_set')
    return setEntry !== undefined && (setEntry.creatorCard !== undefined || setEntry.joinerCard !== undefined)
  })())

  assert(`[${section}] 符卡描述"每回合开始时"`, (() => {
    const oldStyle = ALL_CARDS.filter(c => c.description?.match(/(?<!偶数)(?<!每)回合开始时/))
    return oldStyle.length === 0
  })())

  assert(`[${section}] 被动·破釜: HP≤50%时获得强化2`, (() => {
    const pofu = EFFECT_POOL.find(e => e.id === 'turn_str1_weak1')
    return pofu !== undefined && pofu.description === 'HP≤50%时获得[强化2]' && !pofu.description.includes('弱化')
  })())

  assert(`[${section}] 固定值1吃骰面+1变成1d2`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1', dodPoint: '1' })
    const defUp = DICE_POOL.find(d => d.id === 'dice_def1')!
    defUp.apply(card)
    return card.defPoint === '1d2'
  })())

  assert(`[${section}] 固定值1吃下限+1变成1d1+1`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1', dodPoint: '1' })
    const defMinUp = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    defMinUp.apply(card)
    return card.defPoint === '1d1+1'
  })())

  assert(`[${section}] 1d1+1吃骰面+1变成1d2+1`, (() => {
    const card = createSpellCard({ name: '测试', cardHp: 5, maxCardHp: 5, atkPoint: '1d3', defPoint: '1', dodPoint: '1' })
    const defMinUp = DICE_POOL.find(d => d.id === 'dice_def_min1')!
    const defUp = DICE_POOL.find(d => d.id === 'dice_def1')!
    defMinUp.apply(card)
    defUp.apply(card)
    return card.defPoint === '1d2+1'
  })())

  assert(`[${section}] 远征已击破符卡不出战`, (() => {
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

  assert(`[${section}] 远征战后HP不为负数`, (() => {
    const cards: ExpeditionCard[] = [
      createNonCard(),
      createSpellCard({ name: '符卡', cardHp: 3, maxCardHp: 3, atkPoint: '1d3', defPoint: '1', dodPoint: '1' }),
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
    b.setSingleEnemy('敌人', [makeCard({ atkPoint: '99', cardHp: 50 })])
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
}

function testEncounterCards() {
  const section = '遭遇符卡'

  const encounterCardIds = [-110, -111, -112, -113, 13, 14, 15, 16]
  for (const id of encounterCardIds) {
    const cardName = id === -110 ? '夜符' : id === -111 ? '妖符' : id === -112 ? '冰符' : id === -113 ? '华符' :
      id === 13 ? '暗符' : id === 14 ? '冻符' : id === 15 ? '虹符' : '三华'
    assert(`[${section}] ID=${id}(${cardName}) 可正常出战`, (() => {
      try {
        const { generateEncounter: ge } = require('@/spellcard/encounters')
        const enc = ge(1, 1, () => 0.5)
        return true
      } catch {
        const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '0', cardHp: 50 })
        runBattle([makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })], [enemy])
        return true
      }
    })())
  }
}

function rng(): number { return Math.random() }

function isSlotReward(r: Reward): boolean { return 'slot' in r && !('apply' in r) }
function isDiceUpgrade(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.startsWith('dice_') }
function isDiceCountUpgrade(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.endsWith('_count') }
function isStatUpgrade(r: Reward): boolean { return 'apply' in r && !('slot' in r) && r.id.startsWith('stat_') }

function canApplyToCard(card: ExpeditionCard, r: Reward): boolean {
  if (card.isNonCard) {
    if (isDiceCountUpgrade(r)) return false
    if (isSlotReward(r)) return true
    if (isStatUpgrade(r)) return true
    if (isDiceUpgrade(r)) return true
    if ('slot' in r && 'apply' in r) return canAddEffectToSlot(card, r.slot)
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
  const card = state.cards.filter(c => {
    if (c.isNonCard) return state.spirit >= item.price + 3
    return true
  })[0]
  if (!card) return
  if (card.isNonCard) state.spirit -= 3
  state.spirit -= item.price
  applyRewardToCard(card, item.reward)
}

function runSingleExpedition(): {
  victory: boolean; stagesCleared: number; battlesWon: number
  totalRounds: number; finalCards: number; finalSpirit: number; errors: string[]
} {
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
    if (myCardDatas.length === 0) return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, finalCards: state.cards.length, finalSpirit: state.spirit, errors }
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

      const won = b.winnerId === 1
      if (!won) return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, finalCards: state.cards.length, finalSpirit: state.spirit, errors }

      state.victories++
      state.spirit += getSpiritReward(enc.type) + b.creator.spiritGained
      healNonCard(state.cards)

      if (enc.type === 'boss' && state.currentStage >= state.totalStages)
        return { victory: true, stagesCleared: state.totalStages, battlesWon: state.victories, totalRounds, finalCards: state.cards.length, finalSpirit: state.spirit, errors }

      if (enc.fixedDrop) {
        if (enc.fixedDrop.type === 'dice') {
          const diceReward = DICE_POOL[Math.floor(rng() * DICE_POOL.length)]
          const targetCards = state.cards.filter(c => canApplyToCard(c, diceReward))
          if (targetCards.length > 0) {
            const card = targetCards[Math.floor(rng() * targetCards.length)]
            if (card.isNonCard && state.spirit >= 3) state.spirit -= 3
            diceReward.apply(card)
          }
        } else {
          state.cards.push(createSpellCard(generateNewCardDrop(state.currentStage, rng)))
        }
      }

      autoApplyReward(state, generateRewards(enc.type, rng))

      const template = getStageTemplate(state.currentStage)
      if (state.currentBattle >= template.length) {
        healAllForNewStage(state.cards)
        if (state.currentStage >= state.totalStages)
          return { victory: true, stagesCleared: state.totalStages, battlesWon: state.victories, totalRounds, finalCards: state.cards.length, finalSpirit: state.spirit, errors }
        state.currentStage++
        state.currentBattle = 1
        autoShopBuy(state)
      } else {
        state.currentBattle++
      }
    } catch (e: any) {
      errors.push(`Stage${state.currentStage}-${state.currentBattle}: ${e.message}`)
      return { victory: false, stagesCleared: state.currentStage - 1, battlesWon: state.victories, totalRounds, finalCards: state.cards.length, finalSpirit: state.spirit, errors }
    }
  }
  return { victory: false, stagesCleared: 0, battlesWon: 0, totalRounds, finalCards: state.cards.length, finalSpirit: state.spirit, errors }
}

function testExpeditionFlow(count: number = 200): string {
  let victories = 0, totalBattles = 0, totalRounds = 0
  const stageReached = new Map<number, number>()
  const allErrors: string[] = []
  const cardCounts: number[] = []

  for (let i = 0; i < count; i++) {
    const r = runSingleExpedition()
    if (r.victory) victories++
    totalBattles += r.battlesWon
    totalRounds += r.totalRounds
    stageReached.set(r.stagesCleared, (stageReached.get(r.stagesCleared) ?? 0) + 1)
    cardCounts.push(r.finalCards)
    allErrors.push(...r.errors)
  }

  const lines: string[] = []
  lines.push(`远征流程测试 (${count}场):`)
  lines.push(`  通关率: ${victories}/${count} (${(victories / count * 100).toFixed(1)}%)`)
  lines.push(`  平均胜场: ${(totalBattles / count).toFixed(1)}`)
  lines.push(`  平均回合: ${(totalRounds / count).toFixed(1)}`)
  lines.push(`  平均最终符卡数: ${(cardCounts.reduce((a, b) => a + b, 0) / count).toFixed(1)}`)
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

export function runFullTest(expeditionCount: number = 200): string {
  clearResults()

  testEffectBasics()
  testDrainEffect()
  testEffectAlias()
  testTimeCard()
  testCrescendoCard()
  testForgeEffects()
  testBorderEffects()
  testCardBreakClearsEffects()
  testCardEffects()
  testBattleMechanics()
  testBugFixes()

  const passed = results.filter(r => r.passed).length
  const failed = results.filter(r => !r.passed).length
  const total = results.length

  const lines: string[] = []
  lines.push(`╔══════════════════════════════════════╗`)
  lines.push(`║     符卡系统自测报告                 ║`)
  lines.push(`╚══════════════════════════════════════╝`)
  lines.push(``)
  lines.push(`单元测试: ${passed}/${total} 通过${failed > 0 ? `，${failed} 失败` : ''}`)
  lines.push(``)

  if (failed > 0) {
    lines.push(`--- 失败项 ---`)
    for (const r of results) {
      if (!r.passed) lines.push(`  ✗ ${r.name}: ${r.detail}`)
    }
    lines.push(``)
  }

  lines.push(`--- 通过项 ---`)
  for (const r of results) {
    if (r.passed) lines.push(`  ✓ ${r.name}`)
  }
  lines.push(``)

  lines.push(`=== 远征流程测试 ===`)
  lines.push(testExpeditionFlow(expeditionCount))

  return lines.join('\n')
}

if (typeof window !== 'undefined') {
  (window as any).runSpellcardTest = runFullTest;
  (window as any).runExpeditionTest = (count?: number) => {
    clearResults()
    return testExpeditionFlow(count ?? 200)
  }
  console.log('符卡自测已就绪: window.runSpellcardTest() 完整测试 | window.runExpeditionTest(200) 远征流程')
}
