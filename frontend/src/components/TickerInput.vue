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
    const resp = await fetch('/api/collections')
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
    <div class="ticker-row">
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
      <button
        class="submit-btn"
        :disabled="isStreaming || !queryText.trim() || !selectedCollection"
        @click="handleSubmit"
      >
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

.collection-select {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.collection-select:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
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

.query-field:focus {
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
