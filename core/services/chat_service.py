"""
聊天和大模型审核服务模块

包含所有与大模型交互相关的业务逻辑
"""

import os
import re
import asyncio
import datetime
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union
from openai import OpenAI, APIConnectionError, RateLimitError

from core.config import plugin_config


@dataclass
class TextPart:
    """文本内容块（对应持久化 JSON 的 {"type":"text","text":...}）"""
    text: str

    def to_dict(self) -> dict:
        return {"type": "text", "text": self.text}

    @classmethod
    def from_dict(cls, data: dict) -> "TextPart":
        return cls(text=data.get("text", ""))


@dataclass
class ImagePart:
    """图片内容块（对应持久化 JSON 的 {"type":"image_url","image_url":{"url":...}}）"""
    url: str

    def to_dict(self) -> dict:
        return {"type": "image_url", "image_url": {"url": self.url}}

    @classmethod
    def from_dict(cls, data: dict) -> "ImagePart":
        return cls(url=data.get("image_url", {}).get("url", ""))


@dataclass
class ChatMessage:
    """对话历史中的一条消息

    与持久化 JSON 严格保形：content 为纯字符串（assistant 回复）或
    TextPart/ImagePart 列表（system/user 含多模态内容），并保留可选 botRoleName。
    """
    role: str
    content: Union[str, list]
    botRoleName: str = ''

    def to_dict(self) -> dict:
        """序列化为与旧版持久化格式完全一致的 dict"""
        d = {"role": self.role}
        if self.botRoleName:
            d["botRoleName"] = self.botRoleName
        if isinstance(self.content, str):
            d["content"] = self.content
        else:
            d["content"] = [
                part.to_dict() if isinstance(part, (TextPart, ImagePart)) else part
                for part in self.content
            ]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        """从持久化 dict 还原，兼容旧存档中的 str 与 parts 两种 content"""
        content = data.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if not isinstance(part, dict):
                    parts.append(part)
                elif part.get("type") == "text":
                    parts.append(TextPart.from_dict(part))
                elif part.get("type") == "image_url":
                    parts.append(ImagePart.from_dict(part))
                else:
                    parts.append(part)  # 未知类型原样保留，保证向前兼容
            content = parts
        return cls(
            role=data.get("role", ""),
            content=content,
            botRoleName=data.get("botRoleName", ""),
        )


# DeepSeek 抓不到历史消息里的图片时会整请求 400，报错带坏图 URL
# （形如 ".messages[0].image[0]: Failed to download image from <url>"，
# Responses API 为 "input[0].image[0]: ..."），据此剔除该图后重试。
# URL 以引号或空白为界：服务端 body 是整段 JSON，URL 后面通常跟着 "'"，而非字符串结尾。
IMAGE_EXPIRED_PLACEHOLDER = '（图片已失效，已忽略）'
_IMAGE_DOWNLOAD_FAIL_RE = re.compile(r"Failed to download image from (https?://[^\s'\"]+)")


@dataclass
class ChatReply:
    """大模型回复的统一结果对象

    Chat Completions 与 Responses 两条调用路径共同产出此结构，
    外部消费方只需读取类型化字段，无需关心底层是哪种 API。
    """
    reply: str
    token_usage: int
    reasoning_text: str = ''
    finish_reason: str = ''
    prompt_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0


