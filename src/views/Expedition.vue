<template>
  <div class="expedition-container">
    <template v-if="phase === 'start'">
      <div class="start-section">
        <h3>符卡锻造远征</h3>
        <p class="section-desc">选择初始符卡面板，开始远征</p>
        <div class="panel-cards">
          <el-card v-for="(panel, idx) in basePanels" :key="idx" class="panel-card"
            :class="{ selected: selectedPanelIdx === idx }" @click="selectedPanelIdx = idx" shadow="hover">
            <div class="panel-name">{{ panel.name }}</div>
            <div class="panel-stats">
              <span>HP:{{ panel.cardHp }}</span><span>ATK:{{ diceRange(panel.atkPoint) }}</span>
              <span>DEF:{{ diceRange(panel.defPoint) }}</span><span>DOD:{{ diceRange(panel.dodPoint) }}</span>
            </div>
            <div v-if="INITIAL_CARD_EFFECTS[panel.name]" class="panel-effect">
              <template v-for="(eff, ei) in INITIAL_CARD_EFFECTS[panel.name]" :key="eff.id">
                <template v-for="(seg, si) in parseDescription(eff.description)" :key="`${ei}_${si}`">
                  <el-tooltip v-if="seg.type === 'effect'" :content="seg.effectDesc" placement="top">
                    <el-tag size="small" type="success" class="inline-effect-tag">{{ seg.text }}</el-tag>
                  </el-tooltip>
                  <span v-else class="panel-effect-text">{{ seg.text }}</span>
                </template>
              </template>
            </div>
          </el-card>
        </div>
        <el-button type="primary" size="large" @click="startExpedition" :disabled="selectedPanelIdx === -1">开始远征</el-button>
      </div>
    </template>

    <template v-if="phase === 'encounter'">
      <div class="encounter-section">
        <div class="stage-info">
          <el-tag type="info">第{{ state.currentStage }}面 / 第{{ state.currentBattle }}战</el-tag>
          <el-tag :type="encounterType === 'boss' ? 'danger' : encounterType === 'elite' ? 'warning' : ''">
            {{ encounterType === 'boss' ? 'BOSS' : encounterType === 'elite' ? '精英' : '普通' }}
          </el-tag>
          <el-tag type="success">灵力: {{ state.spirit }}</el-tag>
        </div>

        <div class="vs-preview">
          <div class="preview-side my-side">
            <h4>我的阵容</h4>
            <div class="preview-cards">
              <div v-for="(card, idx) in state.cards" :key="idx" class="preview-card" :class="{ noncard: card.isNonCard }">
                <div class="pc-name">{{ card.name }}</div>
                <div class="pc-hp">HP: {{ card.currentHp }}/{{ card.maxCardHp }}</div>
                <div class="pc-stats">ATK:{{ diceRange(card.atkPoint) }} DEF:{{ diceRange(card.defPoint) }} DOD:{{ diceRange(card.dodPoint) }}</div>
                <div class="pc-effects">
                  <el-tooltip v-for="eff in allEffects(card)" :key="eff.id" :content="eff.description" placement="top">
                    <el-tag size="small" :type="slotTagType(eff.slot)">
                      {{ eff.displayName }}
                    </el-tag>
                  </el-tooltip>
                </div>
              </div>
            </div>
          </div>
          <div class="vs-divider">VS</div>
          <div class="preview-side enemy-side">
            <h4>敌方阵容</h4>
            <div class="preview-cards">
              <div v-for="(card, idx) in enemyCards" :key="idx" class="preview-card enemy">
                <div class="pc-name">{{ card.name }}</div>
                <div class="pc-hp">HP: {{ card.cardHp }}</div>
                <div class="pc-stats">ATK:{{ diceRange(card.atkPoint) }} DEF:{{ diceRange(card.defPoint) }} DOD:{{ diceRange(card.dodPoint) }}</div>
                <div v-if="card.description && card.description !== '无'" class="pc-desc">
                  <template v-for="(seg, si) in parseDescription(card.description)" :key="si">
                    <el-tooltip v-if="seg.type === 'effect'" :content="seg.effectDesc" placement="top">
                      <el-tag size="small" type="info" class="inline-effect-tag">{{ seg.text }}</el-tag>
                    </el-tooltip>
                    <span v-else>{{ seg.text }}</span>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>

        <el-button type="primary" size="large" @click="startBattle">进入战斗</el-button>
      </div>
    </template>

    <template v-if="phase === 'result'">
      <div class="result-section">
        <el-tag :type="battleWon ? 'success' : 'danger'" size="large" effect="dark">
          {{ battleWon ? '胜利！' : '失败...' }}
        </el-tag>

        <div class="battle-summary">
          <h4>战斗总结</h4>
          <div v-if="spiritGainedInBattle > 0" class="spirit-gained-info">获得 {{ spiritGainedInBattle }} 灵力</div>
          <div class="summary-cards">
            <div v-for="(info, idx) in battleSummary" :key="idx" class="summary-card" :class="{ broken: info.broken }">
              <div class="sc-name">{{ info.name }}</div>
              <div class="sc-hp">
                <span v-if="info.broken" class="sc-broken">被击破</span>
                <span v-else>HP: {{ info.hpAfter }}/{{ info.maxHp }} <span class="sc-damage" v-if="info.damage > 0">(-{{ info.damage }})</span></span>
              </div>
            </div>
          </div>
        </div>

        <el-divider class="log-divider">
          <el-button link size="small" @click="logCollapsed = !logCollapsed">详细日志 {{ logCollapsed ? '▸' : '▾' }}</el-button>
        </el-divider>
        <div class="battle-log" v-show="!logCollapsed">
          <div v-for="(entry, index) in battleLog" :key="index" class="log-entry" :class="'log-phase-' + entry.phase">
            <el-tag size="small" class="log-round">R{{ entry.round }}</el-tag>
            <span class="log-message">{{ entry.message }}</span>
          </div>
        </div>

        <div class="result-actions" v-if="battleWon">
          <el-button type="primary" @click="goToReward">领取奖励</el-button>
        </div>
        <div class="result-actions" v-else>
          <el-button type="primary" @click="resetExpedition">重新开始</el-button>
        </div>
      </div>
    </template>

    <template v-if="phase === 'fixedDrop'">
      <div class="fixed-drop-section">
        <h3>固定掉落！</h3>
        <template v-if="currentFixedDrop?.type === 'dice' && fixedDropItem">
          <div class="fixed-drop-item">
            <div class="fd-name">
              {{ fixedDropItem.displayName }}
              <el-tag size="small" :type="fixedDropItem.rarity === 'epic' ? 'warning' : fixedDropItem.rarity === 'rare' ? 'danger' : 'info'">{{ fixedDropItem.rarity === 'epic' ? '史诗' : fixedDropItem.rarity === 'rare' ? '稀有' : '普通' }}</el-tag>
            </div>
            <div class="fd-desc">
              <template v-for="(seg, si) in parseDescription(fixedDropItem.description)" :key="si">
                <el-tooltip v-if="seg.type === 'effect'" :content="seg.effectDesc" placement="top">
                  <el-tag size="small" type="success" class="inline-effect-tag">{{ seg.text }}</el-tag>
                </el-tooltip>
                <span v-else>{{ seg.text }}</span>
              </template>
            </div>
          </div>
          <div class="reward-target">
            <h4>选择装配到：</h4>
            <div class="target-cards">
              <div v-for="(card, idx) in state.cards" :key="idx" class="target-card"
                :class="{ selected: fixedDropTargetIdx === idx, disabled: !canApplyToCard(card, fixedDropItem) }"
                @click="canApplyToCard(card, fixedDropItem) && (fixedDropTargetIdx = idx)">
                <div class="tc-name">{{ card.name }}</div>
                <div class="tc-hp">HP: {{ card.currentHp }}/{{ card.maxCardHp }}</div>
                <div class="tc-stats">ATK:{{ diceRange(card.atkPoint) }} DEF:{{ diceRange(card.defPoint) }} DOD:{{ diceRange(card.dodPoint) }}</div>
                <div v-if="card.isNonCard" class="tc-extra-cost">装配到非符需额外3灵力</div>
              </div>
            </div>
          </div>
          <div class="reward-actions">
            <el-button type="primary" @click="confirmFixedDrop" :disabled="fixedDropTargetIdx === -1">确认装配</el-button>
            <el-button @click="skipFixedDrop">跳过</el-button>
          </div>
        </template>
        <template v-if="currentFixedDrop?.type === 'newCard' && fixedDropNewCard">
          <div class="fixed-drop-item new-card-preview">
            <div class="fd-name">{{ fixedDropNewCard.name }}</div>
            <div class="fd-stats">
              <span>HP:{{ fixedDropNewCard.cardHp }}</span>
              <span>ATK:{{ diceRange(fixedDropNewCard.atkPoint) }}</span>
              <span>DEF:{{ diceRange(fixedDropNewCard.defPoint) }}</span>
              <span>DOD:{{ diceRange(fixedDropNewCard.dodPoint) }}</span>
            </div>
          </div>
          <div class="reward-actions">
            <el-button type="primary" @click="confirmFixedDrop">加入阵容</el-button>
            <el-button @click="skipFixedDrop">跳过</el-button>
          </div>
        </template>
      </div>
    </template>

    <template v-if="phase === 'reward'">
      <div class="reward-section">
        <h3>选择一个奖励 <el-tag type="success">灵力: {{ state.spirit }}</el-tag></h3>
        <div class="reward-cards">
          <el-card v-for="(reward, idx) in currentRewards" :key="idx" class="reward-card"
            :class="{ selected: selectedRewardIdx === idx }" @click="selectReward(idx)" shadow="hover">
            <div class="reward-name">
              {{ reward.displayName }}
              <el-tag size="small" :type="reward.rarity === 'epic' ? 'warning' : reward.rarity === 'rare' ? 'danger' : 'info'">{{ reward.rarity === 'epic' ? '史诗' : reward.rarity === 'rare' ? '稀有' : '普通' }}</el-tag>
            </div>
            <div class="reward-desc">
              <template v-for="(seg, si) in parseDescription(reward.description)" :key="si">
                <el-tooltip v-if="seg.type === 'effect'" :content="seg.effectDesc" placement="top">
                  <el-tag size="small" type="success" class="inline-effect-tag">{{ seg.text }}</el-tag>
                </el-tooltip>
                <span v-else>{{ seg.text }}</span>
              </template>
            </div>
            <div class="reward-slot" v-if="'slot' in reward">
              <el-tag size="small" type="warning">{{ slotLabel(reward.slot) }}</el-tag>
            </div>
          </el-card>
        </div>

        <div v-if="selectedRewardIdx >= 0" class="reward-target">
          <h4>装配到：</h4>
          <div class="target-cards">
            <div v-for="(card, idx) in state.cards" :key="idx" class="target-card"
              :class="{ selected: targetCardIdx === idx, disabled: !canApplyToCard(card, currentRewards[selectedRewardIdx]) }"
              @click="canApplyToCard(card, currentRewards[selectedRewardIdx]) && (targetCardIdx = idx)">
              <div class="tc-name">{{ card.name }}</div>
              <div class="tc-hp">HP: {{ card.currentHp }}/{{ card.maxCardHp }}</div>
              <div class="tc-stats">ATK:{{ diceRange(card.atkPoint) }} DEF:{{ diceRange(card.defPoint) }} DOD:{{ diceRange(card.dodPoint) }}</div>
              <div class="tc-effects">
                <el-tooltip v-for="eff in allEffects(card)" :key="eff.id" :content="eff.description" placement="top">
                  <el-tag size="small" :type="slotTagType(eff.slot)">
                    {{ eff.displayName }}
                  </el-tag>
                </el-tooltip>
              </div>
              <div v-if="card.isNonCard" class="tc-extra-cost">装配到非符需额外3灵力</div>
            </div>
          </div>
        </div>

        <div class="reward-actions">
          <el-button type="primary" @click="confirmReward" :disabled="selectedRewardIdx === -1 || targetCardIdx === -1">确认装配</el-button>
          <el-button @click="skipReward">跳过</el-button>
        </div>

        <el-dialog v-model="replaceConfirmVisible" title="效果替换确认" width="420px">
          <p v-if="replaceSlotInfo">
            该槽位已满，请选择要替换的效果：
          </p>
          <div v-if="replaceSlotInfo" class="replace-options">
            <div v-for="(eff, ei) in replaceSlotInfo.existingEffects" :key="ei" class="replace-option"
              :class="{ selected: replaceChoiceIdx === ei }" @click="replaceChoiceIdx = ei">
              <el-tag size="small" type="danger">{{ eff.displayName }}</el-tag>
              <span class="replace-option-desc">
                <template v-for="(seg, si) in parseDescription(eff.description)" :key="si">
                  <el-tooltip v-if="seg.type === 'effect'" :content="seg.effectDesc" placement="top">
                    <el-tag size="small" type="success" class="inline-effect-tag">{{ seg.text }}</el-tag>
                  </el-tooltip>
                  <span v-else>{{ seg.text }}</span>
                </template>
              </span>
            </div>
          </div>
          <p v-if="replaceSlotInfo" class="replace-new">
            替换为：<el-tag size="small" type="success">{{ replaceSlotInfo.newEffect.displayName }}</el-tag>
          </p>
          <template #footer>
            <el-button @click="replaceConfirmVisible = false">取消</el-button>
            <el-button type="primary" @click="confirmReplaceEffect" :disabled="replaceChoiceIdx === -1">替换</el-button>
          </template>
        </el-dialog>
      </div>
    </template>

    <template v-if="phase === 'shop'">
      <div class="shop-section">
        <h3>商店 <el-tag type="success">灵力: {{ state.spirit }}</el-tag></h3>
        <div class="shop-items">
          <el-card v-for="(item, idx) in shopItems" :key="idx" class="shop-card" shadow="hover">
            <div class="shop-item-name">{{ item.name }}</div>
            <div class="shop-item-desc">
              <template v-for="(seg, si) in parseDescription(item.description)" :key="si">
                <el-tooltip v-if="seg.type === 'effect'" :content="seg.effectDesc" placement="top">
                  <el-tag size="small" type="success" class="inline-effect-tag">{{ seg.text }}</el-tag>
                </el-tooltip>
                <span v-else>{{ seg.text }}</span>
              </template>
            </div>
            <div class="shop-item-price">
              <el-tag type="warning">{{ item.price }} 灵力</el-tag>
            </div>
            <el-button size="small" type="primary" @click="openShopBuy(idx)" :disabled="state.spirit < item.price">购买</el-button>
          </el-card>
        </div>
        <el-button type="primary" @click="leaveShop">继续远征</el-button>

        <el-dialog v-model="shopTargetVisible" title="选择装配目标" width="400px">
          <div class="target-cards">
            <div v-for="(card, idx) in state.cards" :key="idx" class="target-card"
              :class="{ selected: shopTargetIdx === idx, disabled: !canApplyToCard(card, shopBuyingReward!, shopBuyingItem?.price ?? 0) }"
              @click="canApplyToCard(card, shopBuyingReward!, shopBuyingItem?.price ?? 0) && (shopTargetIdx = idx)">
              <div class="tc-name">{{ card.name }}</div>
              <div class="tc-hp">HP: {{ card.currentHp }}/{{ card.maxCardHp }}</div>
              <div class="tc-stats">ATK:{{ diceRange(card.atkPoint) }} DEF:{{ diceRange(card.defPoint) }} DOD:{{ diceRange(card.dodPoint) }}</div>
              <div v-if="card.isNonCard" class="tc-extra-cost">装配到非符需额外3灵力</div>
            </div>
          </div>
          <template #footer>
            <el-button @click="shopTargetVisible = false">取消</el-button>
            <el-button type="primary" @click="confirmShopBuy" :disabled="shopTargetIdx === -1">确认</el-button>
          </template>
        </el-dialog>
      </div>
    </template>

    <template v-if="phase === 'defeated'">
      <div class="defeated-section">
        <h3>远征失败</h3>
        <p>你在第{{ state.currentStage }}面第{{ state.currentBattle }}战被击败</p>
        <p>共取得 {{ state.victories }} 场胜利</p>
        <el-button type="primary" @click="resetExpedition">重新开始</el-button>
      </div>
    </template>

    <template v-if="phase === 'victory'">
      <div class="victory-section">
        <h3>远征胜利！</h3>
        <p>你成功通过了所有挑战！</p>
        <div class="victory-stats">
          <div class="vs-row"><span>总胜场</span><span>{{ state.victories }}</span></div>
          <div class="vs-row"><span>剩余灵力</span><span>{{ state.spirit }}</span></div>
        </div>
        <div class="victory-cards">
          <h4>最终阵容</h4>
          <div class="summary-cards">
            <div v-for="(card, idx) in state.cards" :key="idx" class="summary-card" :class="{ noncard: card.isNonCard }">
              <div class="sc-name">{{ card.name }}</div>
              <div class="sc-hp">HP: {{ card.currentHp }}/{{ card.maxCardHp }}</div>
              <div class="sc-stats">ATK:{{ diceRange(card.atkPoint) }} DEF:{{ diceRange(card.defPoint) }} DOD:{{ diceRange(card.dodPoint) }}</div>
              <div class="sc-effects" v-if="allEffects(card).length > 0">
                <el-tooltip v-for="eff in allEffects(card)" :key="eff.id" :content="eff.description" placement="top">
                  <el-tag size="small" :type="slotTagType(eff.slot)">
                    {{ eff.displayName }}
                  </el-tag>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
        <el-button type="primary" @click="resetExpedition">再来一次</el-button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import '@/spellcard/effects'
