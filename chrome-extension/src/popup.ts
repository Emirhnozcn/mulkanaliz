export {};
declare const chrome: any;

type PropertyCode =
  | "apartment"
  | "detached_house"
  | "villa"
  | "residential_zoned_land"
  | "commercial_zoned_land"
  | "farmland";

type Extracted = {
  url: string;
  sourceName: string;
  sourceListingId?: string;
  title?: string;
  price?: string;
  transactionType?: "sale" | "rent";
  address?: string;
  province?: string;
  district?: string;
  neighborhood?: string;
  netArea?: string;
  grossArea?: string;
  roomCount?: string;
  buildingAge?: string;
  floorNumber?: string;
  totalFloors?: string;
  parcelArea?: string;
  propertyType?: PropertyCode;
  warnings: string[];
};

const $ = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;

const apiBase = $<HTMLInputElement>("apiBase");
const loginEmail = $<HTMLInputElement>("loginEmail");
const loginPassword = $<HTMLInputElement>("loginPassword");
const loginState = $<HTMLParagraphElement>("loginState");
let locationId = $<HTMLSelectElement>("locationId");
const propertyType = $<HTMLSelectElement>("propertyType");
const previewPanel = $<HTMLElement>("previewPanel");
const statusBox = $<HTMLDivElement>("status");

let accessToken = "";
let authenticatedUserId = 0;
let extracted: Extracted | null = null;

type LocationOption = {
  id: number;
  label: string;
};

let availableLocations: LocationOption[] = [];

function status(message: string, kind: "" | "error" | "success" = ""): void {
  statusBox.textContent = message;
  statusBox.className = `status ${kind}`;
}

function value(id: string): string {
  return ($<HTMLInputElement>(id).value || "").trim();
}

function numericValue(id: string): string | undefined {
  let raw = value(id).replace(/\s/g, "");

  if (!raw) return undefined;

  if (raw.includes(",")) {
    raw = raw.replace(/\./g, "").replace(",", ".");
  } else if (/^\d{1,3}(?:\.\d{3})+$/.test(raw)) {
    raw = raw.replace(/\./g, "");
  }

  const number = Number(raw);
  return Number.isFinite(number) && number > 0 ? String(number) : undefined;
}

function set(id: string, v: string | undefined): void {
  $<HTMLInputElement>(id).value = v ?? "";
}

/* -------------------------------------------------------
   KONUM YÖNETİMİ
   Konumlar API'den alınır. Kullanıcı ID'yi elle girmez.
------------------------------------------------------- */

function getLocationLabel(item: Record<string, unknown>): string {
  const parts = [
    item.name,
    item.neighborhood_name,
    item.neighbourhood_name,
    item.district_name,
    item.city_name,
    item.province_name,
    item.city,
    item.district,
    item.neighborhood,
    item.address,
  ]
    .filter(
      (part): part is string =>
        typeof part === "string" && part.trim().length > 0,
    )
    .map((part) => part.trim());

  return [...new Set(parts)].join(" / ") || `Konum #${String(item.id)}`;
}

function normalizeLocations(data: unknown): LocationOption[] {
  let candidates: unknown[] = [];
  if (Array.isArray(data)) candidates = data;
  else if (data && typeof data === "object") {
    const object = data as Record<string, unknown>;
    const list = [
      object.items,
      object.results,
      object.locations,
      object.data,
    ].find(Array.isArray);
    if (Array.isArray(list)) candidates = list;
  }
  const rows = candidates.filter(
    (item): item is Record<string, unknown> =>
      !!item && typeof item === "object",
  );
  const byId = new Map<number, Record<string, unknown>>();
  for (const item of rows) {
    const id = Number(item.id ?? item.location_id);
    if (Number.isInteger(id) && id > 0) byId.set(id, item);
  }
  return [...byId.entries()]
    .filter(([, item]) => item.level === "neighborhood")
    .map(([id, item]) => {
      const parent = byId.get(Number(item.parent_id));
      const grandparent = parent
        ? byId.get(Number(parent.parent_id))
        : undefined;
      const label = [item.name, parent?.name, grandparent?.name]
        .filter(
          (part): part is string => typeof part === "string" && !!part.trim(),
        )
        .join(" / ");
      return { id, label: label || `Konum #${id}` };
    })
    .sort((a, b) => a.label.localeCompare(b.label, "tr-TR"));
}

/**
 * HTML'deki locationId alanı bir input ise select alanına dönüştürür.
 * Böylece mevcut HTML dosyasını hemen değiştirmek gerekmez.
 */
function ensureLocationSelector(): void {
  const current = document.getElementById("locationId");

  if (!current) return;

  if (current.tagName.toLowerCase() !== "select") {
    const select = document.createElement("select");

    select.id = "locationId";
    select.name = "locationId";
    select.className = current.className;
    select.required = true;
    select.setAttribute("aria-label", "Mahalle / konum seçimi");

    current.replaceWith(select);
    locationId = select;
  } else {
    locationId = current as HTMLSelectElement;
  }

  const label = document.querySelector<HTMLLabelElement>(
    'label[for="locationId"]',
  );

  if (label) {
    label.textContent = "Mahalle / konum";
  }
}

/**
 * Kullanıcının erişebildiği konum kayıtlarını API'den yükler.
 * Seçilen konumun ID'si arka planda option.value içinde tutulur.
 */
async function loadLocations(selectedId?: string): Promise<void> {
  ensureLocationSelector();

  const base = apiBase.value.trim().replace(/\/$/, "");

  if (!accessToken) {
    locationId.replaceChildren(
      new Option("Önce API hesabınızla giriş yapın", ""),
    );

    locationId.disabled = true;
    return;
  }

  locationId.disabled = true;

  locationId.replaceChildren(new Option("Konumlar yükleniyor…", ""));

  try {
    const response = await fetch(`${base}/api/v1/locations?limit=500`, {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
    });

    const data: unknown = await response.json().catch(() => []);

    if (!response.ok) {
      const detail =
        data && typeof data === "object" && "detail" in data
          ? String((data as { detail?: unknown }).detail ?? "")
          : "";

      throw new Error(
        detail || `Konumlar alınamadı (HTTP ${response.status}).`,
      );
    }

    availableLocations = normalizeLocations(data);

    locationId.replaceChildren(
      new Option(
        availableLocations.length
          ? "Mahalle / konum seçin"
          : "Sistemde kayıtlı konum bulunamadı",
        "",
      ),
    );

    for (const item of availableLocations) {
      locationId.add(new Option(item.label, String(item.id)));
    }

    if (
      selectedId &&
      availableLocations.some((item) => String(item.id) === selectedId)
    ) {
      locationId.value = selectedId;
    }

    locationId.disabled = availableLocations.length === 0;

    if (!availableLocations.length) {
      status(
        "Sistemde kayıtlı konum yok. Önce konum/mahalle kayıtları eklenmeli.",
        "error",
      );
    }
  } catch (error) {
    locationId.replaceChildren(new Option("Konumlar yüklenemedi", ""));

    locationId.disabled = true;

    status(
      error instanceof Error
        ? `Konum listesi alınamadı: ${error.message}`
        : "Konum listesi alınamadı.",
      "error",
    );
  }
}

