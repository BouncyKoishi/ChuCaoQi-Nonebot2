type MessageHandler = (data: any) => void
type ConnectionHandler = () => void

class FarmWebSocket {
  private ws: WebSocket | null = null
  private userId: string = ''
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectDelay = 1000
  private pingInterval: number | null = null
  private reconnectTimeout: number | null = null
  private messageHandlers: Map<string, MessageHandler[]> = new Map()
  private onConnectHandlers: ConnectionHandler[] = []
  private onDisconnectHandlers: ConnectionHandler[] = []
  private isPageVisible = true
  private shouldReconnect = true

  constructor() {
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => {
        this.isPageVisible = document.visibilityState === 'visible'
        if (this.isPageVisible && !this.isConnected() && this.shouldReconnect) {
          console.log('页面变为可见，尝试重连')
          this.reconnectAttempts = 0
          this.attemptReconnect()
        }
      })

      window.addEventListener('beforeunload', () => {
        this.shouldReconnect = false
        this.disconnect()
      })
    }
  }

  connect(userId: string) {
    if (!userId) {
      console.error('WebSocket connect failed: userId is empty')
      return
    }

    if (this.ws && this.ws.readyState !== WebSocket.CLOSED) {
      this.disconnect()
    }

    this.shouldReconnect = true
    this.offAll()

    this.userId = userId
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.PROD ? window.location.host : 'localhost:8000'
    const basePath = import.meta.env.PROD ? '/kusa' : ''
    const wsUrl = `${protocol}//${host}${basePath}/ws/farm/${userId}`

    try {
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket连接成功')
        this.reconnectAttempts = 0
        this.startPing()
        this.onConnectHandlers.forEach(handler => handler())
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)

          // 全局处理生草完毕通知
          if (message.type === 'kusa_harvested' && message.data) {
            const data = message.data
            // 使用 Element Plus 的全局通知
            import('element-plus').then(({ ElNotification }) => {
              ElNotification.success({
                title: '生草完毕！',
                message: `你的${data.kusaType}生了出来！获得了${data.kusaResult}草${data.advKusaResult ? `，额外获得${data.advKusaResult}草之精华` : ''}`,
                duration: 8000,
                showClose: true
              })
            })
          }

          const handlers = this.messageHandlers.get(message.type) || []
          handlers.forEach(handler => handler(message.data || message))
        } catch (e) {
          console.error('WebSocket消息解析失败:', e)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket连接关闭')
        this.stopPing()
        this.onDisconnectHandlers.forEach(handler => handler())
        if (this.shouldReconnect) {
          this.attemptReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
      }
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      if (this.shouldReconnect) {
        this.attemptReconnect()
      }
    }
  }

  disconnect() {
    this.shouldReconnect = false
    this.stopPing()
    this.clearReconnectTimeout()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  private attemptReconnect() {
    if (!this.isPageVisible) {
      console.log('页面不可见，暂停重连')
      return
    }

    if (!this.userId) {
      console.log('userId为空，停止重连')
      return
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log(`已达到最大重连次数(${this.maxReconnectAttempts})，停止重连`)
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * this.reconnectAttempts, 30000)
    console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，${delay / 1000}秒后...`)

    this.clearReconnectTimeout()
    this.reconnectTimeout = window.setTimeout(() => {
      if (this.shouldReconnect && this.isPageVisible && this.userId) {
        this.connect(this.userId)
      }
    }, delay)
  }

  private clearReconnectTimeout() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
  }

  private startPing() {
    this.pingInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)
  }

  private stopPing() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  on(event: string, handler: MessageHandler) {
    if (!this.messageHandlers.has(event)) {
      this.messageHandlers.set(event, [])
    }
    this.messageHandlers.get(event)!.push(handler)
  }

  off(event: string, handler: MessageHandler) {
    const handlers = this.messageHandlers.get(event)
    if (handlers) {
      const index = handlers.indexOf(handler)
      if (index > -1) {
        handlers.splice(index, 1)
      }
    }
  }

  offAll(event?: string) {
    if (event) {
      this.messageHandlers.set(event, [])
    } else {
      this.messageHandlers.clear()
    }
    this.onConnectHandlers = []
    this.onDisconnectHandlers = []
  }

  onConnect(handler: ConnectionHandler) {
    this.onConnectHandlers.push(handler)
  }

  onDisconnect(handler: ConnectionHandler) {
    this.onDisconnectHandlers.push(handler)
  }

  requestStatus() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'get_status' }))
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

export const farmWebSocket = new FarmWebSocket()
