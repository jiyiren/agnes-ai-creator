export function estimateTokens(text) {
  if (!text) return 0
  let cjk = 0
  for (const c of text) {
    if (c >= '\u4e00' && c <= '\u9fff') cjk++
  }
  const other = text.length - cjk
  return Math.max(1, Math.round(cjk * 1.2 + other / 4))
}

export function userTokenCount(msg) {
  if (!msg) return 0
  return msg.total_tokens || estimateTokens(msg.content)
}