/* -------------------------------------------------------
   OTOMATİK KONUM EŞLEŞTİRME / OLUŞTURMA
------------------------------------------------------- */
const TURKISH_PROVINCES = new Set([
  "adana",
  "adıyaman",
  "afyonkarahisar",
  "ağrı",
  "amasya",
  "ankara",
  "antalya",
  "artvin",
  "aydın",
  "balıkesir",
  "bilecik",
  "bingöl",
  "bitlis",
  "bolu",
  "burdur",
  "bursa",
  "çanakkale",
  "çankırı",
  "çorum",
  "denizli",
  "diyarbakır",
  "edirne",
  "elazığ",
  "erzincan",
  "erzurum",
  "eskişehir",
  "gaziantep",
  "giresun",
  "gümüşhane",
  "hakkâri",
  "hatay",
  "ığdır",
  "ısparta",
  "mersin",
  "istanbul",
  "izmir",
  "kars",
  "kastamonu",
  "kayseri",
  "kırklareli",
  "kırşehir",
  "kocaeli",
  "konya",
  "kütahya",
  "malatya",
  "manisa",
  "kahramanmaraş",
  "mardin",
  "muğla",
  "muş",
  "nevşehir",
  "niğde",
  "ordu",
  "rize",
  "sakarya",
  "samsun",
  "siirt",
  "sinop",
  "sivas",
  "tekirdağ",
  "tokat",
  "trabzon",
  "tunceli",
  "şanlıurfa",
  "uşak",
  "van",
  "yozgat",
  "zonguldak",
  "aksaray",
  "bayburt",
  "karaman",
  "kırıkkale",
  "batman",
  "şırnak",
  "bartın",
  "ardahan",
  "yalova",
  "karabük",
  "kilis",
  "osmaniye",
  "düzce",
]);
function normalizedLocationName(value: string): string {
  return value
    .trim()
    .replace(/\s+/g, " ")
    .replace(/İ/g, "i")
    .replace(/I/g, "ı")
    .toLocaleLowerCase("tr-TR");
}
function cleanNeighborhoodName(value: string): string {
  return value
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\s+(?:mahallesi|mahalle|mah\.?|mh\.?)$/i, "")
    .trim();
}
async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const base = apiBase.value.trim().replace(/\/$/, "");
  const response = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      Authorization: `Bearer ${accessToken}`,
      ...(init.headers || {}),
    },
  });
  const body: any = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return body as T;
}
async function getOrCreateLocation(
  level: "province" | "district" | "neighborhood",
  name: string,
  parentId: number | null,
): Promise<LocationOption & { level: string; parent_id: number | null }> {
  const cleaned =
    level === "neighborhood"
      ? cleanNeighborhoodName(name)
      : name.trim().replace(/\s+/g, " ");
  if (!cleaned) throw new Error(`${level} konumu sayfadan okunamadı.`);
  const rows = await apiRequest<
    Array<{ id: number; name: string; level: string; parent_id: number | null }>
  >(
    `/api/v1/locations?limit=500${parentId === null ? "" : `&parent_id=${parentId}`}${`&level=${level}`}`,
  );
  const existing = rows.find(
    (row) =>
      row.level === level &&
      normalizedLocationName(row.name) === normalizedLocationName(cleaned) &&
      row.parent_id === parentId,
  );
  if (existing)
    return {
      id: existing.id,
      label: existing.name,
      level,
      parent_id: parentId,
    };
  const created = await apiRequest<{
    id: number;
    name: string;
    level: string;
    parent_id: number | null;
  }>("/api/v1/locations", {
    method: "POST",
    body: JSON.stringify({
      parent_id: parentId,
      level,
      name: cleaned,
      normalized_name: normalizedLocationName(cleaned),
      external_code: null,
    }),
  });
  return {
    id: created.id,
    label: created.name,
    level,
    parent_id: created.parent_id,
  };
}
async function resolveListingLocation(): Promise<number> {
  if (!accessToken) throw new Error("Önce API hesabınızla giriş yapın.");
  // Önizlemedeki alanlar kaynak sayfadaki otomatik sonuçtan daha günceldir;
  // kullanıcı bunları düzenleyebilir.
  const provinceName = value("province");
  const districtName = value("district");
  const neighborhoodName = cleanNeighborhoodName(value("neighborhood"));
  if (!provinceName || !districtName || !neighborhoodName) {
    throw new Error(
      "İl, ilçe ve mahalle alanlarını kontrol edip doldurun. Örnek: Bolu / Merkez / Gölyüzü.",
    );
  }
  if (extracted) {
    extracted.province = provinceName;
    extracted.district = districtName;
    extracted.neighborhood = neighborhoodName;
  }
  const province = await getOrCreateLocation(
    "province",
    provinceName,
    null,
  );
  const district = await getOrCreateLocation(
    "district",
    districtName,
    province.id,
  );
  const neighborhood = await getOrCreateLocation(
    "neighborhood",
    neighborhoodName,
    district.id,
  );
  availableLocations = [
    {
      id: neighborhood.id,
      label: `${neighborhood.label} / ${district.label} / ${province.label}`,
    },
  ];
  locationId.replaceChildren(
    new Option(availableLocations[0].label, String(neighborhood.id)),
  );
  locationId.value = String(neighborhood.id);
  locationId.disabled = false;
  await chrome.storage.local.set({ locationId: String(neighborhood.id) });
  return neighborhood.id;
}

/* -------------------------------------------------------
   GAYRİMENKUL TÜRÜNE GÖRE ALANLAR
------------------------------------------------------- */

function showTypeFields(): void {
  const residential = ["apartment", "detached_house", "villa"].includes(
    propertyType.value,
  );

  document.querySelectorAll(".residential-fields").forEach((element) => {
    (element as HTMLElement).hidden = !residential;
  });

  document.querySelectorAll(".land-field").forEach((element) => {
    (element as HTMLElement).hidden = residential;
  });

  document.querySelectorAll(".zoning-fields").forEach((element) => {
    (element as HTMLElement).hidden =
      residential || propertyType.value === "farmland";
  });
}