import { generateEncounter, getSpiritReward, getStageTemplate } from '@/spellcard/encounters'
import type { CardData, LogEntry } from '@/spellcard/engine'
import { Battle } from '@/spellcard/engine'
import {
    type DiceUpgrade, type EffectModule, type EffectSlot,
    type ExpeditionCard, type ExpeditionState, type FixedDrop,
    type Reward, type ShopItem,
    BASE_PANELS, INITIAL_CARD_EFFECTS,
    addEffectToCard,
    addSlotCapacity,
    canAddEffectToSlot,
    createNonCard,
    createSpellCard,
    healAllForNewStage,
    healNonCard,
    toCardData
} from '@/spellcard/expedition'
import { DICE_POOL, generateRewards, generateShopItems, parseDescription } from '@/spellcard/rewards'
import '@/spellcard/spellcard-test'
import { ref } from 'vue'

const phase = ref<'start' | 'encounter' | 'result' | 'fixedDrop' | 'reward' | 'shop' | 'defeated' | 'victory'>('start')
const selectedPanelIdx = ref(-1)
const basePanels = BASE_PANELS

const state = ref<ExpeditionState>(createInitialState())
const encounterType = ref<'normal' | 'elite' | 'boss'>('normal')
const enemyCards = ref<CardData[]>([])
const currentEncounterEnemyCards = ref<CardData[]>([])
const battleLog = ref<LogEntry[]>([])
const battleWon = ref(false)
const spiritGainedInBattle = ref(0)
const logCollapsed = ref(true)

