export const apiBase = '/api'

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { headers: customHeaders, ...restOptions } = options
  const response = await fetch(`${apiBase}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(customHeaders || {})
    },
    ...restOptions
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}
