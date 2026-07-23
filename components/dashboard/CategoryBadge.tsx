'use client'

const categoryColors = {
  Alimentos: { bg: 'bg-orange-100 dark:bg-orange-950', text: 'text-orange-800 dark:text-orange-200' },
  Bebidas: { bg: 'bg-blue-100 dark:bg-blue-950', text: 'text-blue-800 dark:text-blue-200' },
  Limpieza: { bg: 'bg-purple-100 dark:bg-purple-950', text: 'text-purple-800 dark:text-purple-200' },
  Higiene: { bg: 'bg-pink-100 dark:bg-pink-950', text: 'text-pink-800 dark:text-pink-200' },
  Otros: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-800 dark:text-gray-200' },
}

interface CategoryBadgeProps {
  category: string
}

export function CategoryBadge({ category }: CategoryBadgeProps) {
  const colors = categoryColors[category as keyof typeof categoryColors] || categoryColors.Otros

  return (
    <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${colors.bg} ${colors.text}`}>
      {category}
    </span>
  )
}
