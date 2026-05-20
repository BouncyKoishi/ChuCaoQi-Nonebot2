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
  atkPoint: '1d4', defPoint: '1d3', dodPoint: '1d2',
  description: '无',
}

const NON_CARD_STRONG: CardData = {
  id: -102, cost: 0, name: '非符', cardHp: 6,
  atkPoint: '1d5', defPoint: '1d3', dodPoint: '1d3',
  description: '无',
}

const MAGIC_CIRCLE: CardData = {
  id: -110, cost: 0, name: '魔法阵', cardHp: 6,
  atkPoint: '1d4', defPoint: '1d4', dodPoint: '1d1-1',
  description: '回合结束时增加一个攻击骰子(上限6d4)',
  onTurnEnd(user, _enemy) {
    const current = user.nowCard!.atkPoint
    const match = current.match(/^(\d+)d4$/)
    if (match) {
      const count = Math.min(parseInt(match[1]) + 1, 6)
      user.nowCard!.atkPoint = `${count}d4`
      return `[${user.name}]魔法阵蓄力！攻击骰子变为${count}d4\n`
    }
    return ''
  },
}

const WEAK_POOL = ALL_CARDS.filter(c => c.cost === 1 && c.id !== 0)
const MID_POOL = ALL_CARDS.filter(c => c.cost >= 2 && c.cost <= 3 && c.id !== 0)
const STRONG_POOL = ALL_CARDS.filter(c => c.cost >= 3 && c.cost <= 4 && c.id !== 0)

function charPool(character: string, excludeIds: number[] = []): CardData[] {
  return ALL_CARDS.filter(c => c.character === character && !excludeIds.includes(c.id))
}

function pickFromPool(pool: CardData[], count: number, rng: () => number, excludeIds: number[] = []): CardData[] {
  const filtered = pool.filter(c => !excludeIds.includes(c.id))
  const shuffled = [...filtered].sort(() => rng() - 0.5)
  return shuffled.slice(0, count).map(c => ({ ...c }))
}

function pickFromCharPool(character: string, count: number, rng: () => number, excludeIds: number[] = []): CardData[] {
  const pool = charPool(character, excludeIds)
  const shuffled = [...pool].sort(() => rng() - 0.5)
  return shuffled.slice(0, count).map(c => ({ ...c }))
}

interface EncounterTemplate {
  type: StageType
  buildCards: (rng: () => number) => CardData[]
  fixedDrop?: { type: 'dice' | 'newCard' }
}

