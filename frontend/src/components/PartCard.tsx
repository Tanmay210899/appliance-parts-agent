'use client'

import { ExternalLink, Play, Package, DollarSign, Award, Check } from 'lucide-react'

interface PartCardProps {
  part: {
    name: string
    partNumber: string
    details: string[]
  }
}

export default function PartCard({ part }: PartCardProps) {
  // Parse details
  const priceMatch = part.details.find(d => d.includes('$'))?.match(/\$[\d.]+/)
  const price = priceMatch ? priceMatch[0] : null
  
  const brandMatch = part.details.find(d => d.includes('|'))?.split('|')
  const brand = brandMatch ? brandMatch[1]?.trim() : null
  const availability = brandMatch ? brandMatch[2]?.trim() : null
  
  const productUrl = part.details.find(d => d.includes('Product Page:'))
    ?.replace('Product Page:', '').trim()
  
  const videoUrl = part.details.find(d => d.includes('Installation Video:'))
    ?.replace('Installation Video:', '').trim()
  
  const hasVideo = videoUrl && !videoUrl.includes('[Not Available]')

  return (
    <div className="border-2 border-gray-200 rounded-lg p-5 hover:border-[#4A7C7E] hover:shadow-xl transition-all bg-white">
      {/* Badges */}
      <div className="flex gap-2 mb-3">
        <div className="flex items-center gap-1 bg-green-50 text-green-700 text-xs px-2 py-1 rounded border border-green-200">
          <DollarSign className="w-3 h-3" />
          <span className="font-semibold">Price Match</span>
        </div>
        <div className="flex items-center gap-1 bg-blue-50 text-blue-700 text-xs px-2 py-1 rounded border border-blue-200">
          <Award className="w-3 h-3" />
          <span className="font-semibold">Official OEM</span>
        </div>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1">
          <h3 className="font-bold text-gray-900 text-base leading-tight hover:text-[#4A7C7E] cursor-pointer">
            {part.name}
          </h3>
          <p className="text-sm text-gray-600 mt-1.5 flex items-center gap-1">
            <Package className="w-4 h-4 text-gray-400" />
            Part #{part.partNumber}
          </p>
        </div>
        
        {price && (
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">
              {price}
            </div>
            {availability && availability.includes('In Stock') && (
              <div className="flex items-center gap-1 text-green-600 text-sm mt-1">
                <Check className="w-4 h-4" />
                <span className="font-semibold">{availability}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Info Pills */}
      <div className="flex flex-wrap gap-2 mb-4">
        {brand && (
          <span className="bg-gray-100 text-gray-700 text-sm px-3 py-1 rounded-full border border-gray-300 font-medium">
            {brand}
          </span>
        )}
        {availability && !availability.includes('In Stock') && (
          <span className="bg-yellow-50 text-yellow-700 text-sm px-3 py-1 rounded-full border border-yellow-300 font-medium">
            {availability}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-4">
        {productUrl && (
          <a
            href={productUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-[#F7B731] text-gray-900 px-4 py-2.5 rounded hover:bg-[#f5a815] transition-colors flex items-center justify-center gap-2 font-bold text-sm"
          >
            <ExternalLink className="w-4 h-4" />
            View Product
          </a>
        )}
        
        {hasVideo && (
          <a
            href={videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2.5 bg-white border-2 border-[#4A7C7E] text-[#4A7C7E] rounded hover:bg-[#4A7C7E] hover:text-white transition-colors font-bold text-sm"
          >
            <Play className="w-4 h-4" />
            Install Video
          </a>
        )}
      </div>
    </div>
  )
}