interface CardSummary {
  name: string; maxHp: number; hpBefore: number; hpAfter: number; damage: number; broken: boolean; isNonCard: boolean
}
const battleSummary = ref<CardSummary[]>([])

const currentRewards = ref<Reward[]>([])
const selectedRewardIdx = ref(-1)
const targetCardIdx = ref(-1)
const shopItems = ref<ShopItem[]>([])
const shopTargetVisible = ref(false)
const shopTargetIdx = ref(-1)
const shopBuyingIdx = ref(-1)
const shopBuyingReward = ref<Reward | null>(null)
const replaceConfirmVisible = ref(false)
const replaceSlotInfo = ref<{ cardIdx: number; slot: EffectSlot; existingEffects: EffectModule[]; newEffect: EffectModule } | null>(null)
const replaceChoiceIdx = ref(-1)

const currentFixedDrop = ref<FixedDrop | null>(null)
const fixedDropItem = ref<DiceUpgrade | null>(null)
const fixedDropNewCard = ref<typeof NEW_CARD_POOL[number] | null>(null)
const fixedDropTargetIdx = ref(-1)

function diceRange(diceStr: string): string {
  const match = diceStr.match(/^(\d+)d(\d+)(\+\d+)?$/)
  if (!match) return diceStr
  const count = parseInt(match[1])
  const faces = parseInt(match[2])
  const bonus = match[3] ? parseInt(match[3]) : 0
  const min = count * 1 + bonus
  const max = count * faces + bonus
  return min === max ? `${min}` : `${min}~${max}`
}

