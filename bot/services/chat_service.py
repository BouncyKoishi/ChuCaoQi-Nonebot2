"""
聊天和大模型审核服务模块

包含所有与大模型交互相关的业务逻辑
"""

import sys
import os
import asyncio
from typing import Dict, Any, Optional
from openai import OpenAI

sys.path.insert(0, os.path.dirname(__file__) + '/..')

import dbConnection.kusa_system as baseDB
import dbConnection.chat as chatDB
from kusa_base import plugin_config


class ChatService:
    """聊天和审核服务类"""
    
    # 模型配置
    _openai_client: Optional[OpenAI] = None
    _deepseek_client: Optional[OpenAI] = None
    _gemini_client: Optional[OpenAI] = None
    
    @staticmethod
    def _init_clients():
        """初始化模型客户端"""
        if ChatService._openai_client is None:
            web_config = plugin_config.get('web', {})
            proxy = web_config.get('proxy', '')
            
            openai_key = web_config.get('openai', {}).get('key', '')
            deepseek_key = web_config.get('deepseek', {}).get('key', '')
            gemini_key = web_config.get('gemini', {}).get('key', '')
            
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
    
    @staticmethod
    def _get_client(model: str) -> OpenAI:
        """根据模型名称获取对应的客户端"""
        ChatService._init_clients()
        if 'deepseek' in model:
            return ChatService._deepseek_client
        elif 'gemini' in model:
            return ChatService._gemini_client
        else:
            return ChatService._openai_client
    
    @staticmethod
    async def get_chat_reply(model: str, messages: list) -> tuple[str, int, dict]:
        """获取大模型回复
        
        Args:
            model: 模型名称
            messages: 消息历史列表
            
        Returns:
            (回复内容, token使用量, 完整响应字典)
        """
        client = ChatService._get_client(model)
        
        loop = asyncio.get_event_loop()
        
        def _get_response():
            if 'deepseek' in model:
                return client.chat.completions.create(model=model, messages=messages, timeout=120)
            elif 'gemini' in model:
                return client.chat.completions.create(model=model, messages=messages, timeout=120)
            elif 'gpt-5' in model:
                return client.chat.completions.create(model=model, messages=messages, timeout=120, reasoning_effort="low")
            return client.chat.completions.create(model=model, messages=messages, timeout=120)
        
        response = await loop.run_in_executor(None, _get_response)
        response_dict = response.to_dict()
        reply = response_dict['choices'][0]['message']['content']
        token_usage = response_dict['usage']['total_tokens']
        
        return reply, token_usage, response_dict
    
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
            reply, _, _ = await ChatService.get_chat_reply("deepseek-chat", messages)
            
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
