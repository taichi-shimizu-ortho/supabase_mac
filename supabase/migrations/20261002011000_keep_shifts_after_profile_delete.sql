-- 認証アカウントの削除が勤務表に影響しないよう、旧互換カラムを任意にする。
-- 正規の担当医ID duty_doctor_id は doctors を参照し続ける。
begin;

alter table public.assignments
  drop constraint assignments_doctor_id_fkey;

alter table public.assignments
  add constraint assignments_doctor_id_fkey
  foreign key (doctor_id) references public.profiles(id) on delete set null;

commit;
