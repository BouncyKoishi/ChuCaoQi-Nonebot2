let _effectsRegistry: Record<string, new (...args: any[]) => Effect> | null = null

export function registerEffects(registry: Record<string, new (...args: any[]) => Effect>) {
  _effectsRegistry = registry
}

function getEffectsRegistry(): Record<string, new (...args: any[]) => Effect> {
  if (!_effectsRegistry) throw new Error('Effects not registered. Call registerEffects() first.')
  return _effectsRegistry
}

export interface CardData {
  id: number
  cost: number
  name: string
  cardHp: number
  maxCardHp?: number
  atkPoint: string
  defPoint: string
  dodPoint: string
  description: string
  onCardSet?: (user: Battler, enemy: Battler) => string
  onCardBreak?: (user: Battler, enemy: Battler) => string
  onTurnStart?: (user: Battler, enemy: Battler) => string
  onTurnEnd?: (user: Battler, enemy: Battler) => string
  onEnemyCardBreak?: (user: Battler, enemy: Battler) => string
  isTimeCard?: boolean
  timeCardTurns?: number
  character?: string
}

export interface EffectData {
  id: string
  displayName: string
  effectType: 'BUFF' | 'DEBUFF' | 'BORDER'
  amount: number
  turns?: number
  strength?: number
}

export interface VisualData {
  creatorAtk?: number
  creatorDef?: number
  creatorDod?: number
  joinerAtk?: number
  joinerDef?: number
  joinerDod?: number
  creatorDodged?: boolean
  joinerDodged?: boolean
  creatorDefSuccess?: boolean
  joinerDefSuccess?: boolean
  creatorHurt?: number
  joinerHurt?: number
  whoBroke?: 'creator' | 'joiner'
  breakSource?: 'battle' | 'effect' | 'time'
}

export interface LogEntry {
  round: number
  phase: string
  message: string
  creatorHp?: number
  joinerHp?: number
  visual?: VisualData
  creatorCard?: CardData
  joinerCard?: CardData
  creatorEffects?: EffectData[]
  joinerEffects?: EffectData[]
  creatorCardIndex?: number
  joinerCardIndex?: number
}

export class SeededRandom {
  private seed: number

  constructor(seed?: number) {
    this.seed = seed ?? Math.floor(Math.random() * 2147483647)
  }

  next(): number {
    this.seed = (this.seed * 16807) % 2147483647
    return (this.seed - 1) / 2147483646
  }

  nextInt(min: number, max: number): number {
    return Math.floor(this.next() * (max - min + 1)) + min
  }

  getSeed(): number {
    return this.seed
  }
}

export function rollDice(diceStr: string, rng: SeededRandom): number {
  if (!diceStr) return 0
  let resultStr = diceStr
  const minDiceRegex = /(\d{1,2})d\((\d{1,2})~(\d{1,2})\)/g
  let match: RegExpExecArray | null
  while ((match = minDiceRegex.exec(diceStr)) !== null) {
    const amount = parseInt(match[1])
    const min = parseInt(match[2])
    const faces = parseInt(match[3])
    let total = 0
    for (let i = 0; i < amount; i++) {
      total += rng.nextInt(min, faces)
    }
    resultStr = resultStr.replace(match[0], total.toString())
  }
  const diceRegex = /(\d{1,2})d(\d{1,2})/g
  while ((match = diceRegex.exec(resultStr)) !== null) {
    const amount = parseInt(match[1])
    const faces = parseInt(match[2])
    let total = 0
    for (let i = 0; i < amount; i++) {
      total += rng.nextInt(1, faces)
    }
    resultStr = resultStr.replace(match[0], total.toString())
  }
  try {
    const result = Function('"use strict"; return (' + resultStr + ')')()
    return Math.max(Math.floor(result), 0)
  } catch {
    return 0
  }
}

export const PERMANENT_EFFECT_IDS = new Set(['CantDodge', 'CantDefence', 'Freeze'])

export class Effect {
  id: string = 'DefaultEffect'
  displayName: string = ''
  effectType: 'BUFF' | 'DEBUFF' = 'BUFF'
  amount: number = 1
  infoMsg: string = ''
  user: Battler | null = null
  enemy: Battler | null = null

  constructor(amount: number = 1) {
    this.amount = amount
  }

  setPlayerInfo(user: Battler, enemy: Battler) {
    this.user = user
    this.enemy = enemy
  }

  get userName(): string { return this.user?.name ?? '' }
  get enemyName(): string { return this.enemy?.name ?? '' }
  get userHp(): number { return this.user?.nowHp ?? 0 }

  stack(amount: number) {
    this.amount += amount
    if (this.amount < -1) this.amount = -1
    if (this.amount === -1 && !PERMANENT_EFFECT_IDS.has(this.id)) this.amount = 0
  }
  reduce(amount: number) {
    if (this.amount === -1) return
    this.amount = Math.max(0, this.amount - amount)
  }
  clean() { this.amount = 0 }

