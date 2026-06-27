<script setup>
import { ref, onMounted } from 'vue'
import { settingsApi } from '../api'
import { useDialog } from '../composables/useDialog'

const { confirm, alert } = useDialog()

const keys = ref([])
const status = ref({ has_active_key: false, key_count: 0, agnes_base_url: '', default_agnes_base_url: '' })
const loading = ref(false)
const saving = ref(false)
const savingBaseUrl = ref(false)

const baseUrlForm = ref('')
const defaultBaseUrl = ref('https://apihub.agnes-ai.com')

const form = ref({
  name: '',
  api_key: '',
  activate: true,
})

const editingId = ref(null)
const editForm = ref({ name: '', api_key: '' })

async function loadKeys() {
  loading.value = true
  try {
    const [statusData, keysData] = await Promise.all([
      settingsApi.getStatus(),
      settingsApi.listApiKeys(),
    ])
    status.value = statusData
    keys.value = keysData.items
    baseUrlForm.value = statusData.agnes_base_url || ''
    defaultBaseUrl.value = statusData.default_agnes_base_url || 'https://apihub.agnes-ai.com'
  } catch (e) {
    await alert({ title: '加载失败', message: e.message })
  } finally {
    loading.value = false
  }
}

async function handleSaveBaseUrl() {
  const url = baseUrlForm.value.trim()
  if (!url) {
    await alert({ title: '提示', message: '请填写 API Base URL' })
    return
  }
  savingBaseUrl.value = true
  try {
    const data = await settingsApi.updateBaseUrl(url)
    baseUrlForm.value = data.base_url
    status.value.agnes_base_url = data.base_url
    await alert({ title: '已保存', message: 'API Base URL 已更新' })
  } catch (e) {
    await alert({ title: '保存失败', message: e.message })
  } finally {
    savingBaseUrl.value = false
  }
}

function resetBaseUrl() {
  baseUrlForm.value = defaultBaseUrl.value
}

async function handleCreate() {
  const name = form.value.name.trim()
  const apiKey = form.value.api_key.trim()
  if (!name || !apiKey) {
    await alert({ title: '提示', message: '请填写名称和 API Key' })
    return
  }
  saving.value = true
  try {
    await settingsApi.createApiKey({
      name,
      api_key: apiKey,
      activate: form.value.activate,
    })
    form.value = { name: '', api_key: '', activate: true }
    await loadKeys()
  } catch (e) {
    await alert({ title: '添加失败', message: e.message })
  } finally {
    saving.value = false
  }
}

async function handleActivate(id) {
  try {
    await settingsApi.activateApiKey(id)
    await loadKeys()
  } catch (e) {
    await alert({ title: '启用失败', message: e.message })
  }
}

async function handleDelete(item) {
  const ok = await confirm({
    title: '删除 API Key',
    message: `确定删除「${item.name}」吗？此操作不可恢复。`,
    confirmText: '删除',
    confirmVariant: 'danger',
  })
  if (!ok) return
  try {
    await settingsApi.deleteApiKey(item.id)
    await loadKeys()
  } catch (e) {
    await alert({ title: '删除失败', message: e.message })
  }
}

function startEdit(item) {
  editingId.value = item.id
  editForm.value = { name: item.name, api_key: '' }
}

function cancelEdit() {
  editingId.value = null
  editForm.value = { name: '', api_key: '' }
}

async function handleSaveEdit(id) {
  const payload = {}
  const name = editForm.value.name.trim()
  const apiKey = editForm.value.api_key.trim()
  if (!name) {
    await alert({ title: '提示', message: '名称不能为空' })
    return
  }
  payload.name = name
  if (apiKey) payload.api_key = apiKey
  try {
    await settingsApi.updateApiKey(id, payload)
    cancelEdit()
    await loadKeys()
  } catch (e) {
    await alert({ title: '保存失败', message: e.message })
  }
}

onMounted(loadKeys)
</script>

