# 医師シフト管理システム

医師たちがスマートフォンでシフトを確認・管理できるシステムです。

---

## 🌐 ブラウザ版（医師向け）

### アクセス方法

**URL**: https://supabase-mac.vercel.app/

スマートフォン・PC のどちらからでもアクセス可能です。

### ログイン

- **Google でログイン**: 登録済みのメールアドレスと同じ Google アカウントを選択（Android の Chrome でも可）
- **メール・パスワード**: メールアドレスとパスワードを入力して **ログイン** をクリック

※ `profiles` に登録されていない、または無効化されたアカウントはログインできません。

### 機能

| 画面 | 説明 |
|---|---|
| **カレンダー** | 当月のシフトをカレンダー表示 |
| **月選択** | カレンダーで月を切り替え → 集計も自動更新 |
| **集計表示** | 選択月の当直・外勤回数を医師ごとに表示 |
| **勤務医追加** | 管理者のみ表示 - ログイン権限なしの医師を勤務表に登録 |
| **勤務追加・変更** | 管理者のみ表示 - シフトを追加、カレンダーの予定をクリックして変更 |

### 画面の使い方

#### 📅 カレンダー表示
- 当月のシフトを色分け表示
- 赤：当直 / 青：外勤
- クリックして別の月を表示可能

#### 📊 月別集計
- 選択中の月の集計を表示
- 医師ごとに当直・外勤の回数をカウント
- カレンダーで月を変更すると自動更新

#### 👨‍⚕️ 勤務を追加（管理者のみ）
医師が未登録なら、先に「勤務医を追加」で登録します（ログイン権限は作られません）。

1. **追加** ボタンをクリック
2. 以下を入力：
   - **医師を選択**: ドロップダウンから医師名を選択
   - **シフト種別**: 「当直」または「外勤」
   - **日付**: YYYY-MM-DD 形式
   - **備考**: オプション（ER対応など）
3. **保存** をクリック

既存の勤務を変更するには、カレンダーの予定をクリックし、医師・種別・日付・備考を変更して保存します。
**Google でログイン**は認証機能のみです。勤務表は Google カレンダーを正として、管理者が CLI（`import_gcal.py`）で取り込みます。
Google カレンダーから取り込んだ勤務を画面で変更しても、次回の取り込みで Google カレンダーの内容に戻ります。変更は Google カレンダー側で行ってください。

---

## 🛠️ Python CLI ツール（管理者向け）

このディレクトリには Supabase + Python CLI で医師シフトを一括管理するツール一式が含まれています。

> Python スクリプトは `duty-calendar/` ディレクトリを参照

---

## 📦 セットアップ

### 1. 依存パッケージをインストール

```bash
uv sync
```

### 2. .env ファイルを設定

```bash
# .env に以下を設定（既に設定済み）
SUPABASE_URL=<your-project-url>
SUPABASE_KEY=<your-anon-key>
```

⚠️ **重要**: `SUPABASE_KEY` は **anon (public) key** を使用してください。Service Role Key (secret) は使わないこと。

### 3. 接続テスト

```bash
python test_connection.py
```

出力例：
```
✅ Connected to: https://yfurglffuzkffpmodkkq.supabase.co
✅ profiles テーブル OK - 3 件
✅ assignments テーブル OK - 5 件
✅ shift_types テーブル OK - 2 件
   - 1: 当直 (#ef4444)
   - 2: 外勤 (#3b82f6)
```

### 4. CLI のサインイン

RLS で匿名アクセスを禁止しているため、CLI は起動時に管理者アカウントでサインインします。
メールアドレスとパスワードを聞かれるので入力してください（`.env` は Git 管理されているため、パスワードは書かないこと）。
`SUPABASE_EMAIL` / `SUPABASE_PASSWORD` を環境変数で渡すと入力を省略できます。

---

## 🛠️ CLI ツール

### main.py - シフト情報照会

```bash
# 医師一覧
python main.py list-doctors

# 医師の月別回数を表示
python main.py monthly-count --doctor "清水太郎" --month "2026-06"

# 月別集計を表示
python main.py summary --month "2026-06"
```

