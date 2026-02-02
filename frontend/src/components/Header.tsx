'use client'

import { Phone } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200">
      <div className="bg-white">
        <div className="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="bg-[#D67E2E] p-2 rounded">
              <div className="text-white font-bold text-2xl leading-none">P</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">PartSelect</div>
              <div className="text-xs bg-[#4A7C7E] text-white px-2 py-0.5 rounded">
                Here to help since 1999
              </div>
            </div>
          </div>

          {/* Phone Number */}
          <div className="flex items-center gap-2 text-gray-900">
            <Phone className="w-5 h-5" />
            <div className="text-right">
              <div className="font-bold text-lg">1-866-319-8402</div>
              <div className="text-xs text-gray-600">Monday to Saturday 8am - 8pm EST</div>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
