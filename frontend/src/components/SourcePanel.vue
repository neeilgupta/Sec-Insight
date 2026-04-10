<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SourceChunk } from '../types'

const props = defineProps<{
  sources: SourceChunk[]
  highlighted: number | null
}>()

const cardRefs = ref<HTMLElement[]>([])

watch(
  () => props.highlighted,
  (idx) => {
    if (idx !== null && cardRefs.value[idx]) {
      cardRefs.value[idx].scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  },
)

function scoreColor(score: number): string {
  if (score > 5) return '#22C55E'
  if (score > 0) return '#F0A020'
  return '#3D4F63'
}
</script>

<template>
  <aside class="source-panel">
    <div class="panel-header">
      <span class="panel-title">Sources</span>
      <span class="source-count" v-if="sources.length">{{ sources.length }}</span>
    </div>

    <div v-if="!sources.length" class="empty">
      <span class="empty-icon">◈</span>
      <span>Sources appear after your first query</span>
    </div>

    <div
      v-for="(chunk, i) in sources"
      :key="chunk.chunk_id"
      :ref="(el) => { if (el) cardRefs[i] = el as HTMLElement }"
      class="source-card"
      :class="{ highlighted: highlighted === i }"
    >
      <div class="card-header">
        <span class="index">{{ i + 1 }}</span>
        <span class="heading">{{ chunk.metadata.heading || 'Unknown Section' }}</span>
      </div>
      <div class="score-row">
        <div class="score-bar-track">
          <div
            class="score-bar-fill"
            :style="{
              width: Math.max(0, Math.min(100, (chunk.rerank_score / 12) * 100)) + '%',
              background: scoreColor(chunk.rerank_score)
            }"
          />
        </div>
        <span class="score-val" :style="{ color: scoreColor(chunk.rerank_score) }">
          {{ chunk.rerank_score.toFixed(2) }}
        </span>
      </div>
      <p class="excerpt">{{ chunk.text }}</p>
    </div>
  </aside>
</template>

<style scoped>
.source-panel {
  width: 360px;
  flex-shrink: 0;
  border-left: 1px solid var(--border-subtle);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
}

.source-panel::-webkit-scrollbar { width: 3px; }
.source-panel::-webkit-scrollbar-thumb { background: var(--border); }

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  background: var(--bg-surface);
  z-index: 1;
}

.panel-title {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.source-count {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--amber);
  background: var(--amber-soft);
  border: 1px solid var(--amber-dim);
  border-radius: 4px;
  padding: 1px 6px;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 16px;
  color: var(--text-muted);
  font-size: 12px;
  text-align: center;
}

.empty-icon {
  font-size: 20px;
  color: var(--border-strong);
}

.source-card {
  margin: 8px 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  border-left: 2px solid transparent;
  transition: border-color 0.2s, background 0.2s;
  cursor: default;
}

.source-card:hover {
  border-color: var(--border-strong);
  background: var(--bg-hover);
}

.source-card.highlighted {
  border-left-color: var(--amber);
  background: var(--bg-hover);
  border-color: var(--border-strong);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: var(--amber-soft);
  border: 1px solid var(--amber-dim);
  color: var(--amber);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  flex-shrink: 0;
}

.heading {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-family: var(--font-mono);
}

.score-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.score-bar-track {
  flex: 1;
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.score-val {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  flex-shrink: 0;
  min-width: 32px;
  text-align: right;
}

.excerpt {
  margin: 0;
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.source-card.highlighted .excerpt {
  color: var(--text-secondary);
}
</style>
