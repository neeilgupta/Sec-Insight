export interface SourceChunk {
  chunk_id: string
  text: string
  metadata: Record<string, string>
  rerank_score: number
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
}
