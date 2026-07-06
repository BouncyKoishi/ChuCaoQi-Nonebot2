"""
共享核心域 - 纯工具函数
不依赖任何 bot 基础设施或 nonebot
"""


def rd3(floatNumber: float):
    return round(floatNumber, 3)


def romanNumToInt(romanNum):
    romanNum = romanNum.upper()
    romanNumList = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
    return romanNumList.index(romanNum) + 1 if romanNum in romanNumList else 0


def intToRomanNum(intNum):
    romanNumList = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
    return romanNumList[intNum - 1] if 0 < intNum <= 10 else ""