### admin_doctors.py - 医師管理

```bash
# 全医師一覧
python admin_doctors.py list-all

# 医師を追加 (Auth ユーザーをレジスタ)
python admin_doctors.py add --id "550e8400-..." --name "清水太郎"

# ログイン利用者を削除（勤務医名簿・勤務履歴は残る）
python admin_doctors.py delete --name "清水太郎"

# 管理者に昇格
python admin_doctors.py set-admin --name "清水太郎"

# 医師に降格
python admin_doctors.py set-doctor --name "清水太郎"

# ログイン利用者を無効化（勤務医名簿はそのまま）
python admin_doctors.py disable --name "清水太郎"

# ログイン利用者を有効化
python admin_doctors.py enable --name "清水太郎"

# ログイン権限を付けずに勤務担当医だけ登録
python admin_doctors.py add-roster --name "福田"
python admin_doctors.py list-roster

# 勤務医名簿での割当候補だけを無効化・再有効化（過去の勤務は残る）
python admin_doctors.py set-roster-status --name "福田" --inactive
python admin_doctors.py set-roster-status --name "福田" --active
```

### admin_shifts.py - シフト管理

```bash
# 月別シフト一覧を表示
python admin_shifts.py list-assignments --month "2026-06"

# シフトを割り当てる
python admin_shifts.py add --doctor "清水太郎" --date "2026-06-15" --shift "当直" --note "ER対応"

# 割り当てを削除
python admin_shifts.py delete --id "..."

# 特定医師の月別シフトを表示
python admin_shifts.py doctor-shifts --doctor "清水太郎" --month "2026-06"
```

---

## 📤 CSV からシフトをインポート

### shifts.csv の形式

```csv
doctor_name,duty_date,shift_type,note
清水太郎,2026-06-11,当直,
田中花子,2026-06-12,当直,ER対応
佐藤次郎,2026-06-13,外勤,
```

**カラム説明:**
- `doctor_name`: 医師フルネーム（profiles.full_name に存在していること）
- `duty_date`: 日付 (YYYY-MM-DD 形式)
- `shift_type`: シフト種別 ("当直" または "外勤")
- `note`: 備考（オプション）

### インポート実行

```bash
python import_csv_upsert.py
```

出力例：
```
📍 医師情報を取得中...
📍 シフト種別を取得中...
✅ 医師 3 件、シフト種別 2 件

📤 3 件をインポート中...
✅ 3 件がインポートされました
```

**エラー時:**
```
⚠️  エラー:
   行2: 医師 'Shimizu' が見つかりません
   行4: 日付形式が不正です '2026/06/11'
```

---

## 📆 Google カレンダーから取り込み（Google カレンダーが正）

`import_gcal.py` は指定月の勤務を Google カレンダーの内容に合わせます（追加・変更・削除）。

### 初回準備

1. Supabase の SQL Editor で `supabase/migrations/20261002020000_add_gcal_uid_to_assignments.sql` を実行
2. Google カレンダー → 対象カレンダーの「設定と共有」→ **iCal 形式の非公開アドレス** をコピー
3. 実行時に聞かれたら貼り付ける（または環境変数 `GCAL_ICS_URL` で渡す）

⚠️ 非公開アドレスは知っていれば誰でも予定を読めます。Git 管理の `.env` には書かないこと。漏れた場合は Google カレンダーの設定でリセットしてください。

### 予定の書き方

予定タイトルに **勤務医名簿の医師名** と **シフト種別名**（`当直` / `外勤`）を入れます。残りの文字は備考になります。

| 予定タイトル | 取り込み結果 |
|---|---|
| `清水太郎 当直` | 清水太郎 / 当直 |
| `当直：清水 太郎 (ER対応)` | 清水太郎 / 当直 / 備考「ER対応」 |
| `外勤 福田`（終日・2日間） | 福田 / 外勤 を2日分 |
| `医局会` | 医師名も種別もないので無視 |

- 1つの予定に医師は1名
- 終日予定は各日、時刻付きの予定は開始日（日本時間）の勤務になる。翌朝までの当直は開始日
- 繰り返し予定も1回ずつ取り込む
- 名字だけなど名簿と表記が違う場合は `gcal_aliases.csv` に対応を書く

