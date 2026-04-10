<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
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

const renderedA = computed(() => DOMPurify.sanitize(marked.parse(completedA.value) as string))
const renderedB = computed(() => DOMPurify.sanitize(marked.parse(completedB.value) as string))
const renderedSynthesis = computed(() => DOMPurify.sanitize(marked.parse(synthesisText.value) as string))

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
    <!-- Company selectors + query bar in 3-column layout -->
    <div class="selectors">
      <div class="selector-group indigo-group">
        <span class="selector-badge indigo-badge">A</span>
        <select
          v-model="collectionA"
          class="collection-select"
          :disabled="isLoadingCollections || isEitherStreaming"
        >
          <option v-if="isLoadingCollections" value="" disabled>Loading…</option>
          <option v-else-if="!collections.length" value="" disabled>No filings indexed</option>
          <option v-for="col in collections" :key="col" :value="col">
            {{ formatCollection(col) }}
          </option>
        </select>
      </div>

      <div class="query-bar">
        <textarea
          v-model="queryText"
          class="query-field"
          placeholder="Ask the same question about both companies…"
          rows="1"
          :disabled="isEitherStreaming || isSynthesizing"
          @keydown="handleKeydown"
        />
        <button class="submit-btn" :disabled="!canSubmit" @click="handleSubmit">
          <span v-if="isEitherStreaming || isSynthesizing" class="btn-spinner" />
          <span v-else>Compare ↵</span>
        </button>
      </div>

      <div class="selector-group emerald-group">
        <span class="selector-badge emerald-badge">B</span>
        <select
          v-model="collectionB"
          class="collection-select"
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

    <!-- Side-by-side response columns -->
    <div class="columns response-columns">
      <!-- Column A -->
      <div class="column indigo-column">
        <div class="column-header indigo-header">
          <span class="col-label">{{ collectionA ? collectionA.split('_')[0] : 'Company A' }}</span>
          <span class="col-filing" v-if="collectionA">{{ collectionA.split('_').slice(1).join(' · ') }}</span>
        </div>
        <div class="column-body">
          <div v-if="!sseA.streamingContent.value && !completedA" class="col-empty">
            Select a company and ask a question.
          </div>
          <StreamingResponse v-else-if="sseA.isStreaming.value" :content="sseA.streamingContent.value" />
          <div v-else class="response-text markdown-body" v-html="renderedA" />
        </div>
      </div>

      <!-- Column B -->
      <div class="column emerald-column">
        <div class="column-header emerald-header">
          <span class="col-label">{{ collectionB ? collectionB.split('_')[0] : 'Company B' }}</span>
          <span class="col-filing" v-if="collectionB">{{ collectionB.split('_').slice(1).join(' · ') }}</span>
        </div>
        <div class="column-body">
          <div v-if="!sseB.streamingContent.value && !completedB" class="col-empty">
            Select a company and ask a question.
          </div>
          <StreamingResponse v-else-if="sseB.isStreaming.value" :content="sseB.streamingContent.value" />
          <div v-else class="response-text markdown-body" v-html="renderedB" />
        </div>
      </div>
    </div>

    <!-- AI synthesis panel -->
    <div v-if="synthesisText || isSynthesizing" class="synthesis-panel">
      <div class="synthesis-header">
        <span class="synthesis-icon">⟡</span>
        <span class="synthesis-title">AI Comparison Summary</span>
      </div>
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
  background: var(--bg-base);
}

/* Selectors row — 3-column: A selector | query bar | B selector */
.selectors {
  display: grid;
  grid-template-columns: 280px 1fr 280px;
  gap: 1px;
  background: var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-surface);
}

.selector-badge {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 800;
  width: 24px;
  height: 24px;
  border-radius: 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.indigo-badge {
  background: var(--indigo-soft);
  border: 1px solid var(--indigo);
  color: var(--indigo);
}

.emerald-badge {
  background: var(--emerald-soft);
  border: 1px solid var(--emerald);
  color: var(--emerald);
}

.collection-select {
  flex: 1;
  padding: 6px 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-primary);
  appearance: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.collection-select option { background: var(--bg-elevated); }
.collection-select:focus { outline: none; }
.collection-select:disabled { opacity: 0.4; cursor: not-allowed; }

.indigo-group .collection-select:focus { border-color: var(--indigo); }
.emerald-group .collection-select:focus { border-color: var(--emerald); }

/* Query bar (center column) */
.query-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-surface);
}

.query-field {
  flex: 1;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 7px 10px;
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--text-primary);
  resize: none;
  line-height: 1.4;
}

.query-field::placeholder { color: var(--text-muted); }
.query-field:focus { outline: none; border-color: var(--amber); }
.query-field:disabled { opacity: 0.5; }

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
  min-width: 90px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.submit-btn:hover:not(:disabled) {
  background: #FFB830;
  box-shadow: 0 0 12px var(--amber-glow);
}

.submit-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.btn-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid rgba(7, 9, 13, 0.3);
  border-top-color: #07090D;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Two-column grid */
.columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--border-subtle);
}

.response-columns {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.source-columns {
  height: 220px;
  flex-shrink: 0;
}

.column {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-base);
}

.column-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 14px;
  border-bottom: 2px solid var(--border-subtle);
  flex-shrink: 0;
}

.indigo-header { border-bottom-color: var(--indigo); }
.emerald-header { border-bottom-color: var(--emerald); }

.col-label {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.indigo-column .col-label { color: var(--indigo); }
.emerald-column .col-label { color: var(--emerald); }

.col-filing {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.04em;
}

.column-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.col-empty {
  padding: 24px 0;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.response-text {
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-secondary);
}

/* Synthesis panel */
.synthesis-panel {
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  flex-shrink: 0;
}

.synthesis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px 6px;
}

.synthesis-icon {
  color: var(--amber);
  font-size: 14px;
}

.synthesis-title {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--amber);
}

.synthesis-body {
  padding: 0 16px 12px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-secondary);
}

/* Markdown in comparison columns (scoped deep) */
.markdown-body :deep(p) { margin: 0 0 8px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(strong) { font-weight: 600; color: var(--text-primary); }
.markdown-body :deep(ul), .markdown-body :deep(ol) { padding-left: 18px; margin: 6px 0; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) { font-weight: 600; margin: 10px 0 4px; color: var(--text-primary); }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 12px; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid var(--border); padding: 5px 8px; }
.markdown-body :deep(th) { background: var(--bg-elevated); color: var(--text-primary); font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; }
.markdown-body :deep(td) { color: var(--text-secondary); }
.markdown-body :deep(code) { background: var(--bg-elevated); border: 1px solid var(--border); padding: 1px 4px; border-radius: 3px; font-family: var(--font-mono); font-size: 0.88em; color: var(--amber); }

@media (max-width: 900px) {
  .selectors { grid-template-columns: 1fr; }
  .columns { grid-template-columns: 1fr; }
  .source-columns { height: auto; }
}
</style>
