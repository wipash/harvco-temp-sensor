"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DatePickerWithRange } from "@/components/ui/date-picker-with-range"
import { Device, Reading, ReadingStatistics } from "@/types/device"

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
  token: string
}

type ReadingType = "temperature" | "humidity"

const getEndOfDay = (date: Date) => {
  const endOfDay = new Date(date)
  endOfDay.setHours(23, 59, 59, 999)
  return endOfDay
}

export function DeviceReadings({ device, token }: DeviceReadingsProps) {
  const [date, setDate] = useState<DateRange | undefined>({
    from: addDays(new Date(), -7),
    to: new Date(),
  })
  const [readings, setReadings] = useState<Reading[]>([])
  const [stats, setStats] = useState<{ [key in ReadingType]?: ReadingStatistics }>({})
  const [latestReadings, setLatestReadings] = useState<{ [key in ReadingType]?: LatestReading }>({})
  const { toast } = useToast()

  const fetchReadings = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        device_id: device.id.toString(),
        start_date: date?.from?.toISOString() || "",
        end_date: date?.to ? getEndOfDay(date.to).toISOString() : "",
      })

      const res = await fetch(getApiUrl(`/api/v1/readings?${params}`), {
        headers: {
          Authorization: token,
        },
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(JSON.stringify(errorData))
      }

      const data = await res.json()
      setReadings(data)
    } catch (error) {
      console.error("Error fetching readings:", error)
      toast({
        title: "Error fetching readings",
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      })
    }
  }, [device.id, date, token, toast])

  const fetchStatistics = useCallback(async (readingType: ReadingType) => {
    try {
      const params = new URLSearchParams({
        device_id: device.id.toString(),
        reading_type: readingType,
        start_date: date?.from?.toISOString() || "",
        end_date: date?.to ? getEndOfDay(date.to).toISOString() : "",
      })

      const res = await fetch(getApiUrl(`/api/v1/readings/statistics?${params}`), {
        headers: {
          Authorization: token,
        },
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
      console.error(`Error fetching ${readingType} statistics:`, error)
      toast({
        title: `Error fetching ${readingType} statistics`,
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      })
    }
  }, [device.id, date, token, toast])

  const formatReadings = (type: ReadingType) => {
    return readings
      .filter((reading) => reading.reading_type === type)
      .map((reading) => {
        try {
          // Log the incoming timestamp for debugging
          console.log('Raw timestamp:', reading.timestamp)
          
          // Parse the timestamp, ensuring UTC
          const timestamp = reading.timestamp.endsWith('Z') 
            ? reading.timestamp 
            : reading.timestamp + 'Z'
          
          // Create the date object
          const date = new Date(timestamp)
          
          // Validate the date
          if (isNaN(date.getTime())) {
            console.error('Invalid date created from timestamp:', timestamp)
            return null
          }

          return {
            timestamp: date.toISOString(),
            value: reading.value,
          }
        } catch (e) {
          console.error('Error processing reading:', reading, e)
          return null
        }
      })
      .filter((reading): reading is NonNullable<typeof reading> => reading !== null)
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  }

  const fetchLatestReadings = useCallback(async (readingType: ReadingType) => {
    try {
      const params = new URLSearchParams({
        device_id: device.id.toString(),
        reading_type: readingType,
      })

      const res = await fetch(getApiUrl(`/api/v1/readings/latest?${params}`), {
        headers: {
          Authorization: token,
        },
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
      console.error(`Error fetching latest ${readingType} reading:`, error)
      toast({
        title: `Error fetching latest ${readingType} reading`,
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      })
    }
  }, [device.id, token, toast])

  const getCurrentReading = (type: ReadingType) => {
    return latestReadings[type]?.value
  }

  useEffect(() => {
    if (date?.from && date?.to) {
      fetchReadings()
      fetchStatistics("temperature")
      fetchStatistics("humidity")
      fetchLatestReadings("temperature")
      fetchLatestReadings("humidity")
    }
  }, [date, fetchReadings, fetchStatistics, fetchLatestReadings])


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
              {format(new Date(label), "MMM d, yyyy HH:mm:ss")}
            </span>
          </div>
        </div>
      </div>
    )
  }

  const readingTypes: ReadingType[] = ["temperature", "humidity"]

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Readings for {device.name || device.device_id}</CardTitle>
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
                      <div className="text-2xl font-bold">
                        {getCurrentReading(type)?.toFixed(1) || "--"}
                        {type === "temperature" ? "°C" : "%"}
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
                          if (!value) return ''
                          try {
                            return format(new Date(value), "HH:mm")
                          } catch (e) {
                            console.error('Error formatting tick:', value, e)
                            return ''
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
                            return format(new Date(label), "MMM d, yyyy HH:mm:ss")
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
