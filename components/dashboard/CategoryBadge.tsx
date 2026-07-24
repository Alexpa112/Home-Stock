'use client'

const categoryColors = {
  Alimentos: { bg: 'bg-orange-100 dark:bg-orange-950/50', text: 'text-orange-900 dark:text-orange-200', border: 'border-orange-200 dark:border-orange-900' },
  Bebidas: { bg: 'bg-blue-100 dark:bg-blue-950/50', text: 'text-blue-900 dark:text-blue-200', border: 'border-blue-200 dark:border-blue-900' },
  Limpieza: { bg: 'bg-purple-100 dark:bg-purple-950/50', text: 'text-purple-900 dark:text-purple-200', border: 'border-purple-200 dark:border-purple-900' },
  Higiene: { bg: 'bg-pink-100 dark:bg-pink-950/50', text: 'text-pink-900 dark:text-pink-200', border: 'border-pink-200 dark:border-pink-900' },
  Otros: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-900 dark:text-gray-200', border: 'border-gray-200 dark:border-gray-700' },
}

interface CategoryBadgeProps {
  category: string
}

export function CategoryBadge({ category }: CategoryBadgeProps) {
  const colors = categoryColors[category as keyof typeof categoryColors] || categoryColors.Otros

  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${colors.bg} ${colors.text} ${colors.border}`}>
      {category}
    </span>
  )
}
