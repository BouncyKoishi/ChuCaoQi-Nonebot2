"""
WebSocket 连接管理器

使用单例模式确保全局只有一个管理器实例
"""

from fastapi import WebSocket
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, userId: str):
        """建立WebSocket连接"""
        await websocket.accept()
        if userId not in self.active_connections:
            self.active_connections[userId] = []
        self.active_connections[userId].append(websocket)
        logger.info(f"WebSocket连接建立: userId={userId}, 当前连接数={len(self.active_connections[userId])}")
    
    def disconnect(self, websocket: WebSocket, userId: str):
        """断开WebSocket连接"""
        if userId in self.active_connections:
            if websocket in self.active_connections[userId]:
                self.active_connections[userId].remove(websocket)
            if not self.active_connections[userId]:
                del self.active_connections[userId]
        logger.info(f"WebSocket连接断开: userId={userId}")
    
    async def send_personal_message(self, message: dict, userId: str):
        """向指定用户发送消息"""
        if userId not in self.active_connections:
            return
        
        dead_connections = []
        for connection in self.active_connections[userId]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"发送消息失败，标记连接为死亡: userId={userId}, error={e}")
                dead_connections.append(connection)
        
        # 清理死亡连接
        for conn in dead_connections:
            self.disconnect(conn, userId)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        for userId in list(self.active_connections.keys()):
            await self.send_personal_message(message, userId)
    
    def get_connection_count(self, userId: str = None) -> int:
        """获取连接数"""
        if userId:
            return len(self.active_connections.get(userId, []))
        return sum(len(connections) for connections in self.active_connections.values())


# 全局单例实例
manager = ConnectionManager()
