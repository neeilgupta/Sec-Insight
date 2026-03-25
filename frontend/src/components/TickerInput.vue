<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{ isStreaming: boolean }>()
const emit = defineEmits<{
  submit: [query: string, collectionName: string]
}>()

const ticker = ref('')
const filingType = ref('10-K')
const queryText = ref('')

// Hardcoded to the most recently indexed filing date for v1
const FILING_DATE = '2024-09-28'

const collectionName = computed(
  () => `${ticker.value.toUpperCase()}_${filingType.value}_${FILING_DATE}`,
)

function handleSubmit() {
  const q = queryText.value.trim()
  const t = ticker.value.trim()
  if (!q || !t || props.isStreaming) return
  emit('submit', q, collectionName.value)
  queryText.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="ticker-input">
    <div class="ticker-row">
      <input
        v-model="ticker"
        class="ticker-field"
        placeholder="Ticker (e.g. AAPL)"
        :disabled="isStreaming"
        maxlength="10"
      />
      <select v-model="filingType" class="filing-select" :disabled="isStreaming">
        <option>10-K</option>
        <option>10-Q</option>
      </select>
    </div>
    <div class="query-row">
      <textarea
        v-model="queryText"
        class="query-field"
        placeholder="Ask a question about this filing…"
        rows="2"
        :disabled="isStreaming"
        @keydown="handleKeydown"
      />
      <button class="submit-btn" :disabled="isStreaming || !queryText.trim() || !ticker.trim()" @click="handleSubmit">
        {{ isStreaming ? '…' : 'Ask' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.ticker-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}

.ticker-row {
  display: flex;
  gap: 8px;
}

.ticker-field {
  width: 140px;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  text-transform: uppercase;
}

.filing-select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.query-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.query-field {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  resize: none;
  font-family: inherit;
}

.query-field:focus,
.ticker-field:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.submit-btn {
  padding: 8px 20px;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