function allEffects(card: ExpeditionCard): (EffectModule & { slot: EffectSlot })[] {
  const result: (EffectModule & { slot: EffectSlot })[] = []
  for (const eff of card.effects.onCardSet) result.push({ ...eff, slot: 'onCardSet' })
  for (const eff of card.effects.onCardBreak) result.push({ ...eff, slot: 'onCardBreak' })
  for (const eff of card.effects.onPassive) result.push({ ...eff, slot: 'onPassive' })
  return result
}

function isSlotReward(r: Reward): boolean {
  return 'slot' in r && !('apply' in r)
}

function isDiceUpgrade(r: Reward): boolean {
  return 'apply' in r && !('slot' in r) && r.id.startsWith('dice_')
}

function isRefreshItem(r: Reward): boolean {
  return r.id === '_refresh'
}

function isDiceCountUpgrade(r: Reward): boolean {
  return 'apply' in r && !('slot' in r) && r.id.endsWith('_count')
}

function isStatUpgrade(r: Reward): boolean {
  return 'apply' in r && !('slot' in r) && r.id.startsWith('stat_')
}

function canApplyToCard(card: ExpeditionCard, r: Reward, extraCost: number = 0): boolean {
  if (isRefreshItem(r)) return false
  if (card.isNonCard) {
    if (state.value.spirit < 3 + extraCost) return false
    if (isSlotReward(r)) return true
    if (isDiceCountUpgrade(r)) return false
    if (isStatUpgrade(r)) return true
    if (isDiceUpgrade(r)) return true
    if ('slot' in r && 'apply' in r) {
      return canAddEffectToSlot(card, r.slot)
    }
    return false
  }
  return true
}

