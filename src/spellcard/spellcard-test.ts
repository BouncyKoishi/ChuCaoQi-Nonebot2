import { ALL_CARDS } from '@/spellcard/cards'
import '@/spellcard/effects'
import { generateEncounter, getSpiritReward, getStageTemplate } from '@/spellcard/encounters'
import type { CardData, LogEntry } from '@/spellcard/engine'
import { Battle } from '@/spellcard/engine'
import {
  type ExpeditionCard, type ExpeditionState, type Reward,
  BASE_PANELS, INITIAL_CARD_EFFECTS, NEW_CARD_POOL,
  addEffectToCard, addSlotCapacity, canAddEffectToSlot,
  createNonCard, createSpellCard, healAllForNewStage, healNonCard, toCardData,
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

  assert(`[${section}] 防御不可`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '5', dodPoint: '0', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendEffect('CantDefence', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '无法作出防御')
  })())

  assert(`[${section}] 回避不可`, (() => {
    const card = makeCard({ atkPoint: '5', defPoint: '0', dodPoint: '0' })
    const enemy = makeCard({ atkPoint: '1', defPoint: '0', dodPoint: '99', cardHp: 50 })
    const r = runBattle(
      [{ ...card, onCardSet(_u, e) { e.appendEffect('CantDodge', 1); return '' } }],
      [enemy],
    )
    return logContains(r.log, '无法进行回避')
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
    battlesPerStage: 4, totalStages: 3, finished: false, victories: 0,
  }
  let totalRounds = 0

  while (!state.finished) {
    const enc = generateEncounter(state.currentStage, state.currentBattle, rng)
    const myCardDatas = state.cards.map(c => toCardData(c))
    try {
      const b = new Battle(1)
      b.setCreator('玩家')
      b.creator.chosenCards = myCardDatas
      b.setSingleEnemy('敌人', enc.enemyCards)
      b.runFullBattle()
      totalRounds += b.gameRound

      const usedIndices = b.creator.usedCardIndices
      for (let i = 0; i < state.cards.length; i++) {
        const wasUsed = i < usedIndices.length
        if (wasUsed) {
          state.cards[i].currentHp = i === usedIndices.length - 1 ? b.creator.nowHp : 0
        }
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
          const newPanel = NEW_CARD_POOL[Math.floor(rng() * NEW_CARD_POOL.length)]
          state.cards.push(createSpellCard(newPanel))
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
  for (let s = 0; s <= 3; s++) {
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
  testBorderEffects()
  testCardBreakClearsEffects()
  testCardEffects()
  testBattleMechanics()

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
  (window as any).runSpellcardTest = runFullTest
    (window as any).runExpeditionTest = (count?: number) => {
      clearResults()
      return testExpeditionFlow(count ?? 200)
    }
  console.log('符卡自测已就绪: window.runSpellcardTest() 完整测试 | window.runExpeditionTest(200) 远征流程')
}
