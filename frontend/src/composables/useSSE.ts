import { ref } from 'vue'
import type { SourceChunk } from '../types'

export function useSSE() {
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const sources = ref<SourceChunk[]>([])

  async function query(
    queryText: string,
    collectionName: string,
    sessionId: string,
  ): Promise<string> {
    isStreaming.value = true
    streamingContent.value = ''
    sources.value = []

    const controller = new AbortController()

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          collection_name: collectionName,
          session_id: sessionId,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        // Keep the last (potentially incomplete) line in the buffer
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const event = JSON.parse(line.slice(6)) as {
            type: 'sources' | 'token' | 'done'
            chunks?: SourceChunk[]
            content?: string
          }

          if (event.type === 'sources' && event.chunks) {
            sources.value = event.chunks
          } else if (event.type === 'token' && event.content) {
            streamingContent.value += event.content
          } else if (event.type === 'done') {
            return streamingContent.value
          }
        }
      }

      return streamingContent.value
    } finally {
      isStreaming.value = false
    }
  }

  return { isStreaming, streamingContent, sources, query }
}
