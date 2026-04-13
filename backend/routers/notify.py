"""
通知/WebSocket相关路由
"""

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(__file__) + '/../../bot')
os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'bot'))

from services import FarmService

# 从 backend 模块导入，避免与 bot 模块冲突
import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')
from websocket_manager import manager
from common import INTERNAL_API_TOKEN

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/farm/{userId}")
async def websocket_farm(websocket: WebSocket, userId: str):
    """生草地状态WebSocket端点"""
    await manager.connect(websocket, userId)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message.get("type") == "get_status":
                    status = await FarmService.get_status(userId=int(userId))
                    await websocket.send_json({
                        "type": "farm_status",
                        "data": status
                    })
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "无效的JSON格式"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, userId)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket, userId)


@router.post("/internal/notify")
async def internal_notify(request: Request):
    """内部通知接口，供Bot调用以推送WebSocket消息"""
    body = await request.json()
    token = body.get("token")
    if token != INTERNAL_API_TOKEN:
        return {"success": False, "error": "Invalid token"}
    
    userId = body.get("userId")
    message_type = body.get("type")
    data = body.get("data")
    
    if not userId or not message_type:
        return {"success": False, "error": "Missing required fields"}
    
    await manager.send_personal_message({
        "type": message_type,
        "data": data
    }, userId)
    
    return {"success": True}


@router.post("/api/notify/farm-status")
async def notify_farm_status(request: Request):
    """接收Bot插件的通知，广播农田状态更新到WebSocket客户端"""
    try:
        body = await request.json()
        userId = body.get('userId')
        if not userId:
            return {"success": False, "error": "userId不能为空"}
        
        logger.debug(f'收到 farm-status 通知，userId={userId}')
        
        status = await FarmService.get_status(userId=userId)
        
        await manager.send_personal_message({
            "type": "farm_status_update",
            "data": status
        }, str(userId))
        
        return {"success": True}
    except Exception as e:
        logger.error(f'通知农田状态更新失败: {e}')
        return {"success": False, "error": str(e)}


@router.post("/api/notify/kusa-harvested")
async def notify_kusa_harvested(request: Request):
    """接收Bot插件的通知，广播生草完毕消息到WebSocket客户端"""
    try:
        body = await request.json()
        userId = body.get('userId')
        kusa_type = body.get('kusaType', '草')
        kusa_result = body.get('kusaResult', 0)
        adv_kusa_result = body.get('advKusaResult', 0)
        soil_capacity = body.get('soilCapacity', 0)
        
        if not userId:
            return {"success": False, "error": "userId不能为空"}
        
        status = await FarmService.get_status(userId=userId)
        
        await manager.send_personal_message({
            "type": "kusa_harvested",
            "data": {
                "kusaType": kusa_type,
                "kusaResult": kusa_result,
                "advKusaResult": adv_kusa_result,
                "soilCapacity": soil_capacity,
                "isGrowing": False,
                **status
            }
        }, str(userId))
        
        return {"success": True}
    except Exception as e:
        logger.error(f'通知生草完毕失败: {e}')
        return {"success": False, "error": str(e)}
