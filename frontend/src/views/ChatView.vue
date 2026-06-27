<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chatApi } from '../api'
import { renderMarkdown } from '../utils/markdown'
import { userTokenCount } from '../utils/tokens'
import { useDialog } from '../composables/useDialog'
import { useClipboard } from '../composables/useClipboard'
import { useApiKeyGuard } from '../composables/useApiKeyGuard'
import TrashIcon from '../components/TrashIcon.vue'

const route = useRoute()
const router = useRouter()
const { confirm, alert } = useDialog()
const { copyText, isCopied } = useClipboard()
const { hasActiveKey, keyStatusLoading, refreshKeyStatus, requireApiKey } = useApiKeyGuard()

const conversations = ref([])
const currentConv = ref(null)
const messages = ref([])
const input = ref('')
const loading = ref(false)
const streaming = ref(false)
const streamContent = ref('')
const models = ref([])
const DEFAULT_MODEL = 'agnes-2.0-flash'
const selectedModel = ref(DEFAULT_MODEL)
const temperature = ref(0.7)
const maxTokens = ref(4096)
const enableThinking = ref(false)
const lastStats = ref(null)
const messagesEl = ref(null)
const editingConvId = ref(null)
const editingTitle = ref('')
const editInputRef = ref(null)
const streamingModel = ref(null)
const streamingStartedAt = ref(null)

function modelLabel(modelId) {
  if (!modelId) return '模型'
  return models.value.find(m => m.id === modelId)?.name || modelId
}

function senderName(msg) {
  if (msg.role === 'user') return '用户'
  return modelLabel(msg.model || currentConv.value?.model || selectedModel.value)
}

