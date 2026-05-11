<script setup>
/**
 * DateRangePicker — compact single-row component
 * Props:  start (datetime-local string), end (datetime-local string)
 * Emits:  update:start, update:end
 * Layout: [Başlangıç] + [Süre N] [Gün/Ay/Yıl] = [Bitiş]
 */
import { ref, watch } from 'vue';

const props = defineProps({
  start: { type: String, default: '' },
  end:   { type: String, default: '' },
});
const emit = defineEmits(['update:start', 'update:end']);

const localStart = ref(props.start);
const durValue   = ref(10);
const durUnit    = ref('days');
const localEnd   = ref(props.end);

// Recalculate end date from start + duration
function calcEnd() {
  if (!localStart.value || !durValue.value) return;
  const d = new Date(localStart.value);
  if (!isNaN(d)) {
    if (durUnit.value === 'days')   d.setDate(d.getDate() + durValue.value);
    if (durUnit.value === 'months') d.setMonth(d.getMonth() + durValue.value);
    if (durUnit.value === 'years')  d.setFullYear(d.getFullYear() + durValue.value);
    localEnd.value = d.toISOString().slice(0, 16);
    emit('update:end', localEnd.value);
  }
}

function onStartChange() {
  emit('update:start', localStart.value);
  calcEnd();
}

function onDurChange() {
  const n = Number(durValue.value);
  if (n < 1 || isNaN(n)) return;
  calcEnd();
}

// Sync from parent when editing existing campaign
watch(() => props.start, (v) => { if (v && v !== localStart.value) { localStart.value = v; calcEnd(); } });
watch(() => props.end,   (v) => { if (v && v !== localEnd.value)   { localEnd.value   = v; } });
</script>

<template>
  <div class="drp-row">
    <div class="drp-field">
      <label class="eisa-field-label">Başlangıç *</label>
      <input
        v-model="localStart"
        type="datetime-local"
        class="eisa-field"
        @change="onStartChange"
      />
    </div>

    <span class="drp-sep">+</span>

    <div class="drp-field drp-dur">
      <label class="eisa-field-label">Süre *</label>
      <div class="drp-dur-row">
        <input
          v-model.number="durValue"
          type="number"
          min="1"
          class="eisa-field"
          @input="onDurChange"
        />
        <select v-model="durUnit" class="eisa-field" @change="onDurChange">
          <option value="days">Gün</option>
          <option value="months">Ay</option>
          <option value="years">Yıl</option>
        </select>
      </div>
    </div>

    <span class="drp-sep">=</span>

    <div class="drp-field">
      <label class="eisa-field-label">Bitiş (otomatik)</label>
      <input
        :value="localEnd"
        type="datetime-local"
        class="eisa-field drp-end"
        readonly
        tabindex="-1"
      />
    </div>
  </div>
</template>

<style scoped>
.drp-row {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.drp-field {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 160px;
}
.drp-dur { flex: 0 0 auto; min-width: 200px; }
.drp-dur-row { display: flex; gap: 0.35rem; }
.drp-dur-row input  { flex: 1; min-width: 60px; }
.drp-dur-row select { flex: 0 0 80px; }
.drp-sep {
  padding-bottom: 0.5rem;
  font-size: 1.1rem;
  font-weight: 700;
  color: #94a3b8;
  flex-shrink: 0;
}
.drp-end { background: #f8fafc; color: #475569; cursor: default; }
</style>
