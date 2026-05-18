import type { Battler, CardData } from './engine'

export type EffectSlot = 'onCardSet' | 'onCardBreak' | 'onPassive'
export type PassiveTrigger = 'turnStart' | 'enemyCardBreak'
export type Rarity = 'common' | 'rare' | 'epic'

export interface EffectModule {
  id: string
  displayName: string
  slot: EffectSlot
  rarity: Rarity
  description: string
  apply: (user: Battler, enemy: Battler) => string
  trigger?: PassiveTrigger
}

export interface DiceUpgrade {
  id: string
  displayName: string
  rarity: Rarity
  description: string
  apply: (card: ExpeditionCard) => void
}

export interface StatUpgrade {
  id: string
  displayName: string
  rarity: Rarity
  description: string
  apply: (card: ExpeditionCard) => void
}

export interface ExtraSlotReward {
  id: string
  displayName: string
  rarity: Rarity
  description: string
  slot: EffectSlot
}

export type Reward = EffectModule | DiceUpgrade | StatUpgrade | ExtraSlotReward

export interface CardEffects {
  onCardSet: EffectModule[]
  onCardBreak: EffectModule[]
  onPassive: EffectModule[]
}

export interface SlotCapacity {
  onCardSet: number
  onCardBreak: number
  onPassive: number
}

export interface ExpeditionCard {
  name: string
  isNonCard: boolean
  cardHp: number
  maxCardHp: number
  atkPoint: string
  defPoint: string
  dodPoint: string
  currentHp: number
  effects: CardEffects
  slotCapacity: SlotCapacity
}

export type StageType = 'normal' | 'elite' | 'boss'

export interface FixedDrop {
  type: 'dice' | 'newCard'
}

export interface Encounter {
  stage: number
  battle: number
  type: StageType
  enemyCards: CardData[]
  fixedDrop?: FixedDrop
}

export interface ShopItem {
  id: string
  name: string
  description: string
  price: number
  reward: Reward
}

export interface ExpeditionState {
  cards: ExpeditionCard[]
  spirit: number
  currentStage: number
  currentBattle: number
  battlesPerStage: number
  totalStages: number
  finished: boolean
  victories: number
}

function emptyEffects(): CardEffects {
  return { onCardSet: [], onCardBreak: [], onPassive: [] }
}

function spellCardCapacity(): SlotCapacity {
  return { onCardSet: 1, onCardBreak: 1, onPassive: 1 }
}

function nonCardCapacity(): SlotCapacity {
  return { onCardSet: 0, onCardBreak: 0, onPassive: 0 }
}

const INITIAL_NON_CARD: Omit<ExpeditionCard, 'effects' | 'slotCapacity'> = {
  name: '非符',
  isNonCard: true,
  cardHp: 4,
  maxCardHp: 4,
  atkPoint: '1d4',
  defPoint: '1d2',
  dodPoint: '1d2',
  currentHp: 4,
}

