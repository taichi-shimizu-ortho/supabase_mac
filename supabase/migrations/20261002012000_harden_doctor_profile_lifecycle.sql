-- 既存/新規のプロフィール追加、旧クライアントからの割当、
-- ログイン利用者削除のいずれでも独立した勤務担当医を維持する。
begin;

-- この勤務表では表示名は一意。改名・同姓同名が必要な場合は区別可能な表示名を設定する。
create unique index doctors_unique_display_name
on public.doctors (lower(btrim(full_name)));

create function public.create_doctor_for_profile()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.doctors (id, full_name, is_active, profile_id)
  values (new.id, new.full_name, new.is_active, new.id)
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger profiles_create_doctor
  after insert on public.profiles
  for each row execute function public.create_doctor_for_profile();

-- 最初の移行以降、新しいトリガーが有効になるまでの間に増えた利用者も補完する。
insert into public.doctors (id, full_name, is_active, profile_id)
select p.id, p.full_name, p.is_active, p.id
from public.profiles p
where not exists (
  select 1 from public.doctors d where d.profile_id = p.id
)
on conflict (id) do nothing;

create or replace function public.sync_assignment_doctor()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  -- 旧クライアントは profile のIDを送る。doctor のIDと一致する前提を置かない。
  if new.duty_doctor_id is null then
    select id into new.duty_doctor_id
    from public.doctors where profile_id = new.doctor_id;
  elsif tg_op = 'UPDATE'
    and new.duty_doctor_id is not distinct from old.duty_doctor_id
    and new.doctor_id is distinct from old.doctor_id
    and new.doctor_id is not null then
    select id into new.duty_doctor_id
    from public.doctors where profile_id = new.doctor_id;
  end if;

  if new.duty_doctor_id is null then
    raise exception '勤務担当医が登録されていません' using errcode = '23503';
  end if;

  select profile_id into new.doctor_id
  from public.doctors where id = new.duty_doctor_id;
  if not found then
    raise exception '勤務担当医が見つかりません' using errcode = '23503';
  end if;
  return new;
end;
$$;

-- FK による SET NULL より前にリンクを外す。
-- duty_doctor_id は残るため、プロフィールを削除しても勤務履歴は残る。
create function public.detach_doctor_before_profile_delete()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.doctors
  set profile_id = null
  where profile_id = old.id;

  update public.assignments
  set doctor_id = null
  where doctor_id = old.id;

  return old;
end;
$$;

create trigger profiles_detach_doctor
  before delete on public.profiles
  for each row execute function public.detach_doctor_before_profile_delete();

commit;
