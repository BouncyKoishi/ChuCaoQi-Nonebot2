import type { Battler, EffectData } from './engine';
import { Border, Effect, registerEffects } from './engine';

class StrengthEffect extends Effect {
  id = 'Strength'; displayName = '强化'; effectType = 'BUFF' as const
  onAttackCalc(value: number): number {
    this.infoMsg = `[${this.userName}]攻击增加了${this.amount}点！\n`
    return value + this.amount
  }
}

class WeakenEffect extends Effect {
  id = 'Weaken'; displayName = '弱化'; effectType = 'DEBUFF' as const
  onAttackCalc(value: number): number {
    this.infoMsg = `[${this.userName}]攻击减少了${this.amount}点！\n`
    return value - this.amount
  }
}

class StableEffect extends Effect {
  id = 'Stable'; displayName = '稳固'; effectType = 'BUFF' as const
  onDefenceCalc(value: number): number {
    this.infoMsg = `[${this.userName}]防御增加了${this.amount}点！\n`
    return value + this.amount
  }
}

class FragileEffect extends Effect {
  id = 'Fragile'; displayName = '脆弱'; effectType = 'DEBUFF' as const
  onDefenceCalc(value: number): number {
    this.infoMsg = `[${this.userName}]防御减少了${this.amount}点！\n`
    return value - this.amount
  }
}

class AgileEffect extends Effect {
  id = 'Agile'; displayName = '灵动'; effectType = 'BUFF' as const
  onDodgeCalc(value: number): number {
    this.infoMsg = `[${this.userName}]回避增加了${this.amount}点！\n`
    return value + this.amount
  }
}

class SluggishEffect extends Effect {
  id = 'Sluggish'; displayName = '迟缓'; effectType = 'DEBUFF' as const
  onDodgeCalc(value: number): number {
    this.infoMsg = `[${this.userName}]回避减少了${this.amount}点！\n`
    return value - this.amount
  }
}

class BufferEffect extends Effect {
  id = 'Buffer'; displayName = '缓冲'; effectType = 'BUFF' as const
  onHurtValueCalc(value: number): number {
    if (value > 0) {
      this.infoMsg = `[${this.userName}]受缓冲层保护，受到的伤害减少${this.amount}点\n`
      return value - this.amount
    }
    return value
  }
}

class ChaseEffect extends Effect {
  id = 'Chase'; displayName = '追击'; effectType = 'BUFF' as const
  onAttackDamageCalc(value: number): number {
    if (value > 0) {
      this.infoMsg = `[${this.enemyName}]被敌方符卡追击，额外受到${this.amount}点伤害！\n`
      return value + this.amount
    }
    return value
  }
}

class TraceEffect extends Effect {
  id = 'Trace'; displayName = '追踪'; effectType = 'BUFF' as const
  onAttackDamageCalc(value: number): number {
    if (value === 0) {
      this.infoMsg = `[${this.enemyName}]闪避成功，但被敌方符卡追踪，受到${this.amount}点伤害！\n`
      return value + this.amount
    }
    return value
  }
}

class ShieldEffect extends Effect {
  id = 'Shield'; displayName = '护盾'; effectType = 'BUFF' as const
  beforeHurt(value: number): number {
    if (value > 0) {
      const reduceDmg = Math.min(this.amount, value)
      this.infoMsg = `[${this.userName}]消耗了${reduceDmg}点护盾，吸收了${reduceDmg}点伤害！\n`
      this.reduce(reduceDmg)
      return value - reduceDmg
    }
    return value
  }
}

class UnbreakableEffect extends Effect {
  id = 'Unbreakable'; displayName = '击破保护'; effectType = 'BUFF' as const
  beforeHurt(value: number): number {
    if (value >= this.userHp) {
      this.infoMsg = `[${this.userName}]的击破保护触发，免疫本次伤害！\n`
      this.amount -= 1
      return 0
    }
    return value
  }
}