const slotLabel = (slot: EffectSlot) => slot === 'onCardSet' ? '宣言' : slot === 'onCardBreak' ? '亡语' : '被动'
const slotTagType = (slot: EffectSlot) => slot === 'onCardSet' ? 'success' : slot === 'onCardBreak' ? 'danger' : 'warning'

function createInitialState(): ExpeditionState {
  return { cards: [], spirit: 0, currentStage: 1, currentBattle: 1, battlesPerStage: 4, totalStages: 6, finished: false, victories: 0 }
}

function startExpedition() {
  if (selectedPanelIdx.value === -1) return
  const panel = BASE_PANELS[selectedPanelIdx.value]
  const nonCard = createNonCard()
  const spellCard = createSpellCard(panel)
  const initEffects = INITIAL_CARD_EFFECTS[panel.name]
  if (initEffects) {
    for (const eff of initEffects) { addEffectToCard(spellCard, eff) }
  }
  state.value = { ...createInitialState(), cards: [nonCard, spellCard] }
  loadEncounter()
  phase.value = 'encounter'
}

function loadEncounter() {
  const rng = () => Math.random()
  const enc = generateEncounter(state.value.currentStage, state.value.currentBattle, rng)
  encounterType.value = enc.type
  enemyCards.value = enc.enemyCards
  currentEncounterEnemyCards.value = enc.enemyCards
  currentFixedDrop.value = enc.fixedDrop ?? null
}

