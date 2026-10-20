<script setup lang="ts">
const route = useRoute()
const groups = [
  { label: 'GENEL', items: [{ label: 'Dashboard', to: '/', icon: '▦' }] },
  { label: 'PORTFÖY', items: [{ label: 'İlanlar', to: '/listings', icon: '⌂' }, { label: 'İlan ekle', to: '/listings/new', icon: '+' }, { label: 'Fiyat geçmişi', to: '/price-history', icon: '↗' }, { label: 'İlan karşılaştırma', to: '/compare', icon: '⇄' }] },
  { label: 'ANALİZ', items: [{ label: 'Mahalle analizi', to: '/analytics/neighborhoods', icon: '⌖' }, { label: 'Yatırım hesaplayıcı', to: '/tools/investment', icon: '₺' }, { label: 'Ön değer tahmini', to: '/tools/valuation', icon: '◈' }, { label: 'Gelişmiş filtreler', to: '/filters', icon: '☷' }, { label: 'Kayıtlı filtreler', to: '/filters/saved', icon: '☆' }, { label: 'Rapor dışa aktar', to: '/export', icon: '⇩' }] },
  { label: 'YÖNETİM', items: [{ label: 'Kullanıcılar', to: '/users', icon: '♙' }] },
]
const active = (to: string) => to === '/' ? route.path === '/' : route.path === to || route.path.startsWith(`${to}/`)
</script>
<template>
  <aside class="sidebar">
    <NuxtLink to="/" class="brand"><span class="brand-mark">M</span><span><b>MülkAnaliz</b><small>GAYRİMENKUL İSTİHBARATI</small></span></NuxtLink>
    <nav class="side-nav">
      <section v-for="group in groups" :key="group.label" class="nav-group"><p>{{ group.label }}</p><NuxtLink v-for="item in group.items" :key="item.to" :to="item.to" class="nav-link" :class="{ active: active(item.to) }"><span class="nav-icon">{{ item.icon }}</span>{{ item.label }}</NuxtLink></section>
    </nav>
    <div class="sidebar-bottom"><div class="api-status"><span class="status-dot"></span><span><b>API bağlantısı</b><small>İstek sırasında kontrol edilir</small></span></div><div class="profile"><div class="avatar">MA</div><div><b>Çalışma alanı</b><small>Gayrimenkul ekibi</small></div><span class="profile-menu">···</span></div></div>
  </aside>
</template>
