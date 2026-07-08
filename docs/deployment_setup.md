# Web化準備: データ保存先のSupabase移行セットアップ

これは、ローカルファイルに保存していた運用データ(帳票フォーマットの定義・実行履歴・Governance承認履歴など)を、クラウド上でも消えないようSupabaseに移す作業の手順書です。今回は**第1弾: 帳票フォーマット**の移行分です。

## ステップ1: Supabaseにテーブルを作成する

1. [Supabaseダッシュボード](https://supabase.com/dashboard)を開く
2. 対象のプロジェクトを選択
3. 左メニューの「SQL Editor」を開く
4. `docs/sql/14_23_document_formats.sql`の中身をコピーして貼り付け、実行してください

実行後、左メニューの「Table Editor」で`app_document_formats`というテーブルが作られていることを確認してください。

## ステップ2: Supabase Storageにバケットを2つ作成する

「バケット」は、ファイル(Excelファイルなど)を置くための場所です。データベースのテーブルとは別物です。

1. Supabaseダッシュボードの左メニューから「Storage」を開く
2. 「New bucket」を押し、以下の名前で**2つ**作成してください
   - `document-templates`(アップロードされた元のExcelテンプレート)
   - `generated-documents`(生成された帳票ファイル)
3. どちらも「Public bucket」のチェックは**入れないでください**(社内データのため非公開のままにします。ダウンロードはアプリのバックエンド経由で行うので、非公開でも問題なく動作します)

## ステップ3: 環境変数を追加する

`logs-ai-platform/.env`に、以下の2つを新しく追加してください(`SUPABASE_DB_URL`とは別物です)。

```
SUPABASE_URL=プロジェクトのURL
SUPABASE_SERVICE_ROLE_KEY=サービスロールキー
```

これらは、Supabaseダッシュボードの「Project Settings」→「API」の画面で確認できます。

- `SUPABASE_URL`: 「Project URL」という項目にある値(`https://〜.supabase.co`の形式)
- `SUPABASE_SERVICE_ROLE_KEY`: 「Project API keys」の中の**「service_role」**というキー(「anon」ではなく「service_role」の方です。バックエンドサーバーだけが扱う、強い権限を持つ鍵なので、`.env`以外の場所に書いたり、フロントエンドに埋め込んだりしないでください)

## ステップ4: 追加でインストールが必要なパッケージ

```powershell
pip install supabase
```

## ステップ5: 再起動して確認する

```powershell
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
cd backend
uvicorn main:app --reload --port 8000
```

起動できたら、`資料作成`画面から**新しい帳票フォーマットをアップロード**してみてください。以前と同じように動作すれば成功です。念のため、Supabaseダッシュボードの「Table Editor」で`app_document_formats`テーブルに新しい行が増えていることも確認してみてください。

## 今回の移行で変わらないこと

- 画面の操作方法・見た目は一切変わりません
- 承認フローの流れも変わりません
- 既存の`pytest`のテスト(255件)は全てモック化されているため、実際のSupabase接続なしでも通ります

## 今回の移行で失われるもの

**現時点でローカルに保存されている、動作確認用の帳票フォーマットのデータは引き継がれません**(以前確認いただいた通り、動作確認用のデータなので問題ない、というご判断をいただいています)。移行後は、新しくアップロードしたものから全てSupabase上に保存されます。
