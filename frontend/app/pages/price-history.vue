<script setup lang="ts">
import { useApi } from "~/composables/useApi";
import type { Listing, PriceHistory } from "~/types/api";
import { money, dateTR, listingName } from "~/utils/format";
const api = useApi();
const id = ref("");
const rows = ref<PriceHistory[]>([]);
const listings = ref<Listing[]>([]);
const state = ref<"idle" | "loading" | "error" | "success">("idle");
const error = ref("");
async function loadListings() {
  try {
    listings.value = await api.listings({
      limit: 100,
      sort_by: "updated_at",
      sort_order: "desc",
    });
  } catch (e) {
    error.value = e instanceof Error ? e.message : "İlan listesi alınamadı.";
    state.value = "error";
  }
}
async function load() {
  if (!id.value) return;
  state.value = "loading";
  error.value = "";
  try {
    rows.value = await api.priceHistory(id.value);
    state.value = "success";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Fiyat geçmişi alınamadı.";
    state.value = "error";
  }
}
await loadListings();
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">PORTFÖY / FİYAT TAKİBİ</p>
      <h1>Fiyat Geçmişi</h1>
      <p>Bir ilanın sistemde kaydedilen fiyat gözlemlerini inceleyin.</p>
    </div>
  </div>
  <section class="filter-card">
    <div
      class="filter-grid"
      style="grid-template-columns: minmax(220px, 1fr) auto; align-items: end"
    >
      <div class="field">
        <label>İlan seçin</label
        ><select v-model="id">
          <option value="">İlan seçiniz</option>
          <option v-for="l in listings" :key="l.id" :value="String(l.id)">
            {{ listingName(l) }} · {{ money(l.asking_price, l.currency) }}
          </option>
        </select>
      </div>
      <button class="button button-primary" @click="load">
        Geçmişi getir →
      </button>
    </div>
  </section>
  <section class="panel">
    <StatePanel
      v-if="state === 'idle'"
      state="empty"
      message="Fiyat geçmişini görmek için bir ilan seçin."
    /><StatePanel v-else-if="state === 'loading'" state="loading" /><StatePanel
      v-else-if="state === 'error'"
      state="error"
      :message="error"
      @retry="load"
    /><StatePanel
      v-else-if="!rows.length"
      state="empty"
      message="Bu ilan için kaydedilmiş fiyat gözlemi yok."
    />
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Fiyat</th>
            <th>Tarih</th>
            <th>Değişim nedeni</th>
            <th>Kaydeden kullanıcı</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td class="table-primary">
              {{ money(r.asking_price, r.currency) }}
            </td>
            <td>{{ dateTR(r.recorded_at) }}</td>
            <td>{{ r.change_reason }}</td>
            <td>{{ r.recorded_by ?? "—" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="panel-footnote">
      İlk kayıt gerçek ilk yayın fiyatı olmayabilir. İlan fiyatı, gerçekleşmiş
      satış fiyatı değildir.
    </p>
  </section>
</template>
