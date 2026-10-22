// 判定するのは今回のセッションの認証方法。Google と連携済みの利用者も
// パスワードでログインしていれば利用できる。
export function isPasswordSession(methods: readonly unknown[]): boolean {
  return methods.some((entry) =>
    typeof entry === 'object' && entry !== null && 'method' in entry
      ? entry.method === 'password'
      : entry === 'password'
  )
}
