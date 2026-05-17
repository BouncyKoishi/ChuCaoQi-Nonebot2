import { ALL_CARDS } from './cards'
import './effects'
import { generateEncounter, getSpiritReward, getStageTemplate } from './encounters'
import type { CardData, LogEntry } from './engine'
import { Battle } from './engine'
import {
  type ExpeditionCard, type ExpeditionState, type Reward,
  BASE_PANELS, INITIAL_CARD_EFFECTS, NEW_CARD_POOL,
  addEffectToCard, addSlotCapacity, canAddEffectToSlot,
  createNonCard, createSpellCard, healAllForNewStage, healNonCard, toCardData,
} from './expedition'
import { DICE_POOL, generateRewards, generateShopItems } from './rewards'

interface TestResult { name: string; passed: boolean; detail: string }
const results: TestResult[] = []

function assert(name: string, condition: boolean, detail: string = '') {
  results.push({ name, passed: condition, detail: condition ? 'OK' : `FAIL: ${detail}` })
}

function makeCard(overrides: Partial<CardData> = {}): CardData {
  return { id: -1, cost: 0, name: '测试符卡', cardHp: 10, atkPoint: '10', defPoint: '0', dodPoint: '0', description: '', ...overrides }
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
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(u) { u.appendEffect('Strength', 2); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    return logContains(r.log, '攻击增加了2点')
  })())

  assert(`[${S}] 弱化: ATK-2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(u) { u.appendEffect('Weaken', 2); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    return logContains(r.log, '攻击减少了2点')
  })())

  assert(`[${S}] 稳固: DEF+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ defPoint: '3', cardHp: 50 }), onCardSet(u) { u.appendEffect('Stable', 2); return '' } }],
      [makeCard({ atkPoint: '5' })],
    )
    return logContains(r.log, '防御增加了2点')
  })())

  assert(`[${S}] 脆弱: DEF-2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ defPoint: '5', cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('Fragile', 2); return '' } }],
      [makeCard({ atkPoint: '5' })],
    )
    return logContains(r.log, '防御减少了2点')
  })())

  assert(`[${S}] 灵动: DOD+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ dodPoint: '3', cardHp: 50 }), onCardSet(u) { u.appendEffect('Agile', 2); return '' } }],
      [makeCard({ atkPoint: '5' })],
    )
    return logContains(r.log, '回避增加了2点')
  })())

  assert(`[${S}] 迟缓: DOD-2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ dodPoint: '5', cardHp: 50 }), onCardSet(_u, e) { e.appendEffect('Sluggish', 2); return '' } }],
      [makeCard({ atkPoint: '5' })],
    )
    return logContains(r.log, '回避减少了2点')
  })())

  assert(`[${S}] 追击: 受伤时+1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(u) { u.appendEffect('Chase', 1); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    return logContains(r.log, '追击') && logContains(r.log, '额外受到1点伤害')
  })())

  assert(`[${S}] 追踪: 闪避时仍受伤`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1' }), onCardSet(u) { u.appendEffect('Trace', 1); return '' } }],
      [makeCard({ atkPoint: '1', dodPoint: '99', cardHp: 50 })],
    )
    return logContains(r.log, '追踪') && logContains(r.log, '受到1点伤害')
  })())

  assert(`[${S}] 缓冲: 伤害-1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendEffect('Buffer', 1); return '' } }],
      [makeCard({ atkPoint: '5' })],
    )
    return logContains(r.log, '缓冲') && logContains(r.log, '伤害减少1点')
  })())

  assert(`[${S}] 护盾: 抵消伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendEffect('Shield', 3); return '' } }],
      [makeCard({ atkPoint: '5' })],
    )
    return logContains(r.log, '护盾') && logContains(r.log, '吸收了')
  })())

  assert(`[${S}] 击破保护: 免疫致命伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 3 }), onCardSet(u) { u.appendEffect('Unbreakable', 1); return '' } }],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
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

  assert(`[${S}] 防御不可`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(_u, e) { e.appendEffect('CantDefence', 1); return '' } }],
      [makeCard({ atkPoint: '1', defPoint: '5', cardHp: 50 })],
    )
    return logContains(r.log, '无法作出防御')
  })())

  assert(`[${S}] 回避不可`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(_u, e) { e.appendEffect('CantDodge', 1); return '' } }],
      [makeCard({ atkPoint: '1', dodPoint: '99', cardHp: 50 })],
    )
    return logContains(r.log, '无法进行回避')
  })())

  assert(`[${S}] 连击: 敌方受伤时ATK+1`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ atkPoint: '5', cardHp: 5 }), onCardSet(u) { u.appendEffect('Combo', 1); return '' } },
        makeCard({ atkPoint: '5', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    return logContains(r.log, '连击触发')
  })())

  assert(`[${S}] 背水: HP≤3时ATK+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 3 }), onCardSet(u) { u.appendEffect('DesperateAtk', 2); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    return logContains(r.log, '背水触发')
  })())

  assert(`[${S}] 绝境: HP≤3时DOD+1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ dodPoint: '1', cardHp: 3 }), onCardSet(u) { u.appendEffect('DesperateDod', 1); return '' } }],
      [makeCard({ atkPoint: '5' })],
    )
    return logContains(r.log, '绝境触发')
  })())

  assert(`[${S}] 荆棘: 反弹伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendEffect('Thorns', 1); return '' } }],
      [makeCard({ atkPoint: '5', cardHp: 50 })],
    )
    return logContains(r.log, '荆棘反弹')
  })())
}

