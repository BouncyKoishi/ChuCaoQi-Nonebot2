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
  atkPoint: string
  defPoint: string
  dodPoint: string
  description: string
  onCardSet?: (user: Battler, enemy: Battler) => string
  onCardBreak?: (user: Battler, enemy: Battler) => string
  onTurnStart?: (user: Battler, enemy: Battler) => string
  onTurnEnd?: (user: Battler, enemy: Battler) => string
  onEnemyCardBreak?: (user: Battler, enemy: Battler) => string
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
  breakSource?: 'battle' | 'effect'
}

export interface LogEntry {
  round: number
  phase: string
  message: string
  creatorHp?: number
  joinerHp?: number
  visual?: VisualData
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
  const diceRegex = /(\d{1,2})d(\d{1,2})/g
  let resultStr = diceStr
  let match: RegExpExecArray | null
  while ((match = diceRegex.exec(diceStr)) !== null) {
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

  stack(amount: number) { this.amount += amount }
  reduce(amount: number) { this.amount = Math.max(0, this.amount - amount) }
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
  lastHurtType: 'battle' | 'effect' | '' = ''
  gameRound: number = 0
  spiritGained: number = 0

  constructor(id: number, name: string) {
    this.id = id
    this.name = name
  }

  setEnemy(enemy: Battler) { this.enemy = enemy }

  appendEffect(effectId: string, amount: number) {
    if (!effectId) return
    const ALL_EFFECTS = getEffectsRegistry()
    for (const e of this.effects) {
      if (e.id === effectId) { e.stack(amount); return }
    }
    const Cls = ALL_EFFECTS[effectId]
    if (Cls) {
      const effect = new Cls(amount)
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
    this.effects = this.effects.filter(e => e.amount > 0)
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
    this.effects = this.effects.filter(e => e.amount > 0)
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
    const dodgeProb = (this.dodge + enemyAtk) > 0 ? this.dodge / (this.dodge + enemyAtk) : 0
    let dodSuccess = rng.next() < dodgeProb
    const [dodSuccess1, dodMsg] = this.runEffects('onDodgeSuccessJudge', dodSuccess) as [boolean, string]
    dodSuccess = dodSuccess1

    let defSuccess = true
    const [defSuccess1, defMsg] = this.runEffects('onDefenceSuccessJudge', defSuccess) as [boolean, string]
    defSuccess = defSuccess1

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

    const dodgeInfo = `${this.name} 闪避率:${(dodgeProb * 100).toFixed(0)}% ${dodSuccess ? '闪避成功！' : '闪避失败'}\n`
    const calcInfo = dodgeInfo + dodMsg + defMsg + hurtMsg + enemyHurtMsg + `${this.name} 预计受伤:${hurt}\n`
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
  add(round: number, phase: string, message: string, creatorHp?: number, joinerHp?: number, visual?: VisualData) {
    const entry: LogEntry = { round, phase, message }
    if (creatorHp !== undefined) entry.creatorHp = creatorHp
    if (joinerHp !== undefined) entry.joinerHp = joinerHp
    if (visual) entry.visual = visual
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
  log = new BattleLog()
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

    if (this.joiner!.nowCard === null) {
      const aiIdx = this.autoChooseCard(this.joiner!)
      if (aiIdx >= 0) this.applyCard(this.joiner!, aiIdx)
    }

    this.onNewCardsSet()

    while (!this.finished) {
      this.resolveTurnsUntilCardBreak()
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
  }

  onNewCardsSet() {
    this.gameRound++
    this.creator!.gameRound = this.gameRound
    this.joiner!.gameRound = this.gameRound
    this.log.add(this.gameRound, 'card_set',
      `${this.creator!.name} 宣言 [${this.creator!.nowCard?.name ?? '??'}] HP:${this.creator!.nowHp} | ${this.joiner!.name} 宣言 [${this.joiner!.nowCard?.name ?? '??'}] HP:${this.joiner!.nowHp}`,
      this.creator!.nowHp, this.joiner!.nowHp)
    const msg1 = this.creator!.nowCard!.onCardSet?.(this.creator!, this.joiner!) ?? ''
    if (msg1) this.log.add(this.gameRound, 'card_set', `[${this.creator!.nowCard!.name}] ${msg1}`)
    if (this.joiner!.shouldChangeCard()) return
    const msg2 = this.joiner!.nowCard!.onCardSet?.(this.joiner!, this.creator!) ?? ''
    if (msg2) this.log.add(this.gameRound, 'card_set', `[${this.joiner!.nowCard!.name}] ${msg2}`)
  }

  onJoinerNewCard() {
    this.gameRound++
    this.creator!.gameRound = this.gameRound
    this.joiner!.gameRound = this.gameRound
    this.log.add(this.gameRound, 'card_set',
      `${this.creator!.name}[${this.creator!.nowCard?.name ?? '??'}] HP:${this.creator!.nowHp} | ${this.joiner!.name} 宣言 [${this.joiner!.nowCard?.name ?? '??'}] HP:${this.joiner!.nowHp}`,
      this.creator!.nowHp, this.joiner!.nowHp)
    const msg = this.joiner!.nowCard!.onCardSet?.(this.joiner!, this.creator!) ?? ''
    if (msg) this.log.add(this.gameRound, 'card_set', `[${this.joiner!.nowCard!.name}] ${msg}`)
  }

  resolveTurnsUntilCardBreak() {
    while (!this.finished) {
      if (this.creator!.shouldChangeCard() || this.joiner!.shouldChangeCard()) break
      this.resolveSingleTurn()
    }
    const brokenSet = new Set<Battler>()
    if (this.creator!.shouldChangeCard()) { this.handleCardBreak(this.creator!); brokenSet.add(this.creator!) }
    if (this.joiner!.shouldChangeCard()) { this.handleCardBreak(this.joiner!); brokenSet.add(this.joiner!) }
    let recheck = true
    while (recheck) {
      recheck = false
      if (this.creator!.shouldChangeCard() && this.creator!.nowHp <= 0 && !brokenSet.has(this.creator!)) {
        this.handleCardBreak(this.creator!)
        brokenSet.add(this.creator!)
        recheck = true
      }
      if (this.joiner!.shouldChangeCard() && this.joiner!.nowHp <= 0 && !brokenSet.has(this.joiner!)) {
        this.handleCardBreak(this.joiner!)
        brokenSet.add(this.joiner!)
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
    const cMsg = this.creator!.battleHurt(cHurt)
    const jMsg = this.joiner!.battleHurt(jHurt)
    this.log.add(this.gameRound, 'hurt', cMsg + jMsg, this.creator!.nowHp, this.joiner!.nowHp, {
      creatorHurt: prevCreatorHp - this.creator!.nowHp,
      joinerHurt: prevJoinerHp - this.joiner!.nowHp,
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

  handleCardBreak(battler: Battler) {
    const whoBroke = battler === this.creator ? 'creator' : 'joiner'
    const brokenCardName = battler.nowCard?.name ?? '??'
    this.log.add(this.gameRound, 'card_break', `${battler.name}[${brokenCardName}] 的符卡被击破！`, this.creator!.nowHp, this.joiner!.nowHp, {
      whoBroke: whoBroke as 'creator' | 'joiner',
      breakSource: battler.lastHurtType || undefined,
    })
    if (!battler.shouldEnd()) {
      const msg = battler.nowCard!.onCardBreak?.(battler, battler.enemy!) ?? ''
      if (msg) this.log.add(this.gameRound, 'card_break', `[${brokenCardName}] ${msg}`, this.creator!.nowHp, this.joiner!.nowHp)
    }
    battler.effects = battler.effects.filter(e => e instanceof Border)
    battler.states = []
    const enemy = battler.enemy!
    if (!enemy.shouldEnd() && enemy.nowCard?.onEnemyCardBreak) {
      const killMsg = enemy.nowCard.onEnemyCardBreak(enemy, battler)
      if (killMsg) this.log.add(this.gameRound, 'card_break', killMsg, this.creator!.nowHp, this.joiner!.nowHp)
    }
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
      const creatorBreak = this.creator!.shouldChangeCard()
      const joinerBreak = this.joiner!.shouldChangeCard()
      if (creatorBreak && !this.creator!.setNewMainCard()) break
      if (joinerBreak && !this.joiner!.setNewMainCard()) break
      this.gameRound++
      this.creator!.gameRound = this.gameRound
      this.joiner!.gameRound = this.gameRound
      const cCardName = this.creator!.nowCard?.name ?? '??'
      const jCardName = this.joiner!.nowCard?.name ?? '??'
      const cPart = creatorBreak ? `${this.creator!.name} 宣言 [${cCardName}]` : `${this.creator!.name}[${cCardName}]`
      const jPart = joinerBreak ? `${this.joiner!.name} 宣言 [${jCardName}]` : `${this.joiner!.name}[${jCardName}]`
      this.log.add(this.gameRound, 'card_set',
        `${cPart} HP:${this.creator!.nowHp} | ${jPart} HP:${this.joiner!.nowHp}`,
        this.creator!.nowHp, this.joiner!.nowHp)
      if (creatorBreak) {
        const msg = this.creator!.nowCard!.onCardSet?.(this.creator!, this.joiner!) ?? ''
        if (msg) this.log.add(this.gameRound, 'card_set', `[${this.creator!.nowCard!.name}] ${msg}`)
      }
      if (joinerBreak) {
        const msg = this.joiner!.nowCard!.onCardSet?.(this.joiner!, this.creator!) ?? ''
        if (msg) this.log.add(this.gameRound, 'card_set', `[${this.joiner!.nowCard!.name}] ${msg}`)
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
