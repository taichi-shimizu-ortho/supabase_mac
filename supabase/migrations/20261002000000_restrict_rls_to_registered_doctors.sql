-- 閲覧・編集権限を「登録済みの有効な医師」と「管理者」に限定する
--
-- 目的:
--   - 匿名 (anon) からの読み取りを禁止する
--   - 認証済みでも profiles に登録のない (= 未登録の Google アカウント等) ユーザーには何も見せない
--   - profiles への挿入・更新 (role='admin' 付与を含む) を管理者だけに限定する
--
-- 適用方法: Supabase ダッシュボード → SQL Editor に貼り付けて実行
-- 事前確認: 下の「0. 事前確認」を先に単独で実行し、結果を確認してから本体を実行すること

-- ============================================================
-- 0. 事前確認 (本体とは別に実行)
-- ============================================================
-- 現在のポリシー
--   select tablename, policyname, roles, cmd, qual, with_check
--   from pg_policies
--   where schemaname = 'public'
--   order by tablename, policyname;
--
-- auth.users に profiles を自動作成するトリガーがないか
-- (あると未登録の Google アカウントにも profiles が作られ、閲覧できてしまう)
--   select tgname, pg_get_triggerdef(t.oid)
--   from pg_trigger t
--   where tgrelid = 'auth.users'::regclass and not tgisinternal;
--
-- 自分 (管理者) が admin かつ有効であること。これが false だと適用後に誰も管理できなくなる
--   select full_name, role, is_active from public.profiles where role = 'admin';

begin;

-- ============================================================
-- 1. 判定関数
-- ============================================================
-- profiles の RLS から profiles 自身を参照すると再帰するため security definer で判定する

create or replace function public.is_active_member()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles
    where id = (select auth.uid()) and is_active
  );
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles
    where id = (select auth.uid()) and is_active and role = 'admin'
  );
$$;

revoke execute on function public.is_active_member() from public, anon;
revoke execute on function public.is_admin() from public, anon;
grant execute on function public.is_active_member() to authenticated;
grant execute on function public.is_admin() to authenticated;

-- ============================================================
-- 2. 既存ポリシーをすべて削除
-- ============================================================

do $$
declare
  r record;
begin
  for r in
    select tablename, policyname
    from pg_policies
    where schemaname = 'public'
      and tablename in ('profiles', 'assignments', 'shift_types')
  loop
    execute format('drop policy %I on public.%I', r.policyname, r.tablename);
  end loop;
end
$$;

alter table public.profiles enable row level security;
alter table public.assignments enable row level security;
alter table public.shift_types enable row level security;

-- ============================================================
-- 3. 匿名ロールからテーブル権限を剥奪
-- ============================================================

revoke all on public.profiles, public.assignments, public.shift_types from anon;

-- monthly_counts ビューは既定で作成者権限 (RLS 無視) で動くため、呼び出し元の権限で評価させる
do $$
begin
  if exists (select 1 from pg_views where schemaname = 'public' and viewname = 'monthly_counts') then
    execute 'alter view public.monthly_counts set (security_invoker = true)';
    execute 'revoke all on public.monthly_counts from anon';
  end if;
end
$$;

-- ============================================================
-- 4. 新しいポリシー
-- ============================================================

-- profiles: 有効な医師は全員分を閲覧可。自分の行は無効化されていても閲覧可 (画面で「無効」を判定するため)
create policy profiles_select_members on public.profiles
  for select to authenticated
  using (public.is_active_member() or id = (select auth.uid()));

create policy profiles_insert_admin on public.profiles
  for insert to authenticated
  with check (public.is_admin());

create policy profiles_update_admin on public.profiles
  for update to authenticated
  using (public.is_admin())
  with check (public.is_admin());

create policy profiles_delete_admin on public.profiles
  for delete to authenticated
  using (public.is_admin());

-- assignments: 有効な医師は閲覧可、編集は管理者のみ
create policy assignments_select_members on public.assignments
  for select to authenticated
  using (public.is_active_member());

create policy assignments_insert_admin on public.assignments
  for insert to authenticated
  with check (public.is_admin());

create policy assignments_update_admin on public.assignments
  for update to authenticated
  using (public.is_admin())
  with check (public.is_admin());

create policy assignments_delete_admin on public.assignments
  for delete to authenticated
  using (public.is_admin());

-- 既存の「医師が自分の勤務を追加・削除できる」権限は残す (有効な医師に限定)
create policy assignments_insert_self on public.assignments
  for insert to authenticated
  with check (doctor_id = (select auth.uid()) and public.is_active_member());

create policy assignments_delete_self on public.assignments
  for delete to authenticated
  using (doctor_id = (select auth.uid()) and public.is_active_member());

-- shift_types: 有効な医師は閲覧可、編集は管理者のみ
create policy shift_types_select_members on public.shift_types
  for select to authenticated
  using (public.is_active_member());

create policy shift_types_insert_admin on public.shift_types
  for insert to authenticated
  with check (public.is_admin());

create policy shift_types_update_admin on public.shift_types
  for update to authenticated
  using (public.is_admin())
  with check (public.is_admin());

create policy shift_types_delete_admin on public.shift_types
  for delete to authenticated
  using (public.is_admin());

commit;
