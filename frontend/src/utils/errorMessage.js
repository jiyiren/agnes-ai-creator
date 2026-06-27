/**
 * Normalize backend/Agnes error messages for display.
 */
export function formatErrorMessage(raw) {
  if (!raw) return ''
  if (typeof raw === 'string') {
    const text = raw.trim()
    if (!text) return ''
    if (text.startsWith('{') || text.startsWith('[')) {
      try {
        return formatErrorMessage(JSON.parse(text))
      } catch {
        return text
      }
    }
    return text
  }
  if (typeof raw === 'object') {
    for (const key of ['message', 'msg', 'detail', 'error', 'code', 'type']) {
      const val = raw[key]
      if (val == null || val === '') continue
      if (typeof val === 'string') return val
      if (typeof val === 'object') {
        const nested = formatErrorMessage(val)
        if (nested) return nested
      }
      return String(val)
    }
    try {
      return JSON.stringify(raw)
    } catch {
      return String(raw)
    }
  }
  return String(raw)
}
