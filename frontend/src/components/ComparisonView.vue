<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
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

const synthesisStreaming = ref('')
const synthesisText = ref('')
const isSynthesizing = ref(false)

const sessionIdA = crypto.randomUUID()
const sessionIdB = crypto.randomUUID()

const isEitherStreaming = computed(() => sseA.isStreaming.value || sseB.isStreaming.value)

const canSubmit = computed(
  () => queryText.value.trim() && collectionA.value && collectionB.value && !isEitherStreaming.value && !isSynthesizing.value,
)

const renderedA = computed(() => marked(completedA.value))
const renderedB = computed(() => marked(completedB.value))
const renderedSynthesis = computed(() => marked(synthesisText.value))

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

async function streamSynthesis(query: string, answerA: string, answerB: string) {
  if (!answerA || !answerB) return
  isSynthesizing.value = true
  synthesisStreaming.value = ''
  synthesisText.value = ''

  const response = await fetch('/api/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      collection_a: collectionA.value,
      collection_b: collectionB.value,
      answer_a: answerA,
      answer_b: answerB,
    }),
  })

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const event = JSON.parse(line.slice(6))
      if (event.type === 'token') synthesisStreaming.value += event.content
      else if (event.type === 'done') synthesisText.value = synthesisStreaming.value
    }
  }

  isSynthesizing.value = false
}

async function handleSubmit() {
  const q = queryText.value.trim()
  if (!canSubmit.value) return
  completedA.value = ''
  completedB.value = ''
  synthesisText.value = ''
  synthesisStreaming.value = ''
  highlightedA.value = null
  highlightedB.value = null
  queryText.value = ''

  const [a, b] = await Promise.all([
    sseA.query(q, collectionA.value, sessionIdA),
    sseB.query(q, collectionB.value, sessionIdB),
  ])
  completedA.value = a
  completedB.value = b

  await streamSynthesis(q, a, b)
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
        :disabled="isEitherStreaming || isSynthesizing"
        @keydown="handleKeydown"
      />
      <button class="submit-btn" :disabled="!canSubmit" @click="handleSubmit">
        {{ isEitherStreaming ? '…' : isSynthesizing ? 'Comparing…' : 'Ask' }}
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
        <div v-else class="response-bubble markdown-body" v-html="renderedA" />
      </div>

      <!-- Column B -->
      <div class="column">
        <div v-if="isLoadingCollections" class="col-empty">Loading filings…</div>
        <div v-else-if="!sseB.streamingContent.value && !completedB" class="col-empty">
          Ask a question to compare responses.
        </div>
        <StreamingResponse v-else-if="sseB.isStreaming.value" :content="sseB.streamingContent.value" />
        <div v-else class="response-bubble markdown-body" v-html="renderedB" />
      </div>
    </div>

    <!-- Comparison synthesis panel -->
    <div v-if="synthesisText || isSynthesizing" class="synthesis-panel">
      <div class="synthesis-label">Comparison Summary</div>
      <div v-if="isSynthesizing" class="synthesis-body">
        <StreamingResponse :content="synthesisStreaming" />
      </div>
      <div v-else class="synthesis-body markdown-body" v-html="renderedSynthesis" />
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
  word-break: break-word;
}

/* Synthesis panel */
.synthesis-panel {
  border-top: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  background: #fafafa;
  flex-shrink: 0;
}

.synthesis-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #6366f1;
  padding: 8px 16px 4px;
}

.synthesis-body {
  padding: 0 16px 12px;
  font-size: 13px;
  line-height: 1.65;
  color: #374151;
}

/* Markdown styles (scoped to .markdown-body) */
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(ul),
.markdown-body :deep(ol) { padding-left: 20px; margin: 6px 0; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) { font-weight: 600; margin: 10px 0 4px; }
.markdown-body :deep(h1) { font-size: 1.1em; }
.markdown-body :deep(h2) { font-size: 1em; }
.markdown-body :deep(h3) { font-size: 0.95em; }
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #d1d5db;
  padding: 5px 10px;
  text-align: left;
}
.markdown-body :deep(th) { background: #f3f4f6; font-weight: 600; }
.markdown-body :deep(code) {
  background: #f3f4f6;
  padding: 1px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
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
