import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

// ログインはメール・パスワードのみ。OAuth の戻りURLからはログインしない。
// Google カレンダーの取り込みは import_gcal.py が独立して行う。
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: { flowType: 'pkce', detectSessionInUrl: false },
})

export type Profile = {
  id: string
  full_name: string
  role: 'doctor' | 'admin'
  is_active: boolean
}

export type Doctor = {
  id: string
  full_name: string
  is_active: boolean
  profile_id: string | null
}

export type ShiftType = {
  id: number
  name: string
  color: string
}

export type Assignment = {
  id: string
  duty_doctor_id: string
  shift_type_id: number
  duty_date: string
  note: string | null
  doctors?: Pick<Doctor, 'full_name'>
  shift_types?: ShiftType
}
