<template>
  <div class="battle-container">
    <el-card class="battle-card">
      <template #header>
        <div class="card-header"><h2>符卡对战</h2></div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="快速对战" name="quick">
          <div class="quick-battle-section">
            <p class="section-desc">随机生成双方符卡，立即开始对战</p>
            <el-button type="primary" size="large" @click="handleQuickBattle">快速对战</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="逐回合对战" name="turnbased">
          <div class="turnbased-section">
            <template v-if="battlePhase === 'idle'">
              <div class="idle-section">
                <p class="section-desc">选择5张符卡，逐回合与AI对战</p>
                <el-button type="primary" @click="startCardSelection">开始选卡</el-button>
              </div>
            </template>

            <template v-if="battlePhase === 'selecting'">
              <div class="selection-progress">
                <el-tag type="info">第 {{ currentSelectRound + 1 }} / 5 轮选卡</el-tag>
              </div>
              <div class="candidate-cards">
                <el-card v-for="(card, index) in candidateCards" :key="index" class="candidate-card"
                  :class="{ selected: tempSelectedIndex === index }" @click="tempSelectedIndex = index" shadow="hover">
                  <div class="card-name">{{ card.name }}</div>
                  <div class="card-stats">
                    <span>HP:{{ card.cardHp }}</span><span>ATK:{{ card.atkPoint }}</span>
                    <span>DEF:{{ card.defPoint }}</span><span>DOD:{{ card.dodPoint }}</span>
                  </div>
                  <div class="card-desc" v-if="card.description !== '无'">{{ card.description }}</div>
                </el-card>
              </div>
              <el-button type="primary" @click="confirmCardSelection" :disabled="tempSelectedIndex === -1">确认选择</el-button>
            </template>

            <template v-if="battlePhase === 'selected'">
              <h3>已选符卡</h3>
              <div class="selected-cards-list">
                <el-tag v-for="(card, index) in selectedCards" :key="index" class="selected-tag" type="success">{{ card.name }}</el-tag>
              </div>
              <div class="battle-actions">
                <el-button type="primary" size="large" @click="handleCreateBattle">开始对战</el-button>
                <el-button @click="resetSelection">重新选卡</el-button>
              </div>
            </template>

            <template v-if="battlePhase === 'playing' || battlePhase === 'animating'">
              <div class="battle-field">
                <div class="battle-players">
                  <div class="player-panel">
                    <h4>{{ battle?.creator?.name || '你' }}</h4>
                    <div class="hp-bar">
                      <el-progress :percentage="creatorHpPercent"
                        :color="creatorHpPercent > 50 ? '#67c23a' : creatorHpPercent > 20 ? '#e6a23c' : '#f56c6c'"
                        :stroke-width="18" :text-inside="true" :format="() => `HP ${animCreatorHp}`" />
                    </div>
                    <div v-if="animCreatorCard" class="current-card">
                      <el-tag type="danger">{{ animCreatorCard.name }}</el-tag>
                      <span class="card-index">第{{ creatorCardIndex }}张</span>
                    </div>
                    <div v-if="animCreatorEffects.length" class="effects-list">
                      <el-tooltip v-for="eff in animCreatorEffects" :key="eff.id + (eff.effectType === 'BORDER' ? eff.turns : eff.amount)" :content="getEffectTooltip(eff)" placement="top">
                        <el-tag size="small" class="effect-tag">
                          {{ eff.displayName }}{{ eff.effectType === 'BORDER' ? eff.turns : eff.amount }}
                        </el-tag>
                      </el-tooltip>
                    </div>
                  </div>
                  <div class="vs-badge">VS</div>
                  <div class="player-panel">
                    <h4>{{ battle?.joiner?.name || 'AI' }}</h4>
                    <div class="hp-bar">
                      <el-progress :percentage="joinerHpPercent"
                        :color="joinerHpPercent > 50 ? '#67c23a' : joinerHpPercent > 20 ? '#e6a23c' : '#f56c6c'"
                        :stroke-width="18" :text-inside="true" :format="() => `HP ${animJoinerHp}`" />
                    </div>
                    <div v-if="animJoinerCard" class="current-card">
                      <el-tag type="primary">{{ animJoinerCard.name }}</el-tag>
                      <span class="card-index">第{{ joinerCardIndex }}张</span>
                    </div>
                    <div v-if="animJoinerEffects.length" class="effects-list">
                      <el-tooltip v-for="eff in animJoinerEffects" :key="eff.id + (eff.effectType === 'BORDER' ? eff.turns : eff.amount)" :content="getEffectTooltip(eff)" placement="top">
                        <el-tag size="small" class="effect-tag" type="info">
                          {{ eff.displayName }}{{ eff.effectType === 'BORDER' ? eff.turns : eff.amount }}
                        </el-tag>
                      </el-tooltip>
                    </div>
                  </div>
                </div>

                <template v-if="battlePhase === 'playing'">
                  <el-divider>
                    <el-tag v-if="isFirstCard" type="success" effect="plain">选择第一张符卡宣言！</el-tag>
                    <el-tag v-else type="danger" effect="plain">你的符卡被击破！选择下一张</el-tag>
                  </el-divider>
                  <div class="hand-cards">
                    <el-card v-for="(card, index) in myAvailableCards" :key="index" class="hand-card"
                      :class="{ chosen: chosenCardIndex === index }" @click="chosenCardIndex = index" shadow="hover">
                      <div class="card-name">{{ card.name }}</div>
                      <div class="card-stats">
                        <span>HP:{{ card.cardHp }}</span><span>ATK:{{ card.atkPoint }}</span>
                        <span>DEF:{{ card.defPoint }}</span><span>DOD:{{ card.dodPoint }}</span>
                      </div>
                      <div class="card-desc" v-if="card.description !== '无'">{{ card.description }}</div>
                    </el-card>
                  </div>
                  <div class="play-actions">
                    <el-button type="primary" size="large" @click="handlePlayCard" :disabled="chosenCardIndex === -1">宣言</el-button>
                    <el-button v-if="!isFirstCard" @click="handleSurrender">投降</el-button>
                  </div>
                </template>

                <template v-if="battlePhase === 'animating'">
                  <el-divider>
                    <div class="animating-controls">
                      <el-tag type="warning" effect="dark">{{ animPaused ? '已暂停' : '战斗进行中...' }}</el-tag>
                      <el-button :type="animPaused ? 'success' : 'default'" size="small" @click="togglePause" circle>
                        {{ animPaused ? '▶' : '⏸' }}
                      </el-button>
                    </div>
                  </el-divider>
                </template>

                <div class="battle-visual" v-if="turnVisual.stats || turnVisual.damage || turnVisual.cardBreak">
                  <div class="visual-round-badge" v-if="turnVisual.round">R{{ turnVisual.round }}</div>
                  <div class="visual-stats" v-if="turnVisual.stats" :key="'stats-' + turnVisual.statsKey">
                    <div class="stat-side creator-side">
                      <span class="stat-name">你</span>
                      <span class="stat-item atk">⚔️{{ turnVisual.stats.creatorAtk }}</span>
                      <span class="stat-item def">🛡️{{ turnVisual.stats.creatorDef }}</span>
                      <span class="stat-item dod">💨{{ turnVisual.stats.creatorDod }}</span>
                    </div>
                    <span class="stat-separator">⟷</span>
                    <div class="stat-side joiner-side">
                      <span class="stat-name">AI</span>
                      <span class="stat-item atk">⚔️{{ turnVisual.stats.joinerAtk }}</span>
                      <span class="stat-item def">🛡️{{ turnVisual.stats.joinerDef }}</span>
                      <span class="stat-item dod">💨{{ turnVisual.stats.joinerDod }}</span>
                    </div>
                  </div>

                  <div class="visual-attack" v-if="turnVisual.damage" :key="'attack-' + turnVisual.damageKey">
                    <div class="attack-row">
                      <span class="attack-from">你</span>
                      <span class="attack-arrow">⚔️→</span>
                      <span class="attack-to">AI</span>
                      <template v-if="turnVisual.damage.joinerDodged">
                        <span class="attack-miss">MISS!</span>
                      </template>
                      <template v-else>
                        <span v-if="turnVisual.damage.joinerDefended" class="attack-defend">🛡️</span>
                        <span class="attack-damage" :class="{ 'big-damage': turnVisual.damage.joinerHurt >= 5 }">-{{ turnVisual.damage.joinerHurt }}</span>
                      </template>
                    </div>
                    <div class="attack-row">
                      <span class="attack-from">AI</span>
                      <span class="attack-arrow">⚔️→</span>
                      <span class="attack-to">你</span>
                      <template v-if="turnVisual.damage.creatorDodged">
                        <span class="attack-miss">MISS!</span>
                      </template>
                      <template v-else>
                        <span v-if="turnVisual.damage.creatorDefended" class="attack-defend">🛡️</span>
                        <span class="attack-damage" :class="{ 'big-damage': turnVisual.damage.creatorHurt >= 5 }">-{{ turnVisual.damage.creatorHurt }}</span>
                      </template>
                    </div>
                  </div>

                  <div class="visual-card-break" v-if="turnVisual.cardBreak" :key="'break-' + turnVisual.breakKey">
                    <span class="break-icon">💔</span>
                    <span class="break-text">{{ turnVisual.cardBreak === 'creator' ? '你' : 'AI' }}的符卡被{{ turnVisual.breakSource === 'effect' ? '效果伤害' : '战斗伤害' }}击破!</span>
                  </div>
                </div>

                <el-divider class="log-divider">
                  <el-button link size="small" @click="logCollapsed = !logCollapsed">
                    对战日志 {{ logCollapsed ? '▸' : '▾' }}
                  </el-button>
                </el-divider>
                <div class="battle-log" v-show="!logCollapsed">
                  <div v-for="(entry, index) in displayedLog" :key="index" class="log-entry" :class="'log-phase-' + entry.phase">
                    <el-tag size="small" class="log-round">R{{ entry.round }}</el-tag>
                    <span class="log-message">{{ entry.message }}</span>
                  </div>
                </div>
              </div>
            </template>

            <template v-if="battlePhase === 'finished'">
              <div class="result-section">
                <el-tag :type="battle?.winnerId === battle?.creatorId ? 'success' : 'warning'" size="large">
                  {{ battle?.winnerId === battle?.creatorId ? '胜利！' : (battle?.winnerId === null ? '平局' : '失败') }}
                </el-tag>
                <el-divider class="log-divider">
                  <el-button link size="small" @click="logCollapsed = !logCollapsed">
                    对战日志 {{ logCollapsed ? '▸' : '▾' }}
                  </el-button>
                </el-divider>
                <div class="battle-log" v-show="!logCollapsed">
                  <div v-for="(entry, index) in displayedLog" :key="index" class="log-entry" :class="'log-phase-' + entry.phase">
                    <el-tag size="small" class="log-round">R{{ entry.round }}</el-tag>
                    <span class="log-message">{{ entry.message }}</span>
                  </div>
                </div>
                <el-button type="primary" @click="resetBattle">再来一局</el-button>
              </div>
            </template>
          </div>
        </el-tab-pane>

        <el-tab-pane label="符卡图鉴" name="codex">
          <div class="codex-section">
            <el-input v-model="codexSearch" placeholder="搜索符卡名称" clearable style="margin-bottom:16px;max-width:300px;" />
            <div class="codex-grid">
              <el-card v-for="card in filteredCards" :key="card.id" class="codex-card" shadow="hover">
                <div class="codex-card-header">
                  <span class="codex-card-name">{{ card.name }}</span>
                  <el-tag size="small" :type="costTagType(card.cost)">Cost {{ card.cost }}</el-tag>
                </div>
                <div class="codex-card-stats">
                  <span>HP:{{ card.cardHp }}</span><span>ATK:{{ card.atkPoint }}</span>
                  <span>DEF:{{ card.defPoint }}</span><span>DOD:{{ card.dodPoint }}</span>
                </div>
                <div class="codex-card-desc" v-if="card.description !== '无'">{{ card.description }}</div>
              </el-card>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { Battle, Battler, SeededRandom } from '@/spellcard/engine'
