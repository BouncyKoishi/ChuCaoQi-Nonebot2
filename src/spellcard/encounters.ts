import { ALL_CARDS } from './cards'
import type { CardData } from './engine'
import type { Encounter, StageType } from './expedition'

const NON_CARD_WEAK: CardData = {
  id: -100, cost: 0, name: '非符', cardHp: 4,
  atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
  description: '无',
}

const NON_CARD_MID: CardData = {
  id: -101, cost: 0, name: '非符', cardHp: 5,
  atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
  description: '无',
}

const NON_CARD_RUMIA: CardData = {
  id: -102, cost: 0, name: '非符', cardHp: 5,
  atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d2',
  description: '无',
}

const NON_CARD_CIRNO: CardData = {
  id: -103, cost: 0, name: '非符', cardHp: 6,
  atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d2',
  description: '无',
}

const NON_CARD_MEILING: CardData = {
  id: -104, cost: 0, name: '非符', cardHp: 7,
  atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d2',
  description: '无',
}

const NIGHT_BIRD: CardData = {
  id: -110, cost: 0, name: '夜符「Night Bird」', cardHp: 5,
  atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d3',
  description: '宣言时：获得[追击1]',
  onCardSet(user, _enemy) {
    user.appendEffect('Chase', 1)
    return `[${user.name}]获得追击！\n`
  },
}

const FAIRY_DANCE: CardData = {
  id: -111, cost: 0, name: '妖符「Fairy Dance」', cardHp: 6,
  atkPoint: '1d4', defPoint: '1d2', dodPoint: '1d3',
  description: '宣言时：获得[灵动1]',
  onCardSet(user, _enemy) {
    user.appendEffect('Agile', 1)
    return `[${user.name}]获得灵动！\n`
  },
}

const ICICLE_FALL: CardData = {
  id: -112, cost: 0, name: '冰符「Icicle Fall」', cardHp: 7,
  atkPoint: '1d5', defPoint: '1d2', dodPoint: '1d2',
  description: '宣言时：对方获得[迟缓1]',
  onCardSet(user, enemy) {
    enemy.appendEffect('Sluggish', 1)
    return `[${enemy.name}]被施加迟缓！\n`
  },
}

const FANGHUA: CardData = {
  id: -113, cost: 0, name: '华符「芳华绚烂」', cardHp: 7,
  atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d2',
  description: '宣言时：获得[强化2]',
  onCardSet(user, _enemy) {
    user.appendEffect('Strength', 2)
    return `[${user.name}]获得强化！\n`
  },
}

const DEMARCATION = ALL_CARDS.find(c => c.id === 13)!
const PERFECT_FREEZE = ALL_CARDS.find(c => c.id === 14)!
const RAINBOW_WINDCHIME = ALL_CARDS.find(c => c.id === 15)!
const SANHUA = ALL_CARDS.find(c => c.id === 16)!

const WEAK_POOL = ALL_CARDS.filter(c => c.cost <= 1 && c.id !== 0)
const MID_POOL = ALL_CARDS.filter(c => c.cost <= 2 && c.id !== 0)

interface EncounterTemplate {
  type: StageType
  buildCards: (rng: () => number) => CardData[]
  fixedDrop?: FixedDrop
}

const STAGE_TEMPLATES: EncounterTemplate[][] = [
  [
    { type: 'normal', buildCards: () => [{ ...NON_CARD_WEAK }] },
    { type: 'elite', buildCards: () => [NIGHT_BIRD] },
    { type: 'normal', buildCards: () => [{ ...NON_CARD_WEAK }] },
    { type: 'boss', buildCards: () => [{ ...NON_CARD_RUMIA }, DEMARCATION] },
  ],
  [
    { type: 'normal', buildCards: (rng) => pickFromPool(WEAK_POOL, 1, rng) },
    { type: 'elite', buildCards: () => [FAIRY_DANCE], fixedDrop: { type: 'dice' } },
    { type: 'normal', buildCards: (rng) => pickFromPool(WEAK_POOL, 2, rng) },
    { type: 'boss', buildCards: () => [{ ...NON_CARD_CIRNO }, PERFECT_FREEZE] },
  ],
  [
    { type: 'normal', buildCards: (rng) => pickFromPool(MID_POOL, 1, rng) },
    { type: 'elite', buildCards: () => [FANGHUA], fixedDrop: { type: 'newCard' } },
    { type: 'normal', buildCards: (rng) => pickFromPool(MID_POOL, 2, rng) },
    { type: 'boss', buildCards: () => [{ ...NON_CARD_MEILING }, RAINBOW_WINDCHIME, SANHUA] },
  ],
]

function pickFromPool(pool: CardData[], count: number, rng: () => number): CardData[] {
  const shuffled = [...pool].sort(() => rng() - 0.5)
  return shuffled.slice(0, count)
}

export function generateEncounter(
  stage: number,
  battle: number,
  rng: () => number,
): Encounter {
  const stageIdx = Math.min(stage, STAGE_TEMPLATES.length) - 1
  const templates = STAGE_TEMPLATES[stageIdx]
  const template = templates[Math.min(battle - 1, templates.length - 1)]

  const enemyCards = template.buildCards(rng)
  return { stage, battle, type: template.type, enemyCards, fixedDrop: template.fixedDrop }
}

export function getStageTemplate(stage: number) {
  const stageIdx = Math.min(stage, STAGE_TEMPLATES.length) - 1
  return STAGE_TEMPLATES[stageIdx]
}

export function getSpiritReward(type: StageType): number {
  return type === 'boss' ? 5 : type === 'elite' ? 3 : 2
}
