import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, Filter, Star, ChevronLeft, ChevronRight } from 'lucide-react'
import { toursApi } from '@/lib/api'

export default function ToursPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [destination, setDestination] = useState('')
  const [category, setCategory] = useState('')
  const pageSize = 12

  const { data: toursData, isLoading } = useQuery({
    queryKey: ['tours', { page, search, destination, category, page_size: pageSize }],
    queryFn: () =>
      toursApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
        destination: destination || undefined,
        category: category || undefined,
      }),
  })

  const { data: destinations } = useQuery({
    queryKey: ['destinations'],
    queryFn: () => toursApi.getDestinations(),
  })

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => toursApi.getCategories(),
  })

  const tours = toursData?.data?.items || []
  const totalPages = toursData?.data?.pages || 1

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Tour</h1>
        <p className="mt-1 text-gray-500">Esplora i tour disponibili e monitora i prezzi</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Cerca tour..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          <select
            value={destination}
            onChange={(e) => {
              setDestination(e.target.value)
              setPage(1)
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">Tutte le destinazioni</option>
            {destinations?.data?.map((dest: string) => (
              <option key={dest} value={dest}>
                {dest}
              </option>
            ))}
          </select>

          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value)
              setPage(1)
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">Tutte le categorie</option>
            {categories?.data?.map((cat: string) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tours Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : tours.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <p className="text-gray-500">Nessun tour trovato</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tours.map((tour: any) => (
              <Link
                key={tour.id}
                to={`/tours/${tour.id}`}
                className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-3">
                    <span className="px-2 py-1 text-xs font-medium bg-primary-100 text-primary-700 rounded">
                      {tour.destination}
                    </span>
                    {tour.rating && (
                      <span className="flex items-center text-sm text-gray-600">
                        <Star className="w-4 h-4 text-yellow-400 fill-yellow-400 mr-1" />
                        {tour.rating.toFixed(1)}
                      </span>
                    )}
                  </div>

                  <h3 className="text-lg font-semibold text-gray-900 line-clamp-2 mb-2">
                    {tour.name}
                  </h3>

                  {tour.category && (
                    <p className="text-sm text-gray-500 mb-4">{tour.category}</p>
                  )}

                  <div className="flex items-end justify-between">
                    <div>
                      <p className="text-2xl font-bold text-primary-600">
                        {tour.currency} {tour.current_price.toFixed(2)}
                      </p>
                      {tour.min_price && tour.min_price < tour.current_price && (
                        <p className="text-sm text-gray-500">
                          Min: {tour.currency} {tour.min_price.toFixed(2)}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              <span className="px-4 py-2 text-sm text-gray-600">
                Pagina {page} di {totalPages}
              </span>

              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
