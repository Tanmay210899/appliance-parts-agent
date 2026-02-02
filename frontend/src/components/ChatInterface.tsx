'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, MessageSquare, RotateCcw, Trash2 } from 'lucide-react'
import api from '@/lib/api'
import { ChatMessage } from '@/types'
import MessageBubble from './MessageBubble'

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Create session on mount
    const initSession = async () => {
      try {
        const data = await api.createSession()
        setSessionId(data.session_id)
        
        // Add welcome message
        setMessages([{
          role: 'assistant',
          content: "Hi! I'm your PartSelect assistant. I can help you find replacement parts for dishwashers and refrigerators. What are you looking for today?",
          timestamp: new Date()
        }])
      } catch (err) {
        setError('Failed to connect to the server. Please try again.')
        console.error('Failed to create session:', err)
      }
    }
    initSession()
  }, [])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const response = await api.chat({
        message: input,
        session_id: sessionId || undefined,
        enable_validation: true,  // Enable validation for quality
        validation_threshold: 70
      })

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.response,
        timestamp: new Date(response.timestamp),
        validationScore: response.validation_score
      }

      setMessages(prev => [...prev, assistantMessage])
      
      // Update session ID if it changed
      if (response.session_id !== sessionId) {
        setSessionId(response.session_id)
      }
    } catch (err: any) {
      console.error('Chat error:', err)
      setError(err.response?.data?.message || 'Failed to send message. Please try again.')
      
      // Add error message
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again or rephrase your question.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const resetChat = async () => {
    try {
      if (sessionId) {
        await api.deleteSession(sessionId)
      }
      const data = await api.createSession()
      setSessionId(data.session_id)
      setMessages([{
        role: 'assistant',
        content: "Chat reset! How can I help you find parts today?",
        timestamp: new Date()
      }])
      setError(null)
    } catch (err) {
      console.error('Failed to reset chat:', err)
    }
  }

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 80px)' }}>
      {/* Chat Title Bar */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-[#4A7C7E] p-2 rounded-full">
                <MessageSquare className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900">AI Parts Assistant</h2>
                <p className="text-xs text-gray-600">Ask me about appliance parts and repairs</p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={resetChat}
                className="flex items-center gap-2 px-3 py-1.5 bg-[#4A7C7E] hover:bg-[#3d6668] text-white rounded text-sm transition-colors"
                title="Start new conversation"
              >
                <RotateCcw className="w-4 h-4" />
                <span className="hidden sm:inline">New Chat</span>
              </button>
              <button
                onClick={() => window.location.reload()}
                className="flex items-center gap-2 px-3 py-1.5 bg-[#4A7C7E] hover:bg-[#3d6668] text-white rounded text-sm transition-colors"
                title="Refresh page"
              >
                <Trash2 className="w-4 h-4" />
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 py-6 space-y-4">
          {messages.map((message, index) => (
            <MessageBubble key={index} message={message} />
          ))}
          
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white rounded-2xl px-6 py-4 shadow-md flex items-center gap-3">
                <Loader2 className="w-5 h-5 animate-spin text-partselect-blue" />
                <span className="text-gray-600">Searching for parts...</span>
              </div>
            </div>
          )}
          
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-red-700 text-sm">
              {error}
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex gap-3 items-end">
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={(e) => {
                  // Allow default paste behavior
                  e.stopPropagation()
                }}
                placeholder="Ask about dishwasher or refrigerator parts..."
                rows={1}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded focus:outline-none focus:border-[#4A7C7E] resize-none"
                disabled={loading}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="bg-[#4A7C7E] text-white p-3 rounded hover:bg-[#3d6668] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          
          {/* Quick suggestions */}
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              "Show me dishwasher parts",
              "Refrigerator ice maker parts",
              "Parts under $50"
            ].map((suggestion, i) => (
              <button
                key={i}
                onClick={() => setInput(suggestion)}
                className="text-sm px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full hover:bg-[#4A7C7E] hover:text-white transition-colors border border-gray-300"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