  onTurnStart(_user: Battler, _enemy: Battler): void { }
  onTurnEnd(_user: Battler, _enemy: Battler): void { }
  onAttackCalc(value: number): number { return value }
  onDefenceCalc(value: number): number { return value }
  onDodgeCalc(value: number): number { return value }
  onHurtValueCalc(value: number): number { return value }
  onAttackDamageCalc(value: number): number { return value }
  onDefenceSuccessJudge(success: boolean): boolean { return success }
  onDodgeSuccessJudge(success: boolean): boolean { return success }
  beforeHurt(value: number): number { return value }
  onHurt(value: number): number { return value }
  onBattleHurt(value: number): number { return value }
  onEffectHurt(value: number): number { return value }
  onCardSet(_user: Battler, _enemy: Battler): void { }
  onCardBreak(_user: Battler, _enemy: Battler): void { }
  onRoundEnd(_user: Battler, _enemy: Battler): void { }

  toData(): EffectData {
    return {
      id: this.id,
      displayName: this.displayName,
      effectType: this.effectType,
      amount: this.amount,
    }
  }
}

export class Border extends Effect {
  id: string = 'DefaultBorder'
  effectType: 'BUFF' | 'DEBUFF' = 'BUFF'
  turns: number = 0
  strength: number = 0

  constructor(turns: number, strength: number = 0) {
    super(1)
    this.turns = turns
    this.strength = strength
  }

  stack(turns: number) { this.turns = Math.max(this.turns, turns) }
  reduce(_?: number) {
    this.turns--
    if (this.turns <= 0) this.amount = 0
  }
  clean() { this.turns = 0; this.amount = 0 }

  toData(): EffectData {
    return {
      id: this.id,
      displayName: this.displayName,
      effectType: 'BORDER',
      amount: this.amount,
      turns: this.turns,
      strength: this.strength,
    }
  }
}

export class Battler {
  id: number
  name: string
  chosenCards: CardData[] = []
  usedCardIndices: number[] = []
  effects: Effect[] = []
  states: string[] = []
  nowHp: number = 0
  nowCard: CardData | null = null
  enemy: Battler | null = null
  attack: number = 0
  defence: number = 0
  dodge: number = 0
  dodSuccess: boolean | null = null
  defSuccess: boolean | null = null
  lastHurtType: 'battle' | 'effect' | 'time' | '' = ''
  gameRound: number = 0
  spiritGained: number = 0
  timeCardRemaining?: number
  justApplied: boolean = false
  // [亡语鞭尸修复] 保存被击破符卡的引用。
  // 当双方符卡同时被击破时，需要在触发亡语前先切换到新符卡，
  // 否则亡语伤害会打到对方已被击破的旧符卡上（鞭尸）。
  // 切换后 nowCard 已指向新符卡，因此需要此字段保存旧卡引用以正确触发亡语。
  // 生命周期：handleCardBreakLog 中设置 → handleCardBreakEffects 中使用后清除
  _brokenCardRef: CardData | null = null

  constructor(id: number, name: string) {
    this.id = id
    this.name = name
  }

  setEnemy(enemy: Battler) { this.enemy = enemy }

  appendEffect(effectId: string, amount: number, aliasName?: string) {
    if (!effectId) return
    const ALL_EFFECTS = getEffectsRegistry()
    for (const e of this.effects) {
      if (e.id === effectId) {
        e.stack(amount)
        if (aliasName) e.displayName = aliasName
        return
      }
    }
    const Cls = ALL_EFFECTS[effectId]
    if (Cls) {
      const effect = new Cls(amount)
      if (aliasName) effect.displayName = aliasName
      if (this.enemy) effect.setPlayerInfo(this, this.enemy)
      this.effects.push(effect)
    }
  }

  appendBorder(effectId: string, turns: number, strength: number) {
    if (!effectId) return
    const ALL_EFFECTS = getEffectsRegistry()
    for (const e of this.effects) {
      if (e.id === effectId) { e.stack(turns); return }
    }
    const Cls = ALL_EFFECTS[effectId]
    if (Cls) {
      const border = new Cls(turns) as Border
      border.strength = strength
      if (this.enemy) border.setPlayerInfo(this, this.enemy)
      this.effects.push(border)
    }
  }

  removeEffect(effectId: string, amount: number = 0) {
    if (!effectId) return
    for (let i = 0; i < this.effects.length; i++) {
      if (this.effects[i].id === effectId) {
        if (amount === 0) { this.effects.splice(i, 1) }
        else { this.effects[i].reduce(amount) }
        break
      }
    }
    this.effects = this.effects.filter(e => e.amount > 0 || (e.amount === -1 && PERMANENT_EFFECT_IDS.has(e.id)))
  }

  runEffects(funcName: string, ...args: any[]): any {
    const msgs: string[] = []
    for (const effect of this.effects) {
      if (this.states.includes('Frozen')) {
        if (effect.id !== 'Freeze' && !(effect instanceof Border)) continue
      }
      const func = (effect as any)[funcName]
      if (typeof func === 'function') {
        const result = func.apply(effect, args)
        if (result !== undefined) {
          args[0] = result
        }
      }
      if (effect.infoMsg) {
        msgs.push(effect.infoMsg)
        effect.infoMsg = ''
      }
    }
    this.effects = this.effects.filter(e => e.amount > 0 || (e.amount === -1 && PERMANENT_EFFECT_IDS.has(e.id)))
    const msg = msgs.join('\n')
    if (args.length === 0) return msg
    if (args.length === 1) return [args[0], msg]
    return [args, msg]
  }

