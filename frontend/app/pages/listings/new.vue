<script setup lang="ts">
import { useApi } from '~/composables/useApi'
import type { Location } from '~/types/api'

const api = useApi()
const saving = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')
const locations = ref<Location[]>([])
const propertyTypes = [
  { code: 'apartment', label: 'Daire' }, { code: 'detached_house', label: 'Müstakil ev' },
  { code: 'villa', label: 'Villa' }, { code: 'residential_zoned_land', label: 'Konut imarlı arsa' },
  { code: 'commercial_zoned_land', label: 'Ticari imarlı arsa' }, { code: 'farmland', label: 'Tarla' }
]
const form = reactive({
  province_id: '', district_id: '', neighborhood_id: '', new_district: '', new_neighborhood: '',
  property_type: 'apartment', transaction_type: 'sale', address: '', has_parking: null as boolean | null, asking_price: '', currency: 'TRY', status: 'active',
  source_type: 'manual', source_name: '', source_listing_id: '', source_url: '', published_at: '', notes: ''
})
const provinces = computed(() => locations.value.filter(x => x.level === 'province'))
const districts = computed(() => locations.value.filter(x => x.level === 'district' && x.parent_id === Number(form.province_id)))
const neighborhoods = computed(() => locations.value.filter(x => x.level === 'neighborhood' && x.parent_id === Number(form.district_id)))
watch(() => form.province_id, () => { form.district_id = ''; form.neighborhood_id = ''; form.new_district = ''; form.new_neighborhood = '' })
watch(() => form.district_id, () => { form.neighborhood_id = ''; form.new_neighborhood = '' })
async function loadLocations() {
  loading.value = true
  try { locations.value = await api.locations({ limit: 500 }) }
  catch (e) { error.value = e instanceof Error ? e.message : 'Konumlar yüklenemedi.' }
  finally { loading.value = false }
}
function normalizeName(name: string) {
  return name.trim().replace(/\s+/g, ' ').toLocaleLowerCase('tr-TR')
}
async function ensureLocation(level: 'district' | 'neighborhood', name: string, parentId: number) {
  const normalized_name = normalizeName(name)
  const found = locations.value.find(x => x.level === level && x.parent_id === parentId && x.normalized_name === normalized_name)
  if (found) return found.id
  const created = await api.request<Location>('/locations', { method: 'POST', body: { level, name: name.trim().replace(/\s+/g, ' '), normalized_name, parent_id: parentId } })
  locations.value.push(created)
  return created.id
}
async function submit() {
  error.value = ''; success.value = ''; saving.value = true
  try {
    if (!form.province_id) throw new Error('Lütfen şehir seçin.')
    if (!form.district_id && !form.new_district.trim()) throw new Error('İlçe seçin veya yeni ilçe adı girin.')
    let districtId = Number(form.district_id)
    if (!districtId) districtId = await ensureLocation('district', form.new_district, Number(form.province_id))
    if (!form.neighborhood_id && !form.new_neighborhood.trim()) throw new Error('Mahalle seçin veya yeni mahalle adı girin.')
    let neighborhoodId = Number(form.neighborhood_id)
    if (!neighborhoodId) neighborhoodId = await ensureLocation('neighborhood', form.new_neighborhood, districtId)
    const body = {
      property_type: form.property_type, transaction_type: form.transaction_type, location_id: neighborhoodId, address: form.address || null,
      has_parking: ['apartment', 'detached_house', 'villa'].includes(form.property_type) ? form.has_parking : null,
      asking_price: Number(form.asking_price), currency: form.currency, status: form.status,
      source_type: form.source_type, source_name: form.source_name || 'manual',
      source_listing_id: form.source_listing_id || null, source_url: form.source_url || null,
      published_at: form.published_at ? new Date(form.published_at).toISOString() : null,
      notes: form.notes || null
    }
    const created = await api.request<{id:number}>('/listings/quick-create', { method: 'POST', body })
    success.value = `İlan #${created.id} oluşturuldu.`
    await navigateTo(`/listings/${created.id}`)
  } catch (e) { error.value = e instanceof Error ? e.message : 'İlan oluşturulamadı.' }
  finally { saving.value = false }
}
onMounted(loadLocations)
</script>
<template>
  <div class="page-heading"><div><p class="eyebrow">PORTFÖY / YENİ KAYIT</p><h1>Yeni ilan ekle</h1><p>Şehir sabit listeden seçilir; yeni ilçe ve mahalleler ihtiyaç oldukça kaydedilir.</p></div><NuxtLink to="/listings" class="button button-secondary">İlanlara dön</NuxtLink></div>
  <div v-if="error" class="alert">{{ error }}</div><div v-if="success" class="alert alert-info">{{ success }}</div>
  <form class="form-card" style="padding:22px" @submit.prevent="submit">
    <div class="form-grid">
      <h2 class="form-section-title">Konum ve gayrimenkul</h2>
      <div class="field"><label>Şehir *</label><select v-model="form.province_id" required><option value="">Şehir seçin</option><option v-for="p in provinces" :key="p.id" :value="String(p.id)">{{ p.name }}</option></select><small v-if="!provinces.length">Şehir listesi boşsa şehir verileri veritabanına eklenmelidir.</small></div>
      <div class="field"><label>İlçe *</label><select v-model="form.district_id" :disabled="!form.province_id"><option value="">Mevcut ilçeyi seçin</option><option v-for="d in districts" :key="d.id" :value="String(d.id)">{{ d.name }}</option></select><input v-if="form.province_id" v-model="form.new_district" placeholder="Ya da yeni ilçe adı yazın" /></div>
      <div class="field"><label>Mahalle *</label><select v-model="form.neighborhood_id" :disabled="!form.district_id"><option value="">Mevcut mahalleyi seçin</option><option v-for="n in neighborhoods" :key="n.id" :value="String(n.id)">{{ n.name }}</option></select><input v-if="form.district_id || form.new_district.trim()" v-model="form.new_neighborhood" placeholder="Ya da yeni mahalle adı yazın" /></div>
      <div class="field"><label>Gayrimenkul türü *</label><select v-model="form.property_type"><option v-for="t in propertyTypes" :key="t.code" :value="t.code">{{ t.label }}</option></select></div>
      <div class="field" style="grid-column:1/-1"><label>Açık adres</label><input v-model="form.address" placeholder="Cadde, sokak veya açıklayıcı adres" /></div>
      <div v-if="['apartment', 'detached_house', 'villa'].includes(form.property_type)" class="field"><label>Otopark</label><select v-model="form.has_parking"><option :value="null">Belirtilmedi</option><option :value="true">Var</option><option :value="false">Yok</option></select></div>
      <h2 class="form-section-title">İlan bilgileri</h2>
      <div class="field"><label>İşlem türü *</label><select v-model="form.transaction_type" required><option value="sale">Satılık</option><option value="rent">Kiralık (aylık)</option></select><small>{{ form.transaction_type === 'rent' ? 'Kira bedeli aylık olarak kaydedilir.' : 'Satış için istenen toplam bedel kaydedilir.' }}</small></div>
      <div class="field"><label>{{ form.transaction_type === 'rent' ? 'Aylık kira (₺) *' : 'Satış fiyatı (₺) *' }}</label><input v-model="form.asking_price" required min="1" step="0.01" type="number" placeholder="Örn. 4250000" /></div>
      <div class="field"><label>Para birimi</label><select v-model="form.currency"><option value="TRY">Türk lirası (TRY)</option><option value="EUR">Euro (EUR)</option><option value="USD">ABD doları (USD)</option></select></div>
      <div class="field"><label>İlan durumu</label><select v-model="form.status"><option value="active">Aktif</option><option value="passive">Pasif</option><option value="sold">Satıldı</option><option value="withdrawn">Geri çekildi</option></select></div>
      <div class="field"><label>Kayıt türü</label><select v-model="form.source_type"><option value="manual">Manuel</option><option value="import">İçe aktarılan</option><option value="authorized_source">Yetkili kaynak</option></select></div>
      <div class="field"><label>Kaynak adı</label><input v-model="form.source_name" placeholder="Örn. sahibinden" /></div>
      <div class="field"><label>Harici ilan numarası</label><input v-model="form.source_listing_id" placeholder="Varsa ilan numarası" /></div>
      <div class="field"><label>İlan bağlantısı</label><input v-model="form.source_url" type="url" placeholder="https://…" /></div>
      <div class="field"><label>Yayın tarihi</label><input v-model="form.published_at" type="datetime-local" /></div>
      <div class="field" style="grid-column:1/-1"><label>Notlar</label><textarea v-model="form.notes" placeholder="İlanla ilgili notlar…" /></div>
    </div>
    <div class="form-footer"><NuxtLink to="/listings" class="button button-secondary">İptal</NuxtLink><button class="button button-primary" :disabled="saving || loading" type="submit">{{ saving ? 'Kaydediliyor…' : 'İlanı kaydet →' }}</button></div>
  </form>
</template>
