"""QQ 官方适配器兼容层

腾讯会不定期新增事件 type，而 nonebot-adapter-qq 需要升级到对应版本才能识别。
在适配器升级前，这里集中登记"负载结构与已有事件一致"的新事件类型，
避免兼容逻辑散落在 bot.py 或各个插件里。

适配器原生支持某个类型后，这里的映射会自动跳过，可直接删除对应用户条目。
"""

import re
from typing import Any, Dict, List, Optional

from nonebot.log import logger


def install_qq_adapter_compat() -> None:
    """安装 QQ 官方适配器事件兼容映射，幂等。"""
    try:
        from nonebot.adapters.qq.event import EVENT_CLASSES, GroupAtMessageCreateEvent
        from nonebot.adapters.qq.message import Message as QQMessage
    except ImportError:
        return

    if "GROUP_MESSAGE_CREATE" not in EVENT_CLASSES:

        class GroupMessageCreateEvent(GroupAtMessageCreateEvent):
            """新版群消息事件：正文中的 <@openid> 占位需剥离后才能匹配指令"""

            __type__ = "GROUP_MESSAGE_CREATE"

            # 适配器未建模的引用字段，保留原始负载供 PlatformContext 解析引用
            message_type: Optional[int] = None
            message_scene: Optional[Dict[str, Any]] = None
            msg_elements: Optional[List[Dict[str, Any]]] = None
            parallel_message: Optional[Dict[str, Any]] = None

            def get_message(self) -> QQMessage:
                if not hasattr(self, "_message"):
                    content = re.sub(r"<@!?[^>]+>", "", self.content or "").strip()
                    cleaned = self.model_copy(update={"content": content})
                    setattr(self, "_message", QQMessage.from_qq_message(cleaned))
                return getattr(self, "_message")

        EVENT_CLASSES["GROUP_MESSAGE_CREATE"] = GroupMessageCreateEvent
        logger.info("[QQ兼容] 已注册 GROUP_MESSAGE_CREATE 兼容事件")
    else:
        logger.info("[QQ兼容] 适配器已原生支持 GROUP_MESSAGE_CREATE，跳过映射")