  getPoints(rng: SeededRandom): [number, string] {
    if (this.states.includes('Frozen')) {
      this.attack = 0; this.defence = 0; this.dodge = 0
      return [0, `${this.name}被冻结，无法行动！\n`]
    }
    this.attack = rollDice(this.nowCard!.atkPoint, rng)
    const [atkVal, atkMsg] = this.runEffects('onAttackCalc', this.attack) as [number, string]
    this.attack = atkVal

    this.defence = rollDice(this.nowCard!.defPoint, rng)
    const [defVal, defMsg] = this.runEffects('onDefenceCalc', this.defence) as [number, string]
    this.defence = defVal

    this.dodge = rollDice(this.nowCard!.dodPoint, rng)
    const [dodVal, dodMsg] = this.runEffects('onDodgeCalc', this.dodge) as [number, string]
    this.dodge = dodVal

    this.attack = Math.max(this.attack, 0)
    this.defence = Math.max(this.defence, 0)
    this.dodge = Math.max(this.dodge, 0)

    const info = atkMsg + defMsg + dodMsg + `${this.name} Hp:${this.nowHp} Atk:${this.attack} Def:${this.defence} Dod:${this.dodge}\n`
    return [this.attack, info]
  }

  calcHurt(enemyAtk: number, rng: SeededRandom): [number, string] {
    if (this.nowCard?.isTimeCard && this.timeCardRemaining !== undefined && this.timeCardRemaining > 0) {
      this.dodSuccess = true
      this.defSuccess = true
      return [0, `${this.name} 时符效果：免疫战斗伤害\n`]
    }
    const dodgeProb = (this.dodge + enemyAtk) > 0 ? this.dodge / (this.dodge + enemyAtk) : 0
    let dodSuccess = rng.next() < dodgeProb
    const [dodSuccess1, dodMsg] = this.runEffects('onDodgeSuccessJudge', dodSuccess) as [boolean, string]
    dodSuccess = dodSuccess1

    let defSuccess = true
    let defMsg = ''
    if (!dodSuccess) {
      const [defSuccess1, defMsg1] = this.runEffects('onDefenceSuccessJudge', defSuccess) as [boolean, string]
      defSuccess = defSuccess1
      defMsg = defMsg1
    }

    this.dodSuccess = dodSuccess
    this.defSuccess = defSuccess

    let hurt: number
    if (dodSuccess) { hurt = 0 }
    else if (defSuccess) { hurt = Math.max(enemyAtk - this.defence, 1) }
    else { hurt = enemyAtk }

    const [hurtVal1, hurtMsg] = this.runEffects('onHurtValueCalc', hurt) as [number, string]
    hurt = hurtVal1
    const [hurtVal2, enemyHurtMsg] = this.enemy!.runEffects('onAttackDamageCalc', hurt) as [number, string]
    hurt = Math.max(hurtVal2, 0)

    const dodgeInfo = `${this.name} ${dodSuccess ? '闪避成功！' : '闪避失败'}\n`
    const calcInfo = dodgeInfo + dodMsg + defMsg + hurtMsg + enemyHurtMsg
    return [hurt, calcInfo]
  }

  battleHurt(value: number): string {
    this.lastHurtType = 'battle'
    const [val1, beforeMsg] = this.runEffects('beforeHurt', value) as [number, string]
    this.nowHp -= val1
    const [, hurtMsg] = this.runEffects('onHurt', val1) as [number, string]
    const [, battleHurtMsg] = this.runEffects('onBattleHurt', val1) as [number, string]
    return beforeMsg + hurtMsg + battleHurtMsg
  }

  effectHurt(value: number): string {
    if (this.nowCard?.isTimeCard && this.timeCardRemaining !== undefined && this.timeCardRemaining > 0) {
      return `[${this.nowCard.name}]时符效果：无法受到伤害！\n`
    }
    this.lastHurtType = 'effect'
    const [val1, beforeMsg] = this.runEffects('beforeHurt', value) as [number, string]
    this.nowHp -= val1
    const [, hurtMsg] = this.runEffects('onHurt', val1) as [number, string]
    const [, effectHurtMsg] = this.runEffects('onEffectHurt', val1) as [number, string]
    return beforeMsg + hurtMsg + effectHurtMsg
  }

  shouldChangeCard(): boolean { return this.nowHp <= 0 }
  shouldEnd(): boolean { return this.nowHp <= 0 && this.usedCardIndices.length >= this.chosenCards.length }

  setNewMainCard(cardIndex?: number): boolean {
    if (cardIndex !== undefined) {
      if (cardIndex < 0 || cardIndex >= this.chosenCards.length) return false
      if (this.usedCardIndices.includes(cardIndex)) return false
    } else {
      const available = Array.from({ length: this.chosenCards.length }, (_, i) => i)
        .filter(i => !this.usedCardIndices.includes(i))
      if (available.length === 0) return false
      cardIndex = available[0]
    }
    this.nowCard = this.chosenCards[cardIndex]
    this.nowHp = this.nowCard.cardHp
    this.usedCardIndices.push(cardIndex)
    this.justApplied = true
    if (this.nowCard.isTimeCard) {
      this.timeCardRemaining = this.nowCard.timeCardTurns
    }
    return true
  }

  cleanTurnTemp() {
    this.attack = 0
    this.defence = 0
    this.dodge = 0
    this.dodSuccess = null
    this.defSuccess = null
  }

