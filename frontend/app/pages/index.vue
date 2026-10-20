<script setup lang="ts">
import type {
  Listing,
  PriceHistory,
  PriceSummary,
  PriceComparison,
} from "~/types/api";
import { useApi } from "~/composables/useApi";
import { money, numberTR, dateTR, listingStatus, listingName } from "~/utils/format";

const api = useApi();

const summary = ref<PriceSummary | null>(null);
const comparison = ref<PriceComparison | null>(null);
const listings = ref<Listing[]>([]);

type ChangedListing = {
  listing: Listing;
  previous: PriceHistory;
  current: PriceHistory;
  priceChanged: boolean;
  currencyChanged: boolean;
};

const changedListings = ref<ChangedListing[]>([]);

const changedState = ref<"loading" | "error" | "success">("loading");
const changedError = ref("");

const summaryState = ref<"loading" | "error" | "success">("loading");
const comparisonState = ref<"loading" | "error" | "success">("loading");
const listingsState = ref<"loading" | "error" | "success">("loading");

const summaryError = ref("");
const comparisonError = ref("");
const listingsError = ref("");

async function loadSummary() {
  summaryState.value = "loading";
  summaryError.value = "";

  try {
    summary.value = await api.priceSummary({ area_type: "net" });
    summaryState.value = "success";
  } catch (e) {
    summaryState.value = "error";
    summaryError.value = e instanceof Error ? e.message : "Analiz alınamadı.";
  }
}

async function loadComparison() {
  comparisonState.value = "loading";
  comparisonError.value = "";

  try {
    comparison.value = await api.compare({
      group_by: "property_type",
      area_type: "net",
    });

    comparisonState.value = "success";
  } catch (e) {
    comparisonState.value = "error";
    comparisonError.value =
      e instanceof Error ? e.message : "Karşılaştırma alınamadı.";
  }
}

async function loadListings() {
  listingsState.value = "loading";
  changedState.value = "loading";
  listingsError.value = "";
  changedError.value = "";

  try {
    listings.value = await api.listings({
      limit: 10,
      offset: 0,
      sort_by: "updated_at",
      sort_order: "desc",
    });

    listingsState.value = "success";

    const histories = await Promise.allSettled(
      listings.value.map(async (listing) => ({
        listing,
        history: await api.priceHistory(listing.id),
      })),
    );

    changedListings.value = histories.flatMap((result) => {
      if (result.status !== "fulfilled" || result.value.history.length < 2) {
        return [];
      }

      const ordered = [...result.value.history].sort(
        (a, b) =>
          new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime(),
      );

      const previous = ordered[ordered.length - 2];
      const current = ordered[ordered.length - 1];

      // Son iki fiyat gözleminin mevcut olduğundan emin ol.
      if (!previous || !current) {
        return [];
      }

      const priceChanged =
        Number(previous.asking_price) !== Number(current.asking_price);

      const currencyChanged = previous.currency !== current.currency;

      if (!priceChanged && !currencyChanged) {
        return [];
      }

      return [
        {
          listing: result.value.listing,
          previous,
          current,
          priceChanged,
          currencyChanged,
        },
      ];
    });

    const failed = histories.some((result) => result.status === "rejected");

    changedState.value = failed ? "error" : "success";

    if (failed) {
      changedError.value =
        "Bazı ilanların fiyat geçmişi alınamadı; değişen ilan listesi eksik olabilir.";
    }
  } catch (e) {
    listingsState.value = "error";
    listingsError.value = e instanceof Error ? e.message : "İlanlar alınamadı.";

    changedState.value = "error";
    changedError.value = listingsError.value;
  }
}

async function reload() {
  await Promise.all([loadSummary(), loadComparison(), loadListings()]);
}

await reload();

const maxBucket = computed(() =>
  Math.max(1, ...(summary.value?.price_distribution.map((b) => b.count) ?? [])),
);

const maxType = computed(() =>
  Math.max(1, ...(comparison.value?.groups.map((g) => g.listing_count) ?? [])),
);

const areaMetric = computed(() =>
  summary.value?.area_price_metrics.find((m) => m.area_type === "net"),
);
</script>

