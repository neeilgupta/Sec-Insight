<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Message } from './types'
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
      <div class="logo-group">
        <span class="logo-mark">▸</span>
        <span class="logo">SEC<span class="logo-accent">insight</span></span>
        <span class="logo-tag">Financial Filing Intelligence</span>
      </div>
      <nav class="header-nav">
        <button
          class="mode-btn"
          :class="{ active: mode === 'chat' }"
          @click="mode = 'chat'"
        >
          Chat
        </button>
        <button
          class="mode-btn"
          :class="{ active: mode === 'compare' }"
          @click="mode = 'compare'"
        >
          Compare
        </button>
      </nav>
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
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 52px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-mark {
  font-size: 18px;
  color: var(--amber);
  font-family: var(--font-mono);
  line-height: 1;
}

.logo {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: var(--text-primary);
  text-transform: uppercase;
  line-height: 1;
}

.logo-accent {
  color: var(--amber);
}

.logo-tag {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding-left: 12px;
  border-left: 1px solid var(--border);
  margin-left: 2px;
}

.header-nav {
  display: flex;
  gap: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 3px;
}

.mode-btn {
  padding: 5px 16px;
  border: none;
  border-radius: 5px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: var(--text-muted);
  transition: all 0.15s ease;
}

.mode-btn:hover {
  color: var(--text-secondary);
}

.mode-btn.active {
  background: var(--amber);
  color: #07090D;
  font-weight: 600;
}

.main {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}
</style>