import type { CardData, LogEntry, EffectData, VisualData } from '@/spellcard/engine'
import { ALL_CARDS, getRandomCards } from '@/spellcard/cards'
import '@/spellcard/effects'

const userStore = useUserStore()
const userId = computed(() => userStore.userInfo?.qq)

const activeTab = ref('turnbased')
const battlePhase = ref<'idle' | 'selecting' | 'selected' | 'playing' | 'animating' | 'finished'>('idle')
const battle = ref<Battle | null>(null)
const isFirstCard = ref(true)

const currentSelectRound = ref(0)
const candidateCards = ref<CardData[]>([])
const selectedCards = ref<CardData[]>([])
const tempSelectedIndex = ref(-1)
const chosenCardIndex = ref(-1)

const codexSearch = ref('')
const filteredCards = computed(() => {
  if (!codexSearch.value) return ALL_CARDS
  return ALL_CARDS.filter(c => c.name.includes(codexSearch.value))
})
const costTagType = (cost: number) => ({ 0: 'info', 1: '', 2: 'warning', 3: 'danger' }[cost] ?? 'info')

const EFFECT_DESC: Record<string, string> = {
  Strength: '攻击力+{n}',
  Weaken: '攻击力-{n}',
  Stable: '防御力+{n}',
  Fragile: '防御力-{n}',
  Agile: '回避+{n}',
  Sluggish: '回避-{n}',
  Buffer: '受到伤害-{n}',
  Chase: '对方受伤+{n}',
  Trace: '对方闪避成功时仍受{n}点伤害',
  Shield: '护盾：吸收{n}点伤害',
  Unbreakable: '击破保护：免疫致命伤害（剩余{n}次）',
  Freeze: '冻结：无法攻击/防御/回避，非结界效果不触发（剩余{n}回合）',
  CantDefence: '无法防御',
  CantDodge: '无法回避',
  StrengthBorder: '结界：攻击力+{s}（剩余{t}回合）',
  WeakenBorder: '结界：攻击力-{s}（剩余{t}回合）',
  StableBorder: '结界：防御力+{s}（剩余{t}回合）',
  FragileBorder: '结界：防御力-{s}（剩余{t}回合）',
  AgileBorder: '结界：回避+{s}（剩余{t}回合）',
  SluggishBorder: '结界：回避-{s}（剩余{t}回合）',
  DamageBorder: '结界：每回合对对方造成{s}点伤害（剩余{t}回合）',
}

