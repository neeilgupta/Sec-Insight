<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { Message } from '../types'
import MessageBubble from './MessageBubble.vue'
import StreamingResponse from './StreamingResponse.vue'

defineProps<{
  messages: Message[]
  isStreaming: boolean
  streamingContent: string
}>()

const emit = defineEmits<{
  highlightSource: [index: number]
}>()

const scrollEl = ref<HTMLElement | null>(null)

watch(
  () => [scrollEl.value, document.documentElement.scrollTop],
  async () => {
    await nextTick()
    if (scrollEl.value) {
      scrollEl.value.scrollTop = scrollEl.value.scrollHeight
    }
  },
)

// Also scroll when streaming content grows
defineExpose({ scrollToBottom })

async function scrollToBottom() {
  await nextTick()
  if (scrollEl.value) {
    scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  }
}
</script>

<template>
  <div ref="scrollEl" class="chat-window">
    <div v-if="!messages.length && !isStreaming" class="empty-state">
      <div class="empty-icon">▸</div>
      <p class="empty-title">Start querying SEC filings</p>
      <p class="empty-sub">Select a company filing above and ask any financial question.</p>
      <div class="example-queries">
        <span class="example-label">Try asking:</span>
        <div class="examples">
          <span class="example-pill">"What were the primary risk factors?"</span>
          <span class="example-pill">"Summarize revenue and net income for FY2024"</span>
          <span class="example-pill">"What does management say about AI strategy?"</span>
          <span class="example-pill">"Describe the liquidity and capital resources"</span>
        </div>
      </div>
    </div>

    <MessageBubble
      v-for="(msg, i) in messages"
      :key="i"
      :role="msg.role"
      :content="msg.content"
      :sources="msg.sources"
      @highlight-source="emit('highlightSource', $event)"
    />

    <StreamingResponse v-if="isStreaming" :content="streamingContent" />
  </div>
</template>

<style scoped>
.chat-window {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: var(--bg-base);
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.chat-window::-webkit-scrollbar {
  width: 4px;
}

.chat-window::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}

.empty-state {
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 48px 32px;
  max-width: 560px;
}

.empty-icon {
  font-size: 28px;
  color: var(--amber);
  font-family: var(--font-mono);
  margin-bottom: 16px;
  animation: pulse 2.4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.empty-title {
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.empty-sub {
  margin: 0 0 28px;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
}

.example-queries {
  width: 100%;
  text-align: left;
}

.example-label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  display: block;
  margin-bottom: 10px;
}

.examples {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.example-pill {
  display: block;
  padding: 8px 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-left: 2px solid var(--amber-dim);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
  line-height: 1.4;
}
</style>
