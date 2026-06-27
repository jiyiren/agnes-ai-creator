<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { imageApi } from '../api'
import { useDialog } from '../composables/useDialog'
import { useApiKeyGuard, imageModeNeedsQiniu } from '../composables/useApiKeyGuard'
import { usePaginatedTaskHistory } from '../composables/usePaginatedTaskHistory'
import { formatErrorMessage } from '../utils/errorMessage'
import { canRefreshTaskStatus } from '../utils/transientError'
import TrashIcon from '../components/TrashIcon.vue'

const { confirm, alert } = useDialog()
const { hasActiveKey, hasQiniuConfig, keyStatusLoading, refreshKeyStatus, requireApiKey, requireQiniuConfig } = useApiKeyGuard()

const modes = [
  { id: 'text2img', name: '文生图' },
  { id: 'img2img', name: '单图编辑' },
  { id: 'multi_img', name: '多图合成' },
]

const meta = ref({ models: [], sizes: [] })
const form = ref({
  model: 'agnes-image-2.1-flash',
  mode: 'text2img',
  prompt: '',
  size: '1024x768',
  response_format: 'url',
})
const inputImages = ref([])
const generating = ref(false)
const generateStep = ref('')
const selectedTaskId = ref(null)
const {
  history,
  historyLoading,
  historyHasMore,
  resetHistory,
  loadMoreHistory,
} = usePaginatedTaskHistory(imageApi.listTasks)
const error = ref('')
const lightboxUrl = ref(null)
const formCardRef = ref(null)
const refreshingTaskId = ref(null)
const historyScrollRef = ref(null)
const historySentinelRef = ref(null)
let historyObserver = null

const selectedTask = computed(() =>
  history.value.find(t => t.id === selectedTaskId.value) || null
)

const currentModeNeedsQiniu = computed(() => imageModeNeedsQiniu(form.value.mode))

function formatSizeLabel(size) {
  const [w, h] = size.split('x').map(Number)
  if (!w || !h) return size
  const gcd = (a, b) => (b ? gcd(b, a % b) : a)
  const g = gcd(w, h)
  const ratio = `${w / g}:${h / g}`
  if (w === h) return `${size} (${ratio} 方图)`
  if (w > h) return `${size} (${ratio} 横图)`
  return `${size} (${ratio} 竖图)`
}

function modeLabel(mode) {
  return modes.find(m => m.id === mode)?.name || mode
}

function modeTagClass(mode) {
  const map = {
    text2img: 'bg-pink-400/15 text-pink-200 border-pink-400/25',
    img2img: 'bg-violet-400/15 text-violet-200 border-violet-400/25',
    multi_img: 'bg-orange-400/15 text-orange-200 border-orange-400/25',
  }
  return map[mode] || 'bg-white/10 text-white/60 border-white/15'
}

