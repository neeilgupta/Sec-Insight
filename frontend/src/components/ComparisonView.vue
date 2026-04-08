<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSSE } from '../composables/useSSE'
import StreamingResponse from './StreamingResponse.vue'
import ComparisonSourcePanel from './ComparisonSourcePanel.vue'

const collections = ref<string[]>([])
const isLoadingCollections = ref(true)
const collectionA = ref('')
const collectionB = ref('')
const queryText = ref('')

const sseA = useSSE()
const sseB = useSSE()

const completedA = ref('')
const completedB = ref('')
const highlightedA = ref<number | null>(null)
const highlightedB = ref<number | null>(null)

const sessionIdA = crypto.randomUUID()
const sessionIdB = crypto.randomUUID()

const isEitherStreaming = computed(() => sseA.isStreaming.value || sseB.isStreaming.value)

const canSubmit = computed(
  () => queryText.value.trim() && collectionA.value && collectionB.value && !isEitherStreaming.value,
)

onMounted(async () => {
  try {
    const resp = await fetch('/api/collections')
    const data = await resp.json()
    collections.value = data.collections
    if (collections.value.length >= 1) collectionA.value = collections.value[0]
    if (collections.value.length >= 2) collectionB.value = collections.value[1]
  } finally {
    isLoadingCollections.value = false
  }
})

function formatCollection(name: string): string {
  return name.replace(/_/g, ' · ')
}

async function handleSubmit() {
  const q = queryText.value.trim()
  if (!canSubmit.value) return
  completedA.value = ''
  completedB.value = ''
  highlightedA.value = null
  highlightedB.value = null
  queryText.value = ''
  await Promise.all([
    sseA.query(q, collectionA.value, sessionIdA).then(r => { completedA.value = r }),
    sseB.query(q, collectionB.value, sessionIdB).then(r => { completedB.value = r }),
  ])
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="comparison-view">
    <!-- Company selectors -->
    <div class="selectors">
      <div class="selector-group">
        <label class="selector-label">Company A</label>
        <select
          v-model="collectionA"
          class="collection-select indigo"
          :disabled="isLoadingCollections || isEitherStreaming"
        >
          <option v-if="isLoadingCollections" value="" disabled>Loading…</option>
          <option v-else-if="!collections.length" value="" disabled>No filings indexed</option>
          <option v-for="col in collections" :key="col" :value="col">
            {{ formatCollection(col) }}
          </option>
        </select>
      </div>

      <div class="selector-group">
        <label class="selector-label">Company B</label>
        <select
          v-model="collectionB"
          class="collection-select emerald"
          :disabled="isLoadingCollections || isEitherStreaming"
        >
          <option v-if="isLoadingCollections" value="" disabled>Loading…</option>
          <option v-else-if="!collections.length" value="" disabled>No filings indexed</option>
          <option v-for="col in collections" :key="col" :value="col">
            {{ formatCollection(col) }}
          </option>
        </select>
      </div>
    </div>

    <!-- Shared query input -->
    <div class="query-bar">
      <textarea
        v-model="queryText"
        class="query-field"
        placeholder="Ask the same question about both companies…"
        rows="2"
        :disabled="isEitherStreaming"
        @keydown="handleKeydown"
      />
      <button class="submit-btn" :disabled="!canSubmit" @click="handleSubmit">
        {{ isEitherStreaming ? '…' : 'Ask' }}
      </button>
    </div>

    <!-- Side-by-side response columns -->
    <div class="columns response-columns">
      <!-- Column A -->
      <div class="column">
        <div v-if="isLoadingCollections" class="col-empty">Loading filings…</div>
        <div v-else-if="!sseA.streamingContent.value && !completedA" class="col-empty">
          Ask a question to compare responses.
        </div>
        <StreamingResponse v-else-if="sseA.isStreaming.value" :content="sseA.streamingContent.value" />
        <div v-else class="response-bubble">{{ completedA }}</div>
      </div>

      <!-- Column B -->
      <div class="column">
        <div v-if="isLoadingCollections" class="col-empty">Loading filings…</div>
        <div v-else-if="!sseB.streamingContent.value && !completedB" class="col-empty">
          Ask a question to compare responses.
        </div>
        <StreamingResponse v-else-if="sseB.isStreaming.value" :content="sseB.streamingContent.value" />
        <div v-else class="response-bubble">{{ completedB }}</div>
      </div>
    </div>

    <!-- Side-by-side source panels -->
    <div class="columns source-columns">
      <ComparisonSourcePanel
        :sources="sseA.sources.value"
        :highlighted="highlightedA"
        color="indigo"
      />
      <ComparisonSourcePanel
        :sources="sseB.sources.value"
        :highlighted="highlightedB"
        color="emerald"
      />
    </div>
  </div>
</template>

<style scoped>
.comparison-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

/* Selectors row */
.selectors {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: #fff;
}

.selector-label {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  white-space: nowrap;
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
}

.collection-select.indigo:focus {
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.collection-select.emerald:focus {
  border-color: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.15);
}

/* Query bar */
.query-bar {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  padding: 10px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
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

/* Two-column grid */
.columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: #e5e7eb;
}

.response-columns {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.source-columns {
  height: 260px;
  flex-shrink: 0;
}

.column {
  background: #fff;
  overflow-y: auto;
  padding: 12px;
}

.col-empty {
  padding: 24px 16px;
  color: #9ca3af;
  font-size: 13px;
  text-align: center;
}

.response-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  background: #f3f4f6;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Responsive — stack on mobile */
@media (max-width: 640px) {
  .selectors,
  .columns {
    grid-template-columns: 1fr;
  }

  .source-columns {
    height: auto;
  }
}
</style>
