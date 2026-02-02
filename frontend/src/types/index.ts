export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  validationScore?: number
}

export interface ChatRequest {
  message: string
  session_id?: string
  enable_validation?: boolean
  validation_threshold?: number
}

export interface ChatResponse {
  response: string
  session_id: string
  validation_score?: number
  function_calls?: any[]
  timestamp: string
}

export interface Part {
  part_id: string
  part_name: string
  mpn_id: string
  brand: string
  price: number
  availability: string
  install_difficulty?: string
  install_time?: string
  product_url: string
  install_video_url?: string
  appliance_type: string
}
