<script setup lang="ts">
import { useApi } from "~/composables/useApi";
import type { Listing } from "~/types/api";
import { money, dateTR, listingStatus } from "~/utils/format";
const api = useApi();
const status = ref("");
const propertyType = ref("");
const fromPrice = ref("");
const toPrice = ref("");
const rows = ref<Listing[]>([]);
const state = ref<"idle" | "loading" | "error" | "success">("idle");
const error = ref("");
const excelError = ref("");
const excelLoading = ref(false);
async function preview() {
  state.value = "loading";
  error.value = "";
  try {
    rows.value = await api.listings({
      limit: 500,
      offset: 0,
      status: status.value || undefined,
      property_type: propertyType.value || undefined,
      min_price: fromPrice.value || undefined,
      max_price: toPrice.value || undefined,
      sort_by: "updated_at",
      sort_order: "desc",
    });
    state.value = "success";
  } catch (e) {
    state.value = "error";
    error.value = e instanceof Error ? e.message : "Rapor verisi alınamadı.";
  }
}
async function exportExcel() {
  excelError.value = "";
  excelLoading.value = true;
  try {
    const config = useRuntimeConfig();
    const base = String(config.public.apiBase).replace(/\/$/, "");
    const params = new URLSearchParams({ limit: "500", include_archived: "false" });
    // The app stores the access token in sessionStorage and normal API calls
    // attach it as a Bearer token. This raw fetch must do the same or the
    // protected export endpoint responds with 401 even after a successful login.
    const token = sessionStorage.getItem("rea_access_token");
    if (!token) {
      throw new Error("Oturum anahtarı bulunamadı. Lütfen çıkış yapıp yeniden giriş yapın.");
    }
    const response = await fetch(`${base}/exports/listings.xlsx?${params.toString()}`, {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error("Excel raporu için geçerli bir oturum gerekli. Giriş yapıp tekrar deneyin.");
      }
      throw new Error(`Excel raporu indirilemedi (HTTP ${response.status}).`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `mulkanaliz-ilanlar-${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    excelError.value = e instanceof Error ? e.message : "Excel raporu indirilemedi.";
  } finally {
    excelLoading.value = false;
  }
}
function exportCsv() {
  if (!rows.value.length) return;
  const headers = [
    "İlan ID",
    "Gayrimenkul ID",
    "İlan fiyatı",
    "Para birimi",
    "Durum",
    "Kaynak",
    "Yayın tarihi",
    "Son güncelleme",
    "Notlar",
  ];
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const data = rows.value.map((r) => [
    r.id,
    r.property_id,
    r.asking_price,
    r.currency,
    listingStatus(r.status),
    r.source_name || r.source_type,
    r.published_at || "",
    r.updated_at,
    r.notes || "",
  ]);
  const csv =
    "\uFEFF" +
    [headers, ...data].map((row) => row.map(esc).join(";")).join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mulkanaliz-ilanlar-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">RAPORLAMA</p>
      <h1>Rapor dışa aktarma</h1>
      <p>
        API'den dönen ilan kayıtlarını filtreleyip Türkçe CSV olarak indirin.
      </p>
    </div>
  </div>
  <section class="filter-card">
    <div class="filter-grid">
      <div class="field">
        <label>Durum</label
        ><select v-model="status">
          <option value="">Tümü</option>
          <option value="active">Aktif</option>
          <option value="passive">Pasif</option>
          <option value="sold">Satıldı</option>
          <option value="withdrawn">Geri çekildi</option>
        </select>
      </div>
      <div class="field">
        <label>Gayrimenkul türü</label
        ><select v-model="propertyType">
          <option value="">Tümü</option>
          <option value="apartment">Daire</option>
          <option value="detached_house">Müstakil ev</option>
          <option value="villa">Villa</option>
          <option value="residential_land">İmarlı arsa</option>
          <option value="commercial_land">Ticari arsa</option>
          <option value="farmland">Tarla</option>
        </select>
      </div>
      <div class="field">
        <label>Minimum fiyat (₺)</label
        ><input v-model="fromPrice" type="number" min="0" />
      </div>
      <div class="field">
        <label>Maksimum fiyat (₺)</label
        ><input v-model="toPrice" type="number" min="0" />
      </div>
    </div>
    <div class="filter-actions">
      <span class="muted"
        >En fazla 500 kayıt dışa aktarılır. CSV ayıracı noktalı virgüldür.</span
      >
      <div>
        <button
          class="button button-secondary"
          @click="
            status = '';
            propertyType = '';
            fromPrice = '';
            toPrice = '';
            rows = [];
            state = 'idle';
          "
        >
          Temizle</button
        ><button class="button button-primary" @click="preview">
          Verileri getir →
        </button>
      </div>
    </div>
  </section>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h2>Dışa aktarılacak kayıtlar</h2>
        <p>Önizleme API yanıtına dayanır; sahte veri kullanılmaz.</p>
      </div>
      <button
        class="button button-primary"
        :disabled="state !== 'success' || !rows.length"
        @click="exportCsv"
      >
        ⇩ CSV indir ({{ rows.length }})
      </button>
      <button
        class="button button-secondary"
        :disabled="excelLoading"
        @click="exportExcel"
      >
        {{ excelLoading ? "Excel hazırlanıyor…" : "⇩ Excel (.xlsx) indir" }}
      </button>
    </div>
    <p v-if="excelError" class="alert alert-warning" role="alert">{{ excelError }}</p>
    <StatePanel
      v-if="state === 'idle'"
      state="empty"
      message="Önce filtreleri seçip verileri getirin."
    /><StatePanel v-else-if="state === 'loading'" state="loading" /><StatePanel
      v-else-if="state === 'error'"
      state="error"
      :message="error"
      @retry="preview"
    /><StatePanel v-else-if="!rows.length" state="empty" />
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>İlan ID</th>
            <th>Gayrimenkul ID</th>
            <th>Fiyat</th>
            <th>Durum</th>
            <th>Kaynak</th>
            <th>Son güncelleme</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows.slice(0, 30)" :key="r.id">
            <td>#{{ r.id }}</td>
            <td>{{ r.property_id }}</td>
            <td class="table-primary">
              {{ money(r.asking_price, r.currency) }}
            </td>
            <td>{{ listingStatus(r.status) }}</td>
            <td>{{ r.source_name || r.source_type }}</td>
            <td>{{ dateTR(r.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="rows.length > 30" class="panel-footnote">
        Önizlemede ilk 30 kayıt gösterilir; dışa aktarma
        {{ rows.length }} kaydın tamamını içerir.
      </p>
    </div>
  </section>
</template>