const getEffectTooltip = (eff: EffectData): string => {
  const desc = EFFECT_DESC[eff.id]
  if (!desc) return `${eff.displayName} (${eff.effectType})`
  return desc
    .replace('{n}', String(eff.amount))
    .replace('{s}', String(eff.strength ?? 0))
    .replace('{t}', String(eff.turns ?? 0))
}

const animCreatorHp = ref(0)
const animJoinerHp = ref(0)
const animCreatorMaxHp = ref(1)
const animJoinerMaxHp = ref(1)
const animCreatorCard = ref<CardData | null>(null)
const animJoinerCard = ref<CardData | null>(null)
const animCreatorEffects = ref<EffectData[]>([])
const animJoinerEffects = ref<EffectData[]>([])
const displayedLog = ref<LogEntry[]>([])
const animTimer = ref<ReturnType<typeof setTimeout> | null>(null)
const animPaused = ref(false)
let animEntries: LogEntry[] = []
let animIndex = 0
let animFullLog: LogEntry[] = []
let animFinalCreator: any = null
let animFinalJoiner: any = null
const logCollapsed = ref(false)

interface TurnVisualState {
  stats?: { creatorAtk: number; creatorDef: number; creatorDod: number; joinerAtk: number; joinerDef: number; joinerDod: number }
  damage?: { creatorHurt: number; joinerHurt: number; creatorDodged: boolean; joinerDodged: boolean; creatorDefended: boolean; joinerDefended: boolean }
  cardBreak?: 'creator' | 'joiner'
  breakSource?: 'battle' | 'effect'
  round: number
  statsKey: number
  damageKey: number
  breakKey: number
}
const turnVisual = ref<TurnVisualState>({ round: 0, statsKey: 0, damageKey: 0, breakKey: 0 })
let _statsKey = 0, _damageKey = 0, _breakKey = 0

