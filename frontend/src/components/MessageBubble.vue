<script setup lang="ts">
import type { SourceChunk } from '../types'

defineProps<{
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
}>()

const emit = defineEmits<{
  highlightSource: [index: number]
}>()
</script>

<template>
  <div class="message" :class="role">
    <div class="bubble">
      <p class="content">{{ content }}</p>
      <div v-if="sources && sources.length" class="citations">
        <button
          v-for="(_, i) in sources"
          :key="i"
          class="badge"
          @click="emit('highlightSource', i)"
        >
          {{ i + 1 }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message {
  display: flex;
  padding: 4px 16px;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 72%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.message.user .bubble {
  background: #6366f1;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message.assistant .bubble {
  background: #f3f4f6;
  color: #111827;
  border-bottom-left-radius: 4px;
}

.content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.citations {
  display: flex;
  gap: 4px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e0e7ff;
  color: #4338ca;
  font-size: 11px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.badge:hover {
  background: #c7d2fe;
}
</style>
