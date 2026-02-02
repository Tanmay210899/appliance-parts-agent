'use client'

import Header from '@/components/Header'
import ChatInterface from '@/components/ChatInterface'

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1">
        <ChatInterface />
      </main>
    </div>
  )
}