  toData() {
    return {
      id: this.id,
      name: this.name,
      nowHp: this.nowHp,
      nowCard: this.nowCard ? { ...this.nowCard } : null,
      usedCardIndices: [...this.usedCardIndices],
      effects: this.effects.map(e => e.toData()),
      attack: this.attack,
      defence: this.defence,
      dodge: this.dodge,
    }
  }
}

class BattleLog {
  entries: LogEntry[] = []
  private battle: Battle
  constructor(battle: Battle) { this.battle = battle }
  add(round: number, phase: string, message: string, creatorHp?: number, joinerHp?: number, visual?: VisualData, creatorCard?: CardData, joinerCard?: CardData) {
    const entry: LogEntry = { round, phase, message }
    if (creatorHp !== undefined) entry.creatorHp = creatorHp
    if (joinerHp !== undefined) entry.joinerHp = joinerHp
    if (visual) entry.visual = visual
    if (creatorCard) entry.creatorCard = creatorCard
    if (joinerCard) entry.joinerCard = joinerCard
    if (this.battle.creator) {
      entry.creatorEffects = this.battle.creator.effects.map(e => e.toData())
      entry.creatorCardIndex = this.battle.creator.usedCardIndices.length
    }
    if (this.battle.joiner) {
      entry.joinerEffects = this.battle.joiner.effects.map(e => e.toData())
      entry.joinerCardIndex = this.battle.joiner.usedCardIndices.length
    }
    this.entries.push(entry)
  }
}

export class Battle {
  static STATE_WAITING_CREATOR_CARD = 'waiting_creator_card'
  static STATE_FINISHED = 'finished'

  creatorId: number
  joinerId: number = -1
  creator: Battler | null = null
  joiner: Battler | null = null
  gameRound: number = 0
  turnNumber: number = 0
  log = new BattleLog(this)
  finished: boolean = false
  winnerId: number | null = null
  state: string = Battle.STATE_WAITING_CREATOR_CARD
  rng: SeededRandom

  constructor(creatorId: number, seed?: number) {
    this.creatorId = creatorId
    this.rng = new SeededRandom(seed)
  }

  setCreator(name: string) {
    this.creator = new Battler(this.creatorId, name)
  }

  setSingleEnemy(name: string, cardList: CardData[]) {
    this.joinerId = -1
    this.joiner = new Battler(-1, name)
    this.joiner.chosenCards = cardList
    this.creator!.setEnemy(this.joiner)
    this.joiner.setEnemy(this.creator!)
    this.gameRound = 0
  }

  playCardAndResolve(creatorCardIndex: number): Battle {
    this.applyCard(this.creator!, creatorCardIndex)

    if (this.joiner!.nowCard === null || this.joiner!.shouldChangeCard()) {
      const aiIdx = this.autoChooseCard(this.joiner!)
      if (aiIdx >= 0) this.applyCard(this.joiner!, aiIdx)
    }

    this.onNewCardsSet()

    while (!this.finished) {
      this.resolveTurnsUntilCardBreak(false)
      if (this.checkGameEnd()) break

      const creatorBreak = this.creator!.shouldChangeCard()
      const joinerBreak = this.joiner!.shouldChangeCard()

      if (creatorBreak) {
        this.state = Battle.STATE_WAITING_CREATOR_CARD
        return this
      }

      if (joinerBreak) {
        const aiIdx = this.autoChooseCard(this.joiner!)
        if (aiIdx < 0) break
        this.applyCard(this.joiner!, aiIdx)
        this.onJoinerNewCard()
      }
    }

    if (!this.finished) this.checkGameEnd()
    this.state = Battle.STATE_FINISHED
    return this
  }

  autoChooseCard(battler: Battler): number {
    const available = Array.from({ length: battler.chosenCards.length }, (_, i) => i)
      .filter(i => !battler.usedCardIndices.includes(i))
    if (available.length === 0) return -1
    return available[this.rng.nextInt(0, available.length - 1)]
  }

  applyCard(battler: Battler, cardIndex: number) {
    battler.nowCard = battler.chosenCards[cardIndex]
    battler.nowHp = battler.nowCard.cardHp
    battler.usedCardIndices.push(cardIndex)
    battler.justApplied = true
    if (battler.nowCard.isTimeCard) {
      battler.timeCardRemaining = battler.nowCard.timeCardTurns
    }
  }

