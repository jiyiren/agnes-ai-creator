import { marked } from 'marked'

marked.setOptions({
  gfm: true,
  breaks: true,
})

/** Protect fenced/inline code from emphasis preprocessing. */
function preprocessEmphasis(text) {
  const placeholders = []
  let safe = text.replace(/(```[\s\S]*?```|`[^`\n]+`)/g, (match) => {
    placeholders.push(match)
    return `\x00CB${placeholders.length - 1}\x00`
  })

  // marked skips **...** when quotes/punctuation appear inside (common in LLM Chinese output)
  safe = safe.replace(/\*\*([^*\n]+?)\*\*/g, '<strong>$1</strong>')

  return safe.replace(/\x00CB(\d+)\x00/g, (_, index) => placeholders[Number(index)])
}

export function renderMarkdown(text) {
  if (!text) return ''
  try {
    return marked.parse(preprocessEmphasis(text))
  } catch {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
}
