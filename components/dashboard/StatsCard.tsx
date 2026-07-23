'use client'

import { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: number | string
  icon: LucideIcon
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
  description?: string
}

const colorClasses = {
  blue: 'bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400',
  green: 'bg-green-50 dark:bg-green-950/30 text-green-600 dark:text-green-400',
  yellow: 'bg-yellow-50 dark:bg-yellow-950/30 text-yellow-600 dark:text-yellow-400',
  red: 'bg-red-50 dark:bg-red-950/30 text-red-600 dark:text-red-400',
  purple: 'bg-purple-50 dark:bg-purple-950/30 text-purple-600 dark:text-purple-400',
}

export function StatsCard({
  title,
  value,
  icon: Icon,
  color = 'blue',
  description,
}: StatsCardProps) {
  return (
    <div className="card">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-sm text-muted-foreground mb-1">{title}</p>
          <p className="text-2xl lg:text-3xl font-bold text-foreground">{value}</p>
          {description && (
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}
