<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps<{ content: string }>()

const rendered = computed(() => marked(props.content))
</script>

<template>
  <div class="streaming">
    <div class="bubble markdown-body" v-html="rendered" /><span class="cursor" />
  </div>
</template>

<style scoped>
.streaming {
  display: flex;
  justify-content: flex-start;
  align-items: flex-end;
  padding: 6px 20px;
}

.bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 4px 16px 16px 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-left: 2px solid var(--amber-dim);
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-primary);
  word-break: break-word;
}

.cursor {
  display: inline-block;
  width: 2px;
  height: 16px;
  background: var(--amber);
  margin-left: 3px;
  border-radius: 1px;
  vertical-align: text-bottom;
  animation: blink 0.85s step-end infinite;
  box-shadow: 0 0 6px var(--amber-glow);
  flex-shrink: 0;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
