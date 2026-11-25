export function repoName(url: string): string {
  return url.replace('https://github.com/', '')
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