const creatorHpPercent = computed(() => animCreatorMaxHp.value > 0 ? Math.max(0, Math.round(animCreatorHp.value / animCreatorMaxHp.value * 100)) : 0)
const joinerHpPercent = computed(() => animJoinerMaxHp.value > 0 ? Math.max(0, Math.round(animJoinerHp.value / animJoinerMaxHp.value * 100)) : 0)
const creatorCardIndex = computed(() => battle.value?.creator?.usedCardIndices?.length ?? 0)
const joinerCardIndex = computed(() => battle.value?.joiner?.usedCardIndices?.length ?? 0)

const myAvailableCards = computed(() => {
  if (!selectedCards.value.length || !battle.value?.creator) return []
  const used = battle.value.creator.usedCardIndices
  return selectedCards.value
    .map((card, index) => ({ ...card, originalIndex: index }))
    .filter((_, index) => !used.includes(index))
})

const startCardSelection = () => {
  selectedCards.value = []
  currentSelectRound.value = 0
  candidateCards.value = getRandomCards(3)
  tempSelectedIndex.value = -1
  battlePhase.value = 'selecting'
}

const confirmCardSelection = () => {
  if (tempSelectedIndex.value === -1) return
  selectedCards.value.push(candidateCards.value[tempSelectedIndex.value])
  currentSelectRound.value++
  if (currentSelectRound.value >= 5) {
    battlePhase.value = 'selected'
  } else {
    candidateCards.value = getRandomCards(3)
    tempSelectedIndex.value = -1
  }
}

