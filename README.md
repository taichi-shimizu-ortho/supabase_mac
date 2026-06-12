# 医師シフト管理システム

医師たちがスマートフォンでシフトを確認・管理できるシステムです。

---

## 🌐 ブラウザ版（医師向け）

### アクセス方法

**URL**: https://supabase-mac.vercel.app/

スマートフォン・PC のどちらからでもアクセス可能です。

### ログイン

1. メールアドレスを入力
2. パスワードを入力
3. **ログイン** をクリック

### 機能

| 画面 | 説明 |
|---|---|
| **カレンダー** | 当月のシフトをカレンダー表示 |
| **月選択** | カレンダーで月を切り替え → 集計も自動更新 |
| **集計表示** | 選択月の当直・外勤回数を医師ごとに表示 |
| **勤務追加** | 管理者のみ表示 - 医師のシフトを追加・編集 |

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
1. **追加** ボタンをクリック
2. 以下を入力：
   - **医師を選択**: ドロップダウンから医師名を選択
   - **シフト種別**: 「当直」または「外勤」
   - **日付**: YYYY-MM-DD 形式
   - **備考**: オプション（ER対応など）
3. **保存** をクリック

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

# 医師を削除
python admin_doctors.py delete --name "清水太郎"

# 管理者に昇格
python admin_doctors.py set-admin --name "清水太郎"

# 医師に降格
python admin_doctors.py set-doctor --name "清水太郎"

# 医師を無効化（非表示）
python admin_doctors.py disable --name "清水太郎"

# 医師を有効化
python admin_doctors.py enable --name "清水太郎"
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
| `profiles` | 医師プロフィール | id, full_name, role, is_active |
| `shift_types` | 勤務種別マスタ | id, name, color |
| `assignments` | シフト割り当て | id, doctor_id, shift_type_id, duty_date, note |
| `monthly_counts` | 月別集計（ビュー） | doctor_id, shift_type_id, month, cnt |

### RLS ポリシー

| テーブル | ルール | 対象 |
|---|---|---|
| `profiles` | 全員が読み取り可 | ✅ ログイン済み |
| `assignments` | 全員が読み取り可 / 管理者のみ編集 | 管理者のみ INSERT/UPDATE/DELETE |
| `shift_types` | 全員が読み取り可 | ✅ ログイン済み |

---

## 🔐 セキュリティ

- 🔑 `SUPABASE_KEY` (anon key) は Git に上がらない（.gitignore）
- 🛡️ RLS ポリシーで管理者以外の編集を防止
- 🔐 パスワードは Supabase Auth で安全に保管

---

## ❓ よくある質問（FAQ）

### Q: スマートフォンで使えますか？

**A:** はい。ブラウザ版（https://supabase-mac.vercel.app/）はレスポンシブ対応しており、スマートフォンで問題なく動作します。

### Q: 医師が追加されません

**A:** 以下を確認：
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