class ChatService:
    """聊天和审核服务类"""
    
    # 模型配置（仅保留可用的 deepseek / lzusa 两家）
    _deepseek_client: Optional[OpenAI] = None
    _lzusa_client: Optional[OpenAI] = None

    @staticmethod
    def _init_clients():
        """初始化模型客户端（以 deepseek 客户端作为初始化哨兵）"""
        if ChatService._deepseek_client is not None:
            return
        web_config = plugin_config.get('web', {})
        proxy = web_config.get('proxy', '')

        deepseek_key = web_config.get('deepseek', {}).get('key', '')
        lzusa_key = web_config.get('lzusa', {}).get('key', '')
        lzusa_base_url = web_config.get('lzusa', {}).get('base_url', '')

        deepseek_base_url = "https://api.deepseek.com"

        # 设置代理环境变量（所有模型统一使用代理）
        if proxy:
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy

        # 重试统一放在 get_chat_reply，避免 SDK 默认重试与业务重试叠加
        ChatService._deepseek_client = OpenAI(
            api_key=deepseek_key, base_url=deepseek_base_url, max_retries=0)
        if lzusa_key and lzusa_base_url:
            ChatService._lzusa_client = OpenAI(
                api_key=lzusa_key, base_url=lzusa_base_url, max_retries=0)
    
    @staticmethod
    def _get_client(model: str) -> tuple[OpenAI, str]:
        """根据模型名称获取对应的客户端和实际模型名

        只有 lzusa 走本地兼容端点，其余模型统一走 deepseek。
        """
        ChatService._init_clients()
        if model == 'lzusa' or model.startswith('lzusa:'):
            if ChatService._lzusa_client is None:
                raise ValueError("lzusa 客户端未配置（缺少 web.lzusa.key 或 base_url）")
            actual_model = 'qwen-35b' if model == 'lzusa' else model.split(':', 1)[1]
            if not actual_model:
                raise ValueError("lzusa 模型名不能为空")
            return ChatService._lzusa_client, actual_model
        if ChatService._deepseek_client is None:
            raise ValueError("deepseek 客户端未配置（缺少 web.deepseek.key）")
        return ChatService._deepseek_client, model

    @staticmethod
    def _use_responses_api(model: str) -> bool:
        """判断模型是否走 Responses API 路由

        deepseek 走 Responses API（支持思维链档位控制）；
        lzusa 无 OpenAI 兼容的 /responses 端点，继续 Chat Completions。
        """
        return not (model == 'lzusa' or model.startswith('lzusa:'))

    @staticmethod
    def _coerce_messages(messages: list) -> list[ChatMessage]:
        """把消息统一转换为 ChatMessage，兼容直接传 dict 的调用方"""
        return [
            m if isinstance(m, ChatMessage) else ChatMessage.from_dict(m)
            for m in messages
        ]

    @staticmethod
    def parse_expired_image_url(error) -> Optional[str]:
        """从 400 报错里取出下载失败的图片 URL；其它错误返回 None（调用方原样抛出）

        优先读 SDK 解析好的 body，避免依赖 str(error) 的 JSON repr 细节。
        """
        message = ''
        body = getattr(error, 'body', None)
        if isinstance(body, dict):
            err = body.get('error')
            if isinstance(err, dict):
                message = str(err.get('message') or '')
            elif body.get('message'):
                message = str(body['message'])
        if not message:
            message = str(error or '')
        match = _IMAGE_DOWNLOAD_FAIL_RE.search(message)
        return match.group(1).replace('&amp;', '&') if match else None

    @staticmethod
    def drop_image_parts(messages: list[ChatMessage], url: str) -> int:
        """原地剔除该 URL 的图片块并返回数量；消息被删空时补占位文本"""
        if not url:
            return 0
        removed = 0
        for msg in messages:
            if not isinstance(msg.content, list):
                continue
            kept = [p for p in msg.content if not (isinstance(p, ImagePart) and p.url == url)]
            if len(kept) == len(msg.content):
                continue
            removed += len(msg.content) - len(kept)
            # 空 content 会被 Responses 丢弃、被 Chat Completions 拒收
            msg.content = kept or [TextPart(text=IMAGE_EXPIRED_PLACEHOLDER)]
        return removed

    @staticmethod
    def _messages_to_responses_input(messages: list[ChatMessage]) -> list:
        """把 ChatMessage 列表转换为 Responses API 的 input items"""
        items = []
        for msg in messages:
            parts = []
            if isinstance(msg.content, str):
                parts.append({"type": "input_text", "text": msg.content})
            else:
                for part in msg.content or []:
                    if isinstance(part, TextPart):
                        parts.append({"type": "input_text", "text": part.text})
                    elif isinstance(part, ImagePart):
                        if part.url:
                            parts.append({"type": "input_image", "image_url": part.url})
                    elif isinstance(part, dict):  # 兼容未知类型的 part
                        ptype = part.get('type')
                        if ptype == 'text':
                            parts.append({"type": "input_text", "text": part.get('text', '')})
                        elif ptype == 'image_url':
                            url = part.get('image_url', {}).get('url', '')
                            if url:
                                parts.append({"type": "input_image", "image_url": url})
            if parts:
                items.append({"type": "message", "role": msg.role, "content": parts})
        return items

    @staticmethod
    def _normalize_responses(response_dict: dict) -> ChatReply:
        """把 Responses API 响应解析为 ChatReply"""
        reply_text = ''
        reasoning_text = ''
        for item in response_dict.get('output', []):
            if item.get('type') == 'reasoning':
                for s in item.get('summary') or []:
                    if s.get('type') == 'summary_text':
                        reasoning_text += s.get('text') or ''
            elif item.get('type') == 'message':
                for content in item.get('content') or []:
                    if content.get('type') == 'output_text':
                        reply_text += content.get('text') or ''
        status = response_dict.get('status')
        finish_reason = 'stop' if status == 'completed' else (status or '')
        usage = response_dict.get('usage') or {}
        details = usage.get('output_tokens_details') or {}
        in_details = usage.get('input_tokens_details') or {}
        return ChatReply(
            reply=reply_text,
            token_usage=usage.get('total_tokens', 0),
            reasoning_text=reasoning_text,
            finish_reason=finish_reason,
            prompt_tokens=usage.get('input_tokens', 0),
            output_tokens=usage.get('output_tokens', 0),
            reasoning_tokens=details.get('reasoning_tokens', 0),
            cached_tokens=in_details.get('cached_tokens', 0),
        )

    @staticmethod
    def _normalize_chat_completions(response_dict: dict) -> ChatReply:
        """把 Chat Completions 响应解析为 ChatReply"""
        choice = (response_dict.get('choices') or [{}])[0]
        message = choice.get('message') or {}
        usage = response_dict.get('usage') or {}
        details = usage.get('completion_tokens_details') or {}
        prompt_details = usage.get('prompt_tokens_details') or {}
        return ChatReply(
            reply=message.get('content'),
            token_usage=usage.get('total_tokens', 0),
            reasoning_text=message.get('reasoning_content', ''),
            finish_reason=choice.get('finish_reason', ''),
            prompt_tokens=usage.get('prompt_tokens', 0),
            output_tokens=usage.get('completion_tokens', 0),
            reasoning_tokens=details.get('reasoning_tokens', 0),
            cached_tokens=prompt_details.get('cached_tokens', 0),
        )

    @staticmethod
    async def get_chat_reply(model: str, messages: list,
                             reasoning_effort: Optional[str] = "none",
                             source: str = "general") -> ChatReply:
        """获取大模型回复

        Args:
            model: 模型名称
            messages: 消息历史列表
            reasoning_effort: 推理档位。deepseek-flash 为推理型模型，默认 none 关闭推理以免
                每注都烧几百上千 token；``chat`` 等需要思考的场景显式传 ``low``。
                可选: none/minimal/low/medium/high/xhigh/max（注意没有 disabled）。
            source: 请求来源标识（chat/strange_word/trigrams/moderate_content 等），用于日志。

        Returns:
            ChatReply: 回复内容 / token使用量 / 思维链文本 / 结束原因
        """
        client, actual_model = ChatService._get_client(model)
        messages = ChatService._coerce_messages(messages)

        loop = asyncio.get_running_loop()

        def _is_retryable(error) -> bool:
            """只重试限流、连接/超时和 5xx；400/401/403/404 等直接失败"""
            status = getattr(error, 'status_code', None)
            return (
                isinstance(error, (RateLimitError, APIConnectionError))
                or (isinstance(status, int) and (status in (408, 409, 429) or status >= 500))
            )

        def _get_response():
            if ChatService._use_responses_api(model):
                kwargs = dict(
                    model=actual_model,
                    input=ChatService._messages_to_responses_input(messages),
                    reasoning={"effort": reasoning_effort},
                    timeout=120,
                )
                try:
                    return client.responses.create(**kwargs), True
                except Exception as e:
                    # 图片抓取失败与 API 形态无关，交给调用方做图片自愈
                    if ChatService.parse_expired_image_url(e):
                        raise
                    # 只有端点不存在时才回退；认证/限流/参数错误回退只会再失败一次
                    if getattr(e, 'status_code', None) not in (404, 405):
                        raise
                    print(f"[ChatService] {model} 的 /responses 端点不可用，回退 Chat Completions: {e}")

            kwargs = dict(
                messages=[m.to_dict() for m in messages], model=actual_model, timeout=120
            )
            return client.chat.completions.create(**kwargs), False

        response = None
        used_responses = False
        for attempt in range(2):
            try:
                response, used_responses = await loop.run_in_executor(None, _get_response)
                break
            except Exception as e:
                if attempt == 0 and _is_retryable(e):
                    print(f"[ChatService] {model} 调用失败"
                          f"({getattr(e, 'status_code', None) or type(e).__name__})，1 秒后重试一次: {e}")
                    await asyncio.sleep(1)
                    continue
                raise

        if response is None:
            raise RuntimeError("大模型调用未返回结果")
        response_dict = response.to_dict()
        if used_responses:
            result = ChatService._normalize_responses(response_dict)
        else:
            result = ChatService._normalize_chat_completions(response_dict)

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[LLM] {now} src={source} model={model} "
              f"input={result.prompt_tokens} output={result.output_tokens} "
              f"reasoning={result.reasoning_tokens} cached={result.cached_tokens} "
              f"total={result.token_usage} finish={result.finish_reason}")
        return result
    
    @staticmethod
    async def moderate_content(text: str) -> Dict[str, Any]:
        """使用大模型审核内容
        
        Args:
            text: 需要审核的文本
            
        Returns:
            {
                'passed': bool,  # 是否通过
                'reason': str,    # 原因（如果未通过）
                'category': str   # 违规类别（political/pornographic/other）
            }
        """
        system_prompt = """你是一个内容审核专家。请仔细审核用户提供的文本，判断是否包含以下违规内容：
1. 中国政治敏感信息：涉及中国共产党、中国政府、中国领导人、台湾、西藏、新疆、香港等敏感政治话题
2. 色情信息：露骨的色情描写、性暗示等

请以JSON格式返回结果，格式如下：
{
    "passed": true/false,
    "reason": "如果未通过，请简要说明原因",
    "category": "political/pornographic/other"
}

注意：
- 只有明显违规的内容才标记为不通过
- category只能是political、pornographic或other中的一个
- 如果内容没问题，passed为true，reason为空字符串，category为other"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
        
        try:
            reply = (await ChatService.get_chat_reply(
                "deepseek-flash", messages, source="moderate_content")).reply
            
            import json
            result = json.loads(reply)
            
            return {
                'passed': bool(result.get('passed', True)),
                'reason': str(result.get('reason', '')),
                'category': str(result.get('category', 'other'))
            }
        except Exception as e:
            error_str = str(e)
            print(f"[审核API错误] 内容审核API调用失败: {error_str}")
            
            # Deepseek 内容安全拦截（如包含敏感政治内容）
            if 'Content Exists Risk' in error_str:
                return {
                    'passed': False,
                    'reason': '包含敏感内容',
                    'category': 'political'
                }
            
            return {
                'passed': False,
                'api_error': True,
                'error_msg': error_str
            }
