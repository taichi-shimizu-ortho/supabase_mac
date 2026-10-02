-- created_by は任意の監査メタデータ。作成者のログイン削除は勤務を消さない。
begin;

alter table public.assignments
  drop constraint assignments_created_by_fkey;

alter table public.assignments
  add constraint assignments_created_by_fkey
  foreign key (created_by) references public.profiles(id) on delete set null;

commit;
