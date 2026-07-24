'use client'

import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

const variants = {
  error: {
    wrapper: 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-200',
    icon: AlertCircle,
  },
  warning: {
    wrapper: 'bg-yellow-50 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-200',
    icon: AlertTriangle,
  },
  success: {
    wrapper: 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-200',
    icon: CheckCircle2,
  },
  info: {
    wrapper: 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-200',
    icon: Info,
  },
} as const

interface StatusMessageProps {
  variant?: keyof typeof variants
  title?: string
  message: string
  className?: string
}

export function StatusMessage({ variant = 'error', title, message, className }: StatusMessageProps) {
  const config = variants[variant]
  const Icon = config.icon

  return (
    <div className={cn('rounded-lg p-4 text-sm flex items-start gap-3', config.wrapper, className)}>
      <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div>
        {title && <p className="font-medium">{title}</p>}
        <p>{message}</p>
      </div>
    </div>
  )
}
