import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PartSelect Chatbot - Find Appliance Parts',
  description: 'AI-powered chatbot to help you find dishwasher and refrigerator replacement parts',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
