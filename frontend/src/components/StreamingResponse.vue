<script setup lang="ts">
defineProps<{ content: string }>()
</script>

<template>
  <div class="streaming">
    <div class="bubble assistant">
      <span class="content">{{ content }}</span><span class="cursor" />
    </div>
  </div>
</template>

<style scoped>
.streaming {
  display: flex;
  justify-content: flex-start;
  padding: 4px 16px;
}

.bubble {
  max-width: 72%;
  padding: 10px 14px;
  border-radius: 12px;
  background: #f3f4f6;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: #6366f1;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 0.9s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}
</style>
