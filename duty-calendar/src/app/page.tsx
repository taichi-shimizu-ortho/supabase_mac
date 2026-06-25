'use client'

import { useEffect, useMemo, useState, useRef } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import { supabase, type Profile, type ShiftType, type Assignment } from '@/lib/supabase'

export default function Home() {
  const calendarRef = useRef<FullCalendar>(null)
  const [session, setSession] = useState(false)
  const [user, setUser] = useState<Profile | null>(null)
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [doctors, setDoctors] = useState<Profile[]>([])
  const [shiftTypes, setShiftTypes] = useState<ShiftType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  // 新規割り当てフォーム
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({ doctorId: '', shiftTypeId: '', dutyDate: '', note: '' })
  const [submitting, setSubmitting] = useState(false)

  // カレンダー表示月
  const [displayMonth, setDisplayMonth] = useState(() => new Date().toISOString().slice(0, 7))

  // ログイン処理
  useEffect(() => {
    const checkSession = async () => {
      const { data } = await supabase.auth.getSession()
      if (!data.session) {
        setSession(false)
        setLoading(false)
        return
      }

      setSession(true)

      // ユーザープロフィール取得
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', data.session.user.id)
        .single()

      if (profileData) {
        setUser(profileData)
      }

      // データ取得
      await fetchData()
    }

    checkSession()
  }, [])

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
      // 医師一覧
      const { data: doctorsData } = await supabase
        .from('profiles')
        .select('*')
        .eq('is_active', true)

      setDoctors(doctorsData || [])

      // シフト種別
      const { data: shiftsData } = await supabase
        .from('shift_types')
        .select('*')

      setShiftTypes(shiftsData || [])

      // 割り当て
      const { data: assignmentsData } = await supabase
        .from('assignments')
        .select('*, profiles!assignments_doctor_id_fkey(full_name), shift_types(name, color)')
        .order('duty_date', { ascending: true })

      setAssignments(assignmentsData || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました')
    } finally {
      setLoading(false)
    }
  }

  // ログイン
  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const email = (e.currentTarget.elements.namedItem('email') as HTMLInputElement).value
    const password = (e.currentTarget.elements.namedItem('password') as HTMLInputElement).value

    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) {
      setError(error.message)
      return
    }

    // 再度セッション確認
    const { data } = await supabase.auth.getSession()
    if (data.session) {
      setSession(true)
      const { data: profileData } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', data.session.user.id)
        .single()
      if (profileData) setUser(profileData)
      await fetchData()
    }
  }

  // 勤務追加
  const handleAddAssignment = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    const { error } = await supabase.from('assignments').insert({
      doctor_id: formData.doctorId,
      shift_type_id: parseInt(formData.shiftTypeId),
      duty_date: formData.dutyDate,
      note: formData.note || null,
    })

    if (error) {
      setError(error.message)
    } else {
      setFormData({ doctorId: '', shiftTypeId: '', dutyDate: '', note: '' })
      setShowForm(false)
      await fetchData()
    }

    setSubmitting(false)
  }

  const calendarEvents = useMemo(() => {
    return assignments.map((a) => ({
      id: a.id,
      title: a.note
        ? `${a.profiles?.full_name} (${a.shift_types?.name}) - ${a.note}`
        : `${a.profiles?.full_name} (${a.shift_types?.name})`,
      start: a.duty_date,
      allDay: true,
      backgroundColor: a.shift_types?.color || '#3b82f6',
    }))
  }, [assignments])

  const monthlyCounts = useMemo(() => {
    const filtered = assignments.filter((a) => a.duty_date.startsWith(displayMonth))
    const countMap: Record<string, Record<string, number>> = {}

    for (const a of filtered) {
      const name = a.profiles?.full_name || '不明'
      const shiftName = a.shift_types?.name || '不明'
      if (!countMap[name]) countMap[name] = {}
      countMap[name][shiftName] = (countMap[name][shiftName] || 0) + 1
    }

    return countMap
  }, [assignments, displayMonth])

  if (!session) {
    return (
      <div style={{ maxWidth: 400, margin: '100px auto', padding: '24px' }}>
        <h1 style={{ fontSize: '1.5rem', marginBottom: '24px' }}>医師シフト管理</h1>
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '2rem' }}>🏥 医師シフト管理</h1>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: '0.9rem', color: '#666' }}>{user?.full_name}</p>
          <button
            onClick={() => supabase.auth.signOut().then(() => window.location.reload())}
            style={{
              padding: '8px 16px',
              borderRadius: '4px',
              background: '#f3f4f6',
              border: '1px solid #ddd',
              cursor: 'pointer',
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
            />
          </div>

          {/* 管理者: 勤務追加フォーム */}
          {user?.role === 'admin' && (
            <div style={{ background: '#fef3c7', padding: '16px', borderRadius: '12px', marginBottom: '24px', border: '1px solid #fcd34d' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: showForm ? '16px' : 0 }}>
                <h2 style={{ fontSize: '1.1rem' }}>👨‍⚕️ 勤務を追加</h2>
                <button
                  onClick={() => setShowForm(!showForm)}
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

              {showForm && (
                <form onSubmit={handleAddAssignment} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
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
                    {submitting ? '保存中...' : '保存'}
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
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f3f4f6' }}>
                    <th style={{ textAlign: 'left', padding: '12px', borderBottom: '2px solid #ddd' }}>医師</th>
                    {shiftTypes.map((s) => (
                      <th key={s.id} style={{ textAlign: 'left', padding: '12px', borderBottom: '2px solid #ddd' }}>
                        {s.name}
                      </th>
                    ))}
                    <th style={{ textAlign: 'left', padding: '12px', borderBottom: '2px solid #ddd' }}>合計</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(monthlyCounts).map(([doctorName, counts]) => {
                    const total = Object.values(counts).reduce((a, b) => a + b, 0)
                    return (
                      <tr key={doctorName}>
                        <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>{doctorName}</td>
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
            )}
          </section>
        </>
      )}
    </main>
  )
}