export const BASE_PANELS: Omit<ExpeditionCard, 'currentHp' | 'effects' | 'isNonCard' | 'slotCapacity'>[] = [
  { name: '霊符「梦想封印」', cardHp: 7, maxCardHp: 7, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d4' },
  { name: '夢符「封魔陣」', cardHp: 9, maxCardHp: 9, atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2' },
  { name: '恋符「Master Spark」', cardHp: 5, maxCardHp: 5, atkPoint: '2d4+1', defPoint: '1', dodPoint: '1' },
  { name: '魔符「Stardust Reverie」', cardHp: 7, maxCardHp: 7, atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d3' },
]

export const INITIAL_CARD_EFFECTS: Record<string, { slot: EffectSlot; id: string; displayName: string; rarity: Rarity; description: string; apply: (user: Battler, enemy: Battler) => string }[]> = {
  '霊符「梦想封印」': [{
    id: 'init_trace1', displayName: '宣言·追踪', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时获得[追踪1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Trace', 1); return `[${user.name}]获得追踪！\n` },
  }],
  '夢符「封魔陣」': [{
    id: 'init_str_border', displayName: '宣言·强化结界', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时展开3回合[强化结界1]',
    apply(user: Battler, _enemy: Battler) { user.appendBorder('Strength', 1, 3); return `[${user.name}]展开强化结界！\n` },
  }],
  '魔符「Stardust Reverie」': [{
    id: 'init_combo1', displayName: '宣言·连击', slot: 'onCardSet', rarity: 'rare',
    description: '宣言时获得[连击1]',
    apply(user: Battler, _enemy: Battler) { user.appendEffect('Combo', 1); return `[${user.name}]获得连击！\n` },
  }],
}

export const NEW_CARD_POOL: Omit<ExpeditionCard, 'currentHp' | 'effects' | 'isNonCard' | 'slotCapacity'>[] = [
  { name: '火符「Agni Shine」', cardHp: 6, maxCardHp: 6, atkPoint: '1d5', defPoint: '1d2', dodPoint: '1d2' },
  { name: '幻符「Killing Doll」', cardHp: 6, maxCardHp: 6, atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d3' },
  { name: '红符「Scarlet Shoot」', cardHp: 7, maxCardHp: 7, atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d4' },
  { name: '禁忌「Laevatein」', cardHp: 5, maxCardHp: 5, atkPoint: '2d4', defPoint: '1', dodPoint: '1d2' },
]

export function createSpellCard(panel: Omit<ExpeditionCard, 'currentHp' | 'effects' | 'isNonCard' | 'slotCapacity'>): ExpeditionCard {
  return { ...panel, isNonCard: false, currentHp: panel.cardHp, effects: emptyEffects(), slotCapacity: spellCardCapacity() }
}

export function createNonCard(): ExpeditionCard {
  return { ...INITIAL_NON_CARD, effects: emptyEffects(), slotCapacity: nonCardCapacity() }
}

function mergeEffects(effects: EffectModule[]): ((user: Battler, enemy: Battler) => string) | undefined {
  if (effects.length === 0) return undefined
  return (user: Battler, enemy: Battler) => {
    let msg = ''
    for (const eff of effects) { msg += eff.apply(user, enemy) }
    return msg
  }
}

export function toCardData(ec: ExpeditionCard): CardData {
  const turnStartEffects = ec.effects.onPassive.filter(e => !e.trigger || e.trigger === 'turnStart')
  const enemyCardBreakEffects = ec.effects.onPassive.filter(e => e.trigger === 'enemyCardBreak')

  return {
    id: -1,
    cost: 0,
    name: ec.name,
    cardHp: ec.currentHp,
    atkPoint: ec.atkPoint,
    defPoint: ec.defPoint,
    dodPoint: ec.dodPoint,
    description: '',
    onCardSet: mergeEffects(ec.effects.onCardSet),
    onCardBreak: mergeEffects(ec.effects.onCardBreak),
    onTurnStart: mergeEffects(turnStartEffects),
    onEnemyCardBreak: mergeEffects(enemyCardBreakEffects),
  }
}

export function healNonCard(cards: ExpeditionCard[]) {
  for (const c of cards) {
    if (c.isNonCard) c.currentHp = c.maxCardHp
  }
}

export function healAllForNewStage(cards: ExpeditionCard[]) {
  for (const c of cards) { c.currentHp = c.maxCardHp }
}

export function addSlotCapacity(card: ExpeditionCard, slot: EffectSlot) {
  card.slotCapacity[slot]++
}

export function canAddEffectToSlot(card: ExpeditionCard, slot: EffectSlot): boolean {
  return card.effects[slot].length < card.slotCapacity[slot]
}

export function addEffectToCard(card: ExpeditionCard, effect: EffectModule): { replaced: EffectModule | null } {
  const slot = effect.slot
  if (card.effects[slot].length < card.slotCapacity[slot]) {
    card.effects[slot].push(effect)
    return { replaced: null }
  }
  const oldest = card.effects[slot][0]
  card.effects[slot].shift()
  card.effects[slot].push(effect)
  return { replaced: oldest }
}
