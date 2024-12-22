export interface Device {
  device_id: string
  name: string | null
  is_active: boolean
  id: number
  owner_id: number | null
}

export interface DeviceCreate {
  device_id: string
  name?: string | null
  is_active?: boolean
}

export interface DeviceUpdate {
  name?: string | null
  is_active?: boolean
}

export interface Reading {
  reading_type: "temperature" | "humidity"
  value: number
  timestamp: string
  id: number
  device_id: number
}

export interface ReadingStatistics {
  min: number
  max: number
  avg: number
  count: number
}

