'use client'

import { useEffect, useMemo, useState, useRef } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import { supabase, type Profile, type Doctor, type ShiftType, type Assignment } from '@/lib/supabase'

export default function Home() {
  const calendarRef = useRef<FullCalendar>(null)
  const [session, setSession] = useState(false)
  const [user, setUser] = useState<Profile | null>(null)
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [shiftTypes, setShiftTypes] = useState<ShiftType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  // 勤務医とログイン利用者は別名簿。外部勤務医に認証アカウントは作らない。
  const [doctorName, setDoctorName] = useState('')
  const [addingDoctor, setAddingDoctor] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState({ doctorId: '', shiftTypeId: '', dutyDate: '', note: '' })
  const [submitting, setSubmitting] = useState(false)

  // カレンダー表示月
  const [displayMonth, setDisplayMonth] = useState(() => new Date().toISOString().slice(0, 7))

  // 登録済みかつ有効な医師だけを通す。未登録の Google アカウントはここでサインアウトする
  const startSession = async (userId: string) => {
    const { data: profileData } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', userId)
      .maybeSingle()

    if (!profileData || !profileData.is_active) {
      await supabase.auth.signOut()
      setSession(false)
      setLoading(false)
      setError(
        profileData
          ? 'このアカウントは無効化されています。管理者に連絡してください。'
          : 'このアカウントは登録されていません。登録済みのメールアドレスの Google アカウントでログインしてください。'
      )
      return
    }

    setError('')
    setUser(profileData)
    setSession(true)
    await fetchData()
  }

  // displayMonth が変わったときにカレンダーも同期
  useEffect(() => {
    if (calendarRef.current) {
      const [year, month] = displayMonth.split('-')
      const date = new Date(parseInt(year), parseInt(month) - 1, 1)
      calendarRef.current.getApi().gotoDate(date)
    }
  }, [displayMonth])

  const fetchData = async () => {
    setLoading(true)
    try {
      const { data: doctorsData, error: doctorsError } = await supabase
        .from('doctors')
        .select('id, full_name, is_active, profile_id')
        .eq('is_active', true)
        .order('full_name')
      if (doctorsError) throw doctorsError

      setDoctors(doctorsData || [])

      // シフト種別
      const { data: shiftsData, error: shiftsError } = await supabase
        .from('shift_types')
        .select('*')
      if (shiftsError) throw shiftsError

      setShiftTypes(shiftsData || [])

      // 割り当て
      const { data: assignmentsData, error: assignmentsError } = await supabase
        .from('assignments')
        .select('id, duty_doctor_id, shift_type_id, duty_date, note, doctors!assignments_duty_doctor_id_fkey(full_name), shift_types(name, color)')
        .order('duty_date', { ascending: true })
      if (assignmentsError) throw assignmentsError

      // 未生成のDB型では関連テーブルが配列と推論されるが、FKは多対一。
      setAssignments((assignmentsData || []) as unknown as Assignment[])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  // ログイン処理
  useEffect(() => {
    const checkSession = async () => {
      // Google ログインが Supabase 側で拒否された場合 (新規登録無効など) は URL にエラーが付いて戻る
      const params = new URLSearchParams(window.location.search + window.location.hash.replace(/^#/, '&'))
      const redirectError = params.get('error_description') || params.get('error')
      if (redirectError) {
        setError(`ログインできませんでした: ${redirectError}`)
        window.history.replaceState(window.history.state, '', window.location.pathname)
      }

      // Google ログインの戻りでは、getSession が URL の code をセッションに交換してから返る
      const { data } = await supabase.auth.getSession()
      if (!data.session) {
        setSession(false)
        setLoading(false)
        return
      }

      await startSession(data.session.user.id)
    }

    checkSession()
    // 初回表示時だけ実行する
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ログイン
  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const email = (e.currentTarget.elements.namedItem('email') as HTMLInputElement).value
    const password = (e.currentTarget.elements.namedItem('password') as HTMLInputElement).value

    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) {
      setError(error.message)
      return
    }

    await startSession(data.user.id)
  }

  // Google ログイン (Android Chrome を含むブラウザ向けの Web OAuth フロー)
  const handleGoogleLogin = async () => {
    setError('')
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/`,
        queryParams: { prompt: 'select_account' },
      },
    })
    if (error) setError(error.message)
  }

  const handleAddDoctor = async (e: React.FormEvent) => {
    e.preventDefault()
    const name = doctorName.trim()
    if (!name) return
    if (doctors.some((doctor) => doctor.full_name === name)) {
      setError('同じ名前の勤務医が既に登録されています。')
      return
    }
    setAddingDoctor(true)
    setError('')
    const { error: insertError } = await supabase.from('doctors').insert({ full_name: name })
    if (insertError) {
      setError(insertError.message)
    } else {
      setDoctorName('')
      await fetchData()
    }
    setAddingDoctor(false)
  }

  const handleSaveAssignment = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')

    const values = {
      duty_doctor_id: formData.doctorId,
      shift_type_id: parseInt(formData.shiftTypeId),
      duty_date: formData.dutyDate,
      note: formData.note || null,
    }
    const { error: saveError } = editingId
      ? await supabase.from('assignments').update(values).eq('id', editingId)
      : await supabase.from('assignments').insert(values)

    if (saveError) {
      setError(saveError.message)
    } else {
      setFormData({ doctorId: '', shiftTypeId: '', dutyDate: '', note: '' })
      setShowForm(false)
      setEditingId(null)
      await fetchData()
    }

    setSubmitting(false)
  }

  const editAssignment = (id: string) => {
    if (user?.role !== 'admin') return
    const assignment = assignments.find((item) => item.id === id)
    if (!assignment) return
    setEditingId(id)
    setFormData({
      doctorId: assignment.duty_doctor_id,
      shiftTypeId: String(assignment.shift_type_id),
      dutyDate: assignment.duty_date,
      note: assignment.note || '',
    })
    setShowForm(true)
    setError('')
  }

  const calendarEvents = useMemo(() => {
    return assignments.map((a) => ({
      id: a.id,
      title: a.note
        ? `${a.doctors?.full_name} (${a.shift_types?.name}) - ${a.note}`
        : `${a.doctors?.full_name} (${a.shift_types?.name})`,
      start: a.duty_date,
      allDay: true,
      backgroundColor: a.shift_types?.color || '#3b82f6',
    }))
  }, [assignments])

  const monthlyCounts = useMemo(() => {
    const filtered = assignments.filter((a) => a.duty_date.startsWith(displayMonth))
    const countMap: Record<string, { name: string; counts: Record<string, number> }> = {}

    for (const a of filtered) {
      const name = a.doctors?.full_name || '不明'
      const shiftName = a.shift_types?.name || '不明'
      if (!countMap[a.duty_doctor_id]) countMap[a.duty_doctor_id] = { name, counts: {} }
      const counts = countMap[a.duty_doctor_id].counts
      counts[shiftName] = (counts[shiftName] || 0) + 1
    }

    return countMap
  }, [assignments, displayMonth])

  if (!session) {
    return (
      <div style={{ maxWidth: 400, margin: '100px auto', padding: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', marginBottom: '24px' }}>医師シフト管理</h1>
        <button
          type="button"
          onClick={handleGoogleLogin}
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: '8px',
            background: 'white',
            color: '#1f2937',
            border: '1px solid #ddd',
            cursor: 'pointer',
            fontSize: '1rem',
          }}
        >
          Google でログイン
        </button>
        <p style={{ textAlign: 'center', color: '#999', margin: '16px 0', fontSize: '0.85rem' }}>または</p>
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <input
            type="email"
            name="email"
            placeholder="メールアドレス"
            required
            style={{ padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }}
          />
          <input
            type="password"
            name="password"
            placeholder="パスワード"
            required
            style={{ padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }}
          />
          <button
            type="submit"
            style={{
              padding: '12px',
              borderRadius: '8px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            ログイン
          </button>
          {error && <p style={{ color: 'red' }}>{error}</p>}
        </form>
      </div>
    )
  }

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto', padding: '24px' }}>
      <div style={{ display: 'flex', flexWrap: 'nowrap', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', gap: '8px' }}>
        <h1
          style={{
            fontSize: 'clamp(1rem, 5vw, 2rem)',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            minWidth: 0,
          }}
        >
          🏥 医師シフト管理
        </h1>
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <p style={{ fontSize: '0.9rem', color: '#666' }}>{user?.full_name}</p>
          <button
            onClick={() => supabase.auth.signOut().then(() => window.location.reload())}
            style={{
              padding: '8px 12px',
              borderRadius: '4px',
              background: '#f3f4f6',
              border: '1px solid #ddd',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontSize: 'clamp(0.75rem, 3vw, 1rem)',
            }}
          >
            ログアウト
          </button>
        </div>
      </div>

      {error && <p style={{ color: 'crimson', marginBottom: '16px' }}>Error: {error}</p>}

      {loading ? (
        <p>読み込み中...</p>
      ) : (
        <>
          {/* 月選択ボタン */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <button
              onClick={() => {
                const [year, month] = displayMonth.split('-')
                const date = new Date(parseInt(year), parseInt(month) - 2)
                const newYear = date.getFullYear()
                const newMonth = String(date.getMonth() + 1).padStart(2, '0')
                setDisplayMonth(`${newYear}-${newMonth}`)
              }}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              ◀ 前月
            </button>
            <h2 style={{ fontSize: '1.2rem', margin: 0 }}>📅 {displayMonth}</h2>
            <button
              onClick={() => {
                const [year, month] = displayMonth.split('-')
                const date = new Date(parseInt(year), parseInt(month))
                const newYear = date.getFullYear()
                const newMonth = String(date.getMonth() + 1).padStart(2, '0')
                setDisplayMonth(`${newYear}-${newMonth}`)
              }}
              style={{
                padding: '8px 16px',
                borderRadius: '4px',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              翌月 ▶
            </button>
          </div>

          {/* カレンダー */}
          <div style={{ background: '#fff', padding: '16px', borderRadius: '12px', marginBottom: '24px', border: '1px solid #e5e7eb' }}>
            <FullCalendar
              ref={calendarRef}
              plugins={[dayGridPlugin]}
              initialView="dayGridMonth"
              height="auto"
              events={calendarEvents}
              headerToolbar={false}
              eventClick={(info) => editAssignment(info.event.id)}
            />
          </div>

          {/* 管理者: 認証アカウントを作らず勤務医を登録 */}
          {user?.role === 'admin' && (
            <form onSubmit={handleAddDoctor} style={{ background: '#eff6ff', padding: '16px', borderRadius: '12px', marginBottom: '16px', border: '1px solid #bfdbfe', display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
              <label htmlFor="doctor-name">勤務医を追加（ログイン権限なし）</label>
              <input
                id="doctor-name"
                value={doctorName}
                onChange={(e) => setDoctorName(e.target.value)}
                placeholder="医師名"
                required
                style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
              />
              <button type="submit" disabled={addingDoctor} style={{ padding: '8px 16px', borderRadius: '4px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer' }}>
                {addingDoctor ? '登録中...' : '登録'}
              </button>
            </form>
          )}

          {/* 管理者: 勤務追加・変更フォーム */}
          {user?.role === 'admin' && (
            <div style={{ background: '#fef3c7', padding: '16px', borderRadius: '12px', marginBottom: '24px', border: '1px solid #fcd34d' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showForm ? '16px' : 0 }}>
                <h2 style={{ fontSize: '1.1rem' }}>👨‍⚕️ {editingId ? '勤務を変更' : '勤務を追加'}</h2>
                <button
                  onClick={() => {
                    setShowForm(!showForm)
                    setEditingId(null)
                    setFormData({ doctorId: '', shiftTypeId: '', dutyDate: '', note: '' })
                  }}
                  style={{
                    padding: '8px 16px',
                    borderRadius: '4px',
                    background: '#f59e0b',
                    color: 'white',
                    border: 'none',
                    cursor: 'pointer',
                  }}
                >
                  {showForm ? 'キャンセル' : '追加'}
                </button>
              </div>

              {!showForm && <p style={{ marginTop: '8px', color: '#92400e' }}>既存の勤務を変更するには、カレンダーの予定をクリックしてください。</p>}
              {showForm && (
                <form onSubmit={handleSaveAssignment} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <select
                    value={formData.doctorId}
                    onChange={(e) => setFormData({ ...formData, doctorId: e.target.value })}
                    required
                    style={{ padding: '12px', borderRadius: '4px', border: '1px solid #ddd' }}
                  >
                    <option value="">医師を選択</option>
                    {doctors.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.full_name}
                      </option>
                    ))}
                  </select>

                  <select
                    value={formData.shiftTypeId}
                    onChange={(e) => setFormData({ ...formData, shiftTypeId: e.target.value })}
                    required
                    style={{ padding: '12px', borderRadius: '4px', border: '1px solid #ddd' }}
                  >
                    <option value="">シフト種別を選択</option>
                    {shiftTypes.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>

                  <input
                    type="date"
                    value={formData.dutyDate}
                    onChange={(e) => setFormData({ ...formData, dutyDate: e.target.value })}
                    required
                    style={{ padding: '12px', borderRadius: '4px', border: '1px solid #ddd' }}
                  />

                  <input
                    type="text"
                    placeholder="備考（オプション）"
                    value={formData.note}
                    onChange={(e) => setFormData({ ...formData, note: e.target.value })}
                    style={{ padding: '12px', borderRadius: '4px', border: '1px solid #ddd' }}
                  />

                  <button
                    type="submit"
                    disabled={submitting}
                    style={{
                      gridColumn: '1 / -1',
                      padding: '12px',
                      borderRadius: '4px',
                      background: '#10b981',
                      color: 'white',
                      border: 'none',
                      cursor: submitting ? 'not-allowed' : 'pointer',
                      opacity: submitting ? 0.5 : 1,
                    }}
                  >
                    {submitting ? '保存中...' : editingId ? '変更を保存' : '保存'}
                  </button>
                </form>
              )}
            </div>
          )}

          {/* 月別集計 */}
          <section style={{ background: '#fff', padding: '16px', borderRadius: '12px', border: '1px solid #e5e7eb' }}>
            <h2 style={{ fontSize: '1.1rem', marginBottom: '16px' }}>📊 {displayMonth} の集計</h2>
            {Object.keys(monthlyCounts).length === 0 ? (
              <p style={{ color: '#999' }}>選択月のデータはまだありません。</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f3f4f6' }}>
                      <th style={{ textAlign: 'left', padding: '12px', borderBottom: '2px solid #ddd', whiteSpace: 'nowrap' }}>医師</th>
                      {shiftTypes.map((s) => (
                        <th key={s.id} style={{ textAlign: 'left', padding: '12px', borderBottom: '2px solid #ddd', whiteSpace: 'nowrap' }}>
                          {s.name}
                        </th>
                      ))}
                      <th style={{ textAlign: 'left', padding: '12px', borderBottom: '2px solid #ddd', whiteSpace: 'nowrap' }}>合計</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(monthlyCounts).map(([doctorId, { name, counts }]) => {
                      const total = Object.values(counts).reduce((a, b) => a + b, 0)
                      return (
                        <tr key={doctorId}>
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', whiteSpace: 'nowrap' }}>{name}</td>
                          {shiftTypes.map((s) => (
                            <td key={s.id} style={{ padding: '12px', borderBottom: '1px solid #eee' }}>
                              {counts[s.name] || 0}
                            </td>
                          ))}
                          <td style={{ padding: '12px', borderBottom: '1px solid #eee', fontWeight: 'bold' }}>{total}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  )
}
