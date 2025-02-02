"use client"

import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/contexts/auth-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DatePickerWithRange } from "@/components/ui/date-picker-with-range"
import { Device, Reading, ReadingStatistics } from "@/types/device"
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"

interface LatestReading {
  value: number
  timestamp: string
}
import { Line, LineChart, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import { addDays, format } from "date-fns"
import { DateRange } from "react-day-picker"
import { getApiUrl } from "@/utils/api"
import { useToast } from "@/hooks/use-toast"

interface DeviceReadingsProps {
  device: Device
}

type ReadingType = "temperature" | "humidity"

const getEndOfDay = (date: Date) => {
  const endOfDay = new Date(date)
  endOfDay.setHours(23, 59, 59, 999)
  return endOfDay
}

export function DeviceReadings({ device }: DeviceReadingsProps) {
  const { token, fetchWithToken } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [date, setDate] = useState<DateRange | undefined>({
    from: addDays(new Date(), -1),
    to: new Date(),
  })
  const [readings, setReadings] = useState<Reading[]>([])
  const [stats, setStats] = useState<{ [key in ReadingType]?: ReadingStatistics }>({})
  const [latestReadings, setLatestReadings] = useState<{ [key in ReadingType]?: LatestReading }>({})
  const { toast } = useToast()

  const fetchReadings = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      console.log('Skipping fetchReadings - no token');
      return;
    }

    try {
      const params = new URLSearchParams({
        device_id: device.id.toString(),
        start_date: date?.from?.toISOString() || "",
        end_date: date?.to ? getEndOfDay(date.to).toISOString() : "",
      })

      console.log('Fetching readings with params:', params.toString());
      const res = await fetchWithToken(getApiUrl(`/api/v1/readings?${params}`), {
        signal,
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(JSON.stringify(errorData))
      }

      const data = await res.json()
      console.log('Received readings data:', data);
      setReadings(data)
    } catch (error) {
      // Silently ignore abort errors
      if (error instanceof DOMException && error.name === 'AbortError') return;

      // Show toast for non-abort errors
      if (!(error instanceof DOMException) || error.name !== 'AbortError') {
        console.error("Error fetching readings:", error)
        toast({
          title: "Error fetching readings",
          description: error instanceof Error ? error.message : "Unknown error occurred",
          variant: "destructive",
        })
      }
    }
  }, [device.id, date, token, toast, fetchWithToken])

  const fetchStatistics = useCallback(async (readingType: ReadingType, signal?: AbortSignal) => {
    if (!token) return

    try {
      const params = new URLSearchParams({
        device_id: device.id.toString(),
        reading_type: readingType,
        start_date: date?.from?.toISOString() || "",
        end_date: date?.to ? getEndOfDay(date.to).toISOString() : "",
      })

      const res = await fetchWithToken(getApiUrl(`/api/v1/readings/statistics?${params}`), {
        signal,
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(JSON.stringify(errorData))
      }

      const data: ReadingStatistics = await res.json()
      setStats(prev => ({
        ...prev,
        [readingType]: data
      }))
    } catch (error) {
      // Silently ignore abort errors
      if (error instanceof DOMException && error.name === 'AbortError') return;

      // Only show toast for non-abort errors
      if (!(error instanceof DOMException) || error.name !== 'AbortError') {
        console.error(`Error fetching ${readingType} statistics:`, error)
        toast({
          title: `Error fetching ${readingType} statistics`,
          description: error instanceof Error ? error.message : "Unknown error occurred",
          variant: "destructive",
        })
      }
    }
  }, [device.id, date, token, toast, fetchWithToken])

  const formatReadings = (type: ReadingType) => {
    return readings
      .filter((reading) => reading.reading_type === type)
      .map((reading) => {
        try {

          const date = new Date(reading.timestamp);

          const result = {
            timestamp: date.getTime(),
            value: reading.value,
          };
          return result;
        } catch (e) {
          console.error('Error processing reading:', reading, e);
          return null;
        }
      })
      .filter((reading): reading is NonNullable<typeof reading> => reading !== null)
      .sort((a, b) => a.timestamp - b.timestamp);
  }

  const fetchLatestReadings = useCallback(async (readingType: ReadingType, signal?: AbortSignal) => {
    if (!token) return

    try {
      const params = new URLSearchParams({
        device_id: device.id.toString(),
        reading_type: readingType,
      })

      const res = await fetchWithToken(getApiUrl(`/api/v1/readings/latest?${params}`), {
        signal,
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(JSON.stringify(errorData))
      }

      const data: LatestReading = await res.json()
      setLatestReadings(prev => ({
        ...prev,
        [readingType]: data
      }))
    } catch (error) {
      // Silently ignore abort errors
      if (error instanceof DOMException && error.name === 'AbortError') return;

      // Only show toast for non-abort errors
      if (!(error instanceof DOMException) || error.name !== 'AbortError') {
        console.error(`Error fetching latest ${readingType} reading:`, error)
        toast({
          title: `Error fetching latest ${readingType} reading`,
          description: error instanceof Error ? error.message : "Unknown error occurred",
          variant: "destructive",
        })
      }
    }
  }, [device.id, token, toast, fetchWithToken])

  const getCurrentReading = (type: ReadingType) => {
    return latestReadings[type]?.value
  }

  const refreshData = useCallback(async () => {
    if (!token) return

    // Create a local loading state instead of using the shared state
    let isRefreshing = false
    if (isRefreshing) return

    isRefreshing = true
    setIsLoading(true)
    try {
      if (date?.from && date?.to) {
        await fetchReadings()
        await Promise.all([
          fetchStatistics("temperature"),
          fetchStatistics("humidity"),
          fetchLatestReadings("temperature"),
          fetchLatestReadings("humidity")
        ])
      }
    } finally {
      isRefreshing = false
      setIsLoading(false)
    }
  }, [date, fetchReadings, fetchStatistics, fetchLatestReadings, token])

  useEffect(() => {
    if (!date?.from || !date?.to) return;

    const controller = new AbortController();
    setIsInitialLoading(true);

    const fetchData = async () => {
      await fetchReadings(controller.signal);
      await Promise.all([
        fetchStatistics("temperature", controller.signal),
        fetchStatistics("humidity", controller.signal),
        fetchLatestReadings("temperature", controller.signal),
        fetchLatestReadings("humidity", controller.signal),
      ]);
      setIsInitialLoading(false);
    };

    fetchData();

    return () => {
      controller.abort();
    };
  }, [date, fetchReadings, fetchStatistics, fetchLatestReadings]);

  useEffect(() => {
    if (!token) return

    // Initial fetch
    refreshData()

    // Set up interval
    const intervalId = setInterval(() => {
      refreshData()
    }, 60000) // 60000ms = 1 minute

    return () => clearInterval(intervalId)
  }, [token, refreshData])


  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) {
      return null
    }

    return (
      <div className="rounded-lg border bg-background p-2 shadow-sm">
        <div className="grid gap-2">
          <div className="flex flex-col">
            <span className="text-[0.70rem] uppercase text-muted-foreground">
              Value
            </span>
            <span className="font-bold tabular-nums">
              {payload[0].value?.toFixed(1)}
              {payload[0].name === "temperature" ? "°C" : "%"}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-[0.70rem] uppercase text-muted-foreground">
              Time
            </span>
            <span className="font-bold tabular-nums">
              {format(label, "MMM d, yyyy HH:mm:ss")}
            </span>
          </div>
        </div>
      </div>
    )
  }

  const readingTypes: ReadingType[] = ["temperature", "humidity"]

  return (
    <div className="space-y-4">
      {!readings.length && !isInitialLoading && (
        <div className="text-center p-4">
          {token ? 'No readings available' : 'Waiting for authentication...'}
        </div>
      )}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-2">
              <CardTitle>Readings for {device.name || device.device_id}</CardTitle>
              <Button
                variant="outline"
                size="icon"
                onClick={refreshData}
                title="Refresh data"
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <DatePickerWithRange date={date} onDateChange={setDate} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {readingTypes.map((type) => (
              <Card key={type}>
                <CardHeader>
                  <CardTitle className="capitalize">{type} Statistics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-500">Current</div>
                      <div>
                        <div className="text-2xl font-bold">
                          {getCurrentReading(type)?.toFixed(1) || "--"}
                          {type === "temperature" ? "°C" : "%"}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Last received: {latestReadings[type]?.timestamp
                            ? (() => {
                                try {
                                  const date = new Date(latestReadings[type]?.timestamp || '')
                                  return format(date, "MMM d, HH:mm:ss")
                                } catch (e) {
                                  console.error('Error formatting last received timestamp:', latestReadings[type]?.timestamp, e)
                                  return "--"
                                }
                              })()
                            : "--"}
                        </div>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Average</div>
                      <div className="text-2xl font-bold">
                        {stats[type]?.avg.toFixed(1) || "--"}
                        {type === "temperature" ? "°C" : "%"}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {readingTypes.map((type) => (
            <Card key={type}>
              <CardHeader>
                <CardTitle className="capitalize">{type} History</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={formatReadings(type)}>
                      <XAxis
                        dataKey="timestamp"
                        tick={{ fontSize: 12 }}
                        tickFormatter={(value) => {
                          if (!value) return '';
                          try {
                            const formatted = format(value, "HH:mm");
                            return formatted;
                          } catch (e) {
                            console.error('Error formatting tick:', value, e);
                            return '';
                          }
                        }}
                      />
                      <YAxis
                        tick={{ fontSize: 12 }}
                        domain={['auto', 'auto']}
                      />
                      <Tooltip
                        content={<CustomTooltip />}
                        labelFormatter={(label) => {
                          if (!label) return ''
                          try {
                            const date = new Date(label) // This will automatically convert UTC to local
                            return format(date, "MMM d, yyyy HH:mm:ss")
                          } catch (e) {
                            console.error('Error formatting label:', label, e)
                            return ''
                          }
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="value"
                        name={type}
                        stroke={`hsl(var(--primary))`}
                        dot={false}
                        strokeWidth={2}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