const handleCreateBattle = () => {
  const b = new Battle(Number(userId.value) || 1)
  b.setCreator('你')
  b.creator.chosenCards = [...selectedCards.value]
  const enemyCards = getRandomCards(5)
  b.setSingleEnemy('AI对手', enemyCards)
  battle.value = b
  isFirstCard.value = true
  chosenCardIndex.value = -1
  animCreatorHp.value = 0
  animJoinerHp.value = 0
  animCreatorCard.value = null
  animJoinerCard.value = null
  animCreatorEffects.value = []
  animJoinerEffects.value = []
  displayedLog.value = []
  turnVisual.value = { round: 0, statsKey: 0, damageKey: 0, breakKey: 0 }
  _statsKey = 0; _damageKey = 0; _breakKey = 0
  logCollapsed.value = true
  battlePhase.value = 'playing'
}

const handlePlayCard = () => {
  if (chosenCardIndex.value === -1 || !battle.value) return
  const available = myAvailableCards.value
  const card = available[chosenCardIndex.value]
  if (!card) return

  const prevLogLen = battle.value.log.entries.length
  battle.value.playCardAndResolve(card.originalIndex)
  chosenCardIndex.value = -1
  isFirstCard.value = false
  startAnimation(prevLogLen)
}

const startAnimation = (prevLogLen: number) => {
  battlePhase.value = 'animating'
  animPaused.value = false
  logCollapsed.value = true
  animFullLog = battle.value!.log.entries
  animEntries = animFullLog.slice(prevLogLen)
  animIndex = 0
  displayedLog.value = animFullLog.slice(0, prevLogLen)
  animFinalCreator = battle.value!.creator!
  animFinalJoiner = battle.value!.joiner!

  if (animEntries.length === 0) { finishAnimation(); return }
  processNextAnimEntry()
}

const processNextAnimEntry = () => {
  if (animIndex >= animEntries.length) {
    animCreatorHp.value = animFinalCreator.nowHp
    animJoinerHp.value = animFinalJoiner.nowHp
    animCreatorMaxHp.value = animFinalCreator.nowCard?.cardHp ?? 1
    animJoinerMaxHp.value = animFinalJoiner.nowCard?.cardHp ?? 1
    animCreatorCard.value = animFinalCreator.nowCard
    animJoinerCard.value = animFinalJoiner.nowCard
    animCreatorEffects.value = animFinalCreator.effects.map((e: any) => e.toData())
    animJoinerEffects.value = animFinalJoiner.effects.map((e: any) => e.toData())
    displayedLog.value = [...animFullLog]
    nextTick(() => { const el = document.querySelector('.battle-log'); if (el) el.scrollTop = el.scrollHeight })
    finishAnimation()
    return
  }

  const entry = animEntries[animIndex]
  displayedLog.value.push(entry)
  if (entry.creatorHp !== undefined) animCreatorHp.value = entry.creatorHp
  if (entry.joinerHp !== undefined) animJoinerHp.value = entry.joinerHp
  if (entry.phase === 'card_set') {
    if (animFinalCreator.nowCard) { animCreatorCard.value = animFinalCreator.nowCard; animCreatorMaxHp.value = animFinalCreator.nowCard.cardHp }
    if (animFinalJoiner.nowCard) { animJoinerCard.value = animFinalJoiner.nowCard; animJoinerMaxHp.value = animFinalJoiner.nowCard.cardHp }
  }
  if (entry.phase === 'card_break') {
    if (animCreatorHp.value <= 0) animCreatorCard.value = null
    if (animJoinerHp.value <= 0) animJoinerCard.value = null
  }

  updateTurnVisual(entry)

  animCreatorEffects.value = animFinalCreator.effects.map((e: any) => e.toData())
  animJoinerEffects.value = animFinalJoiner.effects.map((e: any) => e.toData())

  nextTick(() => { const el = document.querySelector('.battle-log'); if (el) el.scrollTop = el.scrollHeight })
  animIndex++
  const delay = entry.phase === 'hurt' ? 1800
    : entry.phase === 'card_break' ? 2200
    : entry.phase === 'points' ? 1200
    : entry.phase === 'calc' ? 0
    : entry.phase === 'card_set' ? 600
    : 400
  animTimer.value = setTimeout(processNextAnimEntry, delay)
}

