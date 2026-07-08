# Renderへのデプロイ手順(Web化)

Render 1つのアカウントに、「バックエンド用」「フロントエンド用」の2つのWeb Serviceを作ります。**バックエンドを先に作ってURLを確定させてから、フロントエンドを作る**という順番が重要です(フロントエンドがバックエンドのURLを知る必要があるため)。

## 事前準備

1. [Render](https://render.com/)にアカウントを作成し、GitHubアカウントと連携する
2. `logs-ai-platform`リポジトリへのアクセスを許可する

---

## ステップ1: バックエンド用のWeb Serviceを作る

1. Renderのダッシュボードで「New +」→「Web Service」
2. `logs-ai-platform`リポジトリを選択
3. 以下のように設定する

| 項目 | 値 |
|---|---|
| Name | 任意(例: `logs-ai-backend`) |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Starter(月$7程度。無料枠は常時起動できないため今回は非推奨) |

4. 「Environment Variables」に、`.env`にある内容を全て登録する

```
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
SUPABASE_DB_URL=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
GOOGLE_OAUTH_CLIENT_ID=...
ADMIN_EMAILS=...
SESSION_SECRET_KEY=...
FRONTEND_URL=（まだ空欄でよい。ステップ3で戻って設定します）
```

5. 「Create Web Service」を押してデプロイを開始する
6. デプロイが完了すると、`https://logs-ai-backend-xxxx.onrender.com`のようなURLが発行されます。**このURLを控えておいてください**

---

## ステップ2: フロントエンド用のWeb Serviceを作る

1. 同様に「New +」→「Web Service」→同じリポジトリを選択
2. 以下のように設定する

| 項目 | 値 |
|---|---|
| Name | 任意(例: `logs-ai-frontend`) |
| Root Directory | `frontend` |
| Runtime | Node |
| Build Command | `npm install && npm run build` |
| Start Command | `npm run start` |
| Instance Type | Starter |

3. 「Environment Variables」に、以下を登録する

```
NEXT_PUBLIC_API_BASE=ステップ1で控えたバックエンドのURL
NEXT_PUBLIC_GOOGLE_CLIENT_ID=（.env.localと同じ値）
```

4. 「Create Web Service」を押してデプロイする
5. 完了すると、`https://logs-ai-frontend-xxxx.onrender.com`のようなURLが発行されます。**これが、社内の皆さんに共有する実際のURLになります**

---

## ステップ3: バックエンドに戻って、フロントエンドのURLを設定する

1. ステップ1で作ったバックエンドのWeb Serviceの設定画面に戻る
2. 「Environment Variables」の`FRONTEND_URL`に、ステップ2で発行されたフロントエンドのURLを設定する

```
FRONTEND_URL=https://logs-ai-frontend-xxxx.onrender.com
```

3. 保存すると、バックエンドが自動的に再起動します

---

## ステップ4: Google OAuthの設定を更新する

Google Cloud Consoleに戻り、以前作成したOAuthクライアントIDの設定を開いてください。

「承認済みの JavaScript 生成元」に、フロントエンドの本番URLを追加してください(`http://localhost:3000`は残したままで構いません。ローカル開発でも引き続き使うためです)。

```
https://logs-ai-frontend-xxxx.onrender.com
```

---

## ステップ5: 動作確認

1. フロントエンドのURL(`https://logs-ai-frontend-xxxx.onrender.com`)をブラウザで開く
2. ログイン画面が表示されるか確認
3. 社員のGoogleアカウントでログインできるか確認
4. `chat`・`資料作成`など、一通りの機能が動くか確認

---

## 補足: なぜ2つのWeb Serviceが必要なのか

Next.js(画面)とFastAPI(頭脳)は、全く別のプログラムとして動いています。Render1つのアカウントの中であっても、この2つは別々の「サービス」として起動しておく必要があります(1つのサービスで両方を同時に動かすことはできません)。ただし、管理画面・請求は1つのRenderアカウントにまとまるので、「あちこちのサービスを契約する」という状態にはなりません。

## 補足: 費用の目安

- バックエンド用Web Service: Starterプランで月$7程度
- フロントエンド用Web Service: Starterプランで月$7程度
- 合計: 月$14程度(約2,000円強)+ 既存のSupabase・Anthropic APIの利用料

## 補足: セッションCookie(ログイン状態)の仕組みが自動的に切り替わります

ローカル開発(`http://localhost`)と、Renderにデプロイした後(`https://...`)とで、ログイン状態を保持するCookieの安全性設定が自動的に切り替わるよう、`backend/main.py`を修正済みです。これは`FRONTEND_URL`という1つの環境変数の値(`https://`で始まるかどうか)を見て、バックエンドが自動的に判断します。ローカル開発時に`FRONTEND_URL`を設定する必要はありません(未設定時は自動的にローカル用の設定になります)。
