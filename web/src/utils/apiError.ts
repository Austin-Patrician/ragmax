export function formatApiError(detail: unknown): string {
  if (detail instanceof Error) {
    return detail.message
  }

  if (typeof detail === 'string') {
    return detail
  }

  if (detail && typeof detail === 'object') {
    const record = detail as { detail?: unknown; message?: unknown }
    if (typeof record.detail === 'string') {
      return record.detail
    }
    if (Array.isArray(record.detail)) {
      return record.detail
        .map((item) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: unknown }).msg)
          }
          return String(item)
        })
        .join('; ')
    }
    if (typeof record.message === 'string') {
      return record.message
    }
  }

  return 'Request failed.'
}
