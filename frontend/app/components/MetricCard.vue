<script setup lang="ts">
defineProps<{ label: string; value: string; hint?: string; icon?: string; tone?: string }>()
</script>
<template><article class="metric-card"><div class="metric-top"><span>{{ label }}</span><span class="metric-icon" :class="tone || ''">{{ icon || '↗' }}</span></div><strong class="metric-value">{{ value }}</strong><p v-if="hint" class="metric-hint">{{ hint }}</p></article></template>
