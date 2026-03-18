import { useState, useEffect, useCallback } from 'react'

const POLL_MS = 10_000

function usePoll(url, interval = POLL_MS) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const doFetch = useCallback(async () => {
    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setData(await res.json())
      setError(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [url])

  useEffect(() => {
    doFetch()
    const id = setInterval(doFetch, interval)
    return () => clearInterval(id)
  }, [doFetch, interval])

  return { data, loading, error, refresh: doFetch }
}

export function useCurrentData() {
  return usePoll('/api/current')
}

export function useHistory(limit = 200) {
  return usePoll(`/api/history?limit=${limit}`)
}

export function useMemories() {
  return usePoll('/api/memories', 30_000)
}

export function useSummary() {
  // Summaries are LLM-generated — fetch once on mount, manual refresh only.
  // The backend caches for 30 min so forced refreshes are cheap after the first call.
  return usePoll('/api/summary', 1_800_000)
}

export async function sendChatMessage(message) {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
