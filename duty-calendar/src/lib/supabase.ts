import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

// Google ログインの戻りで URL の ?code= をセッションに交換する
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: { flowType: 'pkce' },
})

export type Profile = {
  id: string
  full_name: string
  role: 'doctor' | 'admin'
  is_active: boolean
}

export type ShiftType = {
  id: number
  name: string
  color: string
}

export type Assignment = {
  id: string
  doctor_id: string
  shift_type_id: number
  duty_date: string
  note: string | null
  profiles?: Profile
  shift_types?: ShiftType
}
