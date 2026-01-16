import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  ArrowLeft,
  Star,
  TrendingDown,
  TrendingUp,
  Bell,
  ExternalLink,
} from 'lucide-react'
import { toursApi, alertsApi } from '@/lib/api'

export default function TourDetailPage() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [showAlertModal, setShowAlertModal] = useState(false)
  const [alertType, setAlertType] = useState('price_drop')
  const [thresholdPrice, setThresholdPrice] = useState('')
  const [thresholdPercentage, setThresholdPercentage] = useState('')

  const { data: tour, isLoading } = useQuery({
    queryKey: ['tour', id],
    queryFn: () => toursApi.get(Number(id)),
  })

  const { data: priceHistory } = useQuery({
    queryKey: ['priceHistory', id],
    queryFn: () => toursApi.getPriceHistory(Number(id), 30),
  })

  const { data: priceStats } = useQuery({
    queryKey: ['priceStats', id],
    queryFn: () => toursApi.getPriceStats(Number(id)),
  })

  const createAlertMutation = useMutation({
    mutationFn: (data: any) => alertsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      setShowAlertModal(false)
      setThresholdPrice('')
      setThresholdPercentage('')
    },
  })

  const handleCreateAlert = () => {
    createAlertMutation.mutate({
      tour_id: Number(id),
      alert_type: alertType,
      threshold_price: alertType !== 'percentage_drop' ? Number(thresholdPrice) : undefined,
      threshold_percentage: alertType === 'percentage_drop' ? Number(thresholdPercentage) : undefined,
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  const tourData = tour?.data
  const stats = priceStats?.data
  const chartData = priceHistory?.data?.items
    ?.slice()
    .reverse()
    .map((item: any) => ({
      date: new Date(item.recorded_at).toLocaleDateString('it-IT', {
        day: '2-digit',
        month: '2-digit',
      }),
      price: item.price,
    }))

  return (
    <div className="space-y-6">
      <Link
        to="/tours"
        className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4 mr-1" />
        Torna ai tour
      </Link>

      {/* Tour Info */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <span className="px-2 py-1 text-xs font-medium bg-primary-100 text-primary-700 rounded">
                {tourData?.destination}
              </span>
              {tourData?.rating && (
                <span className="flex items-center text-sm text-gray-600">
                  <Star className="w-4 h-4 text-yellow-400 fill-yellow-400 mr-1" />
                  {tourData.rating.toFixed(1)}
                </span>
              )}
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{tourData?.name}</h1>
            {tourData?.category && (
              <p className="text-gray-500">{tourData.category}</p>
            )}
          </div>

          <div className="text-right">
            <p className="text-3xl font-bold text-primary-600">
              {tourData?.currency} {tourData?.current_price?.toFixed(2)}
            </p>
            <div className="flex items-center justify-end gap-4 mt-2">
              <button
                onClick={() => setShowAlertModal(true)}
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700"
              >
                <Bell className="w-4 h-4 mr-2" />
                Crea Alert
              </button>
              {tourData?.url && (
                <a
                  href={tourData.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Vedi su Civitatis
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Price Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Prezzo Minimo</p>
          <p className="text-xl font-bold text-green-600">
            {stats?.min_price ? `€${stats.min_price.toFixed(2)}` : '-'}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Prezzo Massimo</p>
          <p className="text-xl font-bold text-red-600">
            {stats?.max_price ? `€${stats.max_price.toFixed(2)}` : '-'}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Prezzo Medio</p>
          <p className="text-xl font-bold text-gray-900">
            {stats?.avg_price ? `€${stats.avg_price.toFixed(2)}` : '-'}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <p className="text-sm text-gray-500">Var. 7 giorni</p>
          <p
            className={`text-xl font-bold flex items-center ${
              stats?.price_change_7d > 0
                ? 'text-red-600'
                : stats?.price_change_7d < 0
                ? 'text-green-600'
                : 'text-gray-900'
            }`}
          >
            {stats?.price_change_7d > 0 && <TrendingUp className="w-5 h-5 mr-1" />}
            {stats?.price_change_7d < 0 && <TrendingDown className="w-5 h-5 mr-1" />}
            {stats?.price_change_7d ? `€${stats.price_change_7d.toFixed(2)}` : '-'}
          </p>
        </div>
      </div>

      {/* Price Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Storico Prezzi (ultimi 30 giorni)
        </h2>
        {chartData && chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis domain={['auto', 'auto']} />
              <Tooltip
                formatter={(value: number) => [`€${value.toFixed(2)}`, 'Prezzo']}
              />
              <Line
                type="monotone"
                dataKey="price"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex items-center justify-center h-64 text-gray-500">
            Nessun dato storico disponibile
          </div>
        )}
      </div>

      {/* Alert Modal */}
      {showAlertModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Crea Alert</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo di Alert
                </label>
                <select
                  value={alertType}
                  onChange={(e) => setAlertType(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="price_drop">Prezzo scende sotto</option>
                  <option value="price_increase">Prezzo sale sopra</option>
                  <option value="percentage_drop">Calo percentuale</option>
                  <option value="price_change">Qualsiasi variazione</option>
                </select>
              </div>

              {alertType !== 'percentage_drop' && alertType !== 'price_change' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Soglia Prezzo (EUR)
                  </label>
                  <input
                    type="number"
                    value={thresholdPrice}
                    onChange={(e) => setThresholdPrice(e.target.value)}
                    placeholder={`Es: ${(tourData?.current_price * 0.9).toFixed(2)}`}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              )}

              {alertType === 'percentage_drop' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Percentuale di calo (%)
                  </label>
                  <input
                    type="number"
                    value={thresholdPercentage}
                    onChange={(e) => setThresholdPercentage(e.target.value)}
                    placeholder="Es: 10"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowAlertModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Annulla
              </button>
              <button
                onClick={handleCreateAlert}
                disabled={createAlertMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {createAlertMutation.isPending ? 'Creazione...' : 'Crea Alert'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
