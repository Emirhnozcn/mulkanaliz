<script setup lang="ts">
defineProps<{ state: 'loading' | 'error' | 'empty'; message?: string }>()
defineEmits<{ retry: [] }>()
</script>
<template>
  <div class="state-panel" :class="`state-${state}`" role="status">
    <span class="state-icon">{{ state === 'loading' ? '◌' : state === 'error' ? '!' : '⌕' }}</span>
    <strong>{{ state === 'loading' ? 'Veriler yükleniyor' : state === 'error' ? 'Veriler alınamadı' : 'Gösterilecek veri yok' }}</strong>
    <p>{{ message || (state === 'loading' ? 'API yanıtı bekleniyor…' : state === 'error' ? 'API bağlantısını ve filtrelerinizi kontrol edin.' : 'Bu koşullara uyan kayıt bulunamadı.') }}</p>
    <button v-if="state === 'error'" class="button button-secondary" @click="$emit('retry')">Tekrar dene</button>
  </div>
</template>