const togglePause = () => {
  if (animPaused.value) {
    animPaused.value = false
    processNextAnimEntry()
  } else {
    animPaused.value = true
    if (animTimer.value) {
      clearTimeout(animTimer.value)
      animTimer.value = null
    }
  }
}

const updateTurnVisual = (entry: LogEntry) => {
  const v = entry.visual
  if (!v) return

  if (entry.phase === 'card_set') {
    turnVisual.value = { round: entry.round, statsKey: 0, damageKey: 0, breakKey: 0 }
    _statsKey = 0; _damageKey = 0; _breakKey = 0
    return
  }

  if (entry.phase === 'points') {
    _statsKey++
    turnVisual.value = {
      ...turnVisual.value,
      round: entry.round,
      stats: {
        creatorAtk: v.creatorAtk ?? 0,
        creatorDef: v.creatorDef ?? 0,
        creatorDod: v.creatorDod ?? 0,
        joinerAtk: v.joinerAtk ?? 0,
        joinerDef: v.joinerDef ?? 0,
        joinerDod: v.joinerDod ?? 0,
      },
      damage: undefined,
      cardBreak: undefined,
      statsKey: _statsKey,
      damageKey: 0,
      breakKey: 0,
    }
    return
  }

  if (entry.phase === 'calc') {
    return
  }

  if (entry.phase === 'hurt') {
    _damageKey++
    turnVisual.value = {
      ...turnVisual.value,
      damage: {
        creatorHurt: v.creatorHurt ?? 0,
        joinerHurt: v.joinerHurt ?? 0,
        creatorDodged: v.creatorDodged ?? false,
        joinerDodged: v.joinerDodged ?? false,
        creatorDefended: v.creatorDefSuccess ?? false,
        joinerDefended: v.joinerDefSuccess ?? false,
      },
      damageKey: _damageKey,
    }
    return
  }

  if (entry.phase === 'card_break') {
    _breakKey++
    turnVisual.value = {
      round: entry.round,
      stats: turnVisual.value.stats,
      cardBreak: v.whoBroke,
      breakSource: v.breakSource,
      statsKey: turnVisual.value.statsKey,
      damageKey: 0, breakKey: _breakKey,
    }
    return
  }
}

const finishAnimation = () => {
  turnVisual.value = { round: 0, statsKey: 0, damageKey: 0, breakKey: 0 }
  _statsKey = 0; _damageKey = 0; _breakKey = 0
  if (battle.value?.finished) {
    battlePhase.value = 'finished'
  } else if (battle.value?.creator?.shouldChangeCard()) {
    battlePhase.value = 'playing'
    chosenCardIndex.value = -1
  } else {
    battlePhase.value = 'playing'
  }
}

const handleQuickBattle = () => {
  try {
    const b = new Battle(Number(userId.value) || 1)
    b.setCreator('你')
    b.creator.chosenCards = getRandomCards(5)
    b.setSingleEnemy('AI对手', getRandomCards(5))
    b.runFullBattle()
    battle.value = b
    displayedLog.value = b.log.entries
    animCreatorHp.value = b.creator.nowHp
    animJoinerHp.value = b.joiner.nowHp
    animCreatorMaxHp.value = b.creator.nowCard?.cardHp ?? 1
    animJoinerMaxHp.value = b.joiner.nowCard?.cardHp ?? 1
    animCreatorCard.value = b.creator.nowCard
    animJoinerCard.value = b.joiner.nowCard
    animCreatorEffects.value = b.creator.effects.map(e => e.toData())
    animJoinerEffects.value = b.joiner.effects.map(e => e.toData())
    turnVisual.value = { round: 0, statsKey: 0, damageKey: 0, breakKey: 0 }
    _statsKey = 0; _damageKey = 0; _breakKey = 0
    logCollapsed.value = false
    battlePhase.value = 'finished'
    activeTab.value = 'turnbased'
  } catch (e) {
    console.error('快速对战失败', e)
  }
}

