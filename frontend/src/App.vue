<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Message, SourceChunk } from './types'
import { useSSE } from './composables/useSSE'
import TickerInput from './components/TickerInput.vue'
import ChatWindow from './components/ChatWindow.vue'
import SourcePanel from './components/SourcePanel.vue'
import ComparisonView from './components/ComparisonView.vue'

const mode = ref<'chat' | 'compare'>('chat')

const messages = ref<Message[]>([])
const sessionId = ref('')
const highlightedSource = ref<number | null>(null)

const { isStreaming, streamingContent, sources, query } = useSSE()

const chatWindow = ref<InstanceType<typeof ChatWindow> | null>(null)

onMounted(() => {
  sessionId.value = crypto.randomUUID()
})

async function handleSubmit(queryText: string, collectionName: string) {
  // Add user message immediately
  messages.value.push({ role: 'user', content: queryText })
  highlightedSource.value = null

  await chatWindow.value?.scrollToBottom()

  // Stream the response
  const fullReply = await query(queryText, collectionName, sessionId.value)

  // Commit to message history with sources attached
  messages.value.push({
    role: 'assistant',
    content: fullReply,
    sources: sources.value.length ? [...sources.value] : undefined,
  })

  await chatWindow.value?.scrollToBottom()
}

function handleHighlightSource(index: number) {
  highlightedSource.value = index
}
</script>

<template>
  <div class="app">
    <header class="app-header">
      <span class="logo">SEC Insight</span>
      <span class="subtitle">Financial filing Q&amp;A</span>
      <button class="mode-toggle" @click="mode = mode === 'chat' ? 'compare' : 'chat'">
        {{ mode === 'chat' ? 'Compare' : '← Chat' }}
      </button>
    </header>

    <template v-if="mode === 'chat'">
      <TickerInput :is-streaming="isStreaming" @submit="handleSubmit" />

      <div class="main">
        <ChatWindow
          ref="chatWindow"
          :messages="messages"
          :is-streaming="isStreaming"
          :streaming-content="streamingContent"
          @highlight-source="handleHighlightSource"
        />
        <SourcePanel :sources="sources" :highlighted="highlightedSource" />
      </div>
    </template>

    <ComparisonView v-else />
  </div>
</template>

<style>
*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #fff;
  color: #111827;
}

#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: #6366f1;
}

.subtitle {
  font-size: 13px;
  color: #9ca3af;
}

.mode-toggle {
  margin-left: auto;
  padding: 5px 12px;
  background: transparent;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
}

.mode-toggle:hover {
  border-color: #6366f1;
  color: #6366f1;
}

.main {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