function testBorderEffects() {
  const S = '结界效果'

  assert(`[${S}] 强化结界: ATK+2`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '5' }), onCardSet(u) { u.appendBorder('StrengthBorder', 3, 2); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    return logContains(r.log, '攻击增加了2点')
  })())

  assert(`[${S}] 伤害结界: 每回合造成伤害`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendBorder('DamageBorder', 5, 1); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    return logContains(r.log, '伤害结界') && logContains(r.log, '受到1点直接伤害')
  })())

  assert(`[${S}] 脆弱结界: DEF-1`, (() => {
    const r = runBattle(
      [{ ...makeCard({ atkPoint: '1' }), onCardSet(_u, e) { e.appendBorder('FragileBorder', 3, 1); return '' } }],
      [makeCard({ atkPoint: '1', defPoint: '5', cardHp: 50 })],
    )
    return logContains(r.log, '防御减少了1点')
  })())

  assert(`[${S}] 结界回合衰减`, (() => {
    const r = runBattle(
      [{ ...makeCard({ cardHp: 50 }), onCardSet(u) { u.appendBorder('StrengthBorder', 2, 5); return '' } }],
      [makeCard({ atkPoint: '1', cardHp: 50 })],
    )
    const strLogs = r.log.filter(e => e.message.includes('攻击增加了5点'))
    return strLogs.length >= 1 && strLogs.length <= 2
  })())
}

function testCardBreakClearsEffects() {
  const S = '击破清效果'

  assert(`[${S}] 非结界效果被清除`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ cardHp: 1 }), onCardSet(u) { u.appendEffect('Strength', 5); return '' } },
        makeCard({ atkPoint: '5', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    return !r2Log.some(e => e.message.includes('攻击增加了5点'))
  })())

  assert(`[${S}] 结界保留`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ cardHp: 1 }), onCardSet(u) { u.appendBorder('StrengthBorder', 5, 3); return '' } },
        makeCard({ atkPoint: '5', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    return r2Log.some(e => e.message.includes('攻击增加了3点'))
  })())

  assert(`[${S}] 冻结状态被清除`, (() => {
    const r = runBattle(
      [
        { ...makeCard({ cardHp: 1 }), onCardSet(u) { u.appendEffect('Freeze', 3); return '' } },
        makeCard({ atkPoint: '5', cardHp: 50 }),
      ],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    const r2Log = r.log.filter(e => e.round >= 2)
    return !r2Log.some(e => e.message.includes('冰冻中') && e.message.includes('A'))
  })())
}

