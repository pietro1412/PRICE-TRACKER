import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Map, Bell, TrendingDown, TrendingUp } from 'lucide-react'
import { toursApi, alertsApi, notificationsApi } from '@/lib/api'

export default function DashboardPage() {
  const { data: toursData } = useQuery({
    queryKey: ['tours', { page: 1, page_size: 5 }],
    queryFn: () => toursApi.list({ page: 1, page_size: 5 }),
  })

  const { data: alertsData } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertsApi.listWithTours(),
  })

  const { data: notificationsData } = useQuery({
    queryKey: ['notifications', { unread_only: true }],
    queryFn: () => notificationsApi.list({ unread_only: true }),
  })

  const stats = [
    {
      name: 'Tour Monitorati',
      value: toursData?.data?.total || 0,
      icon: Map,
      color: 'bg-blue-500',
    },
    {
      name: 'Alert Attivi',
      value: alertsData?.data?.filter((a: any) => a.status === 'active').length || 0,
      icon: Bell,
      color: 'bg-green-500',
    },
    {
      name: 'Notifiche Non Lette',
      value: notificationsData?.data?.unread_count || 0,
      icon: TrendingDown,
      color: 'bg-orange-500',
    },
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-gray-500">Panoramica del tuo price tracker</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center">
              <div className={`${stat.color} p-3 rounded-lg`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recent Tours */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Tour Recenti</h2>
              <Link
                to="/tours"
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                Vedi tutti
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-200">
            {toursData?.data?.items?.slice(0, 5).map((tour: any) => (
              <Link
                key={tour.id}
                to={`/tours/${tour.id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {tour.name}
                  </p>
                  <p className="text-sm text-gray-500">{tour.destination}</p>
                </div>
                <div className="ml-4 text-right">
                  <p className="text-sm font-semibold text-gray-900">
                    {tour.currency} {parseFloat(tour.current_price).toFixed(2)}
                  </p>
                </div>
              </Link>
            ))}
            {(!toursData?.data?.items || toursData.data.items.length === 0) && (
              <div className="px-6 py-8 text-center text-gray-500">
                Nessun tour disponibile
              </div>
            )}
          </div>
        </div>

        {/* Active Alerts */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Alert Attivi</h2>
              <Link
                to="/alerts"
                className="text-sm text-primary-600 hover:text-primary-700"
              >
                Gestisci
              </Link>
            </div>
          </div>
          <div className="divide-y divide-gray-200">
            {alertsData?.data?.slice(0, 5).map((alert: any) => (
              <div key={alert.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {alert.tour_name}
                    </p>
                    <p className="text-sm text-gray-500">
                      {alert.alert_type === 'price_drop' && (
                        <span className="flex items-center">
                          <TrendingDown className="w-4 h-4 mr-1 text-green-500" />
                          Sotto €{parseFloat(alert.threshold_price).toFixed(2)}
                        </span>
                      )}
                      {alert.alert_type === 'price_increase' && (
                        <span className="flex items-center">
                          <TrendingUp className="w-4 h-4 mr-1 text-red-500" />
                          Sopra €{parseFloat(alert.threshold_price).toFixed(2)}
                        </span>
                      )}
                      {alert.alert_type === 'percentage_drop' && (
                        <span className="flex items-center">
                          <TrendingDown className="w-4 h-4 mr-1 text-green-500" />
                          Calo del {parseFloat(alert.threshold_percentage).toFixed(0)}%
                        </span>
                      )}
                    </p>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${
                      alert.status === 'active'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {alert.status === 'active' ? 'Attivo' : alert.status}
                  </span>
                </div>
              </div>
            ))}
            {(!alertsData?.data || alertsData.data.length === 0) && (
              <div className="px-6 py-8 text-center text-gray-500">
                Nessun alert configurato
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
