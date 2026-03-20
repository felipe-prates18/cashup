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

export async function apiUpload<T>(
  path: string,
  body: FormData,
  options: Omit<RequestInit, 'body'> = {}
): Promise<T> {
  const { headers: customHeaders, ...restOptions } = options
  const response = await fetch(`${apiBase}${path}`, {
    method: 'POST',
    body,
    headers: {
      ...(customHeaders || {})
    },
    ...restOptions
  })
  if (!response.ok) {
    throw new Error(await response.text())
  }
  return response.json()
}