class FreezeEffect extends Effect {
  id = 'Freeze'; displayName = '冻结'; effectType = 'DEBUFF' as const
  onTurnStart(user: Battler, _enemy: Battler): void {
    this.infoMsg = `${user.name}正被冰冻中，本回合无法进行攻击/防御/回避，所有非结界效果不触发！\n`
    user.states.push('Frozen')
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void {
    this.reduce(1)
    if (this.amount <= 0) {
      const idx = this.user?.states.indexOf('Frozen') ?? -1
      if (idx >= 0) this.user!.states.splice(idx, 1)
    }
  }
  onCardBreak(_user: Battler, _enemy: Battler): void {
    this.reduce(1)
    if (this.amount <= 0) {
      const idx = this.user?.states.indexOf('Frozen') ?? -1
      if (idx >= 0) this.user!.states.splice(idx, 1)
    }
  }
}

class CantDefenceEffect extends Effect {
  id = 'CantDefence'; displayName = '防御不可'; effectType = 'DEBUFF' as const
  onDefenceSuccessJudge(_success: boolean): boolean {
    this.infoMsg = `[${this.userName}]受符卡效果影响，无法作出防御\n`
    return false
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void {
    if (this.amount > 0) this.reduce(1)
  }
}

class CantDodgeEffect extends Effect {
  id = 'CantDodge'; displayName = '回避不可'; effectType = 'DEBUFF' as const
  onDodgeSuccessJudge(_success: boolean): boolean {
    this.infoMsg = `[${this.userName}]受符卡效果影响，无法进行回避\n`
    return false
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void {
    if (this.amount > 0) this.reduce(1)
  }
}

class StrengthBorder extends Border {
  id = 'StrengthBorder'; displayName = '强化结界'
  onAttackCalc(value: number): number {
    this.infoMsg = `[结界][${this.userName}]攻击增加了${this.strength}点！\n`
    return value + this.strength
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void { this.reduce() }
}

class WeakenBorder extends Border {
  id = 'WeakenBorder'; displayName = '弱化结界'
  onAttackCalc(value: number): number {
    this.infoMsg = `[结界][${this.userName}]攻击减少了${this.strength}点！\n`
    return value - this.strength
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void { this.reduce() }
}

class StableBorder extends Border {
  id = 'StableBorder'; displayName = '稳固结界'
  onDefenceCalc(value: number): number {
    this.infoMsg = `[结界][${this.userName}]防御增加了${this.strength}点！\n`
    return value + this.strength
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void { this.reduce() }
}

class FragileBorder extends Border {
  id = 'FragileBorder'; displayName = '脆弱结界'
  onDefenceCalc(value: number): number {
    this.infoMsg = `[结界][${this.userName}]防御减少了${this.strength}点！\n`
    return value - this.strength
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void { this.reduce() }
}

class AgileBorder extends Border {
  id = 'AgileBorder'; displayName = '灵动结界'
  onDodgeCalc(value: number): number {
    this.infoMsg = `[结界][${this.userName}]回避增加了${this.strength}点！\n`
    return value + this.strength
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void { this.reduce() }
}

class SluggishBorder extends Border {
  id = 'SluggishBorder'; displayName = '迟缓结界'
  onDodgeCalc(value: number): number {
    this.infoMsg = `[结界][${this.userName}]回避减少了${this.strength}点！\n`
    return value - this.strength
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void { this.reduce() }
}

class DamageBorder extends Border {
  id = 'DamageBorder'; displayName = '伤害结界'
  onTurnStart(_user: Battler, enemy: Battler): void {
    this.infoMsg = `[结界]伤害结界：[${enemy.name}]受到${this.strength}点直接伤害\n`
    this.infoMsg += enemy.effectHurt(this.strength)
  }
  onTurnEnd(_user: Battler, _enemy: Battler): void { this.reduce() }
}

class ComboEffect extends Effect {
  id = 'Combo'; displayName = '连击'; effectType = 'BUFF' as const
  onAttackCalc(value: number): number {
    if (this.enemy && this.enemy.nowHp < this.enemy.nowCard!.cardHp) {
      this.infoMsg = `[${this.userName}]连击触发，对方符卡已受伤，攻击力+${this.amount}！\n`
      return value + this.amount
    }
    return value
  }
}

class DesperateAtkEffect extends Effect {
  id = 'DesperateAtk'; displayName = '背水'; effectType = 'BUFF' as const
  onAttackCalc(value: number): number {
    if (this.userHp <= 3) {
      this.infoMsg = `[${this.userName}]背水触发，HP≤3，攻击力+${this.amount}！\n`
      return value + this.amount
    }
    return value
  }
}

class DesperateDodEffect extends Effect {
  id = 'DesperateDod'; displayName = '绝境'; effectType = 'BUFF' as const
  onDodgeCalc(value: number): number {
    if (this.userHp <= 3) {
      this.infoMsg = `[${this.userName}]绝境触发，HP≤3，闪避+${this.amount}！\n`
      return value + this.amount
    }
    return value
  }
}

class ThornsEffect extends Effect {
  id = 'Thorns'; displayName = '荆棘'; effectType = 'BUFF' as const
  onBattleHurt(value: number): number {
    if (value > 0 && this.enemy) {
      const reflected = Math.min(this.amount, value)
      this.enemy.effectHurt(reflected)
      this.infoMsg = `[${this.userName}]荆棘反弹${reflected}点伤害！\n`
    }
    return value
  }
}

class DrainEffect extends Effect {
  id = 'Drain'; displayName = '吸血'; effectType = 'BUFF' as const
}

const ALL_EFFECTS: Record<string, new (...args: any[]) => Effect> = {
  Strength: StrengthEffect,
  Weaken: WeakenEffect,
  Stable: StableEffect,
  Fragile: FragileEffect,
  Agile: AgileEffect,
  Sluggish: SluggishEffect,
  Buffer: BufferEffect,
  Chase: ChaseEffect,
  Trace: TraceEffect,
  Shield: ShieldEffect,
  Unbreakable: UnbreakableEffect,
  Freeze: FreezeEffect,
  CantDefence: CantDefenceEffect,
  CantDodge: CantDodgeEffect,
  StrengthBorder: StrengthBorder,
  WeakenBorder: WeakenBorder,
  StableBorder: StableBorder,
  FragileBorder: FragileBorder,
  AgileBorder: AgileBorder,
  SluggishBorder: SluggishBorder,
  DamageBorder: DamageBorder,
  Combo: ComboEffect,
  DesperateAtk: DesperateAtkEffect,
  DesperateDod: DesperateDodEffect,
  Thorns: ThornsEffect,
  Drain: DrainEffect,
}

registerEffects(ALL_EFFECTS)

export const EFFECT_DESC: Record<string, string> = {
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

export function getEffectTooltip(eff: EffectData): string {
  const desc = EFFECT_DESC[eff.id]
  if (!desc) return `${eff.displayName} (${eff.effectType})`
  return desc
    .replace('{n}', String(eff.amount))
    .replace('{s}', String(eff.strength ?? 0))
    .replace('{t}', String(eff.turns ?? 0))
}