function formatDateTime(value) {
  if (!value) return ''
  const normalized = typeof value === 'string' && !value.includes('T')
    ? value.replace(' ', 'T')
    : value
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function nowISO() {
  return new Date().toISOString()
}

async function loadConversations() {
  conversations.value = await chatApi.listConversations()
}

async function loadConversation(id) {
  const data = await chatApi.getConversation(id)
  currentConv.value = data.conversation
  messages.value = data.messages
  selectedModel.value = data.conversation.model || DEFAULT_MODEL
  await scrollBottom()
}

async function onModelChange() {
  if (!currentConv.value?.id) return
  const prev = currentConv.value.model || DEFAULT_MODEL
  if (selectedModel.value === prev) return
  try {
    const updated = await chatApi.updateConversation(currentConv.value.id, { model: selectedModel.value })
    currentConv.value = { ...currentConv.value, model: updated.model }
    const idx = conversations.value.findIndex(c => c.id === updated.id)
    if (idx !== -1) conversations.value[idx] = { ...conversations.value[idx], model: updated.model }
  } catch (err) {
    selectedModel.value = prev
    await alert({ title: '模型切换失败', message: err.message, confirmVariant: 'danger' })
  }
}

async function newConversation() {
  const conv = await chatApi.createConversation({ title: '新对话', model: DEFAULT_MODEL })
  selectedModel.value = DEFAULT_MODEL
  await loadConversations()
  router.push(`/chat/${conv.id}`)
}

async function deleteConv(id, e) {
  e.stopPropagation()
  const ok = await confirm({
    title: '删除对话',
    message: '确定删除此对话？删除后无法恢复。',
    confirmText: '删除',
    cancelText: '取消',
    confirmVariant: 'danger',
  })
  if (!ok) return
  await chatApi.deleteConversation(id)
  await loadConversations()
  if (currentConv.value?.id === id) {
    currentConv.value = null
    messages.value = []
    router.push('/chat')
  }
}

function startRename(conv, e) {
  e?.stopPropagation()
  editingConvId.value = conv.id
  editingTitle.value = conv.title
  nextTick(() => editInputRef.value?.focus())
}

function cancelRename() {
  editingConvId.value = null
}

function isEditingInHeader(convId) {
  return editingConvId.value === convId && currentConv.value?.id === convId
}

function isEditingInSidebar(convId) {
  return editingConvId.value === convId && currentConv.value?.id !== convId
}

async function saveRename(convId) {
  const title = editingTitle.value.trim()
  const original = conversations.value.find(c => c.id === convId)?.title
  editingConvId.value = null
  if (!title || title === original) return

  try {
    const updated = await chatApi.updateConversation(convId, { title })
    const idx = conversations.value.findIndex(c => c.id === convId)
    if (idx !== -1) conversations.value[idx] = updated
    if (currentConv.value?.id === convId) {
      currentConv.value = { ...currentConv.value, title: updated.title }
    }
  } catch (err) {
    await alert({ title: '重命名失败', message: err.message, confirmVariant: 'danger' })
  }
}

async function selectConversation(conv) {
  if (editingConvId.value) cancelRename()
  if (currentConv.value?.id === conv.id) return
  await router.push(`/chat/${conv.id}`)
}

function scrollBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

function chatPayload() {
  return {
    model: selectedModel.value,
    temperature: temperature.value,
    max_tokens: maxTokens.value,
    enable_thinking: enableThinking.value,
  }
}

function beginStreaming(modelId) {
  loading.value = true
  streaming.value = true
  streamContent.value = ''
  streamingModel.value = modelId
  streamingStartedAt.value = nowISO()
  lastStats.value = null
}

function finishStreaming() {
  streaming.value = false
  loading.value = false
  streamContent.value = ''
  streamingModel.value = null
  streamingStartedAt.value = null
}

function handleStreamDone(stats) {
  lastStats.value = stats
  finishStreaming()
  loadConversations()
  loadConversation(currentConv.value.id).then(() => {
    if (currentConv.value) {
      selectedModel.value = currentConv.value.model || DEFAULT_MODEL
    }
  })
}

async function handleStreamError(err) {
  finishStreaming()
  await alert({
    title: '发送失败',
    message: typeof err === 'string' ? err : '消息发送失败，请稍后重试。',
    confirmVariant: 'danger',
  })
  if (currentConv.value?.id) {
    await loadConversation(currentConv.value.id)
  }
}

function startStream(apiCall, modelId) {
  beginStreaming(modelId)
  scrollBottom()
  apiCall(
    (chunk) => {
      streamContent.value += chunk
      scrollBottom()
    },
    handleStreamDone,
    handleStreamError,
  )
}

async function send() {
  if (!input.value.trim() || loading.value) return
  if (!(await requireApiKey())) return
  if (!currentConv.value) {
    const conv = await chatApi.createConversation({ title: input.value.slice(0, 30), model: selectedModel.value })
    currentConv.value = conv
    await loadConversations()
    await router.replace(`/chat/${conv.id}`)
  }

  const content = input.value.trim()
  input.value = ''
  submitContent(content)
}

function submitContent(content) {
  messages.value.push({ role: 'user', content, created_at: nowISO() })
  startStream(
    (onChunk, onDone, onError) => chatApi.sendMessageStream(
      currentConv.value.id,
      { content, ...chatPayload() },
      onChunk,
      onDone,
      onError,
    ),
    selectedModel.value,
  )
}

async function regenerateMessage(msg, index) {
  if (!msg?.id || loading.value || msg.role !== 'assistant') return
  if (!(await requireApiKey())) return
  const prevUser = [...messages.value.slice(0, index)].reverse().find(m => m.role === 'user')
  if (!prevUser) {
    await alert({ title: '无法重新生成', message: '找不到对应的用户提问。', confirmVariant: 'danger' })
    return
  }

  messages.value = messages.value.filter(m => m.id !== msg.id)
  const modelId = msg.model || selectedModel.value

  startStream(
    (onChunk, onDone, onError) => chatApi.regenerateStream(
      currentConv.value.id,
      msg.id,
      chatPayload(),
      onChunk,
      onDone,
      onError,
    ),
    modelId,
  )
}

async function deleteAssistantMessage(msg) {
  if (!msg?.id || loading.value || msg.role !== 'assistant') return
  const ok = await confirm({
    title: '删除回复',
    message: '确定删除这条模型回复？删除后无法恢复。',
    confirmText: '删除',
    cancelText: '取消',
    confirmVariant: 'danger',
  })
  if (!ok) return

  try {
    await chatApi.deleteMessage(currentConv.value.id, msg.id)
    await loadConversation(currentConv.value.id)
    loadConversations()
  } catch (err) {
    await alert({ title: '删除失败', message: err.message, confirmVariant: 'danger' })
  }
}

async function deleteUserMessage(msg) {
  if (!msg?.id || loading.value || msg.role !== 'user') return
  const ok = await confirm({
    title: '删除提问',
    message: '确定删除这条提问及其后的所有回复？删除后无法恢复。',
    confirmText: '删除',
    cancelText: '取消',
    confirmVariant: 'danger',
  })
  if (!ok) return

  try {
    await chatApi.deleteMessage(currentConv.value.id, msg.id)
    await loadConversation(currentConv.value.id)
    loadConversations()
  } catch (err) {
    await alert({ title: '删除失败', message: err.message, confirmVariant: 'danger' })
  }
}

async function regenerateUserMessage(msg) {
  if (!msg?.id || loading.value || msg.role !== 'user') return
  if (!(await requireApiKey())) return
  const content = msg.content
  try {
    await chatApi.deleteMessage(currentConv.value.id, msg.id)
    messages.value = messages.value.filter(m => m.id != null && m.id < msg.id)
    submitContent(content)
    loadConversations()
  } catch (err) {
    await alert({ title: '重新生成失败', message: err.message, confirmVariant: 'danger' })
    await loadConversation(currentConv.value.id)
  }
}

function messageCopyKey(msg, index) {
  return `${msg.role}-${msg.id ?? index}`
}

function formatDuration(ms) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

onMounted(async () => {
  await refreshKeyStatus()
  const data = await chatApi.getModels()
  models.value = data.models
  await loadConversations()
  if (route.params.id) {
    await loadConversation(Number(route.params.id))
  }
})

watch(() => route.params.id, async (id) => {
  if (loading.value || streaming.value) return
  if (id) await loadConversation(Number(id))
  else {
    currentConv.value = null
    messages.value = []
    selectedModel.value = DEFAULT_MODEL
  }
})
</script>

<template>
  <div class="flex h-full">
    <!-- Conversation list -->
    <div class="w-80 border-r border-white/10 flex flex-col bg-black/10">
      <div class="p-4 border-b border-white/10">
        <button @click="newConversation" class="btn-primary w-full flex items-center justify-center gap-2">
          <span class="text-lg">+</span> 新建对话
        </button>
      </div>
      <div class="flex-1 overflow-y-auto p-3 space-y-2">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          @click="selectConversation(conv)"
          class="group flex items-center justify-between px-4 py-3 rounded-2xl cursor-pointer transition-all duration-200 text-sm border"
          :class="currentConv?.id === conv.id
            ? 'bg-gradient-to-r from-fuchsia-500/20 to-cyan-400/10 border-white/25 text-white shadow-glow-cyan'
            : 'border-white/15 hover:bg-white/10 hover:border-white/20 text-white/70 hover:text-white'"
        >
          <div class="truncate flex-1 min-w-0">
            <template v-if="isEditingInSidebar(conv.id)">
              <input
                ref="editInputRef"
                v-model="editingTitle"
                @keydown.enter="saveRename(conv.id)"
                @keydown.esc="cancelRename"
                @blur="cancelRename"
                @click.stop
                class="input-field text-sm py-1.5 px-2.5 w-full"
              />
            </template>
            <template v-else>
              <p class="truncate font-semibold">{{ conv.title }}</p>
              <p class="text-xs text-white/40 mt-1">{{ conv.model }}</p>
            </template>
          </div>
          <div class="flex items-center gap-0.5 flex-shrink-0">
            <template v-if="editingConvId === conv.id">
              <button
                @mousedown.prevent
                @click.stop="saveRename(conv.id)"
                class="w-7 h-7 rounded-xl flex items-center justify-center text-emerald-400 hover:bg-emerald-500/20 hover:text-emerald-300 transition-all"
                title="保存"
              >✓</button>
              <button
                @mousedown.prevent
                @click.stop="cancelRename"
                class="w-7 h-7 rounded-xl flex items-center justify-center text-white/50 hover:bg-white/10 hover:text-white transition-all"
                title="取消"
              >✕</button>
            </template>
            <template v-else>
              <button
                @click="startRename(conv, $event)"
                class="opacity-0 group-hover:opacity-100 w-7 h-7 rounded-xl flex items-center justify-center text-white/50 hover:bg-white/10 hover:text-white transition-all"
                title="重命名"
              >✎</button>
              <button
                @click="deleteConv(conv.id, $event)"
                class="opacity-0 group-hover:opacity-100 w-7 h-7 rounded-xl flex items-center justify-center text-white/50 hover:bg-rose-500/30 hover:text-rose-300 transition-all"
                title="删除"
              ><TrashIcon /></button>
            </template>
          </div>
        </div>
        <p v-if="!conversations.length" class="text-center text-white/40 text-sm py-12">暂无对话，点击上方开始</p>
      </div>
    </div>

    <!-- Chat area -->
    <div class="flex-1 flex flex-col">
      <div
        v-if="!keyStatusLoading && !hasActiveKey"
        class="mx-6 mt-4 glass-card border border-amber-400/30 bg-amber-400/10 py-3 px-4"
      >
        <p class="text-sm text-amber-100/90">
          尚未配置 Agnes AI API Key，无法发送消息。请前往
          <router-link to="/settings" class="text-cyan-300 hover:underline">设置</router-link>
          添加并启用 Key。
        </p>
      </div>
      <!-- Header -->
      <div class="px-6 py-4 border-b border-white/10 flex items-center gap-4 flex-wrap bg-black/5">
        <div v-if="currentConv" class="flex items-center gap-2 min-w-0 max-w-[240px]">
          <template v-if="isEditingInHeader(currentConv.id)">
            <input
              ref="editInputRef"
              v-model="editingTitle"
              @keydown.enter="saveRename(currentConv.id)"
              @keydown.esc="cancelRename"
              @blur="cancelRename"
              class="input-field text-sm py-1.5 px-2.5 w-full"
            />
            <button
              @mousedown.prevent
              @click.stop="saveRename(currentConv.id)"
              class="btn-ghost text-xs px-2 py-1 text-emerald-400 hover:text-emerald-300 flex-shrink-0"
              title="保存"
            >✓</button>
            <button
              @mousedown.prevent
              @click.stop="cancelRename"
              class="btn-ghost text-xs px-2 py-1 text-white/50 hover:text-white flex-shrink-0"
              title="取消"
            >✕</button>
          </template>
          <template v-else>
            <span class="font-semibold text-white truncate">{{ currentConv.title }}</span>
            <button
              @click="startRename(currentConv)"
              class="btn-ghost text-xs px-2 py-1 text-white/50 hover:text-white flex-shrink-0"
              title="重命名"
            >✎</button>
          </template>
        </div>
        <select v-model="selectedModel" class="select-field w-auto text-sm" @change="onModelChange">
          <option v-for="m in models" :key="m.id" :value="m.id">
            {{ m.name }}{{ m.deprecated ? ' (已废弃)' : '' }}
          </option>
        </select>
        <label class="flex items-center gap-2 text-sm text-white/60 glass px-3 py-2 rounded-2xl">
          温度
          <input v-model.number="temperature" type="range" min="0" max="2" step="0.1" class="w-24 accent-fuchsia-500" />
          <span class="w-8 text-fuchsia-300 font-semibold">{{ temperature }}</span>
        </label>
        <label class="flex items-center gap-2 text-sm text-white/60 glass px-3 py-2 rounded-2xl cursor-pointer">
          <input v-model="enableThinking" type="checkbox" class="rounded accent-fuchsia-500" />
          Thinking 模式
        </label>
      </div>

      <!-- Messages -->
      <div ref="messagesEl" class="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        <div v-if="!messages.length && !streaming" class="flex flex-col items-center justify-center h-full text-white/50">
          <div class="w-20 h-20 rounded-3xl bg-gradient-to-br from-fuchsia-500/30 to-cyan-400/30 flex items-center justify-center text-4xl mb-5 border border-white/20 animate-float">
            💬
          </div>
          <p class="text-xl font-bold bg-gradient-to-r from-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">开始与 Agnes AI 对话</p>
          <p class="text-sm mt-2 text-white/40">支持多轮对话、流式输出、Token 统计</p>
        </div>

        <div
          v-for="(msg, i) in messages"
          :key="msg.id ?? i"
          class="flex gap-3 justify-start"
        >
          <div
            class="w-10 h-10 rounded-2xl flex-shrink-0 flex items-center justify-center border shadow-sm"
            :class="msg.role === 'user'
              ? 'bg-gradient-to-br from-fuchsia-500/90 to-violet-600/90 border-fuchsia-400/30'
              : 'bg-gradient-to-br from-cyan-500/80 to-fuchsia-500/80 border-cyan-400/30'"
            :title="senderName(msg)"
          >
            <svg v-if="msg.role === 'user'" class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
            </svg>
            <svg v-else class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73A2 2 0 0112 2zM7 14a1 1 0 100 2 1 1 0 000-2zm10 0a1 1 0 100 2 1 1 0 000-2z"/>
            </svg>
          </div>

          <div class="flex-1 min-w-0 max-w-4xl group/msg">
            <div class="flex items-center gap-2 mb-1.5 flex-wrap">
              <span class="text-sm font-semibold text-white">{{ senderName(msg) }}</span>
              <span class="text-xs text-white/40">{{ formatDateTime(msg.created_at) }}</span>
            </div>

            <div
              class="rounded-3xl px-5 py-4 text-sm leading-relaxed border border-white/20"
              :class="msg.role === 'user'
                ? 'bg-gradient-to-br from-fuchsia-500/25 to-violet-600/20 text-white'
                : 'glass text-white/90'"
            >
              <div v-if="msg.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
              <div v-else class="whitespace-pre-wrap">{{ msg.content }}</div>

              <div
                v-if="msg.role === 'user'"
                class="mt-3 pt-3 border-t border-white/10 text-xs text-white/50 flex items-center gap-3 flex-wrap"
              >
                <div class="flex gap-3 flex-wrap flex-1 min-w-0">
                  <span>📊 {{ userTokenCount(msg) }} tokens</span>
                </div>
                <div class="flex items-center gap-1 ml-auto flex-shrink-0">
                  <button
                    type="button"
                    @click="copyText(msg.content, messageCopyKey(msg, i))"
                    class="px-2 py-1 rounded-lg transition-colors"
                    :class="isCopied(messageCopyKey(msg, i))
                      ? 'text-emerald-300 bg-emerald-500/20'
                      : 'text-white/60 hover:text-white hover:bg-white/10'"
                  >{{ isCopied(messageCopyKey(msg, i)) ? '已复制' : '复制' }}</button>
                  <button
                    type="button"
                    @click="regenerateUserMessage(msg)"
                    :disabled="loading || !msg.id"
                    class="px-2 py-1 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >重新生成</button>
                  <button
                    type="button"
                    @click="deleteUserMessage(msg)"
                    :disabled="loading || !msg.id"
                    class="px-2 py-1 rounded-lg text-rose-300/80 hover:text-rose-200 hover:bg-rose-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >删除</button>
                </div>
              </div>

              <div
                v-if="msg.role === 'assistant'"
                class="mt-3 pt-3 border-t border-white/10 text-xs text-white/50 flex items-center gap-3 flex-wrap"
              >
                <div class="flex gap-3 flex-wrap flex-1 min-w-0">
                  <span v-if="msg.duration_ms">⏱ {{ formatDuration(msg.duration_ms) }}</span>
                  <span v-if="msg.total_tokens">📊 {{ msg.prompt_tokens }} + {{ msg.completion_tokens }} = {{ msg.total_tokens }} tokens</span>
                </div>
                <div class="flex items-center gap-1 ml-auto flex-shrink-0">
                  <button
                    type="button"
                    @click="copyText(msg.content, messageCopyKey(msg, i))"
                    class="px-2 py-1 rounded-lg transition-colors"
                    :class="isCopied(messageCopyKey(msg, i))
                      ? 'text-emerald-300 bg-emerald-500/20'
                      : 'text-white/60 hover:text-white hover:bg-white/10'"
                  >{{ isCopied(messageCopyKey(msg, i)) ? '已复制' : '复制' }}</button>
                  <button
                    type="button"
                    @click="regenerateMessage(msg, i)"
                    :disabled="loading"
                    class="px-2 py-1 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >重新生成</button>
                  <button
                    type="button"
                    @click="deleteAssistantMessage(msg)"
                    :disabled="loading"
                    class="px-2 py-1 rounded-lg text-rose-300/80 hover:text-rose-200 hover:bg-rose-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >删除</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Streaming -->
        <div v-if="streaming" class="flex gap-3 justify-start">
          <div
            class="w-10 h-10 rounded-2xl flex-shrink-0 flex items-center justify-center border shadow-sm bg-gradient-to-br from-cyan-500/80 to-fuchsia-500/80 border-cyan-400/30"
            :title="modelLabel(streamingModel)"
          >
            <svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73A2 2 0 0112 2zM7 14a1 1 0 100 2 1 1 0 000-2zm10 0a1 1 0 100 2 1 1 0 000-2z"/>
            </svg>
          </div>

          <div class="flex-1 min-w-0 max-w-4xl group/msg">
            <div class="flex items-center gap-2 mb-1.5 flex-wrap">
              <span class="text-sm font-semibold text-white">{{ modelLabel(streamingModel) }}</span>
              <span class="text-xs text-white/40">{{ formatDateTime(streamingStartedAt) }}</span>
              <span class="badge-progress text-[10px]">生成中</span>
            </div>

            <div class="glass rounded-3xl px-5 py-4 text-sm border border-white/20">
              <div v-if="streamContent" class="markdown-body" v-html="renderMarkdown(streamContent)"></div>
              <p v-else class="text-white/50">正在思考...</p>
              <span v-if="streamContent" class="inline-block w-2 h-4 bg-gradient-to-b from-fuchsia-400 to-cyan-400 animate-pulse ml-1 rounded-full align-middle"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="p-5 border-t border-white/10 bg-black/5">
        <div class="flex gap-3 max-w-4xl mx-auto">
          <textarea
            v-model="input"
            @keydown.enter.exact.prevent="send"
            rows="2"
            placeholder="输入消息，Enter 发送..."
            class="input-field flex-1 resize-none"
            :disabled="loading"
          ></textarea>
          <button @click="send" :disabled="loading || !input.trim()" class="btn-primary self-end px-8">
            {{ loading ? '生成中...' : '发送' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.markdown-body {
  @apply prose prose-invert prose-sm max-w-none;
  --tw-prose-bullets: rgb(165 243 252 / 0.95);
  --tw-prose-counters: rgb(165 243 252 / 0.95);
}

:deep(.markdown-body > :first-child) {
  @apply mt-0;
}

:deep(.markdown-body > :last-child) {
  @apply mb-0;
}

:deep(.markdown-body pre) {
  @apply bg-black/40 rounded-2xl p-4 overflow-x-auto border border-white/10 my-3;
}

:deep(.markdown-body pre code) {
  @apply bg-transparent p-0 text-cyan-200 text-xs leading-relaxed;
}

:deep(.markdown-body :not(pre) > code) {
  @apply bg-white/10 text-cyan-300 px-1.5 py-0.5 rounded-md text-xs font-mono;
}

:deep(.markdown-body a) {
  @apply text-fuchsia-300 underline decoration-fuchsia-400/40 hover:text-fuchsia-200;
}

:deep(.markdown-body blockquote) {
  @apply border-l-4 border-fuchsia-400/50 pl-4 text-white/70 italic;
}

:deep(.markdown-body table) {
  @apply w-full border-collapse my-3 text-xs;
}

:deep(.markdown-body th),
:deep(.markdown-body td) {
  @apply border border-white/15 px-3 py-2 text-left;
}

:deep(.markdown-body th) {
  @apply bg-white/10 font-semibold;
}

:deep(.markdown-body hr) {
  @apply border-white/15 my-4;
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  @apply my-2 pl-5 text-white/90;
}

:deep(.markdown-body li) {
  @apply text-white/90 pl-1;
}

:deep(.markdown-body li::marker) {
  color: rgb(165 243 252);
  font-weight: 600;
}

:deep(.markdown-body ol li::marker) {
  color: rgb(103 232 249);
  font-weight: 700;
}

:deep(.markdown-body h1),
:deep(.markdown-body h2),
:deep(.markdown-body h3),
:deep(.markdown-body h4) {
  @apply text-white font-bold mt-4 mb-2;
}

:deep(.markdown-body p) {
  @apply my-2 leading-relaxed;
}

:deep(.markdown-body strong) {
  @apply text-white font-semibold;
}
</style>