  onNewCardsSet() {
    this.gameRound++
    this.creator!.gameRound = this.gameRound
    this.joiner!.gameRound = this.gameRound
    this.log.add(this.gameRound, 'card_set', `─── R${this.gameRound} 宣言 ───`)
    const creatorNew = this.creator!.justApplied
    const joinerNew = this.joiner!.justApplied
    const cPart = creatorNew ? `${this.creator!.name} 宣言 [${this.creator!.nowCard?.name ?? '??'}]` : `${this.creator!.name}[${this.creator!.nowCard?.name ?? '??'}]`
    const jPart = joinerNew ? `${this.joiner!.name} 宣言 [${this.joiner!.nowCard?.name ?? '??'}]` : `${this.joiner!.name}[${this.joiner!.nowCard?.name ?? '??'}]`
    this.log.add(this.gameRound, 'card_set',
      `${cPart} HP:${Math.max(0, this.creator!.nowHp)} | ${jPart} HP:${Math.max(0, this.joiner!.nowHp)}`,
      Math.max(0, this.creator!.nowHp), Math.max(0, this.joiner!.nowHp), undefined, this.creator!.nowCard ? { ...this.creator!.nowCard } : undefined, this.joiner!.nowCard ? { ...this.joiner!.nowCard } : undefined)
    if (this.creator!.justApplied) {
      const beforeEffs = new Set(this.creator!.effects.map(e => e.id + e.amount))
      const msg1 = this.creator!.nowCard!.onCardSet?.(this.creator!, this.joiner!) ?? ''
      const newEffs = this.creator!.effects.filter(e => !beforeEffs.has(e.id + e.amount)).map(e => e.displayName)
      const effDesc = newEffs.length > 0 ? `获得${newEffs.join('、')}` : ''
      const finalMsg1 = msg1 || effDesc
      if (finalMsg1) this.log.add(this.gameRound, 'card_set', `[${this.creator!.nowCard!.name}] [${this.creator!.name}]${finalMsg1}`)
      this.creator!.justApplied = false
    }
    if (this.joiner!.justApplied) {
      const beforeEffs = new Set(this.joiner!.effects.map(e => e.id + e.amount))
      const msg2 = this.joiner!.nowCard!.onCardSet?.(this.joiner!, this.creator!) ?? ''
      const newEffs = this.joiner!.effects.filter(e => !beforeEffs.has(e.id + e.amount)).map(e => e.displayName)
      const effDesc = newEffs.length > 0 ? `获得${newEffs.join('、')}` : ''
      const finalMsg2 = msg2 || effDesc
      if (finalMsg2) this.log.add(this.gameRound, 'card_set', `[${this.joiner!.nowCard!.name}] [${this.joiner!.name}]${finalMsg2}`)
      this.joiner!.justApplied = false
    }
  }

  onJoinerNewCard() {
    this.gameRound++
    this.creator!.gameRound = this.gameRound
    this.joiner!.gameRound = this.gameRound
    this.log.add(this.gameRound, 'card_set', `─── R${this.gameRound} 宣言 ───`)
    this.log.add(this.gameRound, 'card_set',
      `${this.creator!.name}[${this.creator!.nowCard?.name ?? '??'}] HP:${Math.max(0, this.creator!.nowHp)} | ${this.joiner!.name} 宣言 [${this.joiner!.nowCard?.name ?? '??'}] HP:${Math.max(0, this.joiner!.nowHp)}`,
      Math.max(0, this.creator!.nowHp), Math.max(0, this.joiner!.nowHp), undefined, this.creator!.nowCard ? { ...this.creator!.nowCard } : undefined, this.joiner!.nowCard ? { ...this.joiner!.nowCard } : undefined)
    const beforeEffs = new Set(this.joiner!.effects.map(e => e.id + e.amount))
    const msg = this.joiner!.nowCard!.onCardSet?.(this.joiner!, this.creator!) ?? ''
    const newEffs = this.joiner!.effects.filter(e => !beforeEffs.has(e.id + e.amount)).map(e => e.displayName)
    const effDesc = newEffs.length > 0 ? `获得${newEffs.join('、')}` : ''
    const finalMsg = msg || effDesc
    if (finalMsg) this.log.add(this.gameRound, 'card_set', `[${this.joiner!.nowCard!.name}] [${this.joiner!.name}]${finalMsg}`)
  }

  // [亡语鞭尸修复] 击破处理流程（三步走）：
  // 1. handleCardBreakLog：记录击破日志 + 保存旧卡引用(_brokenCardRef) + 清理效果
  // 2. setNewMainCard：切换到新符卡（此时 nowCard 指向新卡，enemy.nowCard 也指向新卡）
  // 3. handleCardBreakEffects：触发亡语（从 _brokenCardRef 取旧卡回调，伤害打到对方新卡上）
  // 关键：步骤2必须在步骤3之前，否则亡语伤害会打到对方已被击破的旧符卡（鞭尸）
  resolveTurnsUntilCardBreak(autoSwap = true) {
    while (!this.finished) {
      if (this.creator!.shouldChangeCard() || this.joiner!.shouldChangeCard()) break
      this.resolveSingleTurn()
    }
    const brokenSet = new Set<Battler>()
    if (this.creator!.shouldChangeCard()) { this.handleCardBreakLog(this.creator!); brokenSet.add(this.creator!) }
    if (this.joiner!.shouldChangeCard()) { this.handleCardBreakLog(this.joiner!); brokenSet.add(this.joiner!) }
    const swapped = new Set<Battler>()
    if (autoSwap) {
      for (const b of brokenSet) {
        if (!b.shouldEnd()) { b.setNewMainCard(); swapped.add(b) }
      }
    }
    for (const b of brokenSet) {
      this.handleCardBreakEffects(b)
    }
    for (const b of swapped) {
      brokenSet.delete(b)
    }
    let recheck = true
    let recheckCount = 0
    while (recheck && recheckCount < 10) {
      recheck = false
      recheckCount++
      if (this.creator!.shouldChangeCard() && !brokenSet.has(this.creator!)) {
        this.handleCardBreakLog(this.creator!)
        brokenSet.add(this.creator!)
        if (autoSwap && !this.creator!.shouldEnd()) {
          this.creator!.setNewMainCard()
          brokenSet.delete(this.creator!)
        }
        this.handleCardBreakEffects(this.creator!)
        recheck = true
      }
      if (this.joiner!.shouldChangeCard() && !brokenSet.has(this.joiner!)) {
        this.handleCardBreakLog(this.joiner!)
        brokenSet.add(this.joiner!)
        if (autoSwap && !this.joiner!.shouldEnd()) {
          this.joiner!.setNewMainCard()
          brokenSet.delete(this.joiner!)
        }
        this.handleCardBreakEffects(this.joiner!)
        recheck = true
      }
    }
  }

