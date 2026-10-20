export interface Listing {
  id: number; property_id: number; created_by: number; source_type: 'manual' | 'import' | 'authorized_source';
  source_name: string | null; source_listing_id: string | null; source_url: string | null; title?: string | null;
  transaction_type?: 'sale' | 'rent'; asking_price: string | number; currency: string; status: 'active' | 'passive' | 'sold' | 'withdrawn';
  published_at: string | null; last_seen_at: string | null; notes: string | null;
  created_at: string; updated_at: string; archived_at: string | null;
  province_name?: string | null; district_name?: string | null; neighborhood_name?: string | null; location_label?: string | null;
  property_type_code?: string | null; property_type_name?: string | null; room_count?: number | null; living_room_count?: number | null; room_label?: string | null;
  net_area_m2?: string | number | null; gross_area_m2?: string | number | null; parcel_area_m2?: string | number | null;
  building_age?: number | null; floor_number?: number | null; total_floors?: number | null;
}
export interface PriceBucket { lower_bound: string | number; upper_bound: string | number | null; count: number }
export interface AreaPriceMetric { area_type: 'net' | 'gross' | 'parcel'; listing_count: number; average_price_per_m2: string | number | null; median_price_per_m2: string | number | null }
export interface PriceSummary {
  filters: Record<string, unknown>; currency: string; listing_count: number;
  average_asking_price: string | number | null; median_asking_price: string | number | null;
  minimum_asking_price: string | number | null; maximum_asking_price: string | number | null;
  area_price_metrics: AreaPriceMetric[]; price_distribution: PriceBucket[];
  observed_price_change: { listings_with_multiple_snapshots: number; average_observed_change: string | number | null; average_observed_change_percent: string | number | null; earliest_snapshot_at: string | null; latest_snapshot_at: string | null; interpretation: string };
  last_data_updated_at: string | null; minimum_listings_threshold: number; reliability: 'limited' | 'threshold_met'; reliability_note: string; price_basis: string;
}
export interface ComparisonRow { group_key: string; group_label: string; listing_count: number; average_asking_price: string | number | null; median_asking_price: string | number | null; minimum_asking_price: string | number | null; maximum_asking_price: string | number | null; average_price_per_m2: string | number | null; median_price_per_m2: string | number | null; area_type: 'net' | 'gross' | 'parcel' | null }
export interface PriceComparison { group_by: string; currency: string; area_type_requested: string; groups: ComparisonRow[]; minimum_listings_threshold: number; reliability_note: string; price_basis: string }
export interface Location { id: number; parent_id: number | null; level: 'province' | 'district' | 'neighborhood'; name: string; normalized_name: string; external_code: string | null; created_at: string }
export interface User { id: number; username: string; email: string; full_name: string; role: 'admin' | 'agent'; is_active: boolean; created_at: string }
export interface PriceHistory { id: number; listing_id: number; asking_price: string | number; currency: string; recorded_at: string; change_reason: string; recorded_by: number | null }
