<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { SourceChunk } from '../types'

const props = defineProps<{
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChunk[]
}>()

const emit = defineEmits<{
  highlightSource: [index: number]
}>()

const rendered = computed(() => marked(props.content))
</script>

<template>
  <div class="message" :class="role">
    <div class="bubble">
      <p v-if="role === 'user'" class="user-content">{{ content }}</p>
      <div v-else class="markdown-body" v-html="rendered" />
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
  padding: 6px 20px;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

/* User bubble — amber */
.message.user .bubble {
  max-width: 68%;
  padding: 10px 16px;
  border-radius: 16px 16px 4px 16px;
  background: var(--amber);
  color: #07090D;
  font-size: 14px;
  line-height: 1.6;
}

/* Assistant bubble — dark card */
.message.assistant .bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 4px 16px 16px 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-left: 2px solid var(--amber-dim);
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-primary);
}

.user-content {
  margin: 0;
  word-break: break-word;
  font-weight: 500;
}

.citations {
  display: flex;
  gap: 5px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: var(--amber-soft);
  border: 1px solid var(--amber-dim);
  color: var(--amber);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.badge:hover {
  background: var(--amber-glow);
  border-color: var(--amber);
}
</style>