function testCardEffects() {
  const S = '符卡效果'
  for (const card of ALL_CARDS) {
    if (card.description === '无') continue
    const hasOnCardSet = !!card.onCardSet
    const hasOnCardBreak = !!card.onCardBreak
    const hasOnTurnStart = !!card.onTurnStart

    assert(`[${S}] ${card.name} 可正常出战`, (() => {
      try { runBattle([card], [makeCard({ atkPoint: '1', cardHp: 50 })]); return true }
      catch { return false }
    })())

    if (hasOnCardSet) {
      assert(`[${S}] ${card.name} 宣言不报错`, (() => {
        try { runBattle([card], [makeCard({ atkPoint: '1', cardHp: 50 })]); return true }
        catch { return false }
      })())
    }

    if (hasOnCardBreak) {
      assert(`[${S}] ${card.name} 亡语不报错`, (() => {
        try {
          runBattle([card, makeCard({ atkPoint: '1', cardHp: 50 })], [makeCard({ atkPoint: '99', cardHp: 50 })])
          return true
        } catch { return false }
      })())
    }

    if (hasOnTurnStart) {
      assert(`[${S}] ${card.name} 回合开始不报错`, (() => {
        try { runBattle([card], [makeCard({ atkPoint: '1', cardHp: 50 })]); return true }
        catch { return false }
      })())
    }
  }
}

function testBattleMechanics() {
  const S = '战斗机制'

  assert(`[${S}] 概率闪避`, (() => {
    for (let i = 0; i < 50; i++) {
      const r = runBattle([makeCard({ atkPoint: '5' })], [makeCard({ atkPoint: '1', dodPoint: '99', cardHp: 50 })])
      if (logContains(r.log, '闪避成功')) return true
    }
    return false
  })())

  assert(`[${S}] 符卡击破日志`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1', cardHp: 50 })],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    return logContains(r.log, '符卡被击破')
  })())

  assert(`[${S}] 多符卡切换`, (() => {
    const r = runBattle(
      [makeCard({ cardHp: 1 }), makeCard({ cardHp: 1 }), makeCard({ atkPoint: '1', cardHp: 50 })],
      [makeCard({ atkPoint: '99', cardHp: 50 })],
    )
    return logPhaseCount(r.log, 'card_break') >= 2
  })())

  assert(`[${S}] 胜负判定`, (() => {
    const r = runBattle([makeCard({ atkPoint: '99' })], [makeCard({ atkPoint: '1', cardHp: 1 })])
    return r.winnerId === 1
  })())

  assert(`[${S}] 骰子表达式`, (() => {
    try {
      runBattle([makeCard({ atkPoint: '2d4+1' })], [makeCard({ atkPoint: '1', cardHp: 50 })])
      return true
    } catch { return false }
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
    battlesPerStage: 4, totalStages: 3, finished: false, victories: 0,
  }
  let totalRounds = 0

  while (!state.finished) {
    const enc = generateEncounter(state.currentStage, state.currentBattle, rng)
    try {
      const b = new Battle(1)
      b.setCreator('玩家')
      b.creator.chosenCards = state.cards.map(c => toCardData(c))
      b.setSingleEnemy('敌人', enc.enemyCards)
      b.runFullBattle()
      totalRounds += b.gameRound

      const usedIndices = b.creator.usedCardIndices
      for (let i = 0; i < state.cards.length; i++) {
        if (i < usedIndices.length) {
          state.cards[i].currentHp = i === usedIndices.length - 1 ? b.creator.nowHp : 0
        }
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
          state.cards.push(createSpellCard(NEW_CARD_POOL[Math.floor(rng() * NEW_CARD_POOL.length)]))
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

console.log('开始符卡系统自测...\n')

testEffectBasics()
testBorderEffects()
testCardBreakClearsEffects()
testCardEffects()
testBattleMechanics()

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
