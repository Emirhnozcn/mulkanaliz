import type { Listing, Location, PriceComparison, PriceHistory, PriceSummary, User } from '~/types/api'

export function useApi() {
  const config = useRuntimeConfig()
  const base = String(config.public.apiBase).replace(/\/$/, '')

  async function request<T>(path: string, options: Parameters<typeof $fetch<T>>[1] = {}): Promise<T> {
    return await $fetch<T>(`${base}${path}`, {
      ...options,
      headers: { Accept: 'application/json', ...(import.meta.client && sessionStorage.getItem('rea_access_token') ? { Authorization: `Bearer ${sessionStorage.getItem('rea_access_token')}` } : {}), ...(options.headers as Record<string, string> | undefined) },
      onResponseError({ response }) {
        const data = response._data as { detail?: string; error?: { message?: string } } | undefined
        const message = data?.error?.message || data?.detail || `İstek başarısız oldu (HTTP ${response.status}).`
        throw new Error(message)
      }
    })
  }
  return {
    request,
    listings: (params: Record<string, string | number | boolean | undefined> = {}) => request<Listing[]>('/listings', { query: params }),
    listing: (id: string | number) => request<Listing>(`/listings/${id}`),
    createListing: (body: Record<string, unknown>) => request<Listing>('/listings', { method: 'POST', body }),
    updateListing: (id: string | number, body: Record<string, unknown>) => request<Listing>(`/listings/${id}`, { method: 'PATCH', body }),
    archiveListing: (id: string | number) => request<void>(`/listings/${id}`, { method: 'DELETE' }),
    permanentlyDeleteListing: (id: string | number) => request<void>(`/listings/${id}/permanent`, { method: 'DELETE' }),
    priceHistory: (id: string | number) => request<PriceHistory[]>(`/listings/${id}/price-history`),
    priceSummary: (params: Record<string, string | number | undefined> = {}) => request<PriceSummary>('/analytics/price-summary', { query: params }),
    compare: (params: Record<string, string | number | undefined>) => request<PriceComparison>('/analytics/compare', { query: params }),
    locations: (params: Record<string, string | number | undefined> = {}) => request<Location[]>('/locations', { query: params }),
    users: (params: Record<string, string | number | undefined> = {}) => request<User[]>('/users', { query: params }),
    deleteUser: (id: number) => request<void>(`/users/${id}`, { method: 'DELETE' }),
    valuation: (params: Record<string, string | number | undefined>) => request<Record<string, any>>('/analytics/valuation', { query: params }),
  }
}
