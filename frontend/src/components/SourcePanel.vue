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
  if (score > 5) return '#16a34a'
  if (score > 0) return '#ca8a04'
  return '#9ca3af'
}
</script>

<template>
  <aside class="source-panel">
    <div class="panel-header">Sources</div>

    <div v-if="!sources.length" class="empty">
      Sources will appear here after your first query.
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
        <span class="heading">{{ chunk.metadata.heading ?? 'Unknown Section' }}</span>
        <span class="score" :style="{ color: scoreColor(chunk.rerank_score) }">
          {{ chunk.rerank_score.toFixed(2) }}
        </span>
      </div>
      <p class="excerpt">{{ chunk.text }}</p>
    </div>
  </aside>
</template>

<style scoped>
.source-panel {
  width: 40%;
  border-left: 1px solid #e5e7eb;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}

.panel-header {
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  position: sticky;
  top: 0;
}

.empty {
  padding: 24px 16px;
  color: #9ca3af;
  font-size: 13px;
  text-align: center;
}

.source-card {
  margin: 8px 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-left: 3px solid transparent;
  transition: border-color 0.15s;
}

.source-card.highlighted {
  border-left-color: #6366f1;
  background: #f5f3ff;
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
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e0e7ff;
  color: #4338ca;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.heading {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.score {
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.excerpt {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
