'use client'

import { useEffect, useMemo, useState } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import { supabase } from '@/lib/supabase'

type ShiftRow = {
  id: number
  staff_name: string
  shift_date: string
  shift_type: string
  note: string | null
}

export default function Home() {
  const [rows, setRows] = useState<ShiftRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    const fetchShifts = async () => {
      setLoading(true)
      setError('')

      const { data, error } = await supabase
        .from('on_call_shifts')
        .select('id, staff_name, shift_date, shift_type, note')
        .order('shift_date', { ascending: true })

      if (error) {
        setError(error.message)
        setLoading(false)
        return
      }

      setRows((data ?? []) as ShiftRow[])
      setLoading(false)
    }

    fetchShifts()
  }, [])

  const calendarEvents = useMemo(() => {
    return rows.map((row) => ({
      id: String(row.id),
      title: `${row.staff_name} (${row.shift_type})`,
      start: row.shift_date,
      allDay: true,
    }))
  }, [rows])

  const currentMonth = new Date().toISOString().slice(0, 7)

  const monthlyCounts = useMemo(() => {
    const filtered = rows.filter((row) => row.shift_date.startsWith(currentMonth))
    const countMap: Record<string, number> = {}

    for (const row of filtered) {
      countMap[row.staff_name] = (countMap[row.staff_name] ?? 0) + 1
    }

    return Object.entries(countMap)
      .map(([staff_name, count]) => ({ staff_name, count }))
      .sort((a, b) => b.count - a.count || a.staff_name.localeCompare(b.staff_name))
  }, [rows, currentMonth])

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: '24px' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '8px' }}>当直管理カレンダー</h1>
      <p style={{ marginBottom: '24px', color: '#555' }}>
        Supabase から当直データを読み込み、月間カレンダーと当月回数を表示します。
      </p>

      {loading && <p>読み込み中...</p>}
      {error && <p style={{ color: 'crimson' }}>Error: {error}</p>}

      {!loading && !error && (
        <>
          <div style={{ background: '#fff', padding: '16px', borderRadius: '12px', marginBottom: '24px' }}>
            <FullCalendar
              plugins={[dayGridPlugin]}
              initialView="dayGridMonth"
              height="auto"
              events={calendarEvents}
            />
          </div>

          <section style={{ background: '#fff', padding: '16px', borderRadius: '12px' }}>
            <h2 style={{ fontSize: '1.25rem', marginBottom: '12px' }}>{currentMonth} の当直回数</h2>
            {monthlyCounts.length === 0 ? (
              <p>今月のデータはまだありません。</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid #ddd' }}>氏名</th>
                    <th style={{ textAlign: 'left', padding: '8px', borderBottom: '1px solid #ddd' }}>回数</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlyCounts.map((item) => (
                    <tr key={item.staff_name}>
                      <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>{item.staff_name}</td>
                      <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </main>
  )
}