/* -------------------------------------------------------
   İLAN VERİLERİNİ ÇIKARMA
------------------------------------------------------- */

// Sahibinden ilan sayfasından görünür verileri çıkarır.
function extractVisibleListingData(): Extracted {
  const warnings: string[] = [];
  const rawUrl = location.href;

  const normalize = (text: string): string =>
    text
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();

  const normalizeLabel = (text: string): string =>
    normalize(text)
      .replace(/:$/, "")
      .replace(/[²]/g, "2")
      .replace(/\s+/g, "")
      .toLocaleLowerCase("tr-TR");

  const provinceNames = new Set([
    "adana",
    "adıyaman",
    "afyonkarahisar",
    "ağrı",
    "amasya",
    "ankara",
    "antalya",
    "artvin",
    "aydın",
    "balıkesir",
    "bilecik",
    "bingöl",
    "bitlis",
    "bolu",
    "burdur",
    "bursa",
    "çanakkale",
    "çankırı",
    "çorum",
    "denizli",
    "diyarbakır",
    "edirne",
    "elazığ",
    "erzincan",
    "erzurum",
    "eskişehir",
    "gaziantep",
    "giresun",
    "gümüşhane",
    "hakkâri",
    "hatay",
    "ığdır",
    "ısparta",
    "mersin",
    "istanbul",
    "izmir",
    "kars",
    "kastamonu",
    "kayseri",
    "kırklareli",
    "kırşehir",
    "kocaeli",
    "konya",
    "kütahya",
    "malatya",
    "manisa",
    "kahramanmaraş",
    "mardin",
    "muğla",
    "muş",
    "nevşehir",
    "niğde",
    "ordu",
    "rize",
    "sakarya",
    "samsun",
    "siirt",
    "sinop",
    "sivas",
    "tekirdağ",
    "tokat",
    "trabzon",
    "tunceli",
    "şanlıurfa",
    "uşak",
    "van",
    "yozgat",
    "zonguldak",
    "aksaray",
    "bayburt",
    "karaman",
    "kırıkkale",
    "batman",
    "şırnak",
    "bartın",
    "ardahan",
    "yalova",
    "karabük",
    "kilis",
    "osmaniye",
    "düzce",
  ]);
  const normLocation = (text: string) =>
    text
      .trim()
      .replace(/İ/g, "i")
      .replace(/I/g, "ı")
      .toLocaleLowerCase("tr-TR");
  const cleanMahalle = (text: string) =>
    text.replace(/\s*(?:mahallesi|mah\.?|mh\.?)$/i, "").trim();

  // Türkçe ve İngilizce sayı biçimlerini güvenle sayıya çevirir:
  // "6.900.000 TL" -> 6900000, "1.250,50" -> 1250.5, "6900000.00" -> 6900000, "85,5" -> 85.5
  const parseNumber = (text?: string): string | undefined => {
    if (!text) return undefined;

    const match = normalize(text).match(
      /\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?/,
    );

    if (!match) return undefined;

    let token = match[0].replace(/\s/g, "");

    if (token.includes(",")) {
      // Virgül ondalık ayırıcıdır; noktalar binlik ayırıcıdır.
      token = token.replace(/\./g, "").replace(",", ".");
    } else if (/^\d{1,3}(?:\.\d{3})+$/.test(token)) {
      // Yalnızca binlik noktaları: 6.900.000 / 1.250
      token = token.replace(/\./g, "");
    }
    // Aksi halde tek nokta ondalıktır (6900000.00, 85.5).

    const number = Number(token);

    return Number.isFinite(number) && number > 0 ? String(number) : undefined;
  };

  const readText = (element: Element | null): string | undefined => {
    const text = normalize(element?.textContent ?? "");
    return text || undefined;
  };

  const details = new Map<string, string>();

  const saveDetail = (label: string, content: string): void => {
    const key = normalizeLabel(label);
    const normalizedContent = normalize(content);

    if (key && normalizedContent && !details.has(key)) {
      details.set(key, normalizedContent);
    }
  };

  // Tablo satırları.
  document.querySelectorAll("tr").forEach((row) => {
    const cells = Array.from(row.querySelectorAll(":scope > th, :scope > td"))
      .map((cell) => normalize(cell.textContent ?? ""))
      .filter(Boolean);

    if (cells.length >= 2) {
      saveDetail(cells[0], cells.slice(1).join(" "));
    }
  });

  // dt/dd eşleşmeleri.
  document.querySelectorAll("dt").forEach((dt) => {
    const label = normalize(dt.textContent ?? "");
    const sibling = dt.nextElementSibling;

    if (sibling?.matches("dd")) {
      saveDetail(label, sibling.textContent ?? "");
    }
  });

  // Etiket ve değer içeren liste elemanları.
  document.querySelectorAll("li").forEach((li) => {
    const text = normalize(li.textContent ?? "");

    const match = text.match(/^([^:：]{2,50})[:：]\s*(.+)$/);

    if (match) {
      saveDetail(match[1], match[2]);
    }

    const children = Array.from(li.children);

    if (children.length >= 2) {
      saveDetail(
        children[0].textContent ?? "",
        children
          .slice(1)
          .map((child) => child.textContent ?? "")
          .join(" "),
      );
    }
  });

  const getDetail = (...labels: string[]): string | undefined => {
    for (const label of labels) {
      const target = normalizeLabel(label);
      const exact = details.get(target);

      if (exact) return exact;
    }

    return undefined;
  };

  // Sahibinden'in farklı detay tablo yapıları.
  document
    .querySelectorAll(
      ".classifiedInfoList, #classifiedDetail .classifiedInfo, .classifiedInfoList li",
    )
    .forEach((container) => {
      const nodes = Array.from(
        container.querySelectorAll("dt, dd, strong, span, li"),
      );

      for (let i = 0; i + 1 < nodes.length; i++) {
        const label = normalize(nodes[i].textContent ?? "").replace(/:$/, "");

        const val = normalize(nodes[i + 1].textContent ?? "");

        if (
          /^(oda sayısı|bina yaşı|yapı yaşı|bulunduğu kat|katı|kat sayısı|bina kat sayısı|m² \(brüt\)|m² \(net\))$/i.test(
            label,
          )
        ) {
          saveDetail(label, val);
        }
      }
    });

  // Başlık ve değer aynı liste elemanında olduğunda.
  document
    .querySelectorAll(
      "#classifiedDetail .classifiedInfoList li, #classifiedDetail .classifiedInfo li",
    )
    .forEach((item) => {
      const text = normalize(item.textContent ?? "");

      const match = text.match(
        /^(Oda Sayısı|Bina Yaşı|Yapı Yaşı|Bulunduğu Kat|Kat Sayısı|Bina Kat Sayısı|m²\s*\(Brüt\)|m²\s*\(Net\))\s*:?\s*(.+)$/i,
      );

      if (match) {
        saveDetail(match[1], match[2]);
      }
    });

  // Etiketin bulunduğu hücrenin yanındaki değer.
  const wantedLabels = new Set([
    "odasayısı",
    "binayaşı",
    "yapıyaşı",
    "bulunduğukat",
    "katsayısı",
    "binakatsayısı",
    "m2(net)",
    "m2(brüt)",
  ]);

  document
    .querySelectorAll(
      "#classifiedDetail th, #classifiedDetail td, #classifiedDetail dt, #classifiedDetail .label, #classifiedDetail .classifiedInfoTitle",
    )
    .forEach((labelNode) => {
      const label = normalizeLabel(labelNode.textContent ?? "");

      if (!wantedLabels.has(label)) return;

      const row = labelNode.closest("tr");

      if (row) {
        const cells = Array.from(row.querySelectorAll("th, td"));

        const index = cells.indexOf(labelNode as HTMLTableCellElement);

        const valueNode = cells[index + 1];

        if (valueNode) {
          saveDetail(label, valueNode.textContent ?? "");
        }

        return;
      }

      const sibling = labelNode.nextElementSibling;

      if (sibling) {
        saveDetail(label, sibling.textContent ?? "");
      }
    });

  // İlan başlığı.
  const title =
    readText(document.querySelector("#classifiedDetail h1")) ||
    readText(document.querySelector("h1")) ||
    normalize(
      document
        .querySelector('meta[property="og:title"]')
        ?.getAttribute("content") ?? "",
    ) ||
    document.title ||
    undefined;

  // Sahibinden ilan numarası.
  const idElement = document.querySelector("#classifiedId");

  const idFromSahibinden =
    idElement?.getAttribute("data-classifiedid")?.match(/\d{8,}/)?.[0] ||
    idElement?.textContent?.match(/\d{8,}/)?.[0];

  const idFromUrl =
    rawUrl.match(/\/(\d{8,})(?:\/detay)?(?:[/?#]|$)/)?.[1] ||
    rawUrl.match(/(\d{8,})/)?.[1];

  const sourceListingId =
    idFromSahibinden ||
    getDetail("İlan No", "İlan numarası")?.match(/\d{8,}/)?.[0] ||
    idFromUrl;

  // İlan fiyatı.
  let price = parseNumber(
    document.querySelector("h3.classifiedPriceValue")?.textContent ?? "",
  );

  if (!price) {
    const metaPrice = document.querySelector(
      'meta[property="product:price:amount"], meta[itemprop="price"]',
    );

    price =
      parseNumber(metaPrice?.getAttribute("content") ?? "") ||
      parseNumber(metaPrice?.textContent ?? "");
  }

  if (!price) {
    const priceElements = Array.from(
      document.querySelectorAll(
        ".classifiedPrice, .classified-price-wrapper, [class*='priceValue']",
      ),
    );

    for (const element of priceElements) {
      const text = normalize(element.textContent ?? "");

      if (text.length > 80) continue;

      const parsed = parseNumber(text);

      if (parsed) {
        price = parsed;
        break;
      }
    }
  }

  // İşlem türü.
  const titleLower = (title ?? "").toLocaleLowerCase("tr-TR");

  const detailText = normalize(
    document.querySelector("#classifiedDetail")?.textContent ?? "",
  ).toLocaleLowerCase("tr-TR");

  const urlLower = rawUrl.toLocaleLowerCase("tr-TR");

  let transactionType: "sale" | "rent" | undefined;

  if (
    titleLower.includes("kiralık") ||
    /(?:^|[/\s_-])kiralik(?:[/\s_-]|$)/i.test(urlLower)
  ) {
    transactionType = "rent";
  } else if (
    titleLower.includes("satılık") ||
    /(?:^|[/\s_-])satilik(?:[/\s_-]|$)/i.test(urlLower)
  ) {
    transactionType = "sale";
  } else if (detailText.includes("kiralık")) {
    transactionType = "rent";
  } else if (detailText.includes("satılık")) {
    transactionType = "sale";
  }

  // İlan özellikleri.
  const netArea = parseNumber(
    getDetail("m² (Net)", "m²(Net)", "Net m²", "Net Alan", "Net Metrekare"),
  );

  const grossArea = parseNumber(
    getDetail(
      "m² (Brüt)",
      "m²(Brüt)",
      "Brüt m²",
      "Brüt Alan",
      "Brüt Metrekare",
    ),
  );

  const roomText = getDetail("Oda Sayısı", "Oda");

  const roomCount = roomText
    ? roomText.match(/\d+\s*\+\s*\d+/)?.[0].replace(/\s/g, "") ||
      roomText.match(/^\d+$/)?.[0] ||
      (/st[üu]dyo/i.test(roomText) ? "1+0" : undefined)
    : undefined;

  const buildingAge = getDetail("Bina Yaşı", "Yapı Yaşı") || undefined;

  const floorNumber = parseNumber(
    getDetail("Bulunduğu Kat", "Bulunduğu kat", "Daire Katı"),
  );

  const totalFloors = parseNumber(
    getDetail("Kat Sayısı", "Bina Kat Sayısı", "Toplam Kat Sayısı"),
  );

  const parcelArea = parseNumber(
    getDetail("Arsa m²", "Arsa Alanı", "Parsel Alanı", "Tarla Alanı", "m²"),
  );

  const address =
    getDetail("Adres") ||
    readText(document.querySelector('[itemprop="streetAddress"]')) ||
    undefined;

  // -----------------------------------------------------------------
  // İL / İLÇE / MAHALLE ÇIKARIMI
  // Sahibinden arayüzü sık değiştiği için tek bir seçiciye güvenilmez.
  // Birden çok strateji sırayla denenir; ilk eksiksiz sonuç kullanılır,
  // yoksa stratejilerden gelen kısmi sonuçlar birleştirilir.
  // -----------------------------------------------------------------
  const fold = (text: string): string =>
    text
      .replace(/İ/g, "i")
      .replace(/I/g, "ı")
      .toLocaleLowerCase("tr-TR")
      .replace(/[âä]/g, "a")
      .replace(/ç/g, "c")
      .replace(/ğ/g, "g")
      .replace(/ı/g, "i")
      .replace(/[öô]/g, "o")
      .replace(/ş/g, "s")
      .replace(/[üû]/g, "u")
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  const provinceFold = new Set<string>(
    [...provinceNames, "afyon", "icel", "hakkari", "adiyaman"].map(fold),
  );
  const isProvince = (text: string): boolean => provinceFold.has(fold(text));
  const MAH_SUFFIX = /\s+(?:mahallesi|mahalle|mah\.?|mh\.?)$/i;
  const isMahalle = (text: string): boolean =>
    MAH_SUFFIX.test(normalize(text)) || /^(?:mahallesi|mah\.?|mh\.?)$/i.test(text);
  const stripMah = (text: string): string =>
    normalize(text).replace(MAH_SUFFIX, "").trim();
  const hoodFromCrumb = (text: string): string =>
    stripMah(text.includes("/") ? text.split("/").pop()!.trim() : text);

  type LocParts = {
    province?: string;
    district?: string;
    neighborhood?: string;
  };
  const locCandidates: LocParts[] = [];

  // Sıralı bir öğe listesinden (il, ilçe, [semt], mahalle) çıkarımı.
  const chainFromItems = (items: string[], lenient: boolean): LocParts | null => {
    const clean = items.map((item) => normalize(item)).filter(Boolean);
    const idx = clean.findIndex((item) => isProvince(item));
    if (idx < 0) return null;
    const result: LocParts = { province: clean[idx] };
    const rest = clean.slice(idx + 1, idx + 5);
    const districtItem = rest[0];
    if (districtItem && !isMahalle(districtItem) && !isProvince(districtItem)) {
      result.district = districtItem.includes("/")
        ? districtItem.split("/")[0].trim()
        : districtItem;
    }
    const tail = rest.slice(result.district ? 1 : 0);
    const hood =
      [...tail].reverse().find((item) => isMahalle(item)) ??
      (lenient ? tail.find((item) => item.includes("/")) : undefined) ??
      (lenient && tail.length === 1 ? tail[0] : undefined);
    if (hood) result.neighborhood = hoodFromCrumb(hood);
    return result;
  };

  // Strateji 1: Sahibinden konum bağlantıları (address_city / address_town / address_quarter).
  {
    const scope: ParentNode =
      document.querySelector("#classifiedDetail") ??
      document.querySelector(".classifiedInfo")?.parentElement ??
      document;
    const parts: LocParts = {};
    scope
      .querySelectorAll<HTMLAnchorElement>(
        'a[href*="address_quarter"], a[href*="address_town"], a[href*="address_city"]',
      )
      .forEach((anchor) => {
        const text = normalize(anchor.textContent ?? "");
        if (!text) return;
        const href = anchor.getAttribute("href") ?? "";
        if (/address_quarter/.test(href)) {
          parts.neighborhood ??= hoodFromCrumb(text);
        } else if (/address_town/.test(href)) {
          parts.district ??= text;
        } else if (/address_city/.test(href)) {
          parts.province ??= text;
        }
      });
    if (parts.province || parts.district || parts.neighborhood) {
      locCandidates.push(parts);
    }
  }

  // Strateji 2: aynı üst öğeyi paylaşan bağlantı/öğe grupları
  // (ör. <h2><a>Bolu</a><a>Merkez</a><a>Gölyüzü Mah.</a></h2>).
  {
    const groups = new Map<Element, string[]>();
    document
      .querySelectorAll("#classifiedDetail a, .classifiedInfo a, h2 a, h3 a")
      .forEach((anchor) => {
        const parent = anchor.parentElement;
        const text = normalize(anchor.textContent ?? "");
        if (!parent || !text || text.length > 60) return;
        const list = groups.get(parent) ?? [];
        list.push(text);
        groups.set(parent, list);
      });
    for (const items of groups.values()) {
      const chain = chainFromItems(items, true);
      if (chain?.province && (chain.district || chain.neighborhood)) {
        locCandidates.push(chain);
      }
    }
  }

  // Strateji 3: breadcrumb (kırıntı) listeleri.
  {
    const breadcrumbSelectors = [
      "li.bc-item",
      "ol[class*=breadcrumb] li, ul[class*=breadcrumb] li",
      "[class*=Breadcrumb] li, [class*=breadcrumb] li",
      "[data-testid*=breadcrumb] li, [data-testid*=breadcrumb] a",
      ".breadcrumb a, .classifiedBreadcrumb a, .classified-breadcrumb a",
      "#breadCrumb a, .breadCrumb a",
    ];
    for (const selector of breadcrumbSelectors) {
      const items = Array.from(document.querySelectorAll(selector))
        .map((node) => normalize(node.textContent ?? ""))
        .filter(Boolean);
      const chain = chainFromItems(items, true);
      if (chain?.province) locCandidates.push(chain);
    }
  }

  // Strateji 4: görünen kısa metin blokları ("Bolu / Merkez / Gölyüzü Mah." vb.).
  {
    const blocks = document.querySelectorAll(
      "#classifiedDetail h1, #classifiedDetail h2, #classifiedDetail h3, #classifiedDetail div, #classifiedDetail span, #classifiedDetail li, #classifiedDetail p, .classifiedInfo *",
    );
    let inspected = 0;
    for (const block of Array.from(blocks)) {
      if (inspected > 800) break;
      if (block.children.length > 8) continue;
      const raw = ((block as HTMLElement).innerText ?? block.textContent ?? "")
        .replace(/ /g, " ")
        .trim();
      if (!raw || raw.length > 120) continue;
      inspected++;
      const pieces = raw
        .split(/\s*(?:\r?\n|\/|>|›|»|,|\||\s[-–]\s)\s*/)
        .map((piece) => piece.trim())
        .filter(Boolean);
      let chain = chainFromItems(pieces, false);
      if (!chain && pieces.length === 1) {
        // "Bolu Merkez Gölyüzü Mah." gibi ayraçsız tek satır.
        const words = pieces[0].split(/\s+/);
        if (words.length >= 3 && isProvince(words[0]) && isMahalle(pieces[0])) {
          const mahIndex = words.length - 1;
          const hoodWord = words[mahIndex - 1];
          chain = {
            province: words[0],
            district: words.slice(1, mahIndex - 1).join(" ") || undefined,
            neighborhood: hoodWord,
          };
        }
      }
      if (chain?.province && chain.neighborhood) {
        locCandidates.push(chain);
        break;
      }
    }
  }

  // Strateji 5: JSON-LD / meta / başlık içindeki adres bilgileri.
  {
    const parts: LocParts = {};
    document
      .querySelectorAll('script[type="application/ld+json"]')
      .forEach((script) => {
        try {
          const walk = (node: unknown): void => {
            if (!node || typeof node !== "object") return;
            if (Array.isArray(node)) return node.forEach(walk);
            const obj = node as Record<string, unknown>;
            const region = obj.addressRegion;
            const locality = obj.addressLocality;
            if (typeof region === "string" && !parts.province) parts.province = region;
            if (typeof locality === "string" && !parts.district) parts.district = locality;
            Object.values(obj).forEach(walk);
          };
          walk(JSON.parse(script.textContent ?? "null"));
        } catch {
          /* geçersiz JSON-LD yoksayılır */
        }
      });
    const sources = [
      document.querySelector('meta[name="description"]')?.getAttribute("content"),
      document.querySelector('meta[property="og:description"]')?.getAttribute("content"),
      title,
      document.title,
    ].filter((item): item is string => !!item);
    for (const source of sources) {
      const match = normalize(source).match(
        /([A-Za-zÇĞİÖŞÜçğıöşüÂâ]+)\s+(?:Mahallesi|Mah\.?|Mh\.?)(?=\s|$|,|\.)/,
      );
      if (match && !parts.neighborhood) parts.neighborhood = match[1];
    }
    if (parts.province || parts.district || parts.neighborhood) {
      locCandidates.push(parts);
    }
  }

  // Adaylardan en iyisini seç; eksik alanları diğer adaylardan tamamla.
  const completeCandidate = locCandidates.find(
    (item) => item.province && item.district && item.neighborhood,
  );
  const merged: LocParts = completeCandidate
    ? { ...completeCandidate }
    : locCandidates.reduce<LocParts>(
        (acc, item) => ({
          province: acc.province ?? item.province,
          district: acc.district ?? item.district,
          neighborhood: acc.neighborhood ?? item.neighborhood,
        }),
        {},
      );
  const clip = (text?: string): string | undefined => {
    const cleaned = text ? normalize(text) : "";
    return cleaned && cleaned.length <= 80 ? cleaned : undefined;
  };
  const province = clip(merged.province);
  const district = clip(merged.district);
  const neighborhood = clip(merged.neighborhood && stripMah(merged.neighborhood));

  const missingLocation = [
    !province ? "il" : "",
    !district ? "ilçe" : "",
    !neighborhood ? "mahalle" : "",
  ].filter(Boolean);
  if (missingLocation.length) {
    warnings.push(
      `Konum otomatik okunamadı (eksik: ${missingLocation.join(", ")}); önizlemede elle tamamlayın.`,
    );
  }

  // -----------------------------------------------------------------
  // GAYRİMENKUL TÜRÜ (daire / müstakil ev / villa / arsa / tarla)
  // Kaynaklar güvenilirlik sırasıyla denenir: "Emlak Tipi" alanı, kategori
  // kırıntısı, ilan başlığı, adres çubuğundaki ilan adı.
  // -----------------------------------------------------------------
  const classifyType = (raw: string | undefined): PropertyCode | undefined => {
    if (!raw) return undefined;
    const t = fold(raw);
    if (!t) return undefined;
    if (/\b(tarla|bag bahce|zeytinlik|tarim arazisi|sera|fidanlik|cayir|mera)\b/.test(t)) {
      return /\bimarli\b/.test(t) && !/\btarla\b/.test(t) ? undefined : "farmland";
    }
    if (/\bticari\b.*\b(imar|arsa)|\b(imar|arsa)\b.*\bticari\b|\bsanayi\b|\bturizm\b/.test(t)) {
      return "commercial_zoned_land";
    }
    if (/\b(konut imarli|imarli|konut arsasi|arsa)\b/.test(t)) {
      return "residential_zoned_land";
    }
    if (/\bvilla\b/.test(t)) return "villa";
    if (/\b(mustakil|mustakil ev|yazlik|koy evi|cift ?lik evi|bungalov|prefabrik|kosk|konak|yali)\b/.test(t)) {
      return "detached_house";
    }
    if (/\b(daire|rezidans|residence|apartman|dubleks|tripleks|studyo|bahce kati|cati kati|zemin kat)\b/.test(t)) {
      return "apartment";
    }
    return undefined;
  };

  const crumbTexts: string[] = [];
  for (const selector of [
    "li.bc-item",
    "ol[class*=breadcrumb] li, ul[class*=breadcrumb] li",
    "[class*=Breadcrumb] li, [class*=breadcrumb] li",
    "[data-testid*=breadcrumb] li, [data-testid*=breadcrumb] a",
    ".breadcrumb a, .classifiedBreadcrumb a, .classified-breadcrumb a",
    "#breadCrumb a, .breadCrumb a",
  ]) {
    document.querySelectorAll(selector).forEach((node) => {
      const text = normalize(node.textContent ?? "");
      if (text && !crumbTexts.includes(text)) crumbTexts.push(text);
    });
  }

  // Kırıntıda il/ilçe/mahalle adları tür sözcüğü taşıyabilir (ör. "Villa Mh."); bunları atla.
  const categoryCrumbs = crumbTexts.filter(
    (crumb) => !isProvince(crumb) && !isMahalle(crumb) && crumb !== district,
  );
  const titleText = normalize(
    document.querySelector("#classifiedDetail h1")?.textContent ?? title ?? "",
  );
  const slugText = (() => {
    try {
      return decodeURIComponent(
        new URL(rawUrl).pathname.replace(/[-_/]+/g, " "),
      );
    } catch {
      return "";
    }
  })();

  const typeSources: Array<string | undefined> = [
    getDetail("Emlak Tipi", "Emlak Türü", "Tür", "Kategori"),
    ...categoryCrumbs.slice().reverse(),
    titleText,
    slugText,
  ];
  let propertyType: PropertyCode | undefined;
  for (const source of typeSources) {
    propertyType = classifyType(source);
    if (propertyType) break;
  }
  // Arsa ilanında "İmar Durumu" alanı ince ayar yapar (Tarla/Bağ-Bahçe, Ticari, Konut).
  if (propertyType === "residential_zoned_land") {
    const zoning = fold(getDetail("İmar Durumu") ?? "");
    if (/\b(tarla|bag|bahce|zeytin|tarim)\b/.test(zoning)) {
      propertyType = "farmland";
    } else if (/\b(ticari|sanayi|turizm)\b/.test(zoning) && !/\bkonut\b/.test(zoning)) {
      propertyType = "commercial_zoned_land";
    }
  }
  const isResidentialType =
    propertyType === undefined ||
    propertyType === "apartment" ||
    propertyType === "detached_house" ||
    propertyType === "villa";

  if (!propertyType) {
    warnings.push("Gayrimenkul türü otomatik anlaşılamadı; önizlemeden seçin.");
  }

  if (!price) {
    warnings.push("Fiyat bulunamadı; elle girin.");
  }

  if (!sourceListingId) {
    warnings.push("İlan numarası bulunamadı.");
  }

  if (isResidentialType && !netArea) {
    warnings.push("Net m² bulunamadı.");
  }

  if (isResidentialType && !grossArea) {
    warnings.push("Brüt m² bulunamadı.");
  }

  if (isResidentialType && !roomCount) {
    warnings.push("Oda sayısı bulunamadı.");
  }

  if (isResidentialType && !buildingAge) {
    warnings.push("Bina yaşı bulunamadı.");
  }

  if (isResidentialType && !floorNumber) {
    warnings.push("Dairenin bulunduğu kat bulunamadı.");
  }

  if (isResidentialType && !totalFloors) {
    warnings.push("Bina kat sayısı bulunamadı.");
  }

  if (!isResidentialType && !parcelArea) {
    warnings.push("Parsel alanı (m²) bulunamadı; elle girin.");
  }

  if (!transactionType) {
    warnings.push("İlan türü (satılık/kiralık) bulunamadı; elle seçin.");
  }

  warnings.push(
    "Aktarmadan önce çıkarılan bilgileri kaynak ilanla karşılaştırın.",
  );

  return {
    url: rawUrl,
    sourceName: location.hostname,
    sourceListingId,
    title,
    price,
    transactionType,
    address,
    province,
    district,
    neighborhood,
    netArea,
    grossArea,
    roomCount,
    buildingAge,
    floorNumber,
    totalFloors,
    parcelArea,
    propertyType,
    warnings,
  };
}

/* -------------------------------------------------------
   BAŞLANGIÇ
------------------------------------------------------- */

async function init(): Promise<void> {
  const saved = await chrome.storage.local.get([
    "apiBase",
    "accessToken",
    "authenticatedUserId",
    "locationId",
    "propertyType",
  ]);

  apiBase.value = String(saved.apiBase ?? "http://localhost:8000");

  accessToken = String(saved.accessToken ?? "");

  authenticatedUserId = Number(saved.authenticatedUserId ?? 0);

  loginState.textContent = accessToken
    ? `Giriş yapılmış (kullanıcı ID: ${authenticatedUserId}).`
    : "Giriş yapılmadı.";

  ensureLocationSelector();

  propertyType.value = String(saved.propertyType ?? "apartment");

  showTypeFields();

  await loadLocations(String(saved.locationId ?? ""));
}

/* -------------------------------------------------------
   API GİRİŞİ
------------------------------------------------------- */

$("login").addEventListener("click", async () => {
  const base = apiBase.value.trim().replace(/\/$/, "");

  const email = loginEmail.value.trim();
  const password = loginPassword.value;

  if (!email || !password) {
    return status("Giriş için kullanıcı adı ve parola girin.", "error");
  }

  let origin: string;

  try {
    origin = new URL(base).origin;
  } catch {
    return status("Geçerli bir API adresi girin.", "error");
  }

  const granted = await chrome.permissions.request({
    origins: [`${origin}/*`],
  });

  if (!granted) {
    return status("API sunucusuna erişim izni verilmedi.", "error");
  }

  const button = $<HTMLButtonElement>("login");

  button.disabled = true;

  try {
    const response = await fetch(`${base}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        username: email,
        password,
      }),
    });

    const result = (await response.json().catch(() => ({}))) as {
      access_token?: string;
      user?: { id?: number };
      detail?: string;
    };

    if (!response.ok || !result.access_token || !result.user?.id) {
      const detail = Array.isArray(result.detail)
        ? result.detail
            .map(
              (item: any) =>
                `${(item.loc ?? []).join(" → ")}: ${item.msg ?? "geçersiz değer"}`,
            )
            .join("; ")
        : result.detail;

      throw new Error(detail ?? `Giriş başarısız (HTTP ${response.status}).`);
    }

    accessToken = result.access_token;
    authenticatedUserId = result.user.id;

    await chrome.storage.local.set({
      apiBase: base,
      accessToken,
      authenticatedUserId,
    });

    loginPassword.value = "";

    loginState.textContent = `Giriş yapıldı (kullanıcı ID: ${authenticatedUserId}).`;

    status("API girişi başarılı.", "success");

    // Giriş başarılı olunca konumları otomatik yükle.
    await loadLocations();
  } catch (error) {
    status(
      error instanceof Error ? error.message : "Giriş başarısız.",
      "error",
    );
  } finally {
    button.disabled = false;
  }
});

$("propertyType").addEventListener("change", showTypeFields);

/* -------------------------------------------------------
   AÇIK İLANDAN VERİ ÇIKARMA
------------------------------------------------------- */

$("extract").addEventListener("click", async () => {
  status("Açık sayfa inceleniyor…");

  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    if (!tab?.id || !tab.url || !/^https?:\/\//i.test(tab.url)) {
      throw new Error("Normal bir HTTP(S) ilan sayfası açıp tekrar deneyin.");
    }

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractVisibleListingData,
    });

    extracted = results[0]?.result ?? null;

    if (!extracted) {
      throw new Error("Sayfadan veri alınamadı.");
    }

    previewPanel.hidden = false;

    $<HTMLParagraphElement>("sourceLabel").textContent =
      `Kaynak: ${extracted.sourceName}`;

    $<HTMLParagraphElement>("warnings").textContent =
      extracted.warnings.join("\n");

    $<HTMLParagraphElement>("sourceUrl").textContent = extracted.url;

    set("title", extracted.title);
    set("price", extracted.price);
    set("address", extracted.address);
    set("province", extracted.province);
    set("district", extracted.district);
    set("neighborhood", extracted.neighborhood);
    set("netArea", extracted.netArea);
    set("grossArea", extracted.grossArea);
    set("roomCount", extracted.roomCount);
    set("buildingAge", extracted.buildingAge);
    set("floorNumber", extracted.floorNumber);
    set("totalFloors", extracted.totalFloors);
    set("parcelArea", extracted.parcelArea);
    set("sourceListingId", extracted.sourceListingId);

    if (extracted.transactionType) {
      $<HTMLSelectElement>("transactionType").value = extracted.transactionType;
    }

    // Gayrimenkul türünü sayfadan otomatik seç; algılanamazsa mevcut seçim kalır.
    if (extracted.propertyType) {
      propertyType.value = extracted.propertyType;
      await chrome.storage.local.set({ propertyType: extracted.propertyType });
    }
    showTypeFields();

    if (
      accessToken &&
      extracted.province &&
      extracted.district &&
      extracted.neighborhood
    ) {
      try {
        await resolveListingLocation();
        status(
          `Önizleme hazır. Tür: ${propertyType.selectedOptions[0]?.text ?? "—"}. Konum otomatik eşleştirildi: ${extracted.province} / ${extracted.district} / ${extracted.neighborhood}.`,
          "success",
        );
      } catch (locationError) {
        status(
          `Önizleme hazır; konum otomatik eşleştirilemedi: ${locationError instanceof Error ? locationError.message : "bilinmeyen hata"}`,
          "error",
        );
      }
    } else {
      status(
        "Önizleme hazır. İl, ilçe ve mahalle alanlarını kontrol edip eksik olanları doldurun.",
        "success",
      );
    }
  } catch (error) {
    status(
      error instanceof Error ? error.message : "Sayfadan veri çıkarılamadı.",
      "error",
    );
  }
});

/* -------------------------------------------------------
   İLANI API'YE AKTARMA
------------------------------------------------------- */

$("import").addEventListener("click", async () => {
  if (!extracted) {
    return status("Önce açık sayfadan veri çıkarın.", "error");
  }

  const price = numericValue("price");
  const userId = authenticatedUserId;
  let locId = Number(locationId.value);

  // Konum alanları doluysa seçicide kalmış eski konum yerine bunları esas al.
  extracted.province = value("province") || extracted.province;
  extracted.district = value("district") || extracted.district;
  extracted.neighborhood = value("neighborhood") || extracted.neighborhood;

  if (!price) {
    return status("Geçerli ve pozitif bir fiyat girin.", "error");
  }

  if (!accessToken || !Number.isInteger(userId) || userId < 1) {
    return status("Önce API hesabınızla giriş yapın.", "error");
  }

  try {
    if (value("province") && value("district") && value("neighborhood")) {
      locId = await resolveListingLocation();
    } else if (
      !Number.isInteger(locId) ||
      locId < 1 ||
      !availableLocations.some((item) => item.id === locId)
    ) {
      locId = await resolveListingLocation();
    }
  } catch (error) {
    return status(
      error instanceof Error
        ? error.message
        : "İlan konumu eşleştirilemedi.",
      "error",
    );
  }

  const type = propertyType.value;

  const residential = ["apartment", "detached_house", "villa"].includes(type);

  const parcelArea = numericValue("parcelArea");

  if (!residential && !parcelArea) {
    return status("Arsa/tarla aktarımı için parsel alanını girin.", "error");
  }

  const base = apiBase.value.trim().replace(/\/$/, "");

  let apiOrigin: string;

  try {
    const parsedUrl = new URL(base);

    if (!/^https?:$/.test(parsedUrl.protocol)) {
      return status("API adresi HTTP(S) olmalıdır.", "error");
    }

    apiOrigin = parsedUrl.origin;
  } catch {
    return status("Geçerli bir API adresi girin.", "error");
  }

  const granted = await chrome.permissions.request({
    origins: [`${apiOrigin}/*`],
  });

  if (!granted) {
    return status("API sunucusuna erişim izni verilmedi.", "error");
  }

  const payload: Record<string, unknown> = {
    source_url: extracted.url,
    source_name: extracted.sourceName,
    source_listing_id: value("sourceListingId") || undefined,
    created_by: userId,
    location_id: locId,
    property_type_code: type,
    transaction_type: value("transactionType") || "sale",
    asking_price: Number(price),
    currency: "TRY",
    title: value("title") || undefined,
    address: value("address") || undefined,
    notes:
      "Chrome eklentisi önizlemesinde kullanıcı tarafından onaylandı. Kaynak ilan bilgileri doğrulanmalıdır.",
  };

  if (residential) {
    payload.net_area_m2 = numericValue("netArea");

    payload.gross_area_m2 = numericValue("grossArea");

    const rooms = value("roomCount");

    const roomMatch = rooms.match(/^(\d+)\s*\+\s*(\d+)$/);

    if (roomMatch) {
      payload.room_count = Number(roomMatch[1]) + Number(roomMatch[2]);
      payload.living_room_count = Number(roomMatch[2]);

      payload.notes += ` Oda düzeni: ${rooms}.`;
    } else if (/^\d+$/.test(rooms) && Number(rooms) > 0) {
      payload.room_count = Number(rooms);
    }

    const age = value("buildingAge");
    const ageMatch = age.match(/(\d+)/);

    if (ageMatch && Number(ageMatch[1]) >= 0) {
      payload.building_age = Number(ageMatch[1]);
    }

    if (age) {
      payload.notes += ` İlan metnindeki bina yaşı: ${age}.`;
    }

    const floor = value("floorNumber");
    const floors = value("totalFloors");

    if (floor !== "" && Number.isFinite(Number(floor))) {
      payload.floor_number = Number(floor);
    }

    if (
      floors !== "" &&
      Number.isFinite(Number(floors)) &&
      Number(floors) > 0
    ) {
      payload.total_floors = Number(floors);
    }
  } else {
    payload.parcel_area_m2 = parcelArea;

    if (type !== "farmland") {
      payload.zoning_status = value("zoningStatus") || undefined;

      payload.zoning_use = value("zoningUse") || undefined;
    }
  }

  const button = $<HTMLButtonElement>("import");

  button.disabled = true;

  status("API ile bağlantı kuruluyor…");

  try {
    await chrome.storage.local.set({
      apiBase: base,
      authenticatedUserId: userId,
      locationId: String(locId),
      propertyType: type,
    });

    const response = await fetch(`${base}/api/v1/imports/listing`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
    });

    const result = (await response.json().catch(() => ({}))) as {
      action?: string;
      message?: string;
      detail?: string;
      error?: { message?: string };
    };

    if (!response.ok) {
      const detail = Array.isArray(result.detail)
        ? result.detail
            .map(
              (item: any) =>
                `${(item.loc ?? []).join(" → ")}: ${item.msg ?? "geçersiz değer"}`,
            )
            .join("; ")
        : (result.error?.message ?? result.detail);

      throw new Error(
        detail ?? `API isteği başarısız (HTTP ${response.status}).`,
      );
    }

    status(
      `${result.message ?? "Aktarım tamamlandı."}\nİşlem: ${result.action ?? "tamamlandı"}.`,
      "success",
    );
  } catch (error) {
    status(
      `${error instanceof Error ? error.message : "Aktarım başarısız."}\nAPI bağlantısını, CORS ayarlarını ve giriş durumunu kontrol edin.`,
      "error",
    );
  } finally {
    button.disabled = false;
  }
});

void init();