const handleSurrender = async () => {
  try {
    await ElMessageBox.confirm('确定要投降吗？', '确认', { type: 'warning' })
    if (battle.value) {
      battle.value.winnerId = battle.value.joinerId
      battle.value.finished = true
      battle.value.state = Battle.STATE_FINISHED
      battle.value.log.add(battle.value.gameRound, 'end', '你投降了！AI对手 获胜！', battle.value.creator.nowHp, battle.value.joiner.nowHp)
      displayedLog.value = [...battle.value.log.entries]
      battlePhase.value = 'finished'
    }
  } catch {}
}

const resetSelection = () => { selectedCards.value = []; battlePhase.value = 'idle'; currentSelectRound.value = 0 }
const resetBattle = () => {
  if (animTimer.value) clearTimeout(animTimer.value)
  animPaused.value = false; animEntries = []; animIndex = 0
  battle.value = null; battlePhase.value = 'idle'
  selectedCards.value = []; currentSelectRound.value = 0
  chosenCardIndex.value = -1; displayedLog.value = []; isFirstCard.value = true
  turnVisual.value = { round: 0, statsKey: 0, damageKey: 0, breakKey: 0 }; _statsKey = 0; _damageKey = 0; _breakKey = 0
  logCollapsed.value = false
}

onMounted(() => {})
onUnmounted(() => { if (animTimer.value) clearTimeout(animTimer.value) })
</script>

