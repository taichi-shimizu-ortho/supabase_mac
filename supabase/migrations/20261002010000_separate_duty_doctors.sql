-- 勤務担当医はログイン利用者とは独立した名簿で管理する。
-- 既存の doctor_id は移行期間中のプロフィール連携として残し、
-- 新しい duty_doctor_id を割当の正規の担当医IDとする。
begin;

create table public.doctors (
  id uuid primary key default gen_random_uuid(),
  full_name text not null check (length(btrim(full_name)) > 0),
  is_active boolean not null default true,
  profile_id uuid unique references public.profiles(id) on delete set null,
  created_at timestamptz not null default now()
);

-- 同じ UUID を引き継ぐことで、既存の自己割当権限と全勤務記録を維持する。
insert into public.doctors (id, full_name, is_active, profile_id)
select id, full_name, is_active, id from public.profiles;

alter table public.assignments
  add column duty_doctor_id uuid references public.doctors(id);

update public.assignments
set duty_doctor_id = doctor_id;

alter table public.assignments
  alter column duty_doctor_id set not null,
  alter column doctor_id drop not null;

alter table public.assignments
  add constraint assignments_duty_doctor_shift_date_key
  unique (duty_doctor_id, shift_type_id, duty_date);

-- 古いクライアントは doctor_id、新しいクライアントは duty_doctor_id を書く。
-- 必ず名簿側のリンクから旧カラムを決定し、不正な自己割当を防止する。
create function public.sync_assignment_doctor()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.duty_doctor_id is null then
    new.duty_doctor_id := new.doctor_id;
  elsif tg_op = 'UPDATE'
    and new.duty_doctor_id is not distinct from old.duty_doctor_id
    and new.doctor_id is distinct from old.doctor_id
    and new.doctor_id is not null then
    new.duty_doctor_id := new.doctor_id;
  end if;

  select d.profile_id into new.doctor_id
  from public.doctors d
  where d.id = new.duty_doctor_id;

  return new;
end;
$$;

create trigger assignments_sync_doctor
before insert or update on public.assignments
for each row execute function public.sync_assignment_doctor();

-- ビューは追加されたログイン不要の医師も集計する。
create or replace view public.monthly_counts
with (security_invoker = true) as
select d.id as doctor_id,
       d.full_name,
       st.id as shift_type_id,
       st.name as shift_name,
       to_char(a.duty_date::timestamptz, 'YYYY-MM') as month,
       count(*) as cnt
from public.assignments a
join public.doctors d on d.id = a.duty_doctor_id
join public.shift_types st on st.id = a.shift_type_id
group by d.id, d.full_name, st.id, st.name,
         to_char(a.duty_date::timestamptz, 'YYYY-MM');

alter table public.doctors enable row level security;
revoke all on public.doctors from anon;
grant select, insert, update, delete on public.doctors to authenticated;

create policy doctors_select_members on public.doctors
  for select to authenticated
  using (public.is_active_member());
create policy doctors_insert_admin on public.doctors
  for insert to authenticated
  with check (public.is_admin());
create policy doctors_update_admin on public.doctors
  for update to authenticated
  using (public.is_admin())
  with check (public.is_admin());
create policy doctors_delete_admin on public.doctors
  for delete to authenticated
  using (public.is_admin());

revoke all on public.monthly_counts from anon;
grant select on public.monthly_counts to authenticated;
commit;
