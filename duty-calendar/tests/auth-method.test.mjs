import { test } from 'node:test'
import assert from 'node:assert/strict'
import { isPasswordSession } from '../src/lib/auth-method.ts'

test('メール・パスワードのセッションは継続できる', () => {
  assert.equal(isPasswordSession([{ method: 'password', timestamp: 1 }]), true)
  assert.equal(isPasswordSession(['password']), true)
})

test('Google によるセッションは継続できない', () => {
  assert.equal(isPasswordSession([{ method: 'oauth', timestamp: 1 }]), false)
  assert.equal(isPasswordSession(['oauth']), false)
})

test('MFA を追加してもパスワードの認証履歴があれば継続できる', () => {
  assert.equal(isPasswordSession([{ method: 'password' }, { method: 'totp' }]), true)
  assert.equal(isPasswordSession([{ method: 'oauth' }, { method: 'totp' }]), false)
})

test('認証方法が不明・不正なら拒否する', () => {
  for (const methods of [[], [null], [{}], ['google'], [{ provider: 'password' }]]) {
    assert.equal(isPasswordSession(methods), false)
  }
})
