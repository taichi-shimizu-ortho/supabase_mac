-- Google カレンダーを正として取り込むため、取り込み元の予定を記録する。
-- 1つの予定が複数日にわたる・繰り返す場合があるため、予定 UID と勤務日の組で一意にする。
-- gcal_uid が null の行はアプリや CSV で手入力した勤務。
begin;

alter table public.assignments
  add column gcal_uid text;

create unique index assignments_gcal_uid_duty_date_key
  on public.assignments (gcal_uid, duty_date)
  where gcal_uid is not null;

commit;
