<script setup lang="ts">
import { useApi } from "~/composables/useApi";
import type { Listing } from "~/types/api";
import { money, dateTR } from "~/utils/format";

const route = useRoute();
const api = useApi();
const id = String(route.params.id);

const row = ref<Listing | null>(null);
const state = ref<"loading" | "error" | "success">("loading");
const error = ref("");
const saving = ref(false);

const form = reactive({
  asking_price: "",
  currency: "TRY",
  status: "active",
  source_url: "",
  published_at: "",
  last_seen_at: "",
  notes: "",
});

async function load() {
  state.value = "loading";
  error.value = "";

  try {
    const listing = await api.listing(id);

    row.value = listing;

    Object.assign(form, {
      asking_price: String(listing.asking_price),
      currency: listing.currency,
      status: listing.status,
      source_url: listing.source_url || "",
      published_at: listing.published_at
        ? listing.published_at.slice(0, 16)
        : "",
      last_seen_at: listing.last_seen_at
        ? listing.last_seen_at.slice(0, 16)
        : "",
      notes: listing.notes || "",
    });

    state.value = "success";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "İlan alınamadı.";

    state.value = "error";
  }
}

async function submit() {
  saving.value = true;
  error.value = "";

  try {
    await api.updateListing(id, {
      asking_price: Number(form.asking_price),
      currency: form.currency,
      status: form.status,
      source_url: form.source_url || null,
      published_at: form.published_at
        ? new Date(form.published_at).toISOString()
        : null,
      last_seen_at: form.last_seen_at
        ? new Date(form.last_seen_at).toISOString()
        : null,
      notes: form.notes || null,
    });

    await navigateTo(`/listings/${id}`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Güncelleme başarısız.";
  } finally {
    saving.value = false;
  }
}

await load();
</script>

<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">PORTFÖY / DÜZENLEME</p>
      <h1>İlanı düzenle</h1>
      <p>İlan #{{ id }} için mevcut alanları güncelleyin.</p>
    </div>

    <NuxtLink :to="`/listings/${id}`" class="button button-secondary">
      ← Detaya dön
    </NuxtLink>
  </div>

  <StatePanel v-if="state === 'loading'" state="loading" />

  <StatePanel
    v-else-if="state === 'error'"
    state="error"
    :message="error"
    @retry="load"
  />

  <template v-else-if="row">
    <div class="alert alert-info">
      Mevcut fiyat:
      <b>{{ money(row.asking_price, row.currency) }}</b
      >. Fiyat değişirse backend'in fiyat geçmişi mekanizması yeni bir gözlem
      kaydedebilir.
    </div>

    <div v-if="error" class="alert">
      {{ error }}
    </div>

    <form class="form-card" style="padding: 22px" @submit.prevent="submit">
      <div class="form-grid">
        <div class="field">
          <label>İlan fiyatı *</label>
          <input
            v-model="form.asking_price"
            type="number"
            min="0.01"
            step="0.01"
            required
          />
        </div>

        <div class="field">
          <label>Para birimi</label>
          <select v-model="form.currency">
            <option value="TRY">TRY</option>
            <option value="EUR">EUR</option>
            <option value="USD">USD</option>
          </select>
        </div>

        <div class="field">
          <label>Durum</label>
          <select v-model="form.status">
            <option value="active">Aktif</option>
            <option value="passive">Pasif</option>
            <option value="sold">Satıldı</option>
            <option value="withdrawn">Geri çekildi</option>
          </select>
        </div>

        <div class="field">
          <label>İlan bağlantısı</label>
          <input v-model="form.source_url" type="url" />
        </div>

        <div class="field">
          <label>Yayın tarihi</label>
          <input v-model="form.published_at" type="datetime-local" />
        </div>

        <div class="field">
          <label>Son görüldüğü tarih</label>
          <input v-model="form.last_seen_at" type="datetime-local" />
        </div>

        <div class="field" style="grid-column: 1 / -1">
          <label>Notlar</label>
          <textarea v-model="form.notes" />
        </div>
      </div>

      <div class="form-footer">
        <NuxtLink :to="`/listings/${id}`" class="button button-secondary">
          İptal
        </NuxtLink>

        <button class="button button-primary" type="submit" :disabled="saving">
          {{ saving ? "Kaydediliyor…" : "Değişiklikleri kaydet" }}
        </button>
      </div>

      <p class="panel-footnote">Son güncelleme: {{ dateTR(row.updated_at) }}</p>
    </form>
  </template>
</template>
