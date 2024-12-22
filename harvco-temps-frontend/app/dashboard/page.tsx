"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useToast } from "@/hooks/use-toast"
import { useAuth } from "@/contexts/auth-context"
import { Device } from "@/types/device"
import { DeviceReadings } from "./device-readings"
import { AddDeviceDialog } from "./add-device-dialog"
import { EditDeviceDialog } from "@/components/edit-device-dialog"
import { getApiUrl } from "@/utils/api"
import { Pencil } from 'lucide-react'

export default function DashboardPage() {
  const { token, logout } = useAuth()
  const router = useRouter()
  const { toast } = useToast()
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null)
  const [isAddDeviceOpen, setIsAddDeviceOpen] = useState(false)
  const [editingDevice, setEditingDevice] = useState<Device | null>(null)

  useEffect(() => {
    if (!token) {
      router.push("/login")
      return
    }

    fetchDevices()
  }, [token, router])

  const fetchDevices = async () => {
    try {
      const res = await fetch(getApiUrl("/api/v1/devices"), {
        headers: {
          Authorization: token!,
        },
      })
      if (!res.ok) throw new Error("Failed to fetch devices")
      const data = await res.json()
      setDevices(data)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch devices",
        variant: "destructive",
      })
    }
  }

  const updateDeviceName = async (name: string) => {
    if (!editingDevice) return

    try {
      const res = await fetch(getApiUrl(`/api/v1/devices/${editingDevice.id}`), {
        method: "PUT",
        headers: {
          Authorization: token!,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      })
      if (!res.ok) throw new Error("Failed to update device name")
      await fetchDevices()
      toast({
        title: "Success",
        description: "Device name updated",
      })
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update device name",
        variant: "destructive",
      })
      throw error
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Image
              src="/logo.png"
              alt="Harvco Logo"
              width={40}
              height={40}
              className="dark:invert"
            />
            <h1 className="text-2xl font-bold">Dashboard</h1>
          </div>
          <div className="space-x-2">
            <Button variant="outline" onClick={() => setIsAddDeviceOpen(true)}>
              Add Device
            </Button>
            <Button variant="ghost" onClick={logout}>
              Sign Out
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Devices</CardTitle>
                <CardDescription>Select a device to view readings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {devices.map((device) => (
                  <div
                    key={device.id}
                    className={`p-3 rounded-lg cursor-pointer hover:bg-gray-100 ${
                      selectedDevice?.id === device.id ? "bg-gray-100" : ""
                    }`}
                    onClick={() => setSelectedDevice(device)}
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <p className="font-medium">{device.name || device.device_id}</p>
                        <p className="text-sm text-gray-500">{device.device_id}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingDevice(device)
                        }}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="md:col-span-3">
            {selectedDevice ? (
              <DeviceReadings device={selectedDevice} token={token!} />
            ) : (
              <Card>
                <CardContent className="p-8 text-center text-gray-500">
                  Select a device to view readings
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      <AddDeviceDialog
        open={isAddDeviceOpen}
        onOpenChange={setIsAddDeviceOpen}
        token={token!}
        onSuccess={() => {
          fetchDevices()
          setIsAddDeviceOpen(false)
        }}
      />

      <EditDeviceDialog
        open={!!editingDevice}
        onOpenChange={(open) => !open && setEditingDevice(null)}
        deviceName={editingDevice?.name || ""}
        onSave={updateDeviceName}
      />
    </div>
  )
}
