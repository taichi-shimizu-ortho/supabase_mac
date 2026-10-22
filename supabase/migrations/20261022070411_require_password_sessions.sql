-- Google カレンダー取り込みとログインを分離する。
-- Google と連携済みのユーザーも、パスワードで認証したセッションなら利用可能。
-- provider メタデータではなく、Supabase が署名した JWT の認証方法を使う。
begin;

create function public.is_password_session()
returns boolean
language sql
stable
set search_path = ''
as $$
  select coalesce((select auth.jwt()) -> 'amr', '[]'::jsonb)
           @> '[{"method":"password"}]'::jsonb
      or coalesce((select auth.jwt()) -> 'amr', '[]'::jsonb)
           @> '["password"]'::jsonb;
$$;

revoke execute on function public.is_password_session() from public, anon;
grant execute on function public.is_password_session() to authenticated;

create or replace function public.is_active_member()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select public.is_password_session() and exists (
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
  select public.is_password_session() and exists (
    select 1 from public.profiles
    where id = (select auth.uid()) and is_active and role = 'admin'
  );
$$;

commit;
