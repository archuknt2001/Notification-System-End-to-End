/** Loading skeleton card. */
import React from 'react'

export default function SkeletonCard() {
  return (
    <div className="flex gap-3 px-4 py-3 border-b border-gray-100 animate-pulse">
      <div className="w-9 h-9 rounded-full bg-gray-200 flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-3 bg-gray-200 rounded w-3/4" />
        <div className="h-2.5 bg-gray-200 rounded w-full" />
        <div className="h-2.5 bg-gray-200 rounded w-1/2" />
      </div>
    </div>
  )
}
