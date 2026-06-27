import { ref, reactive } from 'vue'

const state = reactive({
  visible: false,
  type: 'confirm',
  title: '',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  confirmVariant: 'primary',
})

let resolvePromise = null

export function useDialog() {
  function confirm(options) {
    const opts = typeof options === 'string' ? { message: options } : options
    Object.assign(state, {
      visible: true,
      type: 'confirm',
      title: opts.title || '确认操作',
      message: opts.message || '',
      confirmText: opts.confirmText || '确定',
      cancelText: opts.cancelText || '取消',
      confirmVariant: opts.confirmVariant || 'primary',
    })
    return new Promise((resolve) => {
      resolvePromise = resolve
    })
  }

  function alert(options) {
    const opts = typeof options === 'string' ? { message: options } : options
    Object.assign(state, {
      visible: true,
      type: 'alert',
      title: opts.title || '提示',
      message: opts.message || '',
      confirmText: opts.confirmText || '知道了',
      cancelText: '',
      confirmVariant: opts.confirmVariant || 'primary',
    })
    return new Promise((resolve) => {
      resolvePromise = resolve
    })
  }

  function handleConfirm() {
    state.visible = false
    resolvePromise?.(true)
    resolvePromise = null
  }

  function handleCancel() {
    state.visible = false
    resolvePromise?.(false)
    resolvePromise = null
  }

  return { state, confirm, alert, handleConfirm, handleCancel }
}
