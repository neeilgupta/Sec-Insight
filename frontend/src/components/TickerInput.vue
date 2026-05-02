<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ isStreaming: boolean }>()
const emit = defineEmits<{
  submit: [query: string, collectionName: string]
}>()

const collections = ref<string[]>([])
const selectedCollection = ref('')
const queryText = ref('')
const isLoading = ref(true)

onMounted(async () => {
  try {
    const base = import.meta.env.VITE_API_BASE ?? ''
    const resp = await fetch(`${base}/api/collections`)
    const data = await resp.json()
    collections.value = data.collections
    if (collections.value.length > 0) {
      selectedCollection.value = collections.value[0]
    }
  } finally {
    isLoading.value = false
  }
})

function formatCollection(name: string): string {
  // "AAPL_10-K_2024-09-28" → "AAPL · 10-K · 2024-09-28"
  return name.replace(/_/g, ' · ')
}

function handleSubmit() {
  const q = queryText.value.trim()
  if (!q || !selectedCollection.value || props.isStreaming) return
  emit('submit', q, selectedCollection.value)
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
    <div class="input-row">
      <div class="select-wrapper">
        <span class="select-prefix">FILING</span>
        <select
          v-model="selectedCollection"
          class="collection-select"
          :disabled="isStreaming || isLoading"
        >
          <option v-if="isLoading" value="" disabled>Loading filings…</option>
          <option v-else-if="collections.length === 0" value="" disabled>No filings indexed yet</option>
          <option
            v-for="col in collections"
            :key="col"
            :value="col"
          >{{ formatCollection(col) }}</option>
        </select>
        <span class="select-chevron">▾</span>
      </div>

      <div class="query-wrapper">
        <textarea
          v-model="queryText"
          class="query-field"
          placeholder="Ask a question about this filing…"
          rows="1"
          :disabled="isStreaming"
          @keydown="handleKeydown"
        />
        <button
          class="submit-btn"
          :disabled="isStreaming || !queryText.trim() || !selectedCollection"
          @click="handleSubmit"
        >
          <span v-if="isStreaming" class="btn-spinner" />
          <span v-else>Ask ↵</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ticker-input {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.input-row {
  display: flex;
  gap: 10px;
  align-items: stretch;
}

.select-wrapper {
  display: flex;
  align-items: center;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  transition: border-color 0.15s;
}

.select-wrapper:focus-within {
  border-color: var(--amber);
  box-shadow: 0 0 0 2px var(--amber-soft);
}

.select-prefix {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  color: var(--amber);
  padding: 0 10px;
  border-right: 1px solid var(--border);
  white-space: nowrap;
}

.collection-select {
  padding: 8px 28px 8px 12px;
  background: transparent;
  border: none;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-primary);
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  min-width: 200px;
}

.collection-select:focus {
  outline: none;
}

.collection-select option {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.collection-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.select-chevron {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: 10px;
  pointer-events: none;
  flex-shrink: 0;
}

.query-wrapper {
  flex: 1;
  display: flex;
  gap: 8px;
  align-items: center;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0 6px 0 12px;
  transition: border-color 0.15s;
}

.query-wrapper:focus-within {
  border-color: var(--amber);
  box-shadow: 0 0 0 2px var(--amber-soft);
}

.query-field {
  flex: 1;
  background: transparent;
  border: none;
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--text-primary);
  resize: none;
  padding: 8px 0;
  line-height: 1.5;
}

.query-field::placeholder {
  color: var(--text-muted);
}

.query-field:focus {
  outline: none;
}

.query-field:disabled {
  opacity: 0.5;
}

.submit-btn {
  flex-shrink: 0;
  padding: 6px 16px;
  background: var(--amber);
  color: #07090D;
  border: none;
  border-radius: 6px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  height: 32px;
}

.submit-btn:hover:not(:disabled) {
  background: #FFB830;
  box-shadow: 0 0 12px var(--amber-glow);
}

.submit-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(7, 9, 13, 0.3);
  border-top-color: #07090D;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