<style scoped>
.battle-container { max-width: 900px; margin: 0 auto; }
.battle-card { border-radius: 12px; }
.card-header h2 { margin: 0; font-size: 22px; }
.section-desc { color: #909399; margin-bottom: 20px; }
.quick-battle-section { text-align: center; padding: 40px 0; }
.selection-progress { margin-bottom: 16px; text-align: center; }
.candidate-cards { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 20px; }
.candidate-card { width: 200px; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.candidate-card.selected { border-color: #409eff; box-shadow: 0 0 10px rgba(64,158,255,0.3); }
.candidate-card:hover { transform: translateY(-4px); }
.card-name { font-size: 16px; font-weight: bold; margin-bottom: 8px; }
.card-stats { display: flex; flex-wrap: wrap; gap: 8px; font-size: 13px; color: #606266; margin-bottom: 8px; }
.card-desc { font-size: 12px; color: #909399; border-top: 1px solid #ebeef5; padding-top: 8px; }
.selected-cards-list { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 20px; }
.selected-tag { font-size: 14px; }
.battle-actions { display: flex; gap: 12px; justify-content: center; }
.battle-field { padding: 0; }
.turnbased-section { text-align: center; }
.idle-section { padding: 40px 0; }
.battle-players { display: flex; justify-content: center; align-items: center; gap: 20px; margin-bottom: 16px; }
.player-panel { flex: 1; max-width: 300px; text-align: center; }
.player-panel h4 { margin: 0 0 8px 0; }
.hp-bar { margin-bottom: 8px; }
.current-card { margin-bottom: 8px; display: flex; align-items: center; gap: 6px; justify-content: center; }
.card-index { font-size: 12px; color: #909399; }
.effects-list { display: flex; gap: 4px; justify-content: center; flex-wrap: wrap; }
.effect-tag { font-size: 11px; }
.vs-badge { font-size: 24px; font-weight: bold; color: #909399; flex-shrink: 0; }
.hand-cards { display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-bottom: 16px; }
.hand-card { width: 180px; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.hand-card.chosen { border-color: #409eff; box-shadow: 0 0 10px rgba(64,158,255,0.3); }
.hand-card:hover { transform: translateY(-4px); }
.play-actions { display: flex; gap: 12px; justify-content: center; margin-bottom: 16px; }
.animating-controls { display: flex; align-items: center; gap: 8px; }
.battle-log { max-height: 300px; overflow-y: auto; text-align: left; padding: 8px; background: #f5f7fa; border-radius: 8px; }
.log-entry { display: flex; align-items: flex-start; gap: 8px; padding: 4px 0; font-size: 13px; border-bottom: 1px solid #ebeef5; }
.log-entry:last-child { border-bottom: none; }
.log-round { flex-shrink: 0; min-width: 32px; }
.log-message { white-space: pre-wrap; word-break: break-word; }
.log-phase-card_break { color: #f56c6c; }
.log-phase-card_set { color: #67c23a; }
.log-phase-end { color: #e6a23c; font-weight: bold; }
.result-section { text-align: center; }
.result-section > * { margin-bottom: 16px; }
.codex-section { padding: 0; }
.codex-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.codex-card { border-radius: 8px; }
.codex-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.codex-card-name { font-weight: bold; font-size: 14px; }
.codex-card-stats { display: flex; flex-wrap: wrap; gap: 6px; font-size: 12px; color: #606266; margin-bottom: 6px; }
.codex-card-desc { font-size: 12px; color: #909399; border-top: 1px solid #ebeef5; padding-top: 6px; }

.battle-visual {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 12px;
  padding: 20px 24px;
  margin: 12px 0;
  position: relative;
  overflow: hidden;
  min-height: 80px;
}
.visual-round-badge {
  position: absolute;
  top: 8px;
  right: 12px;
  background: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.7);
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: bold;
}
.visual-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
  animation: visualFadeIn 0.3s ease-out;
}
.stat-side {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-radius: 8px;
}
.creator-side { background: rgba(244, 67, 54, 0.15); }
.joiner-side { background: rgba(33, 150, 243, 0.15); }
.stat-name {
  font-size: 14px;
  font-weight: bold;
  color: rgba(255,255,255,0.9);
  min-width: 28px;
}
.stat-item {
  font-size: 15px;
  font-weight: bold;
  padding: 2px 8px;
  border-radius: 4px;
}
.stat-item.atk { color: #ff6b6b; background: rgba(255,107,107,0.15); }
.stat-item.def { color: #4ecdc4; background: rgba(78,205,196,0.15); }
.stat-item.dod { color: #95e1d3; background: rgba(149,225,211,0.15); }
.stat-separator {
  color: rgba(255,255,255,0.4);
  font-size: 20px;
}

.visual-attack {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  animation: visualFadeIn 0.3s ease-out;
}
.attack-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: 8px;
  background: rgba(255,255,255,0.06);
  font-size: 15px;
  animation: attackSlideIn 0.4s ease-out;
}
.attack-from, .attack-to {
  color: rgba(255,255,255,0.85);
  font-weight: bold;
  min-width: 28px;
  text-align: center;
}
.attack-arrow {
  color: #ffd93d;
  font-size: 16px;
}
.attack-miss {
  color: #69f0ae;
  font-weight: bold;
  font-size: 18px;
  animation: missPop 0.5s ease-out;
  text-shadow: 0 0 10px rgba(105,240,174,0.5);
}
.attack-defend {
  font-size: 16px;
}
.attack-damage {
  color: #ff6b6b;
  font-weight: bold;
  font-size: 20px;
  animation: damagePop 0.5s ease-out;
  text-shadow: 0 0 10px rgba(255,107,107,0.4);
}
.attack-damage.big-damage {
  font-size: 26px;
  color: #ff1744;
  text-shadow: 0 0 16px rgba(255,23,68,0.6);
  animation: damagePopBig 0.6s ease-out;
}

.visual-card-break {
  text-align: center;
  padding: 16px;
  animation: breakShake 0.6s ease-out;
}
.break-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
}
.break-text {
  color: #ff6b6b;
  font-size: 18px;
  font-weight: bold;
  text-shadow: 0 0 12px rgba(255,107,107,0.4);
}

.log-divider { margin: 12px 0; }

@keyframes visualFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes attackSlideIn {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes damagePop {
  0% { opacity: 0; transform: scale(0.5); }
  50% { opacity: 1; transform: scale(1.3); }
  100% { opacity: 1; transform: scale(1); }
}
@keyframes damagePopBig {
  0% { opacity: 0; transform: scale(0.3); }
  40% { opacity: 1; transform: scale(1.5); }
  70% { transform: scale(0.95); }
  100% { opacity: 1; transform: scale(1); }
}
@keyframes missPop {
  0% { opacity: 0; transform: scale(0.5) rotate(-10deg); }
  50% { opacity: 1; transform: scale(1.2) rotate(5deg); }
  100% { opacity: 1; transform: scale(1) rotate(0deg); }
}
@keyframes breakShake {
  0% { opacity: 0; transform: scale(0.8); }
  20% { opacity: 1; transform: scale(1.1) rotate(-3deg); }
  40% { transform: scale(1.05) rotate(3deg); }
  60% { transform: scale(1) rotate(-2deg); }
  80% { transform: scale(1) rotate(1deg); }
  100% { transform: scale(1) rotate(0deg); }
}
</style>
