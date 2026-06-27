import { ref } from 'vue'

export const TASK_HISTORY_PAGE_SIZE = 20

function isServerTask(task) {
  return task && !task._optimistic && !String(task.id).startsWith('temp-')
}

export function usePaginatedTaskHistory(listTasksFn) {
  const history = ref([])
  const historyLoading = ref(false)
  const historyHasMore = ref(true)

  function serverTaskCount() {
    return history.value.filter(isServerTask).length
  }

  async function loadHistory(reset = false) {
    if (historyLoading.value) return
    if (!reset && !historyHasMore.value) return

    historyLoading.value = true
    try {
      const offset = reset ? 0 : serverTaskCount()
      const tasks = await listTasksFn({
        limit: TASK_HISTORY_PAGE_SIZE,
        offset,
      })

      if (reset) {
        const pending = history.value.filter(t => !isServerTask(t))
        history.value = [...pending, ...tasks]
      } else {
        const existingIds = new Set(history.value.map(t => t.id))
        for (const task of tasks) {
          if (!existingIds.has(task.id)) history.value.push(task)
        }
      }

      historyHasMore.value = tasks.length === TASK_HISTORY_PAGE_SIZE
    } finally {
      historyLoading.value = false
    }
  }

  async function loadMoreHistory() {
    return loadHistory(false)
  }

  async function resetHistory() {
    historyHasMore.value = true
    return loadHistory(true)
  }

  return {
    history,
    historyLoading,
    historyHasMore,
    resetHistory,
    loadMoreHistory,
  }
}