function startBattle() {
  const hpBefore = state.value.cards.map(c => c.currentHp)
  const myCardDatas = state.value.cards.map(c => toCardData(c))
  const b = new Battle(1)
  b.setCreator('你')
  b.creator.chosenCards = myCardDatas
  b.setSingleEnemy('敌人', currentEncounterEnemyCards.value)
  b.runFullBattle()

  battleLog.value = b.log.entries
  battleWon.value = b.winnerId === 1

  const summary: CardSummary[] = []
  const usedIndices = b.creator.usedCardIndices
  for (let i = 0; i < state.value.cards.length; i++) {
    const card = state.value.cards[i]
    const wasUsed = i < usedIndices.length
    let hpAfter: number
    let broken = false

    if (wasUsed) {
      if (i === usedIndices.length - 1) {
        hpAfter = b.creator.nowHp
        broken = b.creator.nowHp <= 0
      } else {
        hpAfter = 0
        broken = true
      }
    } else {
      hpAfter = card.currentHp
    }

    summary.push({ name: card.name, maxHp: card.maxCardHp, hpBefore: hpBefore[i], hpAfter, damage: hpBefore[i] - hpAfter, broken, isNonCard: card.isNonCard })
    card.currentHp = hpAfter
  }

  if (battleWon.value) {
    state.value.victories++
    state.value.spirit += getSpiritReward(encounterType.value)
    spiritGainedInBattle.value = b.creator.spiritGained
    state.value.spirit += b.creator.spiritGained
    healNonCard(state.value.cards)
  } else {
    spiritGainedInBattle.value = 0
  }

  battleSummary.value = summary
  logCollapsed.value = true
  phase.value = 'result'
}

function goToReward() {
  if (!battleWon.value) { phase.value = 'defeated'; return }
  if (encounterType.value === 'boss' && state.value.currentStage >= state.value.totalStages) {
    phase.value = 'victory'
    return
  }
  if (currentFixedDrop.value) {
    setupFixedDrop()
    phase.value = 'fixedDrop'
    return
  }
  generateAndShowRewards()
}

function generateAndShowRewards() {
  const rng = () => Math.random()
  currentRewards.value = generateRewards(encounterType.value, rng)
  selectedRewardIdx.value = -1
  targetCardIdx.value = -1
  phase.value = 'reward'
}

function setupFixedDrop() {
  if (!currentFixedDrop.value) return
  if (currentFixedDrop.value.type === 'dice') {
    fixedDropItem.value = DICE_POOL[Math.floor(Math.random() * DICE_POOL.length)]
    fixedDropNewCard.value = null
  } else {
    fixedDropNewCard.value = generateNewCardDrop(state.value.currentStage, Math.random)
    fixedDropItem.value = null
  }
  fixedDropTargetIdx.value = -1
}

function confirmFixedDrop() {
  if (!currentFixedDrop.value) return
  if (currentFixedDrop.value.type === 'dice') {
    if (fixedDropTargetIdx.value === -1 || !fixedDropItem.value) return
    const card = state.value.cards[fixedDropTargetIdx.value]
    if (card.isNonCard) {
      if (state.value.spirit < 3) return
      state.value.spirit -= 3
    }
    fixedDropItem.value.apply(card)
  } else {
    if (!fixedDropNewCard.value) return
    const newCard = createSpellCard(fixedDropNewCard.value)
    state.value.cards.push(newCard)
  }
  currentFixedDrop.value = null
  generateAndShowRewards()
}

function skipFixedDrop() {
  currentFixedDrop.value = null
  generateAndShowRewards()
}

function selectReward(idx: number) {
  selectedRewardIdx.value = idx
  targetCardIdx.value = -1
}

function confirmReward() {
  if (selectedRewardIdx.value === -1) return
  const reward = currentRewards.value[selectedRewardIdx.value]

  if (isSlotReward(reward)) {
    if (targetCardIdx.value === -1) return
    const card = state.value.cards[targetCardIdx.value]
    if (card.isNonCard) {
      if (state.value.spirit < 3) return
      state.value.spirit -= 3
    }
    addSlotCapacity(card, reward.slot)
    advanceAfterReward()
    return
  }

  if (targetCardIdx.value === -1) return
  const card = state.value.cards[targetCardIdx.value]

  if ('slot' in reward && 'apply' in reward) {
    if (!canAddEffectToSlot(card, reward.slot)) {
      const existing = card.effects[reward.slot]
      if (existing.length > 0) {
        replaceSlotInfo.value = { cardIdx: targetCardIdx.value, slot: reward.slot, existingEffects: [...existing], newEffect: reward }
        replaceChoiceIdx.value = -1
        replaceConfirmVisible.value = true
        return
      }
    }
  }

  doApplyReward(card, reward)
}

function doApplyReward(card: ExpeditionCard, reward: Reward) {
  if (card.isNonCard) {
    if (state.value.spirit < 3) return
    state.value.spirit -= 3
  }
  applyRewardToCard(card, reward)
  replaceConfirmVisible.value = false
  advanceAfterReward()
}