<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">PORTFÖYÜNÜZÜN ÖZETİ</p>
      <h1>Genel Bakış</h1>
      <p>
        Gayrimenkul portföyünüzü izleyin, ilan fiyatlarını karşılaştırın ve
        piyasa hareketlerini tek yerden takip edin.
      </p>
    </div>

    <div class="heading-actions">
      <button class="button button-secondary" @click="reload">↻ Yenile</button>

      <NuxtLink to="/listings/new" class="button button-primary">
        ＋ Yeni ilan
      </NuxtLink>
    </div>
  </div>

  <div v-if="summaryState === 'error'" class="alert">
    Analiz verileri API'den alınamadı: {{ summaryError }}
    Sahte gösterge kullanılmıyor.
  </div>

  <div
    v-if="summaryState === 'success' && summary?.reliability === 'limited'"
    class="alert alert-warning"
  >
    {{ summary.reliability_note }}
  </div>

  <div class="metric-grid">
    <MetricCard
      label="Toplam aktif ilan"
      :value="
        summaryState === 'success' ? numberTR(summary?.listing_count) : '—'
      "
      hint="Aktif ve arşivlenmemiş ilanlar"
      icon="⌂"
    />

    <MetricCard
      label="Ortalama ilan fiyatı"
      :value="
        summaryState === 'success' ? money(summary?.average_asking_price) : '—'
      "
      hint="Uç değerlerden etkilenebilir"
      icon="↗"
      tone="green"
    />

    <MetricCard
      label="Medyan ilan fiyatı"
      :value="
        summaryState === 'success' ? money(summary?.median_asking_price) : '—'
      "
      hint="Ortanca ilan fiyatı"
      icon="◈"
      tone="amber"
    />

    <MetricCard
      label="Ortalama net m² fiyatı"
      :value="
        summaryState === 'success'
          ? money(areaMetric?.average_price_per_m2)
          : '—'
      "
      hint="Yalnızca net alanı bilinen konutlar"
      icon="▤"
    />
  </div>

  <div class="dashboard-grid">
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Fiyat dağılımı</h2>
          <p>İlan fiyatlarının aralıklara göre dağılımı</p>
        </div>

        <span class="chip">TL · İlan fiyatı</span>
      </div>

      <StatePanel v-if="summaryState === 'loading'" state="loading" />

      <StatePanel
        v-else-if="summaryState === 'error'"
        state="error"
        :message="summaryError"
        @retry="loadSummary"
      />

      <StatePanel
        v-else-if="!summary?.price_distribution.length"
        state="empty"
      />

      <div v-else class="chart-area">
        <div class="bar-chart">
          <div
            v-for="(bucket, i) in summary.price_distribution"
            :key="i"
            class="bar-col"
          >
            <span class="bar-count">{{ bucket.count }}</span>

            <div
              class="bar"
              :style="{
                height: `${Math.max(3, (bucket.count / maxBucket) * 72)}%`,
              }"
              :title="`${bucket.count} ilan`"
            />

            <span class="bar-label">
              {{ money(bucket.lower_bound).replace("₺", "") }}
            </span>
          </div>
        </div>

        <p class="panel-footnote">
          {{ summary.price_basis }} {{ summary.reliability_note }}
        </p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Gayrimenkul türü dağılımı</h2>
          <p>Filtrelerle eşleşen ilan sayısı</p>
        </div>

        <NuxtLink to="/analytics/neighborhoods" class="panel-link">
          Analiz et ↗
        </NuxtLink>
      </div>

      <StatePanel v-if="comparisonState === 'loading'" state="loading" />

      <StatePanel
        v-else-if="comparisonState === 'error'"
        state="error"
        :message="comparisonError"
        @retry="loadComparison"
      />

      <StatePanel v-else-if="!comparison?.groups.length" state="empty" />

      <div v-else class="distribution-list">
        <div
          v-for="item in comparison.groups"
          :key="item.group_key"
          class="distribution-row"
        >
          <span class="distribution-name">
            {{ item.group_label }}
          </span>

          <div class="distribution-track">
            <div
              class="distribution-fill"
              :style="{
                width: `${(item.listing_count / maxType) * 100}%`,
              }"
            />
          </div>

          <span class="distribution-count">
            {{ item.listing_count }}
          </span>
        </div>

        <p class="panel-footnote">
          {{ comparison.price_basis }}
        </p>
      </div>
    </section>
  </div>

  <div class="dashboard-grid">
    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Son güncellenen ilanlar</h2>
          <p>En son değiştirilen portföy kayıtları</p>
        </div>

        <NuxtLink to="/listings" class="panel-link"> Tüm ilanlar ↗ </NuxtLink>
      </div>

      <StatePanel v-if="listingsState === 'loading'" state="loading" />

      <StatePanel
        v-else-if="listingsState === 'error'"
        state="error"
        :message="listingsError"
        @retry="loadListings"
      />

      <StatePanel
        v-else-if="!listings.length"
        state="empty"
        message="API bu koşullarda ilan döndürmedi."
      />

      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>İlan / Kayıt</th>
              <th>Fiyat</th>
              <th>Durum</th>
              <th>Son güncelleme</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="item in listings" :key="item.id">
              <td>
                <div class="table-primary">{{ listingName(item) }}</div>
                <div class="table-sub">{{ item.location_label || `Gayrimenkul #${item.property_id}` }}</div>
              </td>

              <td class="table-primary">
                {{ money(item.asking_price, item.currency) }}
              </td>

              <td>
                <span class="status-badge" :class="`status-${item.status}`">
                  {{ listingStatus(item.status) }}
                </span>
              </td>

              <td>{{ dateTR(item.updated_at) }}</td>

              <td>
                <NuxtLink :to="`/listings/${item.id}`" class="text-link">
                  Detay →
                </NuxtLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h2>Fiyat görünümü</h2>
          <p>Özet istatistikler</p>
        </div>

        <span class="chip">TRY</span>
      </div>

      <StatePanel v-if="summaryState === 'loading'" state="loading" />

      <StatePanel
        v-else-if="summaryState === 'error'"
        state="error"
        :message="summaryError"
        @retry="loadSummary"
      />

      <div v-else-if="summary" class="detail-meta">
        <div>
          <span>Medyan fiyat</span>
          <b>{{ money(summary.median_asking_price) }}</b>
        </div>

        <div>
          <span>En düşük fiyat</span>
          <b>{{ money(summary.minimum_asking_price) }}</b>
        </div>

        <div>
          <span>En yüksek fiyat</span>
          <b>{{ money(summary.maximum_asking_price) }}</b>
        </div>

        <div>
          <span>Ort. brüt m² fiyatı</span>
          <b>
            {{
              money(
                summary.area_price_metrics.find((m) => m.area_type === "gross")
                  ?.average_price_per_m2,
              )
            }}
          </b>
        </div>

        <div>
          <span>Fiyatı gözlenen ilan</span>
          <b>
            {{
              numberTR(
                summary.observed_price_change.listings_with_multiple_snapshots,
              )
            }}
          </b>
        </div>

        <div>
          <span>Son veri güncellemesi</span>
          <b>{{ dateTR(summary.last_data_updated_at) }}</b>
        </div>

        <p class="panel-footnote" style="grid-column: 1 / -1">
          {{ summary.observed_price_change.interpretation }}
        </p>
      </div>
    </section>
  </div>

  <section class="panel mt-16">
    <div class="panel-header">
      <div>
        <h2>Fiyatı değişen ilanlar</h2>
        <p>
          Son güncellenen 10 ilan içindeki birden fazla fiyat gözlemi
          karşılaştırılır.
        </p>
      </div>

      <NuxtLink to="/price-history" class="panel-link">
        Fiyat geçmişi ↗
      </NuxtLink>
    </div>

    <StatePanel v-if="changedState === 'loading'" state="loading" />

    <StatePanel
      v-else-if="changedState === 'error'"
      state="error"
      :message="changedError"
      @retry="loadListings"
    />

    <StatePanel
      v-else-if="!changedListings.length"
      state="empty"
      message="İncelenen ilanlarda birden fazla ve farklı fiyat gözlemi bulunamadı."
    />

    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>İlan</th>
            <th>Önceki gözlem</th>
            <th>Son gözlem</th>
            <th>Değişim</th>
            <th>Gözlem tarihi</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="item in changedListings" :key="item.listing.id">
            <td>
              <div class="table-primary">{{ listingName(item.listing) }}</div>

              <div class="table-sub">
                {{ item.listing.location_label || `Gayrimenkul #${item.listing.property_id}` }}
              </div>
            </td>

            <td>
              {{ money(item.previous.asking_price, item.previous.currency) }}
            </td>

            <td class="table-primary">
              {{ money(item.current.asking_price, item.current.currency) }}
            </td>

            <td>
              <span v-if="item.currencyChanged" class="chip">
                Para birimi değişti
              </span>

              <span
                v-else-if="item.priceChanged"
                class="chip"
                :class="
                  Number(item.current.asking_price) >
                  Number(item.previous.asking_price)
                    ? 'chip-red'
                    : 'chip-green'
                "
              >
                {{
                  Number(item.current.asking_price) >
                  Number(item.previous.asking_price)
                    ? "+"
                    : "−"
                }}{{
                  money(
                    Math.abs(
                      Number(item.current.asking_price) -
                        Number(item.previous.asking_price),
                    ),
                    item.current.currency,
                  )
                }}
              </span>

              <span v-else>—</span>
            </td>

            <td>{{ dateTR(item.current.recorded_at) }}</td>

            <td>
              <NuxtLink
                :to="`/listings/${item.listing.id}/price-history`"
                class="text-link"
              >
                Geçmiş →
              </NuxtLink>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="panel-footnote">
      Yalnızca uygulamada kaydedilen fiyat gözlemleri karşılaştırılır; bu tablo
      gerçek ilk yayın fiyatı veya gerçekleşmiş satış fiyatı göstermez.
    </p>
  </section>
</template>