```csv
alias,doctor_name
清水,清水太郎
```

### 実行

```bash
# 変更内容の確認だけ
uv run import_gcal.py --month 2026-11 --dry-run

# 確認して反映（複数月も可）
uv run import_gcal.py --month 2026-11 --month 2026-12

# 手元の .ics ファイルから
uv run import_gcal.py --month 2026-11 --ics calendar.ics
```

出力例：
```
  ＋ 追加  2026-11-10 福田 外勤
  ～ 変更  2026-11-03 清水太郎 当直 → 2026-11-03 清水太郎 当直 (ER対応)
  － 削除  2026-11-25 田中花子 外勤
  ？ 手入力のみ (残す)  2026-11-26 田中花子 外勤
  ・ 勤務以外として無視  2026-11-13 「医局会」

⚠️  解釈できない予定 (この予定の既存勤務は変更しません):
   2026-11-14 「当直 山田」: 勤務医名簿にある医師名が見つかりません (別名は gcal_aliases.csv に登録)
```

- Google カレンダーで消した・日付を変えた予定の勤務は削除される
- アプリや CSV で手入力した勤務は、同じ医師・種別・日付の予定があれば Google 予定に紐付け、なければ残す（`--delete-manual` で削除）
- 解釈できない予定は既存の勤務を変更しないので、予定を直してから再実行する

---

## 🔄 ワークフロー例

### 初期セットアップ

```bash
# 1. 接続確認
python test_connection.py

# 2. 医師を登録 (Supabase Auth で作成した User ID を使用)
python admin_doctors.py add --id "550e8400-..." --name "清水太郎"
python admin_doctors.py add --id "550e8401-..." --name "田中花子"

# 3. 自分を管理者に昇格
python admin_doctors.py set-admin --name "清水太郎"

# 4. 確認
python admin_doctors.py list-all
```

### 月別シフト設定

```bash
# 方法1: CLI で1件ずつ割り当て
python admin_shifts.py add --doctor "清水太郎" --date "2026-06-11" --shift "当直"

# 方法2: CSV で一括インポート
# shifts.csv を編集 → python import_csv_upsert.py

# 方法2': Google カレンダーから取り込み（推奨）
uv run import_gcal.py --month "2026-06"

# 方法3: 割り当て確認
python admin_shifts.py list-assignments --month "2026-06"

# 方法4: 月別集計を確認
python main.py summary --month "2026-06"
```

### 医師の月別回数確認

```bash
python main.py monthly-count --doctor "清水太郎" --month "2026-06"
```

---

## 📱 React フロントエンド

React アプリは `duty-calendar/` ディレクトリで構成されています。

```bash
cd duty-calendar
npm install
npm run dev
```

画面での操作：
1. **医師ログイン**: メール・パスワード
2. **カレンダー表示**: 月別シフト確認
3. **管理画面**: 管理者のみ
   - `/calendar` - シフト割り当て
   - `/summary` - 月別集計
   - `/admin/doctors` - 医師管理

---

## 🐛 トラブルシューティング

### エラー: `Missing SUPABASE_URL or SUPABASE_KEY`

`.env` ファイルが正しく設定されているか確認：

```bash
cat .env
```

### エラー: `relation "profiles" does not exist`

Supabase スキーマが投入されていません。以下の SQL を実行：

```sql
-- Supabase ダッシュボード → SQL Editor で以下を実行
-- 詳細はドキュメント冒頭の「Supabase スキーマ投入」を参照
```

### CSV インポート時に医師が見つからない

医師が `profiles` テーブルに登録されているか確認：

```bash
python main.py list-doctors
```

見つからない場合は以下で登録：

```bash
python admin_doctors.py add --id "<user-id>" --name "医師名"
```

### CLI コマンドが見つからない

`uv sync` で再度依存パッケージをインストール：

```bash
uv sync
```

---

## 📊 データベース構造

### テーブル一覧

