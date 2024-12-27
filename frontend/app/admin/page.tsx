"use client"

import { AuthGuard } from "@/components/auth-guard"
import { UserManagement } from "@/components/admin/user-management"

export default function AdminPage() {
  return (
    <AuthGuard requireSuper>
      <div className="container py-8">
        <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>
        <UserManagement />
      </div>
    </AuthGuard>
  )
}