<template>
  <div class="h-full flex flex-col overflow-hidden">
    <header class="flex-shrink-0 px-8 py-6 border-b border-white/10">
      <h2 class="text-2xl font-bold bg-gradient-to-r from-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">
        设置
      </h2>
      <p class="text-sm text-white/50 mt-1">管理 Agnes AI 连接配置，包括 API 地址与 API Key</p>
    </header>

    <div class="flex-1 overflow-y-auto p-8 space-y-8">
      <!-- 状态提示 -->
      <div
        v-if="!loading && !status.has_active_key"
        class="glass-card border border-amber-400/30 bg-amber-400/10"
      >
        <div class="flex items-start gap-3">
          <span class="text-2xl">⚠️</span>
          <div>
            <p class="font-semibold text-amber-200">尚未启用 API Key</p>
            <p class="text-sm text-white/60 mt-1">
              请添加至少一个 API Key 并启用，否则无法使用对话、图片和视频生成功能。
              可在
              <a
                href="https://platform.agnes-ai.com/"
                target="_blank"
                rel="noopener noreferrer"
                class="text-cyan-300 hover:underline"
              >Agnes AI 平台</a>
              免费申请。
            </p>
          </div>
        </div>
      </div>

      <!-- API Base URL -->
      <section class="glass-card">
        <h3 class="text-lg font-bold text-white mb-1">API Base URL</h3>
        <p class="text-sm text-white/50 mb-4">
          Agnes AI 接口地址，默认为
          <code class="text-cyan-300/90">{{ defaultBaseUrl }}</code>
        </p>
        <div class="flex flex-col sm:flex-row gap-3">
          <input
            v-model="baseUrlForm"
            type="url"
            class="input-field flex-1"
            placeholder="https://apihub.agnes-ai.com"
          />
          <div class="flex gap-2 flex-shrink-0">
            <button class="btn-secondary" @click="resetBaseUrl">恢复默认</button>
            <button
              class="btn-primary"
              :disabled="savingBaseUrl"
              @click="handleSaveBaseUrl"
            >
              {{ savingBaseUrl ? '保存中…' : '保存' }}
            </button>
          </div>
        </div>
      </section>

      <!-- 添加 Key -->
      <section class="glass-card">
        <h3 class="text-lg font-bold text-white mb-4">添加 API Key</h3>
        <div class="grid gap-4 md:grid-cols-2">
          <div>
            <label class="block text-xs text-white/50 mb-1.5">名称</label>
            <input
              v-model="form.name"
              type="text"
              class="input-field"
              placeholder="例如：主账号、备用账号"
            />
          </div>
          <div>
            <label class="block text-xs text-white/50 mb-1.5">API Key</label>
            <input
              v-model="form.api_key"
              type="password"
              class="input-field"
              placeholder="粘贴你的 Agnes AI API Key"
              autocomplete="off"
            />
          </div>
        </div>
        <div class="flex items-center justify-between mt-4">
          <label class="flex items-center gap-2 text-sm text-white/70 cursor-pointer">
            <input
              v-model="form.activate"
              type="checkbox"
              class="rounded border-white/20 bg-white/10 text-fuchsia-500 focus:ring-fuchsia-400/50"
            />
            添加后立即启用
          </label>
          <button
            class="btn-primary"
            :disabled="saving"
            @click="handleCreate"
          >
            {{ saving ? '添加中…' : '添加 Key' }}
          </button>
        </div>
      </section>

      <!-- Key 列表 -->
      <section class="glass-card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-white">已配置的 Key</h3>
          <span class="text-xs text-white/40">{{ keys.length }} 个</span>
        </div>

        <div v-if="loading" class="text-center py-12 text-white/40">加载中…</div>

        <div v-else-if="keys.length === 0" class="text-center py-12 text-white/40">
          暂无 API Key，请先添加
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="item in keys"
            :key="item.id"
            class="rounded-2xl border p-4 transition-all duration-200"
            :class="item.is_active
              ? 'border-emerald-400/40 bg-emerald-400/10'
              : 'border-white/10 bg-white/[0.04]'"
          >
            <template v-if="editingId === item.id">
              <div class="grid gap-3 md:grid-cols-2">
                <div>
                  <label class="block text-xs text-white/50 mb-1">名称</label>
                  <input v-model="editForm.name" type="text" class="input-field" />
                </div>
                <div>
                  <label class="block text-xs text-white/50 mb-1">新 API Key（留空则不修改）</label>
                  <input
                    v-model="editForm.api_key"
                    type="password"
                    class="input-field"
                    placeholder="留空保持原 Key 不变"
                    autocomplete="off"
                  />
                </div>
              </div>
              <div class="flex justify-end gap-2 mt-3">
                <button class="btn-ghost" @click="cancelEdit">取消</button>
                <button class="btn-primary" @click="handleSaveEdit(item.id)">保存</button>
              </div>
            </template>

            <template v-else>
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-semibold text-white">{{ item.name }}</span>
                    <span v-if="item.is_active" class="badge-completed">使用中</span>
                  </div>
                  <p class="text-sm text-white/50 font-mono mt-1">{{ item.key_masked }}</p>
                  <p class="text-xs text-white/30 mt-2">创建于 {{ item.created_at }}</p>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <button
                    v-if="!item.is_active"
                    class="btn-secondary text-sm py-2 px-4"
                    @click="handleActivate(item.id)"
                  >
                    启用
                  </button>
                  <button class="btn-ghost text-sm" @click="startEdit(item)">编辑</button>
                  <button
                    class="btn-ghost text-sm text-rose-300 hover:text-rose-200"
                    @click="handleDelete(item)"
                  >
                    删除
                  </button>
                </div>
              </div>
            </template>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
