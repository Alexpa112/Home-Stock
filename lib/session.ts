import { auth } from '@/lib/api'

export async function logoutAndRedirect() {
  await auth.logout()
  window.location.href = '/'
}
