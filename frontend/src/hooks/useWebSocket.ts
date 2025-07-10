import { useEffect, useRef, useState } from 'react'
import { ProgressUpdate } from '@/types'

export const useWebSocket = (jobId: string | null, onProgressUpdate?: (update: ProgressUpdate) => void) => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<ProgressUpdate | null>(null)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number>()

  const connect = () => {
    if (!jobId) return

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/jobs/${jobId}`
      
      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
      }

      ws.current.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data) as ProgressUpdate
          setLastUpdate(update)
          onProgressUpdate?.(update)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      ws.current.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        
        // Attempt to reconnect after 2 seconds
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect()
        }, 2000)
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
    }
  }

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    
    setIsConnected(false)
  }

  const sendPing = () => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send('ping')
    }
  }

  useEffect(() => {
    if (jobId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [jobId])

  // Send periodic pings to keep connection alive
  useEffect(() => {
    if (isConnected) {
      const pingInterval = setInterval(sendPing, 30000) // Every 30 seconds
      return () => clearInterval(pingInterval)
    }
  }, [isConnected])

  return {
    isConnected,
    lastUpdate,
    disconnect,
    connect
  }
}