  resolveSingleTurn() {
    this.turnStart()
    if (this.creator!.shouldChangeCard() || this.joiner!.shouldChangeCard()) return
    const [cAtk, jAtk] = this.turnGetPoints()
    const [cHurt, jHurt] = this.turnCalcHurt(cAtk, jAtk)
    this.turnHpChange(cHurt, jHurt)
    this.turnEnd()
  }

  turnStart() {
    this.turnNumber++
    this.log.add(this.gameRound, 'turn_start', `─── Turn ${this.turnNumber} ───`)
    const msg1 = this.creator!.nowCard!.onTurnStart?.(this.creator!, this.joiner!) ?? ''
    if (msg1) this.log.add(this.gameRound, 'turn_start', `[${this.creator!.nowCard!.name}] ${msg1}`)
    const msg2 = this.joiner!.nowCard!.onTurnStart?.(this.joiner!, this.creator!) ?? ''
    if (msg2) this.log.add(this.gameRound, 'turn_start', `[${this.joiner!.nowCard!.name}] ${msg2}`)
    const effMsg = this.runEffectsBoth('onTurnStart')
    if (effMsg) this.log.add(this.gameRound, 'turn_start', effMsg)
  }

  turnGetPoints(): [number, number] {
    const [cAtk, cMsg] = this.creator!.getPoints(this.rng)
    const [jAtk, jMsg] = this.joiner!.getPoints(this.rng)
    this.log.add(this.gameRound, 'points', cMsg + jMsg, undefined, undefined, {
      creatorAtk: this.creator!.attack,
      creatorDef: this.creator!.defence,
      creatorDod: this.creator!.dodge,
      joinerAtk: this.joiner!.attack,
      joinerDef: this.joiner!.defence,
      joinerDod: this.joiner!.dodge,
    })
    return [cAtk, jAtk]
  }

  turnCalcHurt(cAtk: number, jAtk: number): [number, number] {
    const [cHurt, cMsg] = this.creator!.calcHurt(jAtk, this.rng)
    const [jHurt, jMsg] = this.joiner!.calcHurt(cAtk, this.rng)
    this.log.add(this.gameRound, 'calc', cMsg + jMsg, undefined, undefined, {
      creatorDodged: this.creator!.dodSuccess ?? false,
      joinerDodged: this.joiner!.dodSuccess ?? false,
      creatorDefSuccess: this.creator!.defSuccess ?? false,
      joinerDefSuccess: this.joiner!.defSuccess ?? false,
      creatorHurt: cHurt,
      joinerHurt: jHurt,
    })
    return [cHurt, jHurt]
  }

  turnHpChange(cHurt: number, jHurt: number) {
    const prevCreatorHp = this.creator!.nowHp
    const prevJoinerHp = this.joiner!.nowHp
    const cMsg = cHurt > 0 ? this.creator!.battleHurt(cHurt) : ''
    const jMsg = jHurt > 0 ? this.joiner!.battleHurt(jHurt) : ''

    // Drain（吸血）钩子
    const creatorRawDmg = prevCreatorHp - this.creator!.nowHp
    const joinerRawDmg = prevJoinerHp - this.joiner!.nowHp

    const creatorHpAfterDmg = this.creator!.nowHp
    const joinerHpAfterDmg = this.joiner!.nowHp

    const drainParts: string[] = []
    if (joinerRawDmg > 0) {
      const drainEffect = this.creator!.effects.find(e => e.id === 'Drain')
      if (drainEffect) {
        const healAmt = Math.min(joinerRawDmg, drainEffect.amount, this.creator!.nowCard!.cardHp - this.creator!.nowHp)
        if (healAmt > 0) {
          this.creator!.nowHp += healAmt
          drainParts.push(`[${this.creator!.name}]吸血恢复了${healAmt}点HP (HP:${this.creator!.nowHp})`)
        }
      }
    }
    if (creatorRawDmg > 0) {
      const drainEffect = this.joiner!.effects.find(e => e.id === 'Drain')
      if (drainEffect) {
        const healAmt = Math.min(creatorRawDmg, drainEffect.amount, this.joiner!.nowCard!.cardHp - this.joiner!.nowHp)
        if (healAmt > 0) {
          this.joiner!.nowHp += healAmt
          drainParts.push(`[${this.joiner!.name}]吸血恢复了${healAmt}点HP (HP:${this.joiner!.nowHp})`)
        }
      }
    }

    const hurtParts: string[] = []
    if (creatorRawDmg > 0) hurtParts.push(`${this.creator!.name} 受到${creatorRawDmg}点伤害 (HP:${Math.max(0, creatorHpAfterDmg)})`)
    if (joinerRawDmg > 0) hurtParts.push(`${this.joiner!.name} 受到${joinerRawDmg}点伤害 (HP:${Math.max(0, joinerHpAfterDmg)})`)
    const hurtSummary = hurtParts.length > 0 ? hurtParts.join(' | ') + '\n' : ''
    const drainSummary = drainParts.length > 0 ? drainParts.join(' | ') + '\n' : ''

    this.log.add(this.gameRound, 'hurt', hurtSummary + drainSummary + cMsg + jMsg, this.creator!.nowHp, this.joiner!.nowHp, {
      creatorHurt: creatorRawDmg,
      joinerHurt: joinerRawDmg,
      creatorDodged: this.creator!.dodSuccess ?? false,
      joinerDodged: this.joiner!.dodSuccess ?? false,
      creatorDefSuccess: this.creator!.defSuccess ?? false,
      joinerDefSuccess: this.joiner!.defSuccess ?? false,
    })
  }

