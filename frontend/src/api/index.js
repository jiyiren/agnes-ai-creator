const BASE = '/api'

async function request(url, options = {}) {
  const resp = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || resp.statusText)
  }
  return resp
}

export const chatApi = {
  listConversations: () => request('/chat/conversations').then(r => r.json()),
  createConversation: (data) => request('/chat/conversations', { method: 'POST', body: JSON.stringify(data) }).then(r => r.json()),
  getConversation: (id) => request(`/chat/conversations/${id}`).then(r => r.json()),
  deleteConversation: (id) => request(`/chat/conversations/${id}`, { method: 'DELETE' }).then(r => r.json()),
  updateConversation: (id, data) => request(`/chat/conversations/${id}`, { method: 'PATCH', body: JSON.stringify(data) }).then(r => r.json()),
  getModels: () => request('/chat/models').then(r => r.json()),
  deleteMessage: (convId, msgId) => request(`/chat/conversations/${convId}/messages/${msgId}`, { method: 'DELETE' }).then(r => r.json()),

  sendMessageStream(convId, data, onChunk, onDone, onError) {
    chatApi._postStream(`/chat/conversations/${convId}/send`, data, onChunk, onDone, onError)
  },

  regenerateStream(convId, msgId, data, onChunk, onDone, onError) {
    chatApi._postStream(`/chat/conversations/${convId}/messages/${msgId}/regenerate`, data, onChunk, onDone, onError)
  },

  _postStream(url, data, onChunk, onDone, onError) {
    fetch(`${BASE}${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...data, stream: true }),
    }).then(async (resp) => {
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        onError(err.detail || '请求失败')
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let finished = false

      const processLine = (line) => {
        if (!line.startsWith('data: ')) return
        try {
          const parsed = JSON.parse(line.slice(6))
          if (parsed.type === 'content') onChunk(parsed.content)
          else if (parsed.type === 'done') {
            finished = true
            onDone(parsed)
          } else if (parsed.type === 'error') {
            finished = true
            onError(parsed.message || '请求失败')
          }
        } catch {}
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) processLine(line)
      }
      buffer += decoder.decode()
      for (const line of buffer.split('\n')) processLine(line)
      if (!finished) onError('模型未返回完整响应，请检查后端服务或网络连接')
    }).catch(onError)
  },
}

export const imageApi = {
  getModels: () => request('/images/models').then(r => r.json()),
  generate: (data, files) => {
    if (files?.length) {
      const form = new FormData()
      for (const [k, v] of Object.entries(data)) {
        if (v !== undefined && v !== null) form.append(k, String(v))
      }
      for (const file of files) form.append('files', file)
      return fetch(`${BASE}/images/generate`, { method: 'POST', body: form }).then(async (resp) => {
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({ detail: resp.statusText }))
          throw new Error(err.detail || resp.statusText)
        }
        return resp.json()
      })
    }
    return request('/images/generate', { method: 'POST', body: JSON.stringify(data) }).then(r => r.json())
  },
  listTasks: ({ limit = 20, offset = 0 } = {}) =>
    request(`/images/tasks?limit=${limit}&offset=${offset}`).then(r => r.json()),
  getTask: (id) => request(`/images/tasks/${id}`).then(r => r.json()),
  syncTask: (id) => request(`/images/tasks/${id}/sync`, { method: 'POST' }).then(r => r.json()),
  deleteTask: (id) => request(`/images/tasks/${id}`, { method: 'DELETE' }).then(r => r.json()),
  upload: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const resp = await fetch(`${BASE}/images/upload`, { method: 'POST', body: form })
    if (!resp.ok) throw new Error('上传失败')
    return resp.json()
  },
}

export const videoApi = {
  getModels: () => request('/videos/models').then(r => r.json()),
  generate: (data) => request('/videos/generate', { method: 'POST', body: JSON.stringify(data) }).then(r => r.json()),
  getTask: (id) => request(`/videos/tasks/${id}`).then(r => r.json()),
  syncTask: (id) => request(`/videos/tasks/${id}/sync`, { method: 'POST' }).then(r => r.json()),
  retry: (id) => request(`/videos/tasks/${id}/retry`, { method: 'POST' }).then(r => r.json()),
  deleteTask: (id) => request(`/videos/tasks/${id}`, { method: 'DELETE' }).then(r => r.json()),
  listTasks: ({ limit = 20, offset = 0 } = {}) =>
    request(`/videos/tasks?limit=${limit}&offset=${offset}`).then(r => r.json()),
  upload: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const resp = await fetch(`${BASE}/videos/upload`, { method: 'POST', body: form })
    if (!resp.ok) throw new Error('上传失败')
    return resp.json()
  },
}

export const settingsApi = {
  getStatus: () => request('/settings/status').then(r => r.json()),
  getBaseUrl: () => request('/settings/base-url').then(r => r.json()),
  updateBaseUrl: (base_url) =>
    request('/settings/base-url', { method: 'PUT', body: JSON.stringify({ base_url }) }).then(r => r.json()),
  listApiKeys: () => request('/settings/api-keys').then(r => r.json()),
  createApiKey: (data) =>
    request('/settings/api-keys', { method: 'POST', body: JSON.stringify(data) }).then(r => r.json()),
  updateApiKey: (id, data) =>
    request(`/settings/api-keys/${id}`, { method: 'PATCH', body: JSON.stringify(data) }).then(r => r.json()),
  activateApiKey: (id) =>
    request(`/settings/api-keys/${id}/activate`, { method: 'POST' }).then(r => r.json()),
  deleteApiKey: (id) =>
    request(`/settings/api-keys/${id}`, { method: 'DELETE' }).then(r => r.json()),
}
