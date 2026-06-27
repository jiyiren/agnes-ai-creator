<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { videoApi } from '../api'
import { useDialog } from '../composables/useDialog'
import { usePaginatedTaskHistory } from '../composables/usePaginatedTaskHistory'
import { formatErrorMessage } from '../utils/errorMessage'
import { canRefreshTaskStatus } from '../utils/transientError'
import TrashIcon from '../components/TrashIcon.vue'

const { alert, confirm } = useDialog()

const meta = ref({ modes: [], frame_presets: [], resolution_presets: [] })
const form = ref({
  model: 'agnes-video-v2.0',
  mode: 'text2video',
  prompt: '',
  negative_prompt: '',
  width: 1280,
  height: 720,
  num_frames: 121,
  frame_rate: 24,
  seed: null,
})
const inputImages = ref([])
const uploading = ref(false)
const submitting = ref(false)
const retrying = ref(false)
const refreshingTaskId = ref(null)
const selectedTaskId = ref(null)
const {
  history,
  historyLoading,
  historyHasMore,
  resetHistory,
  loadMoreHistory,
} = usePaginatedTaskHistory(videoApi.listTasks)
const error = ref('')
const formCardRef = ref(null)
const historyScrollRef = ref(null)
const historySentinelRef = ref(null)
let historyObserver = null
let pollTimer = null

const selectedTask = computed(() =>
  history.value.find(t => t.id === selectedTaskId.value) || null
)

const activeTasks = computed(() =>
  history.value.filter(t => ['queued', 'in_progress', 'submitting'].includes(t.status))
)

const selectedResolutionId = computed({
  get() {
    const match = meta.value.resolution_presets?.find(
      p => p.width === form.value.width && p.height === form.value.height
    )
    return match?.id || '720p-h'
  },
  set(id) {
    const preset = meta.value.resolution_presets?.find(p => p.id === id)
    if (preset) {
      form.value.width = preset.width
      form.value.height = preset.height
    }
  },
})

const resolutionGroups = computed(() => {
  const presets = meta.value.resolution_presets || []
  return [
    { label: '横屏', items: presets.filter(p => p.group === 'landscape') },
    { label: '竖屏', items: presets.filter(p => p.group === 'portrait') },
  ].filter(g => g.items.length)
})

async function loadMeta() {
  meta.value = await videoApi.getModels()
  await resetHistory()
  if (history.value.length && !selectedTaskId.value) {
    selectedTaskId.value = history.value[0].id
  }
  startPollingAll()
}

function setupHistoryObserver() {
  historyObserver?.disconnect()
  if (!historyScrollRef.value || !historySentinelRef.value || !historyHasMore.value) return

  historyObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) loadMoreHistory()
    },
    { root: historyScrollRef.value, rootMargin: '120px' },
  )
  historyObserver.observe(historySentinelRef.value)
}