  turnEnd() {
    const effMsg = this.runEffectsBoth('onTurnEnd')
    if (effMsg) this.log.add(this.gameRound, 'turn_end', effMsg)
    const msg1 = this.creator!.nowCard!.onTurnEnd?.(this.creator!, this.joiner!) ?? ''
    if (msg1) this.log.add(this.gameRound, 'turn_end', msg1)
    const msg2 = this.joiner!.nowCard!.onTurnEnd?.(this.joiner!, this.creator!) ?? ''
    if (msg2) this.log.add(this.gameRound, 'turn_end', msg2)

    // 时符倒计时
    if (this.creator!.nowCard?.isTimeCard && this.creator!.timeCardRemaining !== undefined) {
      this.creator!.timeCardRemaining--
      if (this.creator!.timeCardRemaining <= 0) {
        this.creator!.lastHurtType = 'time'
        this.log.add(this.gameRound, 'time_expire', `[${this.creator!.nowCard.name}] 时符时间耗尽，自行消散！`, this.creator!.nowHp, this.joiner!.nowHp)
        this.creator!.nowHp = 0
      }
    }
    if (this.joiner!.nowCard?.isTimeCard && this.joiner!.timeCardRemaining !== undefined) {
      this.joiner!.timeCardRemaining--
      if (this.joiner!.timeCardRemaining <= 0) {
        this.joiner!.lastHurtType = 'time'
        this.log.add(this.gameRound, 'time_expire', `[${this.joiner!.nowCard.name}] 时符时间耗尽，自行消散！`, this.creator!.nowHp, this.joiner!.nowHp)
        this.joiner!.nowHp = 0
      }
    }

    this.creator!.cleanTurnTemp()
    this.joiner!.cleanTurnTemp()
  }

  runEffectsBoth(funcName: string): string {
    const r1 = this.creator!.runEffects(funcName, this.creator!, this.joiner!)
    const r2 = this.joiner!.runEffects(funcName, this.joiner!, this.creator!)
    const m1 = Array.isArray(r1) ? r1[r1.length - 1] : r1
    const m2 = Array.isArray(r2) ? r2[r2.length - 1] : r2
    return [m1, m2].filter((m): m is string => typeof m === 'string' && m.length > 0).join('\n')
  }

  // [亡语鞭尸修复] 击破处理第一步：记录日志 + 保存旧卡引用 + 清理效果
  // 必须在 setNewMainCard 之前调用，因为此时 nowCard 仍指向被击破的符卡
  handleCardBreakLog(battler: Battler) {
    const whoBroke = battler === this.creator ? 'creator' : 'joiner'
    const brokenCardName = battler.nowCard?.name ?? '??'
    const brokenCard = battler.nowCard ? { ...battler.nowCard } : undefined
    battler._brokenCardRef = battler.nowCard
    battler.effects = battler.effects.filter(e => e instanceof Border)
    battler.states = []
    battler.timeCardRemaining = undefined
    const breakSourceText = battler.lastHurtType === 'effect' ? '被效果伤害击破' : battler.lastHurtType === 'time' ? '因时符耗尽而消散' : '被战斗伤害击破'
    this.log.add(this.gameRound, 'card_break', `${battler.name}[${brokenCardName}] 的符卡${breakSourceText}！`, this.creator!.nowHp, this.joiner!.nowHp, {
      whoBroke: whoBroke as 'creator' | 'joiner',
      breakSource: battler.lastHurtType || undefined,
    }, whoBroke === 'creator' ? brokenCard : undefined, whoBroke === 'joiner' ? brokenCard : undefined)
  }

  // [亡语鞭尸修复] 击破处理第二步：触发亡语效果
  // 此时对方已切换到新符卡（setNewMainCard 已调用），
  // 所以亡语伤害会正确打到对方的新符卡上，而非已被击破的旧符卡。
  // 亡语回调从 _brokenCardRef（旧卡引用）上取，而非 nowCard（已指向新卡）。
  handleCardBreakEffects(battler: Battler) {
    const brokenCard = battler._brokenCardRef
    const brokenCardName = brokenCard?.name ?? '??'
    if (brokenCard) {
      const msg = brokenCard.onCardBreak?.(battler, battler.enemy!) ?? ''
      if (msg) this.log.add(this.gameRound, 'card_break', `[${brokenCardName}] ${msg}`, this.creator!.nowHp, this.joiner!.nowHp)
    }
    const enemy = battler.enemy!
    if (!enemy.shouldEnd() && enemy.nowCard?.onEnemyCardBreak) {
      const killMsg = enemy.nowCard.onEnemyCardBreak(enemy, battler)
      if (killMsg) this.log.add(this.gameRound, 'card_break', killMsg, this.creator!.nowHp, this.joiner!.nowHp)
    }
    battler._brokenCardRef = null
  }

