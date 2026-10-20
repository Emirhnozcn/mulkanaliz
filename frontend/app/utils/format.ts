export const money = (value: string | number | null | undefined, currency = 'TRY') => {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency, maximumFractionDigits: 0 }).format(number)
}
export const numberTR = (value: string | number | null | undefined, digits = 0) => {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  return Number.isFinite(number) ? new Intl.NumberFormat('tr-TR', { maximumFractionDigits: digits }).format(number) : '—'
}
export const dateTR = (value: string | null | undefined) => value ? new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
export const listingStatus = (status: string) => ({ active: 'Aktif', passive: 'Pasif', sold: 'Satıldı', withdrawn: 'Geri çekildi' }[status] || status)

type ListingLike = {
  id: number; property_id: number; title?: string | null; location_label?: string | null; neighborhood_name?: string | null; district_name?: string | null;
  property_type_name?: string | null; room_label?: string | null; room_count?: number | null; net_area_m2?: string | number | null; gross_area_m2?: string | number | null;
  parcel_area_m2?: string | number | null; building_age?: number | null; floor_number?: number | null; total_floors?: number | null; transaction_type?: string
}
const m2 = (v: string | number | null | undefined) => { const n = Number(v); return v !== null && v !== undefined && v !== '' && Number.isFinite(n) && n > 0 ? `${new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 1 }).format(n)} m²` : '' }
/** Konum + tür + oda + m² gibi ilanları birbirinden ayıran kısa özet parçaları. */
export const listingFacts = (l: ListingLike): string[] => {
  const facts: string[] = []
  if (l.property_type_name) facts.push(l.property_type_name)
  if (l.room_label) facts.push(l.room_label)
  else if (l.room_count) facts.push(`${l.room_count} oda`)
  const area = m2(l.net_area_m2) ? `${m2(l.net_area_m2)} net` : m2(l.gross_area_m2) ? `${m2(l.gross_area_m2)} brüt` : m2(l.parcel_area_m2) ? `${m2(l.parcel_area_m2)} parsel` : ''
  if (area) facts.push(area)
  if (l.building_age !== null && l.building_age !== undefined) facts.push(l.building_age === 0 ? 'Sıfır bina' : `${l.building_age} yaşında`)
  if (l.floor_number !== null && l.floor_number !== undefined) facts.push(l.total_floors ? `${l.floor_number}. kat / ${l.total_floors}` : `${l.floor_number}. kat`)
  return facts
}
/** Başlık yoksa bile ayırt edici bir ilan adı üretir: "Gölyüzü · 2+1 · 95 m² · İlan #12". */
export const listingName = (l: ListingLike): string => {
  const parts = [l.neighborhood_name ? `${l.neighborhood_name} Mah.` : '', l.room_label || (l.room_count ? `${l.room_count} oda` : ''), m2(l.net_area_m2) || m2(l.gross_area_m2) || m2(l.parcel_area_m2)].filter(Boolean)
  return parts.length ? `${parts.join(' · ')} · İlan #${l.id}` : `İlan #${l.id}`
}