async function handleUpload(e) {
  const files = Array.from(e.target.files)
  uploading.value = true
  try {
    for (const file of files) {
      const res = await videoApi.upload(file)
      inputImages.value.push(res.url)
    }
  } catch (err) {
    error.value = err.message
    await alert({ title: '上传失败', message: err.message, confirmVariant: 'danger' })
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

function removeImage(i) {
  inputImages.value.splice(i, 1)
}

function applyPreset(preset) {
  form.value.num_frames = preset.num_frames
  form.value.frame_rate = preset.frame_rate
}

function taskErrorMessage(task) {
  return formatErrorMessage(task?.error_message) || (task?.status === 'failed' ? '生成失败' : '')
}

function startPollingAll() {
  stopPolling()
  pollTimer = setInterval(async () => {
    const pending = history.value.filter(t =>
      (t.status === 'queued' || t.status === 'in_progress' || t.status === 'submitting')
      && !String(t.id).startsWith('temp-')
    )
    if (!pending.length) return

    for (const task of pending) {
      try {
        const prevStatus = task.status
        const updated = await videoApi.getTask(task.id)
        const idx = history.value.findIndex(t => t.id === updated.id)
        if (idx !== -1) history.value[idx] = updated
        if (prevStatus !== 'failed' && updated.status === 'failed') {
          const msg = taskErrorMessage(updated) || '生成失败'
          if (selectedTaskId.value === updated.id) {
            error.value = msg
          }
          await alert({ title: '生成失败', message: msg, confirmVariant: 'danger' })
        }
      } catch {}
    }
  }, 8000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function generate() {
  if (!form.value.prompt.trim()) {
    error.value = '请输入提示词'
    return
  }
  if (form.value.mode === 'img2video' && !inputImages.value.length) {
    error.value = '请上传输入图片'
    return
  }
  if (['multi_img', 'keyframes'].includes(form.value.mode) && inputImages.value.length < 2) {
    error.value = '至少需要 2 张图片'
    return
  }

  error.value = ''
  submitting.value = true

  const tempId = `temp-${Date.now()}`
  const optimisticInputImages =
    form.value.mode === 'img2video' && inputImages.value.length
      ? [inputImages.value[0]]
      : ['multi_img', 'keyframes'].includes(form.value.mode) && inputImages.value.length
        ? [...inputImages.value]
        : null

  const optimisticTask = {
    id: tempId,
    status: 'submitting',
    progress: 0,
    prompt: form.value.prompt,
    negative_prompt: form.value.negative_prompt || null,
    mode: form.value.mode,
    width: form.value.width,
    height: form.value.height,
    num_frames: form.value.num_frames,
    frame_rate: form.value.frame_rate,
    seed: form.value.seed,
    input_images: optimisticInputImages,
    created_at: new Date().toISOString(),
    _optimistic: true,
  }

  history.value.unshift(optimisticTask)
  selectedTaskId.value = tempId

  try {
    const payload = { ...form.value }
    if (form.value.mode === 'img2video') {
      payload.image = inputImages.value[0]
    } else if (['multi_img', 'keyframes'].includes(form.value.mode)) {
      payload.images = inputImages.value
    }
    if (!payload.seed) delete payload.seed

    const task = await videoApi.generate(payload)

    const idx = history.value.findIndex(t => t.id === tempId)
    if (idx !== -1) {
      history.value[idx] = task
    } else {
      history.value.unshift(task)
    }
    selectedTaskId.value = task.id
    startPollingAll()
    if (task.status === 'failed') {
      const msg = taskErrorMessage(task) || '提交失败'
      error.value = msg
      await alert({ title: '提交失败', message: msg, confirmVariant: 'danger' })
    }
  } catch (err) {
    try {
      await resetHistory()
      if (history.value.length) selectedTaskId.value = history.value[0].id
    } catch {}
    error.value = err.message
    await alert({ title: '提交失败', message: err.message, confirmVariant: 'danger' })
  } finally {
    submitting.value = false
  }
}

function displayUrl(task) {
  return task?.qiniu_url || task?.output_url
}

function inputImagesOf(task) {
  if (!task?.input_images) return []
  if (Array.isArray(task.input_images)) return task.input_images
  try {
    const parsed = JSON.parse(task.input_images)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function statusLabel(status) {
  const map = {
    submitting: '提交中',
    queued: '排队中',
    in_progress: '生成中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function statusBadgeClass(status) {
  const map = {
    submitting: 'badge-progress',
    queued: 'badge-queued',
    in_progress: 'badge-progress',
    completed: 'badge-completed',
    failed: 'badge-failed',
  }
  return map[status] || 'badge'
}

function modeLabel(mode) {
  return meta.value.modes.find(m => m.id === mode)?.name || mode
}

function modeTagClass(mode) {
  const map = {
    text2video: 'bg-cyan-400/15 text-cyan-200 border-cyan-400/25',
    img2video: 'bg-violet-400/15 text-violet-200 border-violet-400/25',
    multi_img: 'bg-orange-400/15 text-orange-200 border-orange-400/25',
    keyframes: 'bg-pink-400/15 text-pink-200 border-pink-400/25',
  }
  return map[mode] || 'bg-white/10 text-white/60 border-white/15'
}

function formatResolution(task) {
  if (!task?.width || !task?.height) return '—'
  return `${task.width}×${task.height}`
}

function formatDuration(task) {
  if (!task?.num_frames || !task?.frame_rate) return '—'
  return `${(task.num_frames / task.frame_rate).toFixed(1)}s`
}

function formatTaskMeta(task) {
  const parts = [
    formatResolution(task),
    formatDuration(task),
    task.num_frames != null ? `${task.num_frames}帧` : null,
    task.frame_rate != null ? `${task.frame_rate}fps` : null,
    task.seed != null && task.seed !== '' ? `seed:${task.seed}` : null,
  ].filter(Boolean)
  return parts.join(' · ')
}

async function refreshTaskStatus(task) {
  if (!task?.id || task._optimistic || refreshingTaskId.value) return
  refreshingTaskId.value = task.id
  error.value = ''

  const idx = history.value.findIndex(t => t.id === task.id)
  if (idx !== -1 && task.video_id) {
    history.value[idx] = {
      ...history.value[idx],
      error_message: null,
      status: ['failed'].includes(task.status) ? 'in_progress' : history.value[idx].status,
    }
  }

  try {
    const updated = await videoApi.syncTask(task.id)
    const updateIdx = history.value.findIndex(t => t.id === updated.id)
    if (updateIdx !== -1) history.value[updateIdx] = updated
    selectedTaskId.value = updated.id
    if (updated.status !== 'failed' && updated.status !== 'completed') {
      startPollingAll()
    } else if (updated.status === 'failed') {
      await alert({
        title: '仍未完成',
        message: taskErrorMessage(updated) || '任务尚未完成，请稍后再试',
        confirmVariant: 'danger',
      })
    }
  } catch (err) {
    error.value = err.message
    await alert({ title: '刷新失败', message: err.message, confirmVariant: 'danger' })
    try {
      const latest = await videoApi.getTask(task.id)
      const revertIdx = history.value.findIndex(t => t.id === task.id)
      if (revertIdx !== -1) history.value[revertIdx] = latest
    } catch {}
  } finally {
    refreshingTaskId.value = null
  }
}

async function retryTask(task) {
  if (!task?.id || task._optimistic || retrying.value) return
  retrying.value = true
  error.value = ''

  const idx = history.value.findIndex(t => t.id === task.id)
  if (idx !== -1) {
    history.value[idx] = {
      ...history.value[idx],
      status: 'submitting',
      progress: 0,
      error_message: null,
      task_id: null,
      video_id: null,
      output_url: null,
      qiniu_url: null,
      seconds: null,
      size: null,
      completed_at: null,
    }
  }

  try {
    const updated = await videoApi.retry(task.id)
    const updateIdx = history.value.findIndex(t => t.id === updated.id)
    if (updateIdx !== -1) {
      history.value[updateIdx] = updated
    }
    selectedTaskId.value = updated.id
    if (updated.status !== 'failed') {
      startPollingAll()
    } else {
      const msg = taskErrorMessage(updated) || '提交失败'
      await alert({ title: '重试失败', message: msg, confirmVariant: 'danger' })
    }
  } catch (err) {
    error.value = err.message
    await alert({ title: '重试失败', message: err.message, confirmVariant: 'danger' })
    try {
      const latest = await videoApi.getTask(task.id)
      const revertIdx = history.value.findIndex(t => t.id === task.id)
      if (revertIdx !== -1) history.value[revertIdx] = latest
    } catch {}
  } finally {
    retrying.value = false
  }
}

async function deleteTask(task, e) {
  e?.stopPropagation()
  if (task._optimistic) return

  const ok = await confirm({
    title: '删除任务',
    message: '确定删除此视频任务？删除后无法恢复。',
    confirmText: '删除',
    cancelText: '取消',
    confirmVariant: 'danger',
  })
  if (!ok) return

  try {
    await videoApi.deleteTask(task.id)
    history.value = history.value.filter(t => t.id !== task.id)
    if (selectedTaskId.value === task.id) {
      selectedTaskId.value = history.value[0]?.id || null
    }
  } catch (err) {
    await alert({ title: '删除失败', message: err.message, confirmVariant: 'danger' })
  }
}

function selectTask(task) {
  selectedTaskId.value = task.id
}

function fillFormFromTask(task) {
  if (!task) return
  form.value = {
    model: task.model || 'agnes-video-v2.0',
    mode: task.mode || 'text2video',
    prompt: task.prompt || '',
    negative_prompt: task.negative_prompt || '',
    width: task.width ?? 1280,
    height: task.height ?? 720,
    num_frames: task.num_frames ?? 121,
    frame_rate: task.frame_rate ?? 24,
    seed: task.seed ?? null,
  }
  inputImages.value = [...inputImagesOf(task)]
  error.value = ''
  formCardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(async () => {
  await loadMeta()
  await nextTick()
  setupHistoryObserver()
})

watch(historyHasMore, async () => {
  await nextTick()
  setupHistoryObserver()
})

onUnmounted(() => {
  historyObserver?.disconnect()
  stopPolling()
})
</script>

<template>
  <div class="flex h-full">
    <!-- Task list sidebar -->
    <div class="w-96 border-r border-white/10 flex flex-col bg-black/10">
      <div class="p-4 border-b border-white/10">
        <div class="flex items-center justify-between mb-1">
          <h3 class="font-bold text-white">任务列表</h3>
          <span v-if="activeTasks.length" class="badge-progress">{{ activeTasks.length }} 进行中</span>
        </div>
        <p class="text-xs text-white/40">提交后立即显示进度</p>
      </div>

      <div ref="historyScrollRef" class="flex-1 overflow-y-auto p-3 space-y-2">
        <div
          v-for="task in history"
          :key="task.id"
          @click="selectTask(task)"
          class="group p-4 rounded-2xl cursor-pointer transition-all duration-200 border"
          :class="selectedTaskId === task.id
            ? 'bg-gradient-to-r from-fuchsia-500/20 to-cyan-400/10 border-white/25 shadow-glow-cyan'
            : 'border-white/15 hover:bg-white/10 hover:border-white/20'"
        >
          <div class="flex gap-2">
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2 mb-2">
                <span class="text-xs text-white/40 font-mono">#{{ task._optimistic ? '...' : task.id }}</span>
                <span :class="statusBadgeClass(task.status)">{{ statusLabel(task.status) }}</span>
              </div>
              <p class="text-sm text-white/90 truncate font-medium">{{ task.prompt }}</p>
              <p v-if="task.negative_prompt" class="text-xs text-white/40 truncate mt-0.5">负向: {{ task.negative_prompt }}</p>
              <p class="text-[11px] text-white/35 mt-1 font-mono">{{ formatTaskMeta(task) }}</p>
              <div class="mt-1">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border"
                  :class="modeTagClass(task.mode)"
                >{{ modeLabel(task.mode) }}</span>
              </div>

              <div v-if="inputImagesOf(task).length" class="mt-2 flex flex-wrap gap-1.5">
                <img
                  v-for="(url, i) in inputImagesOf(task)"
                  :key="i"
                  :src="url"
                  class="w-10 h-10 object-cover rounded-lg border border-white/15"
                  :title="inputImagesOf(task).length > 1 ? `参考图 ${i + 1}` : '参考图'"
                />
              </div>

              <!-- Progress bar for active tasks -->
              <div v-if="['submitting', 'queued', 'in_progress'].includes(task.status)" class="mt-3">
                <div class="progress-bar">
                  <div
                    class="progress-fill"
                    :class="task.status === 'submitting' ? 'animate-pulse' : ''"
                    :style="{ width: task.status === 'submitting' ? '15%' : `${task.progress || 5}%` }"
                  ></div>
                </div>
                <p class="text-xs text-white/40 mt-1.5">
                  <template v-if="task.status === 'submitting'">正在提交任务...</template>
                  <template v-else-if="task.status === 'queued'">排队等待中...</template>
                  <template v-else>进度 {{ task.progress || 0 }}%</template>
                </p>
              </div>

              <p v-if="task.status === 'failed'" class="text-xs text-rose-300/80 mt-2 truncate">
                {{ taskErrorMessage(task) }}
              </p>
              <button
                v-if="canRefreshTaskStatus(task, 'video')"
                @click.stop="refreshTaskStatus(task)"
                :disabled="refreshingTaskId === task.id"
                class="mt-2 text-xs px-2.5 py-1 rounded-lg border border-cyan-400/30 text-cyan-200 hover:bg-cyan-400/10 transition-colors disabled:opacity-50"
              >{{ refreshingTaskId === task.id ? '刷新中...' : '刷新状态' }}</button>
            </div>

            <button
              @click="deleteTask(task, $event)"
              class="w-8 h-8 rounded-xl flex items-center justify-center text-white/50 hover:bg-rose-500/30 hover:text-rose-300 transition-all flex-shrink-0 self-start mt-0.5"
              :class="task._optimistic
                ? 'invisible pointer-events-none'
                : 'opacity-0 group-hover:opacity-100'"
              title="删除"
            ><TrashIcon /></button>
          </div>
        </div>

        <div
          v-if="historyHasMore && history.length"
          ref="historySentinelRef"
          class="py-3 flex justify-center"
        >
          <div
            v-if="historyLoading"
            class="w-5 h-5 border-2 border-fuchsia-400/30 border-t-fuchsia-400 rounded-full animate-spin"
          ></div>
        </div>

        <div v-if="!history.length && historyLoading" class="flex flex-col items-center justify-center py-16 text-white/40">
          <div class="w-6 h-6 border-2 border-fuchsia-400/30 border-t-fuchsia-400 rounded-full animate-spin"></div>
          <p class="text-xs mt-3">加载中...</p>
        </div>

        <div v-if="!history.length && !historyLoading" class="flex flex-col items-center justify-center py-16 text-white/40">
          <div class="text-4xl mb-3">🎬</div>
          <p class="text-sm">暂无任务</p>
          <p class="text-xs mt-1">填写参数后点击生成</p>
        </div>
      </div>
    </div>

    <!-- Main area: form + preview -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <div class="flex-1 overflow-y-auto p-6">
        <div class="max-w-5xl mx-auto space-y-6">
          <div>
            <h2 class="text-2xl font-extrabold bg-gradient-to-r from-cyan-300 via-fuchsia-300 to-orange-300 bg-clip-text text-transparent">
              视频生成
            </h2>
            <p class="text-white/50 text-sm mt-1">文生视频 · 图生视频 · 多图视频 · 关键帧动画</p>
          </div>

          <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <!-- Form -->
            <div ref="formCardRef" class="glass-card space-y-4">
              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">生成模式</label>
                <div class="grid grid-cols-2 gap-2">
                  <button
                    v-for="m in meta.modes"
                    :key="m.id"
                    @click="form.mode = m.id"
                    class="px-3 py-2.5 rounded-2xl text-sm font-medium transition-all duration-200 border"
                    :class="form.mode === m.id
                      ? 'border-fuchsia-400/50 bg-gradient-to-r from-fuchsia-500/25 to-cyan-400/15 text-white shadow-glow-cyan'
                      : 'border-white/10 text-white/50 hover:border-white/25 hover:bg-white/5'"
                  >{{ m.name }}</button>
                </div>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">提示词</label>
                <textarea v-model="form.prompt" rows="3" class="input-field text-sm" placeholder="描述视频内容、动作、镜头运动..."></textarea>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">负向提示词（可选）</label>
                <input v-model="form.negative_prompt" class="input-field text-sm" placeholder="描述需要避免的内容" />
              </div>

              <div v-if="form.mode !== 'text2video'">
                <label class="text-sm text-white/60 mb-2 block font-medium">
                  {{ form.mode === 'img2video' ? '输入图片' : '参考图片' }}
                </label>
                <div class="flex flex-wrap gap-2 mb-2">
                  <div v-for="(url, i) in inputImages" :key="i" class="relative group">
                    <img :src="url" class="w-20 h-20 object-cover rounded-2xl border border-white/20" />
                    <button @click="removeImage(i)" class="absolute -top-1 -right-1 w-6 h-6 bg-rose-500 rounded-full text-xs opacity-0 group-hover:opacity-100 shadow-lg">✕</button>
                  </div>
                </div>
                <label class="btn-secondary inline-flex items-center gap-2 cursor-pointer text-sm">
                  <input type="file" accept="image/*" multiple class="hidden" @change="handleUpload" />
                  {{ uploading ? '上传中...' : '+ 上传图片' }}
                </label>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">分辨率</label>
                <select v-model="selectedResolutionId" class="select-field text-sm w-full">
                  <optgroup v-for="g in resolutionGroups" :key="g.label" :label="g.label">
                    <option
                      v-for="p in g.items"
                      :key="p.id"
                      :value="p.id"
                    >{{ p.label }}</option>
                  </optgroup>
                </select>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">视频时长</label>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="p in meta.frame_presets"
                    :key="p.label"
                    @click="applyPreset(p)"
                    class="px-4 py-1.5 rounded-full text-xs border transition-all duration-200"
                    :class="form.num_frames === p.num_frames
                      ? 'border-fuchsia-400/50 text-fuchsia-200 bg-fuchsia-500/20'
                      : 'border-white/15 text-white/50 hover:border-white/30'"
                  >{{ p.label }}</button>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="text-sm text-white/60 mb-2 block">帧数</label>
                  <input v-model.number="form.num_frames" type="number" class="input-field text-sm" />
                </div>
                <div>
                  <label class="text-sm text-white/60 mb-2 block">帧率</label>
                  <input v-model.number="form.frame_rate" type="number" class="input-field text-sm" />
                </div>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block">随机种子（可选）</label>
                <input v-model.number="form.seed" type="number" class="input-field text-sm" placeholder="留空则随机" />
              </div>

              <p v-if="error" class="text-rose-300 text-sm glass px-4 py-2 rounded-2xl border border-rose-400/30">{{ error }}</p>

              <button @click="generate" :disabled="submitting" class="btn-primary w-full py-3 text-base">
                {{ submitting ? '提交中...' : '✨ 开始生成' }}
              </button>
            </div>

            <!-- Preview -->
            <div class="glass-card flex flex-col min-h-[420px]">
              <div v-if="selectedTask" class="flex-1 flex flex-col">
                <div class="flex items-center justify-between mb-4">
                  <span class="font-bold text-white">
                    {{ selectedTask._optimistic ? '新任务' : `任务 #${selectedTask.id}` }}
                  </span>
                  <div class="flex items-center gap-2">
                    <span :class="statusBadgeClass(selectedTask.status)">
                      {{ statusLabel(selectedTask.status) }}
                    </span>
                    <button
                      v-if="!selectedTask._optimistic"
                      @click="deleteTask(selectedTask)"
                      class="btn-ghost text-rose-300 hover:bg-rose-500/20 hover:text-rose-200 text-xs px-3 py-1.5"
                    >
                      删除
                    </button>
                  </div>
                </div>

                <div v-if="['submitting', 'queued', 'in_progress'].includes(selectedTask.status)" class="mb-5">
                  <div class="progress-bar h-3">
                    <div
                      class="progress-fill"
                      :class="selectedTask.status === 'submitting' ? 'animate-pulse' : ''"
                      :style="{ width: selectedTask.status === 'submitting' ? '15%' : `${selectedTask.progress || 5}%` }"
                    ></div>
                  </div>
                  <p class="text-sm text-white/50 mt-2">
                    <template v-if="selectedTask.status === 'submitting'">正在提交到服务器...</template>
                    <template v-else-if="selectedTask.status === 'queued'">任务已排队，等待处理...</template>
                    <template v-else>生成进度 {{ selectedTask.progress || 0 }}%，请耐心等待</template>
                  </p>
                </div>

                <div v-if="displayUrl(selectedTask)" class="flex-1">
                  <video :src="displayUrl(selectedTask)" controls class="w-full rounded-2xl border border-white/15 shadow-glow"></video>
                  <div class="mt-3 text-xs text-white/50 flex flex-wrap gap-4">
                    <span v-if="selectedTask.seconds">时长: {{ selectedTask.seconds }}s</span>
                    <span v-if="selectedTask.size">分辨率: {{ selectedTask.size }}</span>
                    <span v-if="selectedTask.qiniu_url" class="text-emerald-300">✓ 已存储至七牛云</span>
                  </div>
                  <div v-if="inputImagesOf(selectedTask).length" class="mt-4">
                    <p class="text-xs text-white/50 mb-2 font-medium">参考图</p>
                    <div class="flex flex-wrap gap-2">
                      <img
                        v-for="(url, i) in inputImagesOf(selectedTask)"
                        :key="i"
                        :src="url"
                        class="w-20 h-20 object-cover rounded-xl border border-white/20"
                      />
                    </div>
                  </div>
                </div>

                <div v-else-if="['submitting', 'queued', 'in_progress'].includes(selectedTask.status)" class="flex-1 flex flex-col">
                  <div class="flex-1 flex flex-col items-center justify-center">
                    <div class="w-16 h-16 rounded-full border-4 border-fuchsia-400/30 border-t-fuchsia-400 animate-spin"></div>
                    <p class="text-white/50 mt-5 text-sm">视频生成中，可能需要数分钟</p>
                    <button
                      v-if="canRefreshTaskStatus(selectedTask, 'video')"
                      @click.stop="refreshTaskStatus(selectedTask)"
                      :disabled="refreshingTaskId === selectedTask.id"
                      class="mt-4 btn-secondary text-xs px-4 py-2"
                    >{{ refreshingTaskId === selectedTask.id ? '刷新中...' : '手动刷新状态' }}</button>
                  </div>
                  <div v-if="inputImagesOf(selectedTask).length" class="mt-4">
                    <p class="text-xs text-white/50 mb-2 font-medium">参考图</p>
                    <div class="flex flex-wrap gap-2">
                      <img
                        v-for="(url, i) in inputImagesOf(selectedTask)"
                        :key="i"
                        :src="url"
                        class="w-20 h-20 object-cover rounded-xl border border-white/20"
                      />
                    </div>
                  </div>
                </div>

                <div v-if="selectedTask.status === 'failed'" class="glass px-4 py-3 rounded-2xl border border-rose-400/30 mt-2">
                  <p class="text-rose-300 text-sm whitespace-pre-wrap break-words">{{ taskErrorMessage(selectedTask) }}</p>
                  <div class="mt-3 flex flex-wrap gap-2">
                    <button
                      v-if="canRefreshTaskStatus(selectedTask, 'video')"
                      @click.stop="refreshTaskStatus(selectedTask)"
                      :disabled="refreshingTaskId === selectedTask.id"
                      class="btn-primary px-4 py-2 text-sm"
                    >{{ refreshingTaskId === selectedTask.id ? '刷新中...' : '手动刷新状态' }}</button>
                    <button
                      v-if="!selectedTask._optimistic && !selectedTask.video_id"
                      @click.stop="retryTask(selectedTask)"
                      :disabled="retrying"
                      class="btn-secondary px-4 py-2 text-sm"
                    >{{ retrying ? '提交中...' : '重试提交' }}</button>
                  </div>
                  <p v-if="canRefreshTaskStatus(selectedTask, 'video')" class="text-xs text-white/40 mt-2">
                    若因限流导致状态未更新，可点击刷新从服务器同步最新结果
                  </p>
                </div>

                <div class="mt-4 space-y-3">
                  <div class="flex items-center justify-between gap-2">
                    <p class="text-xs text-white/50 font-medium">生成参数</p>
                    <button
                      v-if="!selectedTask._optimistic"
                      @click="fillFormFromTask(selectedTask)"
                      class="btn-secondary text-xs px-3 py-1.5"
                    >
                      填充到表单
                    </button>
                  </div>
                  <div class="glass px-4 py-3 rounded-2xl border border-white/10 space-y-2 text-sm">
                    <div>
                      <span class="text-white/40 text-xs">正向提示词</span>
                      <p class="text-white/80 mt-0.5 leading-relaxed">{{ selectedTask.prompt || '—' }}</p>
                    </div>
                    <div v-if="selectedTask.negative_prompt">
                      <span class="text-white/40 text-xs">负向提示词</span>
                      <p class="text-white/60 mt-0.5 leading-relaxed">{{ selectedTask.negative_prompt }}</p>
                    </div>
                    <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs pt-1">
                      <div><span class="text-white/40">分辨率</span> <span class="text-white/70">{{ formatResolution(selectedTask) }}</span></div>
                      <div><span class="text-white/40">时长</span> <span class="text-white/70">{{ formatDuration(selectedTask) }}</span></div>
                      <div><span class="text-white/40">帧数</span> <span class="text-white/70">{{ selectedTask.num_frames ?? '—' }}</span></div>
                      <div><span class="text-white/40">帧率</span> <span class="text-white/70">{{ selectedTask.frame_rate != null ? `${selectedTask.frame_rate} fps` : '—' }}</span></div>
                      <div class="col-span-2"><span class="text-white/40">随机种子</span> <span class="text-white/70 font-mono">{{ selectedTask.seed != null && selectedTask.seed !== '' ? selectedTask.seed : '随机' }}</span></div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="flex-1 flex flex-col items-center justify-center text-white/40">
                <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-cyan-400/30 to-fuchsia-500/30 flex items-center justify-center text-4xl mb-4 border border-white/20 animate-float">
                  🎬
                </div>
                <p>选择左侧任务或创建新任务</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
