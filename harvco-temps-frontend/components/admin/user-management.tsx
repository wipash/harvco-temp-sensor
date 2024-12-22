"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/contexts/auth-context"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { useToast } from "@/hooks/use-toast"
import { getApiUrl } from "@/utils/api"

interface User {
  id: number
  email: string
  is_active: boolean
  is_superuser: boolean
}

interface UserFormData {
  email: string
  password: string
  is_active: boolean
  is_superuser: boolean
}

export function UserManagement() {
  const { fetchWithToken } = useAuth()
  const { toast } = useToast()
  const [users, setUsers] = useState<User[]>([])
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [formData, setFormData] = useState<UserFormData>({
    email: "",
    password: "",
    is_active: true,
    is_superuser: false,
  })

  const fetchUsers = async () => {
    try {
      const response = await fetchWithToken(getApiUrl("/api/v1/users"))
      if (!response.ok) throw new Error("Failed to fetch users")
      const data = await response.json()
      setUsers(data)
    } catch {
      toast({
        title: "Error",
        description: "Failed to fetch users",
        variant: "destructive",
      })
    }
  }

  const createUser = async () => {
    try {
      const response = await fetchWithToken(getApiUrl("/api/v1/users"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) throw new Error("Failed to create user")

      toast({
        title: "Success",
        description: "User created successfully",
      })

      setIsCreateDialogOpen(false)
      setFormData({
        email: "",
        password: "",
        is_active: true,
        is_superuser: false,
      })
      fetchUsers()
    } catch {
      toast({
        title: "Error",
        description: "Failed to create user",
        variant: "destructive",
      })
    }
  }

  const deactivateUser = async (userId: number) => {
    try {
      const response = await fetchWithToken(
        getApiUrl(`/api/v1/users/${userId}`),
        {
          method: "DELETE",
        }
      )

      if (!response.ok) throw new Error("Failed to deactivate user")

      toast({
        title: "Success",
        description: "User deactivated successfully",
      })

      fetchUsers()
    } catch {
      toast({
        title: "Error",
        description: "Failed to deactivate user",
        variant: "destructive",
      })
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">User Management</h2>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create User</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New User</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                />
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_active: checked as boolean })
                  }
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is_superuser"
                  checked={formData.is_superuser}
                  onCheckedChange={(checked) =>
                    setFormData({ ...formData, is_superuser: checked as boolean })
                  }
                />
                <Label htmlFor="is_superuser">Superuser</Label>
              </div>
              <Button onClick={createUser}>Create</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="border rounded-lg">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="px-4 py-2 text-left">Email</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Role</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b">
                <td className="px-4 py-2">{user.email}</td>
                <td className="px-4 py-2">
                  {user.is_active ? "Active" : "Inactive"}
                </td>
                <td className="px-4 py-2">
                  {user.is_superuser ? "Superuser" : "User"}
                </td>
                <td className="px-4 py-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deactivateUser(user.id)}
                  >
                    Deactivate
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
