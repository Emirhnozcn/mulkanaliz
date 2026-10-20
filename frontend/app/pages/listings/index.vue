<script setup lang="ts">
import { useApi } from '~/composables/useApi'
import type { Listing } from '~/types/api'
import { money, dateTR, listingStatus, listingFacts, listingName } from '~/utils/format'

const api = useApi()
const rows = ref<Listing[]>([])
const state = ref<'loading' | 'error' | 'success'>('loading')
const error = ref('')
const page = ref(1)
const pageSize = ref(20)
const sortBy = ref('updated_at')
const sortOrder = ref('desc')
const status = ref('')
const propertyType = ref('')
const minPrice = ref('')
const maxPrice = ref('')
const hasMore = ref(false)
const busyId = ref<number | null>(null)

async function load() {
  state.value = 'loading'; error.value = ''
  try {
    rows.value = await api.listings({ limit: pageSize.value, offset: (page.value - 1) * pageSize.value, sort_by: sortBy.value, sort_order: sortOrder.value, status: status.value || undefined, property_type: propertyType.value || undefined, min_price: minPrice.value || undefined, max_price: maxPrice.value || undefined })
    hasMore.value = rows.value.length === pageSize.value
    state.value = 'success'
  } catch (e) { state.value = 'error'; error.value = e instanceof Error ? e.message : 'İlanlar yüklenemedi.' }
}
function apply() { page.value = 1; load() }
async function changeStatus(item: Listing, nextStatus: 'active' | 'passive') {
  const label = nextStatus === 'active' ? 'aktif' : 'pasif'
  if (item.status === nextStatus) return
  if (!confirm(`#${item.id} ilanı ${label} hale getirilsin mi?`)) return
  busyId.value = item.id
  try { await api.updateListing(item.id, { status: nextStatus }); await load() }
  catch (e) { error.value = e instanceof Error ? e.message : 'İlan durumu güncellenemedi.'; state.value = 'error' }
  finally { busyId.value = null }
}
async function archive(item: Listing) {
  if (!confirm(`#${item.id} ilanını arşivlemek istiyor musunuz? Kayıt kalır, normal listeden gizlenir.`)) return
  busyId.value = item.id
  try { await api.archiveListing(item.id); await load() }
  catch (e) { error.value = e instanceof Error ? e.message : 'Arşivleme başarısız.'; state.value = 'error' }
  finally { busyId.value = null }
}
async function permanentlyDelete(item: Listing) {
  const confirmation = prompt(`#${item.id} ilanını kalıcı olarak silmek için SİL yazın.`)
  if (confirmation !== 'SİL') return
  busyId.value = item.id
  try { await api.permanentlyDeleteListing(item.id); await load() }
  catch (e) { error.value = e instanceof Error ? e.message : 'İlan silinemedi.'; state.value = 'error' }
  finally { busyId.value = null }
}
await load()
</script>
<template>
  <div class="page-heading"><div><p class="eyebrow">PORTFÖY</p><h1>İlan Yönetimi</h1><p>İlanları filtreleyin, aktif/pasif yapın, arşivleyin veya kalıcı olarak silin.</p></div><div class="heading-actions"><NuxtLink to="/filters" class="button button-secondary">☷ Gelişmiş filtreler</NuxtLink><NuxtLink to="/listings/new" class="button button-primary">＋ İlan ekle</NuxtLink></div></div>
  <section class="filter-card"><div class="filter-grid"><div class="field"><label>Durum</label><select v-model="status"><option value="">Tüm durumlar</option><option value="active">Aktif</option><option value="passive">Pasif</option><option value="sold">Satıldı</option><option value="withdrawn">Geri çekildi</option></select></div><div class="field"><label>Gayrimenkul türü</label><select v-model="propertyType"><option value="">Tüm türler</option><option value="apartment">Daire</option><option value="detached_house">Müstakil ev</option><option value="villa">Villa</option><option value="residential_land">İmarlı arsa</option><option value="commercial_land">Ticari arsa</option><option value="farmland">Tarla</option></select></div><div class="field"><label>Minimum fiyat (₺)</label><input v-model="minPrice" type="number" min="0" placeholder="0" /></div><div class="field"><label>Maksimum fiyat (₺)</label><input v-model="maxPrice" type="number" min="0" placeholder="Sınır yok" /></div></div><div class="filter-actions"><span class="muted">Filtreler API sorgusuna gönderilir.</span><div><button class="button button-secondary" @click="status='';propertyType='';minPrice='';maxPrice='';apply()">Temizle</button><button class="button button-primary" @click="apply">Filtrele →</button></div></div></section>
  <section class="panel"><div class="results-toolbar"><span>{{ state==='success' ? `${rows.length} kayıt gösteriliyor` : 'İlanlar' }}</span><div style="display:flex;gap:8px;align-items:center"><label for="sortBy">Sırala:</label><select id="sortBy" v-model="sortBy" class="select-small" @change="apply"><option value="updated_at">Son güncelleme</option><option value="created_at">Oluşturulma</option><option value="asking_price">Fiyat</option><option value="id">İlan numarası</option></select><button class="button button-secondary" @click="sortOrder=sortOrder==='asc'?'desc':'asc';apply()">{{ sortOrder==='asc'?'↑ Artan':'↓ Azalan' }}</button></div></div>
    <StatePanel v-if="state==='loading'" state="loading"/><StatePanel v-else-if="state==='error'" state="error" :message="error" @retry="load"/><StatePanel v-else-if="!rows.length" state="empty" message="Filtrelerinize uygun ilan bulunamadı."/>
    <div v-else class="table-wrap"><table><thead><tr><th>İlan / özellikler</th><th>İstenen fiyat</th><th>İşlem</th><th>Durum</th><th>Kaynak / ilan no</th><th>Oluşturulma</th><th>Güncelleme</th><th>İşlemler</th></tr></thead><tbody><tr v-for="item in rows" :key="item.id"><td class="listing-summary-cell"><NuxtLink :to="`/listings/${item.id}`" class="table-primary listing-title">{{ item.title || listingName(item) }}</NuxtLink><div v-if="item.location_label" class="table-sub listing-location">📍 {{ item.location_label }}</div><div v-if="listingFacts(item).length" class="listing-facts"><span v-for="fact in listingFacts(item)" :key="fact" class="chip">{{ fact }}</span></div><div class="table-sub">İlan #{{ item.id }} · Gayrimenkul #{{ item.property_id }}</div><div class="table-sub" v-if="item.source_listing_id">Harici no: {{ item.source_listing_id }}</div></td><td class="table-primary">{{ money(item.asking_price,item.currency) }}</td><td><span class="chip">{{ item.transaction_type === 'rent' ? 'Kiralık / aylık' : 'Satılık' }}</span></td><td><span class="status-badge" :class="`status-${item.status}`">{{ listingStatus(item.status) }}</span></td><td><div>{{ item.source_name || (item.source_type==='manual'?'Manuel':'Harici kaynak') }}</div><div class="table-sub">{{ item.source_listing_id || (item.source_type==='manual' ? 'Elle girildi' : 'Harici numara yok') }}</div></td><td>{{ dateTR(item.created_at) }}</td><td>{{ dateTR(item.updated_at) }}</td><td><div class="table-actions"><NuxtLink :to="`/listings/${item.id}`" class="text-link">Detay</NuxtLink><NuxtLink :to="`/listings/${item.id}/edit`" class="text-link">Düzenle</NuxtLink><button class="text-link" :disabled="busyId===item.id" style="border:0;background:none" @click="changeStatus(item,item.status==='active'?'passive':'active')">{{ item.status==='active'?'Pasif yap':'Aktif yap' }}</button><button class="text-link" :disabled="busyId===item.id" style="border:0;background:none" @click="archive(item)">Arşivle</button><button class="text-link" :disabled="busyId===item.id" style="border:0;background:none;color:#b42318" @click="permanentlyDelete(item)">Kalıcı sil</button></div></td></tr></tbody></table></div>
    <div class="pagination"><span>Sayfa {{ page }}</span><div class="pagination-actions"><button :disabled="page<=1||state==='loading'" @click="page--;load()">‹</button><button class="page-current">{{ page }}</button><button :disabled="!hasMore||state==='loading'" @click="page++;load()">›</button></div><select v-model.number="pageSize" class="select-small" @change="page=1;load()"><option :value="10">10 / sayfa</option><option :value="20">20 / sayfa</option><option :value="50">50 / sayfa</option></select></div>
  </section>
</template>