  handleCardBreak(battler: Battler) {
    this.handleCardBreakLog(battler)
    this.handleCardBreakEffects(battler)
  }

  checkGameEnd(): boolean {
    const creatorDone = this.creator!.shouldEnd()
    const joinerDone = this.joiner!.shouldEnd()
    if (!creatorDone && !joinerDone) return false
    const losers: string[] = []
    if (creatorDone) losers.push(this.creator!.name)
    if (joinerDone) losers.push(this.joiner!.name)
    if (losers.length === 1) {
      const winner = losers[0] === this.creator!.name ? this.joiner! : this.creator!
      this.winnerId = winner.id
      this.log.add(this.gameRound, 'end', `${losers[0]} 已被击破！${winner.name} 获胜！`, this.creator!.nowHp, this.joiner!.nowHp)
    } else if (losers.length === 2) {
      this.log.add(this.gameRound, 'end', `${losers[0]} 和 ${losers[1]} 同时被击破！平局！`, this.creator!.nowHp, this.joiner!.nowHp)
    }
    this.finished = true
    return true
  }

  runFullBattle(): Battle {
    this.creator!.setNewMainCard()
    this.joiner!.setNewMainCard()
    this.onNewCardsSet()

    while (!this.finished) {
      this.resolveTurnsUntilCardBreak()
      if (this.checkGameEnd()) break
      // [亡语鞭尸修复] resolveTurnsUntilCardBreak 内部已调用 setNewMainCard，
      // 所以这里 shouldChangeCard() 通常为 false（新卡HP>0）。
      // 这两行是兜底：如果因某种原因未自动切换，则在此切换。
      if (this.creator!.shouldChangeCard() && !this.creator!.setNewMainCard()) break
      if (this.joiner!.shouldChangeCard() && !this.joiner!.setNewMainCard()) break
      // [亡语鞭尸修复] 用 justApplied 标记判断是否为新宣言，而非 shouldChangeCard()。
      // 因为 resolveTurnsUntilCardBreak 内部已调用 setNewMainCard（重置了HP），
      // shouldChangeCard() 此时返回 false，无法区分"刚切换新卡"和"无需切换"。
      const creatorBreak = this.creator!.justApplied
      const joinerBreak = this.joiner!.justApplied
      if (!creatorBreak && !joinerBreak) continue
      this.gameRound++
      this.creator!.gameRound = this.gameRound
      this.joiner!.gameRound = this.gameRound
      this.log.add(this.gameRound, 'card_set', `─── R${this.gameRound} 宣言 ───`)
      const cCardName = this.creator!.nowCard?.name ?? '??'
      const jCardName = this.joiner!.nowCard?.name ?? '??'
      const cPart = creatorBreak ? `${this.creator!.name} 宣言 [${cCardName}]` : `${this.creator!.name}[${cCardName}]`
      const jPart = joinerBreak ? `${this.joiner!.name} 宣言 [${jCardName}]` : `${this.joiner!.name}[${jCardName}]`
      this.log.add(this.gameRound, 'card_set',
        `${cPart} HP:${Math.max(0, this.creator!.nowHp)} | ${jPart} HP:${Math.max(0, this.joiner!.nowHp)}`,
        Math.max(0, this.creator!.nowHp), Math.max(0, this.joiner!.nowHp), undefined, this.creator!.nowCard ? { ...this.creator!.nowCard } : undefined, this.joiner!.nowCard ? { ...this.joiner!.nowCard } : undefined)
      if (creatorBreak) {
        const beforeEffs = new Set(this.creator!.effects.map(e => e.id + e.amount))
        const msg = this.creator!.nowCard!.onCardSet?.(this.creator!, this.joiner!) ?? ''
        const newEffs = this.creator!.effects.filter(e => !beforeEffs.has(e.id + e.amount)).map(e => e.displayName)
        const effDesc = newEffs.length > 0 ? `获得${newEffs.join('、')}` : ''
        const finalMsg = msg || effDesc
        if (finalMsg) this.log.add(this.gameRound, 'card_set', `[${this.creator!.nowCard!.name}] [${this.creator!.name}]${finalMsg}`)
        this.creator!.justApplied = false
      }
      if (joinerBreak) {
        const beforeEffs = new Set(this.joiner!.effects.map(e => e.id + e.amount))
        const msg = this.joiner!.nowCard!.onCardSet?.(this.joiner!, this.creator!) ?? ''
        const newEffs = this.joiner!.effects.filter(e => !beforeEffs.has(e.id + e.amount)).map(e => e.displayName)
        const effDesc = newEffs.length > 0 ? `获得${newEffs.join('、')}` : ''
        const finalMsg = msg || effDesc
        if (finalMsg) this.log.add(this.gameRound, 'card_set', `[${this.joiner!.nowCard!.name}] [${this.joiner!.name}]${finalMsg}`)
        this.joiner!.justApplied = false
      }
    }

    if (!this.finished) this.checkGameEnd()
    this.state = Battle.STATE_FINISHED
    return this
  }

  toData() {
    return {
      creatorId: this.creatorId,
      joinerId: this.joinerId,
      gameRound: this.gameRound,
      state: this.state,
      finished: this.finished,
      winnerId: this.winnerId,
      creatorNeedsCard: this.creator?.shouldChangeCard() ?? false,
      creator: this.creator?.toData(),
      joiner: this.joiner?.toData(),
      log: this.log.entries,
    }
  }
}