| テーブル名 | 用途 | 主なカラム |
|---|---|---|
| `profiles` | ログイン利用者・管理権限 | id (auth.users と同じ), full_name, role, is_active |
| `doctors` | ログイン権限と独立した勤務担当医名簿 | id, full_name, is_active, profile_id (任意) |
| `shift_types` | 勤務種別マスタ | id, name, color |
| `assignments` | シフト割り当て | id, duty_doctor_id, shift_type_id, duty_date, note, gcal_uid (Google 予定 UID・手入力は null), doctor_id (旧互換) |
| `monthly_counts` | 月別集計（ビュー） | doctor_id, shift_type_id, month, cnt |

### RLS ポリシー

| テーブル | ルール | 対象 |
|---|---|---|
| `profiles` | 有効な登録医師が読み取り可（自分の行は常に可） / 管理者のみ編集 | 管理者のみ INSERT/UPDATE/DELETE |
| `doctors` | 有効な登録利用者が読み取り可 / 管理者のみ編集 | 管理者のみ INSERT/UPDATE/DELETE |
| `assignments` | 有効な登録医師が読み取り可 / 管理者のみ編集 | 管理者のみ INSERT/UPDATE/DELETE |
| `shift_types` | 有効な登録医師が読み取り可 / 管理者のみ編集 | 管理者のみ INSERT/UPDATE/DELETE |

匿名（未ログイン）ユーザーはすべて読み取り不可。定義は `supabase/migrations/` を参照。

---

## 🔐 セキュリティ

- 🔑 `SUPABASE_KEY` (anon key) は Git に上がらない（.gitignore）
- 🛡️ RLS ポリシーで管理者以外の編集を防止
- 🔐 パスワードは Supabase Auth で安全に保管

---

## ❓ よくある質問（FAQ）

### Q: スマートフォンで使えますか？

**A:** はい。ブラウザ版（https://supabase-mac.vercel.app/）はレスポンシブ対応しており、スマートフォンで問題なく動作します。

### Q: ログイン利用者が追加されません

**A:** アプリにログインさせる場合のみ以下を確認（勤務表に載せるだけなら画面の「勤務医を追加」を使用）：
1. Supabase Auth でユーザーを作成した
2. Python CLI で `admin_doctors.py add` で profiles に登録した
3. 医師の `is_active` が `true` になっている

### Q: カレンダーで月を変更しても集計が変わりません

**A:** ブラウザをリロード（Cmd+R or Ctrl+R）してください。

### Q: 勤務を追加したが表示されません

**A:** 以下を確認：
1. 管理者でログインしているか
2. ブラウザをリロードしたか
3. データベースに実際に保存されているか（Python CLI で確認）

### Q: ログイン画面に戻ってしまいます

**A:** 以下の理由が考えられます：
1. メール・パスワードが間違っている
2. Auth ユーザーが存在しない
3. ブラウザのクッキーが削除されている

### Q: オフラインでも使えますか？

**A:** 現在のバージョンはオンライン必須です。オフライン対応には Service Worker の追加が必要です。

### Q: パスワードをリセットしたい

**A:** Supabase ダッシュボード → **Authentication** → 該当ユーザーを選択 → **Reset password** でリセット可能です。

### Q: 複数PC・複数人で同時に使用できますか？

**A:** はい。Supabase がクラウド共有なため、複数人が同時にアクセスしても問題ありません。割り当て追加時はリアルタイムで全員に反映されます。

---

## 🚀 デプロイ

### 現在の本番環境

**ブラウザ版**: https://supabase-mac.vercel.app/

Vercel に自動デプロイ設定済み。`main` ブランチに push すると自動的に本番環境が更新されます。

### ローカル開発環境

React アプリのローカル開発：

```bash
cd duty-calendar
npm run dev
# http://localhost:3000 で実行
```

Python CLI の実行：

```bash
uv run main.py list-doctors
```

---

## 📚 参考資料

- [Supabase Python Client](https://github.com/supabase-community/supabase-py)
- [Click (Python CLI)](https://click.palletsprojects.com/)
- [Pandas](https://pandas.pydata.org/)

---

**最終更新**: 2026-06-12
