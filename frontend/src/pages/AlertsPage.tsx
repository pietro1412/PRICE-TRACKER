import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bell, Trash2, Pause, Play, TrendingDown, TrendingUp } from 'lucide-react'
import { alertsApi } from '@/lib/api'

export default function AlertsPage() {
  const queryClient = useQueryClient()

  const { data: alerts, isLoading } = useQuery({
    queryKey: ['alertsWithTours'],
    queryFn: () => alertsApi.listWithTours(),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => alertsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alertsWithTours'] }),
  })

  const pauseMutation = useMutation({
    mutationFn: (id: number) => alertsApi.pause(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alertsWithTours'] }),
  })

  const resumeMutation = useMutation({
    mutationFn: (id: number) => alertsApi.resume(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alertsWithTours'] }),
  })

  const getAlertTypeLabel = (type: string) => {
    switch (type) {
      case 'price_drop':
        return 'Prezzo sotto soglia'
      case 'price_increase':
        return 'Prezzo sopra soglia'
      case 'percentage_drop':
        return 'Calo percentuale'
      case 'price_change':
        return 'Qualsiasi variazione'
      default:
        return type
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-700'
      case 'paused':
        return 'bg-yellow-100 text-yellow-700'
      case 'triggered':
        return 'bg-blue-100 text-blue-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">I Tuoi Alert</h1>
        <p className="mt-1 text-gray-500">Gestisci i tuoi alert sui prezzi dei tour</p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : !alerts?.data || alerts.data.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <Bell className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500 mb-4">Non hai ancora creato nessun alert</p>
          <Link
            to="/tours"
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700"
          >
            Esplora i tour
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tour
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tipo Alert
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Soglia
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Prezzo Attuale
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stato
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Attivazioni
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Azioni
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {alerts.data.map((alert: any) => (
                <tr key={alert.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <Link
                      to={`/tours/${alert.tour_id}`}
                      className="text-sm font-medium text-gray-900 hover:text-primary-600"
                    >
                      {alert.tour_name}
                    </Link>
                    {alert.tour_destination && (
                      <p className="text-sm text-gray-500">{alert.tour_destination}</p>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="flex items-center text-sm text-gray-900">
                      {alert.alert_type === 'price_drop' && (
                        <TrendingDown className="w-4 h-4 text-green-500 mr-1" />
                      )}
                      {alert.alert_type === 'price_increase' && (
                        <TrendingUp className="w-4 h-4 text-red-500 mr-1" />
                      )}
                      {getAlertTypeLabel(alert.alert_type)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {alert.threshold_price
                      ? `€${parseFloat(alert.threshold_price).toFixed(2)}`
                      : alert.threshold_percentage
                      ? `${alert.threshold_percentage}%`
                      : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    €{alert.tour_current_price ? parseFloat(alert.tour_current_price).toFixed(2) : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                        alert.status
                      )}`}
                    >
                      {alert.status === 'active' ? 'Attivo' : alert.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {alert.trigger_count}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <div className="flex items-center justify-end gap-2">
                      {alert.status === 'active' ? (
                        <button
                          onClick={() => pauseMutation.mutate(alert.id)}
                          className="p-2 text-gray-400 hover:text-yellow-600 hover:bg-yellow-50 rounded-lg"
                          title="Metti in pausa"
                        >
                          <Pause className="w-4 h-4" />
                        </button>
                      ) : alert.status === 'paused' ? (
                        <button
                          onClick={() => resumeMutation.mutate(alert.id)}
                          className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg"
                          title="Riattiva"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                      ) : null}
                      <button
                        onClick={() => deleteMutation.mutate(alert.id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                        title="Elimina"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
