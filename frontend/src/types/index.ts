export interface UserInfo {
  userId: number
  qq: string
  name: string | null
  title: string | null
  kusa: number
  advKusa: number
  vipLevel: number
  isSuperAdmin: boolean
  isRobot: boolean
  relatedQQ: string | null
  lastUseTime: string | null
}

export interface UserItem {
  item: Item
  amount: number
  allowUse: boolean
  timeLimitTs: number | null
}

export interface WarehouseInfo {
  user: UserInfo
  items: UserItem[]
}

export interface Item {
  name: string
  detail: string | null
  type: string | null
  isControllable: boolean
  isTransferable: boolean
  shopPrice: number | null
  sellingPrice: number | null
  priceRate: number | null
  priceType: string | null
  amountLimit: number | null
  shopPreItems: string | null
}

export interface GrowInfo {
  finishTimestamp: number
  predictFinishTime: string
  remainingSeconds: number
  kusaResult: number
  advKusaResult: number
  isPrescient: boolean
}

export interface KusaField {
  userId: number
  qq: string
  kusaFinishTs: number | null
  isUsingKela: boolean
  isPrescient: boolean
  isMirroring: boolean
  overloadOnHarvest: boolean
  biogasEffect: number
  soilCapacity: number
  weedCosting: number
  kusaResult: number
  advKusaResult: number
  kusaType: string | null
  defaultKusaType: string
  lastUseTime: string | null
  fieldAmount: number
  doubleMagic: boolean
  spiritualSign: boolean
  spiritualSignEffective: boolean
  kusaTypeEffect: number
  fallowSign: number
  spareCapacity: number
  kelaAvailable: boolean
  biogasAvailable: boolean
  hasPrescient: boolean
  kusaQualityLevel: number
  kusaQualityEffect: number
  quantityEffect: number
  vipLevel: number
  vipBonus: number
  predictKusaMin: number
  predictKusaMax: number
  predictAdvKusa: number
  isOverloaded: boolean
  isGrowing: boolean
  growInfo: GrowInfo | null
  hasBlackTea: boolean
  overloadEndTime?: string
  spiritualMachineAvailable: boolean
}

export interface KusaHistory {
  kusaType: string
  kusaResult: number
  advKusaResult: number
  createTimeTs: number
  createTime: string
}

export interface GValue {
  cycle: number
  turn: number
  eastValue: number
  southValue: number
  northValue: number
  zhuhaiValue: number
  shenzhenValue: number
  createTime: string
  areas?: {
    [key: string]: {
      current: number
      change: number
    }
  }
  holdings?: {
    [key: string]: {
      amount: number
      value: number
    }
  }
  totalValue?: number
  isTradingTime?: boolean
}

export interface GValueHistory {
  turn: number
  eastValue: number
  southValue: number
  northValue: number
  zhuhaiValue: number
  shenzhenValue: number
  createTime: string
}

export interface GValueHistoryResponse {
  history: GValueHistory[]
}
