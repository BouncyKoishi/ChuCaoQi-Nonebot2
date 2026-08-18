"""
聊天和大模型审核服务模块

包含所有与大模型交互相关的业务逻辑
"""

import sys
import os
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, Optional, Union
from openai import OpenAI


import core.db.kusa_system as baseDB
import core.db.chat as chatDB
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


class ChatService:
    """聊天和审核服务类"""
    
    # 模型配置
    _openai_client: Optional[OpenAI] = None
    _deepseek_client: Optional[OpenAI] = None
    _gemini_client: Optional[OpenAI] = None
    _lzusa_client: Optional[OpenAI] = None
    
    @staticmethod
    def _init_clients():
        """初始化模型客户端"""
        if ChatService._openai_client is None:
            web_config = plugin_config.get('web', {})
            proxy = web_config.get('proxy', '')
            
            openai_key = web_config.get('openai', {}).get('key', '')
            deepseek_key = web_config.get('deepseek', {}).get('key', '')
            gemini_key = web_config.get('gemini', {}).get('key', '')
            lzusa_key = web_config.get('lzusa', {}).get('key', '')
            lzusa_base_url = web_config.get('lzusa', {}).get('base_url', '')
            
            deepseek_base_url = "https://api.deepseek.com"
            gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            
            # 设置代理环境变量（所有模型统一使用代理）
            if proxy:
                os.environ["http_proxy"] = proxy
                os.environ["https_proxy"] = proxy
            
            # 初始化所有客户端
            ChatService._openai_client = OpenAI(api_key=openai_key)
            ChatService._gemini_client = OpenAI(api_key=gemini_key, base_url=gemini_base_url)
            ChatService._deepseek_client = OpenAI(api_key=deepseek_key, base_url=deepseek_base_url)
            if lzusa_key and lzusa_base_url:
                ChatService._lzusa_client = OpenAI(api_key=lzusa_key, base_url=lzusa_base_url)
    
    @staticmethod
    def _get_client(model: str) -> tuple[OpenAI, str]:
        """根据模型名称获取对应的客户端和实际模型名

        Returns:
            (client, actual_model_name)
        """
        ChatService._init_clients()
        if model == 'lzusa':
            return ChatService._lzusa_client, 'qwen-35b'
        if model.startswith('lzusa:'):
            return ChatService._lzusa_client, model.split(':', 1)[1]
        if 'deepseek' in model:
            return ChatService._deepseek_client, model
        elif 'gemini' in model:
            return ChatService._gemini_client, model
        else:
            return ChatService._openai_client, model
    
    @staticmethod
    def _use_responses_api(model: str) -> bool:
        """判断模型是否走 Responses API 路由

        deepseek / gpt 系列走 Responses API（支持联网搜索、思维链档位控制），
        gemini / lzusa 无 OpenAI 兼容的 /responses 端点，继续 Chat Completions。
        """
        return 'deepseek' in model or 'gpt' in model

    @staticmethod
    def _coerce_messages(messages: list) -> list[ChatMessage]:
        """把消息统一转换为 ChatMessage，兼容直接传 dict 的调用方"""
        return [
            m if isinstance(m, ChatMessage) else ChatMessage.from_dict(m)
            for m in messages
        ]

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
        return ChatReply(
            reply=reply_text,
            token_usage=(response_dict.get('usage') or {}).get('total_tokens', 0),
            reasoning_text=reasoning_text,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _normalize_chat_completions(response_dict: dict) -> ChatReply:
        """把 Chat Completions 响应解析为 ChatReply"""
        choice = (response_dict.get('choices') or [{}])[0]
        message = choice.get('message') or {}
        return ChatReply(
            reply=message.get('content'),
            token_usage=(response_dict.get('usage') or {}).get('total_tokens', 0),
            reasoning_text=message.get('reasoning_content', ''),
            finish_reason=choice.get('finish_reason', ''),
        )

    @staticmethod
    async def get_chat_reply(model: str, messages: list) -> ChatReply:
        """获取大模型回复
        
        Args:
            model: 模型名称
            messages: 消息历史列表
            
        Returns:
            ChatReply: 回复内容 / token使用量 / 思维链文本 / 结束原因
        """
        client, actual_model = ChatService._get_client(model)
        messages = ChatService._coerce_messages(messages)

        loop = asyncio.get_event_loop()
        
        def _get_response():
            # deepseek / gpt 走 Responses API，失败自动回退 Chat Completions
            if ChatService._use_responses_api(model):
                kwargs = dict(
                    model=actual_model,
                    input=ChatService._messages_to_responses_input(messages),
                    reasoning={"effort": "low"},
                    timeout=120,
                )
                try:
                    return client.responses.create(**kwargs), True
                except Exception as e:
                    print(f"[ChatService] {model} Responses API 调用失败，回退 Chat Completions: {e}")
                    return client.chat.completions.create(
                        messages=[m.to_dict() for m in messages], model=actual_model, timeout=120
                    ), False
            
            kwargs = dict(
                messages=[m.to_dict() for m in messages], model=actual_model, timeout=120
            )
            if 'gpt-5' in model:
                kwargs['reasoning_effort'] = "low"
            return client.chat.completions.create(**kwargs), False
        
        response, used_responses = await loop.run_in_executor(None, _get_response)
        response_dict = response.to_dict()
        if used_responses:
            return ChatService._normalize_responses(response_dict)
        return ChatService._normalize_chat_completions(response_dict)
    
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
            reply = (await ChatService.get_chat_reply("deepseek-v4-flash", messages)).reply
            
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
