"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useToast } from "@/hooks/use-toast"
import { DeviceCreate } from "@/types/device"
import { getApiUrl } from "@/utils/api"

interface AddDeviceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  token: string
  onSuccess: () => void
}

export function AddDeviceDialog({ open, onOpenChange, token, onSuccess }: AddDeviceDialogProps) {
  const [deviceId, setDeviceId] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const deviceData: DeviceCreate = {
        device_id: deviceId,
      }

      const res = await fetch(getApiUrl("/api/v1/devices"), {
        method: "POST",
        headers: {
          Authorization: token,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(deviceData),
      })

      if (!res.ok) throw new Error("Failed to add device")

      toast({
        title: "Success",
        description: "Device added successfully",
      })
      onSuccess()
      setDeviceId("")
    } catch {
      toast({
        title: "Error",
        description: "Failed to add device",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add New Device</DialogTitle>
          <DialogDescription>Enter the 6-character device ID to add it to your account.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="deviceId">Device ID</Label>
            <Input
              id="deviceId"
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              placeholder="Enter 6-character device ID"
              maxLength={6}
              pattern="[A-Za-z0-9]{6}"
              required
            />
          </div>
          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? "Adding..." : "Add Device"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
