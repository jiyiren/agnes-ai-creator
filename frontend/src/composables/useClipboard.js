import { ref } from 'vue'

export function useClipboard(resetMs = 2000) {
  const copiedKey = ref(null)

  async function copyText(text, key) {
    if (!text?.trim()) return false
    try {
      await navigator.clipboard.writeText(text)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    copiedKey.value = key
    setTimeout(() => {
      if (copiedKey.value === key) copiedKey.value = null
    }, resetMs)
    return true
  }

  function isCopied(key) {
    return copiedKey.value === key
  }

  return { copyText, isCopied }
}
