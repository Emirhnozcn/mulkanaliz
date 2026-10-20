<script setup lang="ts">
const route = useRoute()
const titles: Record<string, string> = {
  '/': 'Genel Bakış', '/listings': 'İlan Yönetimi', '/listings/new': 'Yeni İlan', '/compare': 'İlan Karşılaştırma', '/tools/investment': 'Yatırım Hesaplayıcı', '/tools/valuation': 'Ön Değer Tahmini', '/price-history': 'Fiyat Geçmişi',
  '/analytics/neighborhoods': 'Mahalle Analizi', '/filters': 'Gelişmiş Filtreleme', '/filters/saved': 'Kayıtlı Filtreler', '/users': 'Kullanıcı Yönetimi', '/export': 'Rapor Dışa Aktarma', '/login': 'Giriş'
}
const title = computed(() => titles[route.path] || (route.path.includes('/edit') ? 'İlanı Düzenle' : route.path.match(/^\/listings\/\d+$/) ? 'İlan Detayı' : route.path.includes('price-history') ? 'Fiyat Geçmişi' : 'Gayrimenkul Analizi'))
const mobileMenu = ref(false)
</script>
<template>
  <div class="app-shell">
    <AppSidebar />
    <div class="main-shell">
      <header class="topbar"><button class="mobile-menu" aria-label="Menüyü aç" @click="mobileMenu = !mobileMenu">☰</button><div class="breadcrumbs"><span>Çalışma alanı</span><span class="crumb-slash">/</span><b>{{ title }}</b></div><div class="top-actions"><span class="top-date">{{ new Intl.DateTimeFormat('tr-TR', { dateStyle: 'long' }).format(new Date()) }}</span><NuxtLink class="top-avatar" to="/login" aria-label="Giriş sayfası">MA</NuxtLink></div></header>
      <div v-if="mobileMenu" class="mobile-nav"><NuxtLink to="/">Dashboard</NuxtLink><NuxtLink to="/listings">İlanlar</NuxtLink><NuxtLink to="/analytics/neighborhoods">Mahalle analizi</NuxtLink><NuxtLink to="/filters">Gelişmiş filtreler</NuxtLink><NuxtLink to="/users">Kullanıcılar</NuxtLink></div>
      <main class="page-content"><slot /></main>
      <footer class="app-footer"><span>MülkAnaliz · Gayrimenkul portföy yönetimi</span><span>Gösterilen veriler bağlı API'den alınır.</span></footer>
    </div>
  </div>
</template>
