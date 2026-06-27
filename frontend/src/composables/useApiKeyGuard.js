import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { settingsApi } from '../api'
import { useDialog } from './useDialog'

export const NO_API_KEY_TITLE = '无法操作'
export const NO_API_KEY_MESSAGE =
  '尚未配置 Agnes AI API Key，无法执行此操作。请前往「设置」页面添加并启用 API Key。'

export const NO_QINIU_TITLE = '需要对象存储'
export const NO_QINIU_MESSAGE =
  '尚未配置七牛云对象存储，无法上传参考图片。请在 backend/.env 中配置 QINIU_ACCESS_KEY、QINIU_SECRET_KEY、QINIU_BUCKET、QINIU_DOMAIN 后重启后端。详细说明请见「设置」页面。'

export function imageModeNeedsQiniu(mode) {
  return mode !== 'text2img'
}

export function videoModeNeedsQiniu(mode) {
  return mode !== 'text2video'
}

export function useApiKeyGuard() {
  const router = useRouter()
  const { confirm } = useDialog()

  const hasActiveKey = ref(true)
  const hasQiniuConfig = ref(true)
  const keyStatusLoading = ref(true)

  async function refreshKeyStatus() {
    keyStatusLoading.value = true
    try {
      const status = await settingsApi.getStatus()
      hasActiveKey.value = status.has_active_key
      hasQiniuConfig.value = status.has_qiniu_config
    } catch {
      hasActiveKey.value = false
      hasQiniuConfig.value = false
    } finally {
      keyStatusLoading.value = false
    }
  }

  async function requireApiKey() {
    await refreshKeyStatus()
    if (hasActiveKey.value) return true

    const goSettings = await confirm({
      title: NO_API_KEY_TITLE,
      message: NO_API_KEY_MESSAGE,
      confirmText: '前往设置',
      cancelText: '取消',
      confirmVariant: 'primary',
    })
    if (goSettings) {
      await router.push('/settings')
    }
    return false
  }

  async function requireQiniuConfig() {
    await refreshKeyStatus()
    if (hasQiniuConfig.value) return true

    const goSettings = await confirm({
      title: NO_QINIU_TITLE,
      message: NO_QINIU_MESSAGE,
      confirmText: '查看说明',
      cancelText: '取消',
      confirmVariant: 'primary',
    })
    if (goSettings) {
      await router.push('/settings#storage')
    }
    return false
  }

  return {
    hasActiveKey,
    hasQiniuConfig,
    keyStatusLoading,
    refreshKeyStatus,
    requireApiKey,
    requireQiniuConfig,
  }
}
