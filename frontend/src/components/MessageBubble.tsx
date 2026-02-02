'use client'

import { ChatMessage } from '@/types'
import { User, Bot } from 'lucide-react'
import PartCard from './PartCard'

interface MessageBubbleProps {
  message: ChatMessage
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  
  // Parse message for parts (simple heuristic: look for patterns)
  const hasPartInfo = !isUser && (
    message.content.includes('$') || 
    message.content.includes('Product Page:') ||
    message.content.includes('partselect.com')
  )

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-10 h-10 rounded-full bg-[#4A7C7E] flex items-center justify-center flex-shrink-0">
          <Bot className="w-6 h-6 text-white" />
        </div>
      )}
      
      <div className={`max-w-3xl ${isUser ? 'order-1' : ''}`}>
        <div
          className={`rounded-2xl px-6 py-4 shadow-md ${
            isUser
              ? 'bg-[#4A7C7E] text-white'
              : 'bg-white text-gray-800'
          }`}
        >
          {hasPartInfo ? (
            <div className="space-y-4">
              <PartList content={message.content} />
            </div>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>
        
        <div className={`text-xs text-gray-500 mt-1 px-2 ${isUser ? 'text-right' : ''}`}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
      
      {isUser && (
        <div className="w-10 h-10 rounded-full bg-gray-300 flex items-center justify-center flex-shrink-0">
          <User className="w-6 h-6 text-gray-700" />
        </div>
      )}
    </div>
  )
}

// Component to parse and display parts from response
function PartList({ content }: { content: string }) {
  const lines = content.split('\n')
  const parts: any[] = []
  let currentPart: any = null
  let introText = ''
  let isIntro = true

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    
    if (!line) continue

    // Check for part name with part number in parentheses followed by price on next line
    // Format: "Part Name (PS12345)"
    const partMatch = line.match(/^(.+?)\s+\(([^)]+)\)\s*$/)
    
    if (partMatch && i + 1 < lines.length && lines[i + 1].includes('$')) {
      // This looks like a part title
      isIntro = false
      
      if (currentPart) {
        parts.push(currentPart)
      }
      
      currentPart = {
        name: partMatch[1].trim(),
        partNumber: partMatch[2].trim(),
        details: []
      }
      continue
    }
    
    if (currentPart) {
      // Collect details for current part (price, installation, product page)
      if (line.includes('$') || line.includes('Product Page:') || line.includes('Installation:') || line.includes('https://')) {
        currentPart.details.push(line)
      }
    } else if (isIntro) {
      introText += line + '\n'
    }
  }

  if (currentPart) {
    parts.push(currentPart)
  }

  return (
    <div className="space-y-4">
      {introText && <p className="mb-4 whitespace-pre-wrap">{introText.trim()}</p>}
      
      {parts.length > 0 ? (
        parts.map((part, index) => (
          <PartCard key={index} part={part} />
        ))
      ) : (
        <p className="whitespace-pre-wrap">{content}</p>
      )}
    </div>
  )
}
