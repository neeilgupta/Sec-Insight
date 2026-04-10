<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { SourceChunk } from '../types'

const props = defineProps<{
  sources: SourceChunk[]
  highlighted: number | null
  color: 'indigo' | 'emerald'
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

const cssVars = computed(() => {
  if (props.color === 'emerald') {
    return {
      '--accent': '#00C48C',
      '--accent-dim': '#00856A',
      '--accent-soft': 'rgba(0, 196, 140, 0.10)',
      '--highlight-border': '#00C48C',
      '--highlight-bg': 'rgba(0, 196, 140, 0.05)',
      '--badge-bg': 'rgba(0, 196, 140, 0.10)',
      '--badge-text': '#00C48C',
    }
  }
  return {
    '--accent': '#7C8EF5',
    '--accent-dim': '#5B6FD8',
    '--accent-soft': 'rgba(124, 142, 245, 0.10)',
    '--highlight-border': '#7C8EF5',
    '--highlight-bg': 'rgba(124, 142, 245, 0.05)',
    '--badge-bg': 'rgba(124, 142, 245, 0.10)',
    '--badge-text': '#7C8EF5',
  }
})

function scoreColor(score: number): string {
  if (score > 5) return '#22C55E'
  if (score > 0) return '#F0A020'
  return '#3D4F63'
}
</script>

<template>
  <aside class="source-panel" :style="cssVars">
    <div class="panel-header">
      <span class="panel-title">Sources</span>
      <span class="source-count" v-if="sources.length">{{ sources.length }}</span>
    </div>

    <div v-if="!sources.length" class="empty">
      <span>No sources yet</span>
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
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-subtle);
  position: sticky;
  top: 0;
  background: var(--bg-surface);
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
  color: var(--accent);
  background: var(--accent-soft);
  border: 1px solid var(--accent-dim);
  border-radius: 4px;
  padding: 1px 5px;
}

.empty {
  padding: 12px 16px;
  color: var(--text-muted);
  font-size: 11px;
  text-align: center;
}

.source-card {
  margin: 6px 8px;
  padding: 8px 10px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  border-left: 2px solid transparent;
  transition: border-color 0.2s, background 0.2s;
}

.source-card:hover {
  background: var(--bg-hover);
}

.source-card.highlighted {
  border-left-color: var(--accent);
  background: var(--bg-hover);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 3px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-dim);
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 500;
  flex-shrink: 0;
}

.heading {
  font-size: 10px;
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
  gap: 6px;
  margin-bottom: 6px;
}

.score-bar-track {
  flex: 1;
  height: 2px;
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
  font-size: 9px;
  font-weight: 500;
  flex-shrink: 0;
  min-width: 28px;
  text-align: right;
}

.excerpt {
  margin: 0;
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