const STAGE_TEMPLATES: EncounterTemplate[][] = [
  [
    { type: 'normal', buildCards: () => [{ ...NON_CARD_WEAK }] },
    { type: 'elite', buildCards: () => [({ ...ALL_CARDS.find(c => c.id === 26)! })] },
    { type: 'normal', buildCards: (rng) => pickFromPool(WEAK_POOL, 1, rng) },
    { type: 'boss', buildCards: (rng) => [{ ...NON_CARD_WEAK }, ...pickFromCharPool('rumia', 1, rng, [26])] },
  ],
  [
    { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_WEAK }, ...pickFromPool(WEAK_POOL, 1, rng)] },
    { type: 'elite', buildCards: () => [({ ...ALL_CARDS.find(c => c.id === 29)! })], fixedDrop: { type: 'dice' } },
    { type: 'normal', buildCards: (rng) => pickFromPool(WEAK_POOL, 2, rng) },
    { type: 'boss', buildCards: (rng) => [{ ...NON_CARD_MID }, ...pickFromCharPool('cirno', 2, rng, [29])] },
  ],
  [
    { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_MID }, ...pickFromPool(MID_POOL, 1, rng)] },
    { type: 'elite', buildCards: () => [({ ...ALL_CARDS.find(c => c.id === 31)! })], fixedDrop: { type: 'newCard' } },
    { type: 'normal', buildCards: (rng) => [...pickFromPool(WEAK_POOL, 1, rng), ...pickFromPool(MID_POOL, 1, rng)] },
    { type: 'boss', buildCards: (rng) => pickFromCharPool('meiling', 3, rng, [31]) },
  ],
  [
    { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_MID }, ...pickFromPool(WEAK_POOL, 1, rng), ...pickFromPool(MID_POOL, 1, rng)] },
    { type: 'elite', buildCards: () => [{ ...NON_CARD_MID }, { ...MAGIC_CIRCLE }], fixedDrop: { type: 'dice' } },
    { type: 'normal', buildCards: (rng) => [...pickFromPool(WEAK_POOL, 1, rng), ...pickFromPool(MID_POOL, 2, rng)] },
    { type: 'boss', buildCards: (rng) => pickFromCharPool('patchouli', 3, rng) },
  ],
  [
    { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_STRONG }, ...pickFromPool(STRONG_POOL, 2, rng)] },
    { type: 'elite', buildCards: () => [({ ...ALL_CARDS.find(c => c.id === 48)! }), ({ ...ALL_CARDS.find(c => c.id === 49)! })], fixedDrop: { type: 'newCard' } },
    { type: 'normal', buildCards: (rng) => pickFromPool(STRONG_POOL, 3, rng) },
    { type: 'boss', buildCards: (rng) => pickFromCharPool('sakuya', 3, rng, [48, 49]) },
  ],
  [
    { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_STRONG }, ...pickFromPool(STRONG_POOL, 3, rng)] },
    { type: 'elite', buildCards: () => [{ ...NON_CARD_STRONG }, ({ ...ALL_CARDS.find(c => c.id === 52)! })], fixedDrop: { type: 'dice' } },
    { type: 'normal', buildCards: (rng) => pickFromPool(STRONG_POOL, 4, rng) },
    { type: 'boss', buildCards: () => [53, 54, 55, 56, 57].map(id => ({ ...ALL_CARDS.find(c => c.id === id)! })) },
  ],
]

const EX_STAGE_TEMPLATES: EncounterTemplate[] = [
  { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_STRONG }, { ...NON_CARD_STRONG }, ...pickFromPool(STRONG_POOL, 3, rng)] },
  { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_STRONG }, ...pickFromPool(STRONG_POOL, 4, rng)] },
  { type: 'elite', buildCards: () => [45, 46, 47].map(id => ({ ...ALL_CARDS.find(c => c.id === id)! })), fixedDrop: { type: 'dice' } },
  { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_STRONG }, { ...NON_CARD_STRONG }, ...pickFromPool(STRONG_POOL, 3, rng)] },
  { type: 'normal', buildCards: (rng) => [{ ...NON_CARD_STRONG }, ...pickFromPool(STRONG_POOL, 4, rng)] },
  { type: 'shop', buildCards: () => [] },
  { type: 'boss', buildCards: () => [58, 59, 24, 12, 60, 25, 61, 62, 63, 64].map(id => ({ ...ALL_CARDS.find(c => c.id === id)! })) },
]

export function generateExEncounter(battle: number, rng: () => number): Encounter {
  const template = EX_STAGE_TEMPLATES[Math.min(battle - 1, EX_STAGE_TEMPLATES.length - 1)]
  const enemyCards = template.buildCards(rng)
  return { stage: 7, battle, type: template.type, enemyCards, fixedDrop: template.fixedDrop }
}

export function getExStageTemplate() {
  return EX_STAGE_TEMPLATES
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

export function generateNewCardDrop(stage: number, rng: () => number): { name: string; cardHp: number; maxCardHp: number; atkPoint: string; defPoint: string; dodPoint: string } {
  const pool = stage <= 2 ? WEAK_POOL : stage <= 4 ? MID_POOL : STRONG_POOL
  const card = pool[Math.floor(rng() * pool.length)]
  return { name: card.name, cardHp: card.cardHp, maxCardHp: card.cardHp, atkPoint: card.atkPoint, defPoint: card.defPoint, dodPoint: card.dodPoint }
}
