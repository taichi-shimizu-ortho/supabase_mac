-- 承認済みの勤務医統合に先立ち、API ロールからアクセスできない退避先を作る。
begin;
create table public._doctor_merge_backup_20261022 (data jsonb not null);
alter table public._doctor_merge_backup_20261022 enable row level security;
revoke all on public._doctor_merge_backup_20261022 from public, anon, authenticated;
commit;
