import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BellRing, Check, CheckCheck, Trash2, TrendingDown, TrendingUp } from 'lucide-react'
import { notificationsApi } from '@/lib/api'

export default function NotificationsPage() {
  const queryClient = useQueryClient()

  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notificationsWithTours'],
    queryFn: () => notificationsApi.listWithTours(),
  })

  const markAsReadMutation = useMutation({
    mutationFn: (id: number) => notificationsApi.markAsRead(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['notificationsWithTours'] }),
  })

  const markAllAsReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllAsRead(),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['notificationsWithTours'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => notificationsApi.delete(id),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['notificationsWithTours'] }),
  })

  const unreadCount = notifications?.data?.filter((n: any) => !n.is_read).length || 0

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifiche</h1>
          <p className="mt-1 text-gray-500">
            {unreadCount > 0
              ? `Hai ${unreadCount} notifiche non lette`
              : 'Tutte le notifiche sono state lette'}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllAsReadMutation.mutate()}
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-primary-600 bg-primary-50 rounded-lg hover:bg-primary-100"
          >
            <CheckCheck className="w-4 h-4 mr-2" />
            Segna tutte come lette
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : !notifications?.data || notifications.data.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
          <BellRing className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">Nessuna notifica</p>
        </div>
      ) : (
        <div className="space-y-4">
          {notifications.data.map((notification: any) => (
            <div
              key={notification.id}
              className={`bg-white rounded-xl shadow-sm border ${
                notification.is_read ? 'border-gray-200' : 'border-primary-200 bg-primary-50/30'
              } p-4`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div
                    className={`p-2 rounded-lg ${
                      parseFloat(notification.price_change) < 0
                        ? 'bg-green-100 text-green-600'
                        : 'bg-red-100 text-red-600'
                    }`}
                  >
                    {parseFloat(notification.price_change) < 0 ? (
                      <TrendingDown className="w-5 h-5" />
                    ) : (
                      <TrendingUp className="w-5 h-5" />
                    )}
                  </div>
                  <div>
                    <Link
                      to={`/tours/${notification.tour_id}`}
                      className="text-sm font-semibold text-gray-900 hover:text-primary-600"
                    >
                      {notification.tour_name}
                    </Link>
                    {notification.tour_destination && (
                      <span className="ml-2 text-sm text-gray-500">
                        ({notification.tour_destination})
                      </span>
                    )}
                    <p className="text-sm text-gray-600 mt-1">
                      {notification.message || (
                        <>
                          Il prezzo è cambiato da €{parseFloat(notification.old_price).toFixed(2)} a €
                          {parseFloat(notification.new_price).toFixed(2)}
                        </>
                      )}
                    </p>
                    <div className="flex items-center gap-4 mt-2">
                      <span
                        className={`text-sm font-medium ${
                          parseFloat(notification.price_change) < 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {parseFloat(notification.price_change) > 0 ? '+' : ''}€
                        {parseFloat(notification.price_change).toFixed(2)} (
                        {parseFloat(notification.price_change_percent) > 0 ? '+' : ''}
                        {parseFloat(notification.price_change_percent).toFixed(1)}%)
                      </span>
                      <span className="text-xs text-gray-400">
                        {formatDate(notification.sent_at)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {!notification.is_read && (
                    <button
                      onClick={() => markAsReadMutation.mutate(notification.id)}
                      className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg"
                      title="Segna come letta"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  )}
                  <button
                    onClick={() => deleteMutation.mutate(notification.id)}
                    className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                    title="Elimina"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