function confirmReplaceEffect() {
  if (!replaceSlotInfo.value || replaceChoiceIdx.value === -1) return
  const info = replaceSlotInfo.value
  const card = state.value.cards[info.cardIdx]
  card.effects[info.slot].splice(replaceChoiceIdx.value, 1)
  card.effects[info.slot].push(info.newEffect)
  if (card.isNonCard) {
    if (state.value.spirit < 3) return
    state.value.spirit -= 3
  }
  replaceConfirmVisible.value = false
  advanceAfterReward()
}

function applyRewardToCard(card: ExpeditionCard, reward: Reward) {
  if (isSlotReward(reward)) { addSlotCapacity(card, reward.slot); return }
  if ('slot' in reward && 'apply' in reward) {
    addEffectToCard(card, reward)
  } else if ('apply' in reward) {
    reward.apply(card)
  }
}

function skipReward() { advanceAfterReward() }

function advanceAfterReward() {
  const template = getStageTemplate(state.value.currentStage)
  if (state.value.currentBattle >= template.length) {
    healAllForNewStage(state.value.cards)
    if (state.value.currentStage >= state.value.totalStages) {
      phase.value = 'victory'
      return
    }
    state.value.currentStage++
    state.value.currentBattle = 1
    shopItems.value = generateShopItems(() => Math.random())
    phase.value = 'shop'
  } else {
    state.value.currentBattle++
    loadEncounter()
    phase.value = 'encounter'
  }
}

function openShopBuy(idx: number) {
  const item = shopItems.value[idx]
  if (state.value.spirit < item.price) return

  if (isRefreshItem(item.reward)) {
    state.value.spirit -= item.price
    shopItems.value = generateShopItems(() => Math.random())
    return
  }

  shopBuyingIdx.value = idx
  shopBuyingReward.value = item.reward
  shopTargetIdx.value = -1

  shopTargetVisible.value = true
}

function confirmShopBuyDirect(idx: number) {
  const item = shopItems.value[idx]
  state.value.spirit -= item.price
  shopItems.value = shopItems.value.filter((_, i) => i !== idx)
}

function confirmShopBuy() {
  if (shopTargetIdx.value === -1 || shopBuyingIdx.value === -1) return
  const item = shopItems.value[shopBuyingIdx.value]
  const card = state.value.cards[shopTargetIdx.value]

  if (card.isNonCard) {
    if (state.value.spirit < item.price + 3) return
    state.value.spirit -= 3
  }

  state.value.spirit -= item.price
  applyRewardToCard(card, item.reward)
  shopItems.value = shopItems.value.filter((_, i) => i !== shopBuyingIdx.value)
  shopTargetVisible.value = false
}

function leaveShop() { loadEncounter(); phase.value = 'encounter' }
function resetExpedition() { phase.value = 'start'; selectedPanelIdx.value = -1; state.value = createInitialState(); currentFixedDrop.value = null }
</script>