async function loadMeta() {
  meta.value = await imageApi.getModels()
  await resetHistory()
  if (history.value.length && !selectedTaskId.value) {
    selectedTaskId.value = history.value[0].id
  }
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

function revokePreview(item) {
  if (item?.preview?.startsWith('blob:')) {
    URL.revokeObjectURL(item.preview)
  }
}

function selectMode(modeId) {
  form.value.mode = modeId
  if (modeId === 'img2img' && inputImages.value.length > 1) {
    inputImages.value.slice(1).forEach(revokePreview)
    inputImages.value = [inputImages.value[0]]
  }
}

async function handleFileSelect(e) {
  const files = Array.from(e.target.files)
  if (!files.length) return
  if (!(await requireQiniuConfig())) {
    e.target.value = ''
    return
  }
  if (form.value.mode === 'img2img') {
    if (inputImages.value[0]) revokePreview(inputImages.value[0])
    inputImages.value = [{ file: files[0], preview: URL.createObjectURL(files[0]) }]
  } else {
    for (const file of files) {
      inputImages.value.push({ file, preview: URL.createObjectURL(file) })
    }
  }
  e.target.value = ''
}

function removeInputImage(i) {
  revokePreview(inputImages.value[i])
  inputImages.value.splice(i, 1)
}

async function generate() {
  if (!form.value.prompt.trim()) {
    error.value = '请输入提示词'
    return
  }
  if (form.value.mode === 'img2img' && !inputImages.value.length) {
    error.value = '请选择参考图'
    return
  }
  if (form.value.mode === 'multi_img' && !inputImages.value.length) {
    error.value = '请选择输入图片'
    return
  }
  if (!(await requireApiKey())) return
  if (currentModeNeedsQiniu.value && !(await requireQiniuConfig())) return

  generating.value = true
  generateStep.value = form.value.mode === 'text2img' ? 'generating' : 'uploading'
  error.value = ''

  const previewUrls = inputImages.value.map(item => item.preview)
  const tempId = `temp-${Date.now()}`
  const optimisticTask = {
    id: tempId,
    status: 'processing',
    prompt: form.value.prompt,
    mode: form.value.mode,
    size: form.value.size,
    input_images: form.value.mode !== 'text2img' ? previewUrls : null,
    created_at: new Date().toISOString(),
    _optimistic: true,
  }

  history.value.unshift(optimisticTask)
  selectedTaskId.value = tempId

  try {
    const payload = { ...form.value }
    let task
    if (form.value.mode === 'img2img') {
      if (hasLocalFiles()) {
        generateStep.value = 'uploading'
        task = await imageApi.generate(payload, [inputImages.value[0].file])
      } else {
        generateStep.value = 'generating'
        task = await imageApi.generate({ ...payload, images: imageUrlsFromInput() })
      }
    } else if (form.value.mode === 'multi_img') {
      if (hasLocalFiles()) {
        generateStep.value = 'uploading'
        task = await imageApi.generate(payload, inputImages.value.map(item => item.file))
      } else {
        generateStep.value = 'generating'
        task = await imageApi.generate({ ...payload, images: imageUrlsFromInput() })
      }
    } else {
      generateStep.value = 'generating'
      task = await imageApi.generate(payload)
    }

    const idx = history.value.findIndex(t => t.id === tempId)
    if (idx !== -1) {
      history.value[idx] = task
    } else {
      history.value.unshift(task)
    }
    selectedTaskId.value = task.id
  } catch (err) {
    history.value = history.value.filter(t => t.id !== tempId)
    if (selectedTaskId.value === tempId) {
      selectedTaskId.value = history.value[0]?.id || null
    }
    error.value = err.message
    await alert({ title: '生成失败', message: err.message, confirmVariant: 'danger' })
  } finally {
    generating.value = false
    generateStep.value = ''
  }
}

async function deleteTask(task, e) {
  e?.stopPropagation()
  if (task._optimistic) return

  const ok = await confirm({
    title: '删除图片',
    message: '确定删除此生成结果？删除后无法恢复。',
    confirmText: '删除',
    cancelText: '取消',
    confirmVariant: 'danger',
  })
  if (!ok) return

  try {
    await imageApi.deleteTask(task.id)
    history.value = history.value.filter(t => t.id !== task.id)
    if (selectedTaskId.value === task.id) {
      selectedTaskId.value = history.value[0]?.id || null
    }
  } catch (err) {
    await alert({ title: '删除失败', message: err.message, confirmVariant: 'danger' })
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

function openLightbox(url) {
  if (url) lightboxUrl.value = url
}

function closeLightbox() {
  lightboxUrl.value = null
}

function onKeydown(e) {
  if (e.key === 'Escape') closeLightbox()
}

function statusLabel(status) {
  const map = {
    processing: '生成中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function statusBadgeClass(status) {
  const map = {
    processing: 'badge-progress',
    completed: 'badge-completed',
    failed: 'badge-failed',
  }
  return map[status] || 'badge'
}

function taskErrorMessage(task) {
  return formatErrorMessage(task?.error_message) || (task?.status === 'failed' ? '生成失败' : '')
}

async function refreshTaskStatus(task) {
  if (!task?.id || task._optimistic || refreshingTaskId.value) return
  refreshingTaskId.value = task.id
  error.value = ''

  const idx = history.value.findIndex(t => t.id === task.id)
  if (idx !== -1) {
    history.value[idx] = {
      ...history.value[idx],
      status: 'processing',
      error_message: null,
    }
  }

  try {
    const updated = await imageApi.syncTask(task.id)
    const updateIdx = history.value.findIndex(t => t.id === updated.id)
    if (updateIdx !== -1) history.value[updateIdx] = updated
    selectedTaskId.value = updated.id
    if (updated.status === 'failed') {
      await alert({
        title: '仍未完成',
        message: taskErrorMessage(updated) || '生成尚未成功，请稍后再试',
        confirmVariant: 'danger',
      })
    }
  } catch (err) {
    error.value = err.message
    await alert({ title: '刷新失败', message: err.message, confirmVariant: 'danger' })
    try {
      const latest = await imageApi.getTask(task.id)
      const revertIdx = history.value.findIndex(t => t.id === task.id)
      if (revertIdx !== -1) history.value[revertIdx] = latest
    } catch {}
  } finally {
    refreshingTaskId.value = null
  }
}

function selectTask(task) {
  selectedTaskId.value = task.id
}

function imageUrlsFromInput() {
  return inputImages.value.map(item => item.preview).filter(Boolean)
}

function hasLocalFiles() {
  return inputImages.value.length > 0 && inputImages.value.every(item => item.file)
}

function fillFormFromTask(task) {
  if (!task || task._optimistic) return
  let responseFormat = 'url'
  try {
    const params = typeof task.request_params === 'string'
      ? JSON.parse(task.request_params)
      : task.request_params
    responseFormat = params?.extra_body?.response_format || 'url'
  } catch {}

  form.value = {
    model: task.model || 'agnes-image-2.1-flash',
    mode: task.mode || 'text2img',
    prompt: task.prompt || '',
    size: task.size || '1024x768',
    response_format: responseFormat,
  }
  inputImages.value.forEach(revokePreview)
  inputImages.value = inputImagesOf(task).map(url => ({ preview: url }))
  error.value = ''
  formCardRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(async () => {
  await refreshKeyStatus()
  await loadMeta()
  await nextTick()
  setupHistoryObserver()
  window.addEventListener('keydown', onKeydown)
})

watch(historyHasMore, async () => {
  await nextTick()
  setupHistoryObserver()
})

onUnmounted(() => {
  historyObserver?.disconnect()
  window.removeEventListener('keydown', onKeydown)
  inputImages.value.forEach(revokePreview)
})
</script>

<template>
  <div class="flex h-full">
    <!-- Task list sidebar -->
    <div class="w-96 border-r border-white/10 flex flex-col bg-black/10">
      <div class="p-4 border-b border-white/10">
        <div class="flex items-center justify-between mb-1">
          <h3 class="font-bold text-white">生成历史</h3>
          <span v-if="generating" class="badge-progress">生成中</span>
        </div>
        <p class="text-xs text-white/40">点击预览，悬停可删除</p>
      </div>

      <div ref="historyScrollRef" class="flex-1 overflow-y-auto p-3 space-y-2">
        <div
          v-for="task in history"
          :key="task.id"
          @click="selectTask(task)"
          class="group p-3 rounded-2xl cursor-pointer transition-all duration-200 border"
          :class="selectedTaskId === task.id
            ? 'bg-gradient-to-r from-pink-500/20 to-orange-400/10 border-white/25 shadow-glow-cyan'
            : 'border-white/15 hover:bg-white/10 hover:border-white/20'"
        >
          <div class="flex gap-3">
            <div class="w-16 h-16 rounded-xl flex-shrink-0 overflow-hidden bg-white/5 border border-white/10 flex items-center justify-center">
              <img
                v-if="displayUrl(task)"
                :src="displayUrl(task)"
                class="w-full h-full object-cover cursor-zoom-in hover:opacity-90 transition-opacity"
                @click.stop="openLightbox(displayUrl(task))"
              />
              <div v-else-if="task.status === 'processing'" class="w-6 h-6 border-2 border-fuchsia-400/30 border-t-fuchsia-400 rounded-full animate-spin"></div>
              <span v-else class="text-xs text-white/40">{{ statusLabel(task.status) }}</span>
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <span class="text-xs text-white/40 font-mono">#{{ task._optimistic ? '...' : task.id }}</span>
                <span :class="statusBadgeClass(task.status)">{{ statusLabel(task.status) }}</span>
              </div>
              <p class="text-sm text-white/90 truncate font-medium mt-1">{{ task.prompt }}</p>
              <div class="flex items-center gap-1.5 mt-0.5 flex-wrap">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border"
                  :class="modeTagClass(task.mode)"
                >{{ modeLabel(task.mode) }}</span>
                <span class="text-xs text-white/40">{{ formatSizeLabel(task.size) }}</span>
              </div>
              <p v-if="task.status === 'failed'" class="text-xs text-rose-300/80 mt-1.5 truncate">
                {{ taskErrorMessage(task) }}
              </p>
              <button
                v-if="canRefreshTaskStatus(task, 'image')"
                @click.stop="refreshTaskStatus(task)"
                :disabled="refreshingTaskId === task.id"
                class="mt-2 text-xs px-2.5 py-1 rounded-lg border border-cyan-400/30 text-cyan-200 hover:bg-cyan-400/10 transition-colors disabled:opacity-50"
              >{{ refreshingTaskId === task.id ? '刷新中...' : '刷新状态' }}</button>
            </div>

            <button
              @click="deleteTask(task, $event)"
              class="w-8 h-8 rounded-xl flex items-center justify-center text-white/50 hover:bg-rose-500/30 hover:text-rose-300 transition-all flex-shrink-0 self-center"
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
          <div class="text-4xl mb-3">🎨</div>
          <p class="text-sm">暂无生成记录</p>
          <p class="text-xs mt-1">填写参数后点击生成</p>
        </div>
      </div>
    </div>

    <!-- Main area -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <div class="flex-1 overflow-y-auto p-6">
        <div class="max-w-5xl mx-auto space-y-6">
          <div>
            <h2 class="text-2xl font-extrabold bg-gradient-to-r from-pink-300 via-fuchsia-300 to-orange-300 bg-clip-text text-transparent">
              图片生成
            </h2>
            <p class="text-white/50 text-sm mt-1">文生图 · 单图编辑 · 多图合成</p>
          </div>

          <div
            v-if="!keyStatusLoading && !hasActiveKey"
            class="glass-card border border-amber-400/30 bg-amber-400/10 py-3 px-4"
          >
            <p class="text-sm text-amber-100/90">
              尚未配置 Agnes AI API Key，无法生成图片。请前往
              <router-link to="/settings" class="text-cyan-300 hover:underline">设置</router-link>
              添加并启用 Key。
            </p>
          </div>

          <div
            v-if="!keyStatusLoading && !hasQiniuConfig"
            class="glass-card border border-sky-400/25 bg-sky-400/10 py-3 px-4"
          >
            <p class="text-sm text-sky-100/90">
              未配置七牛云对象存储：当前可使用<strong class="font-semibold text-white/90">文生图</strong>；单图编辑、多图合成需上传参考图，暂不可用。生成结果使用 Agnes 临时链接，可能无法长期访问。
              <router-link to="/settings#storage" class="text-cyan-300 hover:underline ml-1">查看配置说明</router-link>
            </p>
          </div>

          <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <!-- Form -->
            <div ref="formCardRef" class="glass-card space-y-4">
              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">生成模式</label>
                <div class="grid grid-cols-3 gap-2">
                  <button
                    v-for="m in modes"
                    :key="m.id"
                    @click="selectMode(m.id)"
                    class="px-3 py-2.5 rounded-2xl text-sm font-medium transition-all duration-200 border"
                    :class="form.mode === m.id
                      ? 'border-fuchsia-400/50 bg-gradient-to-r from-fuchsia-500/25 to-pink-400/15 text-white shadow-glow-cyan'
                      : 'border-white/10 text-white/50 hover:border-white/25 hover:bg-white/5'"
                  >{{ m.name }}</button>
                </div>
                <p
                  v-if="!keyStatusLoading && !hasQiniuConfig && currentModeNeedsQiniu"
                  class="text-xs text-amber-200/90 mt-2 glass px-3 py-2 rounded-xl border border-amber-400/25"
                >
                  此模式需上传参考图，请先配置七牛云对象存储。
                  <router-link to="/settings#storage" class="text-cyan-300 hover:underline">查看说明</router-link>
                </p>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">模型</label>
                <select v-model="form.model" class="select-field text-sm">
                  <option v-for="m in meta.models" :key="m.id" :value="m.id">{{ m.name }}</option>
                </select>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">尺寸</label>
                <select v-model="form.size" class="select-field text-sm">
                  <option v-for="s in meta.sizes" :key="s" :value="s">{{ formatSizeLabel(s) }}</option>
                </select>
              </div>

              <div>
                <label class="text-sm text-white/60 mb-2 block font-medium">提示词</label>
                <textarea v-model="form.prompt" rows="3" class="input-field text-sm" placeholder="描述你想生成的图片内容..."></textarea>
              </div>

              <div v-if="form.mode !== 'text2img'">
                <label class="text-sm text-white/60 mb-2 block font-medium">
                  {{ form.mode === 'img2img' ? '参考图' : '输入图片' }}
                </label>
                <div class="flex flex-wrap gap-2 mb-2">
                  <div v-for="(item, i) in inputImages" :key="i" class="relative group">
                    <img :src="item.preview" class="w-20 h-20 object-cover rounded-2xl border border-white/20" />
                    <button @click="removeInputImage(i)" class="absolute -top-1 -right-1 w-6 h-6 bg-rose-500 rounded-full text-xs opacity-0 group-hover:opacity-100 shadow-lg">✕</button>
                  </div>
                </div>
                <label
                  class="btn-secondary inline-flex items-center gap-2 text-sm"
                  :class="!hasQiniuConfig ? 'opacity-50 cursor-not-allowed pointer-events-none' : 'cursor-pointer'"
                >
                  <input
                    type="file"
                    accept="image/*"
                    :multiple="form.mode === 'multi_img'"
                    class="hidden"
                    @change="handleFileSelect"
                  />
                  {{
                    form.mode === 'img2img'
                      ? (inputImages.length ? '更换参考图' : '选择参考图')
                      : '+ 选择图片'
                  }}
                </label>
                <p v-if="form.mode === 'img2img'" class="text-xs text-white/40 mt-2">仅支持一张参考图，选择新图将替换当前参考图；提交任务时才会上传</p>
              </div>

              <p v-if="error" class="text-rose-300 text-sm glass px-4 py-2 rounded-2xl border border-rose-400/30">{{ error }}</p>

              <button @click="generate" :disabled="generating" class="btn-primary w-full py-3 text-base">
                {{
                  generateStep === 'uploading'
                    ? '上传并生成中...'
                    : generating
                      ? '生成中...'
                      : '✨ 开始生成'
                }}
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

                <div v-if="selectedTask.status === 'processing'" class="flex-1 flex flex-col">
                  <div class="flex-1 flex flex-col items-center justify-center">
                    <div class="w-16 h-16 rounded-full border-4 border-fuchsia-400/30 border-t-fuchsia-400 animate-spin"></div>
                    <p class="text-white/50 mt-5 text-sm">图片生成中，请稍候...</p>
                    <button
                      v-if="canRefreshTaskStatus(selectedTask, 'image')"
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
                        class="w-20 h-20 object-cover rounded-xl border border-white/20 cursor-zoom-in hover:border-fuchsia-400/40 transition-colors"
                        @click="openLightbox(url)"
                      />
                    </div>
                  </div>
                </div>

                <div v-else-if="displayUrl(selectedTask)" class="flex-1">
                  <p class="text-xs text-white/50 mb-2 font-medium">生成结果</p>
                  <img
                    :src="displayUrl(selectedTask)"
                    class="w-full rounded-2xl border border-white/15 shadow-glow object-contain max-h-[360px] bg-black/20 cursor-zoom-in hover:opacity-90 transition-opacity"
                    @click="openLightbox(displayUrl(selectedTask))"
                  />
                  <div class="mt-3 text-xs text-white/50 flex flex-wrap gap-4">
                    <span>{{ formatSizeLabel(selectedTask.size) }}</span>
                    <span v-if="selectedTask.duration_ms">耗时: {{ selectedTask.duration_ms }}ms</span>
                    <span v-if="selectedTask.qiniu_url" class="text-emerald-300">✓ 已存储至七牛云</span>
                  </div>
                  <p v-if="selectedTask.revised_prompt" class="mt-3 text-xs text-white/40 leading-relaxed">
                    优化提示词: {{ selectedTask.revised_prompt }}
                  </p>
                  <div v-if="inputImagesOf(selectedTask).length" class="mt-4">
                    <p class="text-xs text-white/50 mb-2 font-medium">参考图</p>
                    <div class="flex flex-wrap gap-2">
                      <img
                        v-for="(url, i) in inputImagesOf(selectedTask)"
                        :key="i"
                        :src="url"
                        class="w-20 h-20 object-cover rounded-xl border border-white/20 cursor-zoom-in hover:border-fuchsia-400/40 transition-colors"
                        @click="openLightbox(url)"
                      />
                    </div>
                  </div>
                </div>

                <div v-else-if="selectedTask.status === 'failed'" class="glass px-4 py-3 rounded-2xl border border-rose-400/30">
                  <p class="text-rose-300 text-sm whitespace-pre-wrap break-words">{{ taskErrorMessage(selectedTask) }}</p>
                  <button
                    v-if="canRefreshTaskStatus(selectedTask, 'image')"
                    @click.stop="refreshTaskStatus(selectedTask)"
                    :disabled="refreshingTaskId === selectedTask.id"
                    class="btn-primary mt-3 px-4 py-2 text-sm"
                  >{{ refreshingTaskId === selectedTask.id ? '刷新中...' : '手动刷新状态' }}</button>
                  <p v-if="canRefreshTaskStatus(selectedTask, 'image')" class="text-xs text-white/40 mt-2">
                    若因限流导致状态未更新，可点击刷新重新获取结果
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
                      <span class="text-white/40 text-xs">提示词</span>
                      <p class="text-white/80 mt-0.5 leading-relaxed">{{ selectedTask.prompt || '—' }}</p>
                    </div>
                    <div v-if="selectedTask.revised_prompt">
                      <span class="text-white/40 text-xs">优化提示词</span>
                      <p class="text-white/60 mt-0.5 leading-relaxed">{{ selectedTask.revised_prompt }}</p>
                    </div>
                    <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs pt-1">
                      <div><span class="text-white/40">模式</span> <span class="text-white/70">{{ modeLabel(selectedTask.mode) }}</span></div>
                      <div><span class="text-white/40">尺寸</span> <span class="text-white/70">{{ formatSizeLabel(selectedTask.size) }}</span></div>
                      <div class="col-span-2"><span class="text-white/40">模型</span> <span class="text-white/70">{{ selectedTask.model || '—' }}</span></div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="flex-1 flex flex-col items-center justify-center text-white/40">
                <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-pink-400/30 to-orange-400/30 flex items-center justify-center text-4xl mb-4 border border-white/20 animate-float">
                  🎨
                </div>
                <p>选择左侧记录或创建新任务</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <Teleport to="body">
    <Transition name="lightbox">
      <div
        v-if="lightboxUrl"
        class="fixed inset-0 z-[9998] flex items-center justify-center p-4 md:p-8"
        @click="closeLightbox"
      >
        <div class="absolute inset-0 bg-black/85 backdrop-blur-sm"></div>
        <button
          class="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 text-white/80 hover:bg-white/20 hover:text-white transition-colors z-10"
          @click="closeLightbox"
        >✕</button>
        <img
          :src="lightboxUrl"
          class="relative max-w-full max-h-full object-contain rounded-lg shadow-2xl"
          @click.stop
        />
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity 0.2s ease;
}
.lightbox-enter-active img,
.lightbox-leave-active img {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}
.lightbox-enter-from img,
.lightbox-leave-to img {
  transform: scale(0.95);
  opacity: 0;
}
</style>
