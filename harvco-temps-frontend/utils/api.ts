export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://sensorapi.harvco.nz'

export function getApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}
