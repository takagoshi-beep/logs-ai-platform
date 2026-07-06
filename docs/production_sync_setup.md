# 「1クリックで両方完了」を実現する設定手順

logsys-chat 側の「ログシス DB同期」が完了した直後に、logs-ai-platform 側の
「生産管理データ同期」を自動で呼び出すための設定です。以下の3ステップを、
記載の順番で実施してください。

---

## ステップ1: logs-ai-platform リポジトリにSecretsを登録

`logs-ai-platform` リポジトリの Settings → Secrets and variables → Actions
→ "New repository secret" から、以下の3つを登録してください。

| Secret名 | 値 |
|---|---|
| `SUPABASE_DB_URL` | logsys-chat と同じ値 |
| `GOOGLE_SA_KEY_JSON` | 今回ダウンロードしたサービスアカウントのJSONファイルの中身をそのまま貼り付け |
| `PRODUCTION_SHEET_ID` | `1722vOB9mNUqFTjDkbPO3A6nz-WOsW0PSME2Voor5Iy8` |

---

## ステップ2: 個人アクセストークン(PAT)を作成

logsys-chat から logs-ai-platform のワークフローを起動するために必要です。

1. GitHubの右上のご自身のアイコン → Settings
2. 左メニュー一番下の "Developer settings"
3. "Personal access tokens" → "Fine-grained tokens" → "Generate new token"
4. 以下のように設定:
   - **Token name**: 例）`trigger-production-sync`
   - **Expiration**: お好みで(90日など。切れたら再発行が必要です)
   - **Repository access**: "Only select repositories" → `logs-ai-platform` を選択
   - **Permissions** → "Repository permissions" → **"Actions"** を **"Read and write"** に設定
5. "Generate token" を押すと表示される文字列(`github_pat_...`)を**コピー**してください(この画面を閉じると二度と表示されません)

---

## ステップ3: PATをlogsys-chatにSecretとして登録

`logsys-chat` リポジトリの Settings → Secrets and variables → Actions
→ "New repository secret" から登録:

| Secret名 | 値 |
|---|---|
| `PRODUCTION_SYNC_PAT` | ステップ2でコピーした`github_pat_...`の文字列 |

---

## ステップ4: sync.yml の末尾に、以下のステップを追加

`logsys-chat` リポジトリの `sync.yml` を開き、既存の「DB同期を実行」ステップの
**後に**、以下を追加してください。

```yaml
      - name: 生産管理データ同期を呼び出す
        run: |
          curl -X POST \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer ${{ secrets.PRODUCTION_SYNC_PAT }}" \
            https://api.github.com/repos/takagoshi-beep/logs-ai-platform/dispatches \
            -d '{"event_type":"production-data-sync"}'
```

（リポジトリ名 `takagoshi-beep/logs-ai-platform` の部分は実際のオーナー名/
リポジトリ名に合わせて調整してください。今回のやり取りから推測した値です。
異なる場合は教えてください。）

---

## これで実現されること

`logsys-chat` の「Run workflow」ボタンを1回押すだけで、

1. ログシス本体のExcel → Supabase同期(既存の`sync.py`)が実行される
2. 完了後、自動的に `logs-ai-platform` 側の「生産管理データ同期」が呼び出される
3. `production_samples` / `production_mass` の2テーブルが最新化される

という流れが、1クリックで完結します。