<style scoped>
.expedition-container { max-width: 900px; margin: 0 auto; text-align: center; }
.start-section, .encounter-section, .reward-section, .shop-section, .defeated-section, .victory-section { padding: 20px 0; }
.section-desc { color: #909399; margin-bottom: 20px; }
.panel-cards { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 24px; align-items: stretch; }
.panel-card { width: 200px; min-height: 160px; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.panel-card.selected { border-color: #409eff; box-shadow: 0 0 10px rgba(64,158,255,0.3); }
.panel-card:hover { transform: translateY(-4px); }
.panel-name { font-size: 14px; font-weight: bold; margin-bottom: 8px; word-break: break-all; }
.panel-stats { display: flex; flex-wrap: wrap; gap: 6px; font-size: 13px; color: #606266; }
.panel-effect { margin-top: 6px; display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; font-size: 12px; color: #909399; }
.panel-effect .el-tag { font-size: 11px; white-space: normal; height: auto; line-height: 1.4; }
.panel-effect-text { font-size: 12px; color: #909399; }

.stage-info { display: flex; gap: 12px; justify-content: center; margin-bottom: 20px; }

.vs-preview { display: flex; justify-content: center; align-items: flex-start; gap: 24px; margin-bottom: 24px; }
.preview-side { flex: 1; max-width: 380px; }
.preview-side h4 { margin: 0 0 12px 0; }
.vs-divider { font-size: 28px; font-weight: bold; color: #909399; padding-top: 40px; flex-shrink: 0; }
.preview-cards { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.preview-card { background: #f5f7fa; border-radius: 8px; padding: 12px 16px; min-width: 150px; text-align: center; }
.preview-card.noncard { background: #fafafa; border: 1px dashed #dcdfe6; }
.preview-card.enemy { background: #fef0f0; border: 1px solid #fbc4c4; }
.pc-name { font-weight: bold; margin-bottom: 4px; }
.pc-hp { font-size: 13px; color: #606266; margin-bottom: 2px; }
.pc-stats { font-size: 12px; color: #909399; margin-bottom: 4px; }
.pc-desc { font-size: 11px; color: #909399; border-top: 1px solid #ebeef5; padding-top: 4px; margin-top: 4px; }
.inline-effect-tag { display: inline-flex; align-items: center; height: 20px; margin: 0 1px; cursor: help; vertical-align: baseline; padding: 0 6px; }
.pc-effects { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; margin-top: 6px; }

.result-section { padding: 20px 0; }
.battle-summary { margin: 20px 0; }
.battle-summary h4 { margin: 0 0 12px 0; }
.summary-cards { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
.summary-card { background: #f5f7fa; border-radius: 8px; padding: 12px 20px; min-width: 140px; text-align: center; }
.summary-card.broken { background: #fef0f0; border: 1px solid #fbc4c4; }
.sc-name { font-weight: bold; margin-bottom: 4px; }
.sc-hp { font-size: 14px; color: #606266; }
.sc-broken { color: #f56c6c; font-weight: bold; }
.sc-damage { color: #f56c6c; font-size: 13px; }
.result-actions { margin-top: 20px; }

.battle-log { max-height: 300px; overflow-y: auto; text-align: left; padding: 8px; background: #f5f7fa; border-radius: 8px; }
.log-entry { display: flex; align-items: flex-start; gap: 8px; padding: 4px 0; font-size: 13px; border-bottom: 1px solid #ebeef5; }
.log-entry:last-child { border-bottom: none; }
.log-round { flex-shrink: 0; min-width: 32px; }
.log-message { white-space: pre-wrap; word-break: break-word; }
.log-phase-card_break { color: #f56c6c; }
.log-phase-card_set { color: #67c23a; }
.log-phase-end { color: #e6a23c; font-weight: bold; }
.log-divider { margin: 12px 0; }

.reward-cards { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 24px; }
.reward-card { width: 220px; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.reward-card.selected { border-color: #409eff; box-shadow: 0 0 10px rgba(64,158,255,0.3); }
.reward-card:hover { transform: translateY(-4px); }
.reward-name { font-size: 15px; font-weight: bold; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.reward-desc { font-size: 13px; color: #606266; margin-bottom: 8px; }
.reward-slot { margin-bottom: 4px; }
.reward-target { margin-bottom: 24px; }
.target-cards { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; }
.target-card { background: #f5f7fa; border-radius: 8px; padding: 12px 16px; min-width: 160px; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.target-card.selected { border-color: #409eff; box-shadow: 0 0 10px rgba(64,158,255,0.3); }
.target-card.disabled { opacity: 0.4; cursor: not-allowed; }
.tc-name { font-weight: bold; margin-bottom: 4px; }
.tc-hp { font-size: 13px; color: #606266; margin-bottom: 2px; }
.tc-stats { font-size: 12px; color: #909399; margin-bottom: 4px; }
.tc-effects { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; margin-top: 6px; }
.tc-extra-cost { font-size: 12px; color: #e6a23c; margin-top: 4px; }
.reward-actions { display: flex; gap: 12px; justify-content: center; }

.shop-items { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 24px; }
.shop-card { width: 180px; text-align: center; }
.shop-item-name { font-weight: bold; margin-bottom: 6px; }
.shop-item-desc { font-size: 12px; color: #909399; margin-bottom: 8px; }
.shop-item-price { margin-bottom: 8px; }

.victory-stats { display: inline-block; text-align: left; margin: 16px 0; background: #f0f9eb; border-radius: 8px; padding: 12px 24px; }
.vs-row { display: flex; justify-content: space-between; gap: 32px; font-size: 15px; padding: 4px 0; }
.vs-row span:first-child { color: #606266; }
.vs-row span:last-child { font-weight: bold; }
.victory-cards { margin: 16px 0; }
.victory-cards h4 { margin: 0 0 12px 0; }
.summary-card.noncard { background: #fafafa; border: 1px dashed #dcdfe6; }
.spirit-gained-info { color: #e6a23c; font-weight: bold; margin-bottom: 8px; }
.sc-effects { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; margin-top: 6px; }

.fixed-drop-section { padding: 20px 0; }
.fixed-drop-item { background: #fdf6ec; border: 2px solid #e6a23c; border-radius: 12px; padding: 16px 24px; display: inline-block; margin-bottom: 20px; }
.fixed-drop-item.new-card-preview { background: #f0f9eb; border-color: #67c23a; }
.fd-name { font-size: 16px; font-weight: bold; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.fd-desc { font-size: 13px; color: #606266; }
.fd-stats { display: flex; flex-wrap: wrap; gap: 8px; font-size: 14px; color: #606266; }

.replace-options { display: flex; flex-direction: column; gap: 8px; margin: 12px 0; }
.replace-option { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border: 2px solid #ebeef5; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
.replace-option.selected { border-color: #f56c6c; background: #fef0f0; }
.replace-option:hover { border-color: #f56c6c; }
.replace-option-desc { font-size: 12px; color: #909399; }
.replace-new { margin-top: 8px; }
</style>
