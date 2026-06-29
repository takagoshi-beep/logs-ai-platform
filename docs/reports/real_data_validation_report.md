# Real Data Validation Report

## 検証日時

- 2026-06-29T04:50:18.722726+00:00

## 対象Google Drive folder_id

- not configured

## 読み込んだファイル一覧

- Not executed: GOOGLE_OAUTH_ENABLED, GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH, GOOGLE_DRIVE_FOLDER_ID, GOOGLE_OAUTH_ENABLED must be true

## 読み込んだシート一覧

- Not executed

## rows_imported

- 0

## validation結果

- Not executed

## catalog結果

- Not executed

## 実質問テスト結果

- Not executed

## 失敗ケース

- Real Google Drive OAuth prerequisites are not satisfied in this environment.

## 修正が必要な点

- Set GOOGLE_OAUTH_ENABLED=true.
- Provide GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH, and GOOGLE_DRIVE_FOLDER_ID.
- Re-run this report after generating token.json and syncing the target folder.
