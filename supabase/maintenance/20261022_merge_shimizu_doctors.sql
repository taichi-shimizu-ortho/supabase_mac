-- 清水太一（taichi8）の勤務を、パスワードで利用中の「清水太一」に統合する。
-- Supabase SQL Editor の所有者権限で実行する。通常の migration には含めない。
-- 先に 20261022070424_prepare_doctor_merge_backup.sql を適用して退避先を用意する。
-- 既定は末尾の ROLLBACK で全変更を取り消す確認実行。
-- 結果を確認・承認後、末尾の ROLLBACK だけを COMMIT に変えて再実行する。
-- 本番反映時は元のレコードを RLS 有効・API 読み書き不可のバックアップ表に残す。
begin;

-- 点検から更新完了まで、勤務・名簿・権限の変更を待たせる。
lock table public.assignments, public.doctors, public.profiles in share row exclusive mode;

do $$
declare
  source_id constant uuid := '78296141-19ae-478e-baef-91a905a289cf';
  target_id constant uuid := '41e0526d-06d7-49e0-aa4b-c72dedca8a97';
  swapped_assignment constant uuid := 'a586f1f7-a80d-4568-94d4-6866ae80b41b';
  affected integer;
begin
  if not exists (
    select 1 from public.doctors d join public.profiles p on p.id = d.profile_id
    where d.id = target_id and d.full_name = '清水太一' and d.is_active
      and p.id = target_id and p.is_active and p.role = 'admin'
  ) or not exists (
    select 1 from public.doctors d join public.profiles p on p.id = d.profile_id
    where d.id = source_id and d.full_name = '清水太一（taichi8）'
      and p.id = source_id
  ) then
    raise exception '統合対象の名簿または通常ログインの状態が確認時と異なります';
  end if;

  if (select count(*) from public.assignments where duty_doctor_id = source_id) <> 18
    or (select count(*) from public.assignments where duty_doctor_id = target_id) <> 29
    or exists (select 1 from public.assignments where duty_doctor_id = source_id and gcal_uid is not null)
  then
    raise exception '勤務の件数または取り込み元が確認時と異なります。再レビューしてください';
  end if;

  if (select count(*) from public.assignments s join public.assignments t
      on s.duty_date = t.duty_date and s.shift_type_id = t.shift_type_id
      where s.duty_doctor_id = source_id and t.duty_doctor_id = target_id) <> 7
    or exists (
      select 1 from public.assignments s join public.assignments t
        on s.duty_date = t.duty_date and s.shift_type_id = t.shift_type_id
      where s.duty_doctor_id = source_id and t.duty_doctor_id = target_id
        and coalesce(s.note, '') <> coalesce(t.note, '')
        and not coalesce((s.duty_date = '2026-09-04' and s.shift_type_id = 2
          and s.note = 'タケスポ' and t.note = '馬借'), false)
    ) then
    raise exception '重複勤務または備考が確認時と異なります。再レビューしてください';
  end if;

  -- 10/14 新小倉は Google カレンダーで藤原医師への交代が確定している。
  if not exists (
    select 1 from public.assignments s join public.assignments t
      on s.duty_date = t.duty_date and s.shift_type_id = t.shift_type_id
    where s.id = swapped_assignment and s.duty_doctor_id = source_id
      and s.duty_date = '2026-10-14' and s.shift_type_id = 2 and s.note = '新小倉'
      and t.duty_doctor_id = '20c4c5ae-949e-40ac-9632-ff8961ea4bea'
      and t.note = '新小倉'
      and t.gcal_uid = 'c5hj6o9m69h3cbb6cdijab9k65imabb270qjcb9pc8pm4phmcdgm6p3568@google.com'
  ) then
    raise exception '10月14日の交代先勤務が確認時と異なります';
  end if;

  if exists (select 1 from public._doctor_merge_backup_20261022) then
    raise exception '既存の統合バックアップがあります。再実行しないでください';
  end if;
  insert into public._doctor_merge_backup_20261022 (data)
  select jsonb_build_object(
    'profiles', (select jsonb_agg(to_jsonb(p)) from public.profiles p where id in (source_id, target_id)),
    'doctors', (select jsonb_agg(to_jsonb(d)) from public.doctors d where id in (source_id, target_id)),
    'assignments', (select jsonb_agg(to_jsonb(a)) from public.assignments a where duty_doctor_id in (source_id, target_id))
  );

  -- 同じ日・同じ種別は通常ログイン側のレコードと Google UID を残す。
  -- 異なる備考は両方残す（9/4 は「馬借 / タケスポ」）。
  update public.assignments t
  set note = case
    when coalesce(t.note, '') = coalesce(s.note, '') then t.note
    when coalesce(t.note, '') = '' then s.note
    when coalesce(s.note, '') = '' then t.note
    else t.note || ' / ' || s.note
  end
  from public.assignments s
  where s.duty_doctor_id = source_id and t.duty_doctor_id = target_id
    and s.duty_date = t.duty_date and s.shift_type_id = t.shift_type_id;
  get diagnostics affected = row_count;
  if affected <> 7 then raise exception '重複統合件数が7件ではありません'; end if;

  delete from public.assignments s using public.assignments t
  where s.duty_doctor_id = source_id and t.duty_doctor_id = target_id
    and s.duty_date = t.duty_date and s.shift_type_id = t.shift_type_id;
  get diagnostics affected = row_count;
  if affected <> 7 then raise exception '重複削除件数が7件ではありません'; end if;

  delete from public.assignments where id = swapped_assignment;
  get diagnostics affected = row_count;
  if affected <> 1 then raise exception '交代済み勤務が1件ではありません'; end if;

  update public.assignments set duty_doctor_id = target_id where duty_doctor_id = source_id;
  get diagnostics affected = row_count;
  if affected <> 10 then raise exception '勤務移動件数が10件ではありません'; end if;

  -- Auth ユーザー自体は削除せず、旧名簿のログイン権限・割当候補を無効化する。
  update public.profiles set is_active = false where id = source_id;
  update public.doctors set is_active = false where id = source_id;

  if exists (select 1 from public.assignments where duty_doctor_id = source_id)
    or (select count(*) from public.assignments where duty_doctor_id = target_id) <> 39
  then
    raise exception '統合後の勤務件数が想定と異なります';
  end if;
  raise notice '重複7件を統合、交代済み1件を除去、10件を移動。清水太一の勤務は39件。';
end;
$$;

select d.full_name, d.is_active, count(a.id) as assignments
from public.doctors d left join public.assignments a on a.duty_doctor_id = d.id
where d.id in ('78296141-19ae-478e-baef-91a905a289cf', '41e0526d-06d7-49e0-aa4b-c72dedca8a97')
group by d.id, d.full_name, d.is_active;

-- 確認実行。本番反映の承認後に、この1行だけ COMMIT に変更する。
rollback;
