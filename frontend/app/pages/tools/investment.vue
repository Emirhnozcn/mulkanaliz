<script setup lang="ts">
import { money } from '~/utils/format'
const price = ref(4000000)
const monthlyRent = ref(20000)
const monthlyExpenses = ref(3500)
const vacancyMonths = ref(1)
const purchaseCosts = ref(5)
const annualAppreciation = ref(0)
const annualRent = computed(() => Math.max(0, monthlyRent.value) * Math.max(0, 12 - Math.min(12, vacancyMonths.value)))
const annualExpense = computed(() => Math.max(0, monthlyExpenses.value) * 12)
const totalInvestment = computed(() => Math.max(0, price.value) * (1 + Math.max(0, purchaseCosts.value) / 100))
const netAnnual = computed(() => annualRent.value - annualExpense.value)
const grossYield = computed(() => price.value > 0 ? (monthlyRent.value * 12 / price.value) * 100 : 0)
const netYield = computed(() => totalInvestment.value > 0 ? netAnnual.value / totalInvestment.value * 100 : 0)
const payback = computed(() => netAnnual.value > 0 ? totalInvestment.value / netAnnual.value : null)
const futureValue = computed(() => Math.max(0, price.value) * Math.pow(1 + Math.max(-100, annualAppreciation.value) / 100, 5))
const fmt = (n:number) => new Intl.NumberFormat('tr-TR',{style:'currency',currency:'TRY',maximumFractionDigits:0}).format(n)
</script>
<template>
  <div class="page-heading"><div><p class="eyebrow">ANALİZ / YATIRIM</p><h1>Kira getirisi ve yatırım hesaplayıcı</h1><p>Girdiğiniz varsayımlarla brüt/net getiri, yıllık nakit akışı ve geri ödeme süresini hesaplayın.</p></div></div>
  <div class="alert alert-warning">Bu hesaplama kullanıcı girdilerine dayanır; piyasa değerlemesi veya yatırım tavsiyesi değildir. Vergi, finansman ve beklenmeyen giderler ayrıca değerlendirilmelidir.</div>
  <div class="dashboard-grid" style="grid-template-columns:minmax(0,1fr) minmax(280px,.85fr)">
    <section class="panel"><h2>Varsayımlar</h2><div class="form-grid">
      <div class="field"><label>Satın alma fiyatı (₺)</label><input v-model.number="price" type="number" min="0" step="10000"></div>
      <div class="field"><label>Aylık kira (₺)</label><input v-model.number="monthlyRent" type="number" min="0" step="500"></div>
      <div class="field"><label>Aylık giderler (₺)</label><input v-model.number="monthlyExpenses" type="number" min="0" step="100"></div>
      <div class="field"><label>Yıllık boş kalma (ay)</label><input v-model.number="vacancyMonths" type="number" min="0" max="12" step="1"></div>
      <div class="field"><label>Alım masrafları (%)</label><input v-model.number="purchaseCosts" type="number" min="0" max="100" step="0.5"></div>
      <div class="field"><label>Varsayılan yıllık değer artışı (%)</label><input v-model.number="annualAppreciation" type="number" min="-100" max="100" step="0.5"></div>
    </div></section>
    <section class="panel"><h2>Sonuçlar</h2><div class="metric-grid" style="grid-template-columns:1fr 1fr">
      <MetricCard label="Brüt kira getirisi" :value="`${grossYield.toLocaleString('tr-TR',{maximumFractionDigits:2})}%`" hint="Kira / satın alma fiyatı" icon="↗" />
      <MetricCard label="Net yıllık getiri" :value="`${netYield.toLocaleString('tr-TR',{maximumFractionDigits:2})}%`" hint="Masraf ve boş kalma sonrası" icon="◈" />
      <MetricCard label="Yıllık net nakit akışı" :value="fmt(netAnnual)" hint="Vergi ve finansman hariç" icon="₺" />
      <MetricCard label="Toplam başlangıç yatırımı" :value="fmt(totalInvestment)" hint="Alım masrafı dahil" icon="⌂" />
    </div><div class="result-list"><div><span>Tahmini geri ödeme süresi</span><b>{{ payback === null ? 'Hesaplanamıyor' : `${payback.toLocaleString('tr-TR',{maximumFractionDigits:1})} yıl` }}</b></div><div><span>5 yıl sonraki varsayımsal değer</span><b>{{ fmt(futureValue) }}</b></div><div><span>Yıllık tahmini kira</span><b>{{ fmt(annualRent) }}</b></div></div></section>
  </div>
</template>
<style scoped>.result-list{margin-top:18px;display:grid;gap:12px}.result-list>div{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid var(--border,#e4e8ef)}.result-list span{color:var(--muted,#65738b)}.result-list b{text-align:right}</style>
