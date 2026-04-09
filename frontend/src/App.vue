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

:root {
  --bg-base: #07090D;
  --bg-surface: #0D1117;
  --bg-elevated: #131920;
  --bg-hover: #1C2330;
  --border-subtle: #1A2332;
  --border: #243044;
  --border-strong: #3A4F66;

  --amber: #F0A020;
  --amber-dim: #B87800;
  --amber-soft: rgba(240, 160, 32, 0.10);
  --amber-glow: rgba(240, 160, 32, 0.20);

  --indigo: #7C8EF5;
  --indigo-soft: rgba(124, 142, 245, 0.10);

  --emerald: #00C48C;
  --emerald-soft: rgba(0, 196, 140, 0.10);

  --text-primary: #E2E8F0;
  --text-secondary: #7A8BA0;
  --text-muted: #3D4F63;

  --font-body: 'Plus Jakarta Sans', sans-serif;
  --font-display: 'Syne', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

body {
  margin: 0;
  font-family: var(--font-body);
  background: var(--bg-base);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

#app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Global markdown styles used across MessageBubble, StreamingResponse, ComparisonView */
.markdown-body p { margin: 0 0 8px; }
.markdown-body p:last-child { margin-bottom: 0; }
.markdown-body strong { font-weight: 600; color: var(--text-primary); }
.markdown-body em { font-style: italic; }
.markdown-body ul,
.markdown-body ol { padding-left: 20px; margin: 6px 0; }
.markdown-body li { margin: 3px 0; color: var(--text-secondary); }
.markdown-body h1,
.markdown-body h2,
.markdown-body h3 { font-weight: 600; margin: 12px 0 4px; color: var(--text-primary); }
.markdown-body h1 { font-size: 1.1em; }
.markdown-body h2 { font-size: 1em; }
.markdown-body h3 { font-size: 0.95em; }
.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
  font-size: 13px;
}
.markdown-body th,
.markdown-body td {
  border: 1px solid var(--border);
  padding: 6px 10px;
  text-align: left;
}
.markdown-body th {
  background: var(--bg-elevated);
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.markdown-body td { color: var(--text-secondary); }
.markdown-body code {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 0.88em;
  color: var(--amber);
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
