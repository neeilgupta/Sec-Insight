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
    <div v-if="!messages.length && !isStreaming" class="empty">
      Enter a ticker and ask a question to get started.
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
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty {
  margin: auto;
  color: #9ca3af;
  font-size: 14px;
  text-align: center;
  padding: 40px 16px;
}
</style>
