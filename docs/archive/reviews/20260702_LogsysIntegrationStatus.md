# Logsys Integration Status — Reasoning/Execution Layer

**Date:** 2026-07-02
**Scope:** Logsys only（案件管理シート／Gmail／Slackは対象外）
**Status:** 調査完了（コード変更なし）

---

## 1. 結論（先出し）

`backend/services/data_providers.py` の `LogisysProvider` は **本物のSQLite接続コード**であり、`mock_data`（ハードコードのPythonリスト）ではない。

しかし接続先の `logsys.db` は **実データではなく、seedスクリプトが生成した架空のデモDB** である。一方で、実際にGoogle Driveから同期された **本物のLogsysデータ（289MB、21テーブル、約30万行の売上明細を含む）が同じリポジトリ内の別パスに既に存在し、Reasoning Pipelineから未接続のまま放置されている**。

つまり「SQLite接続の仕組み」はすでに存在するが、「見ているデータ」が別物という状態。DB_PATHを差し替えるだけでは動かない — 理由は本文で述べる列名・データ形式の差異。

---

## 2. 現状の接続方式（実装レベルの事実）

### 2.1 二つの`logsys.db`

| | `backend/data/sqlite/logsys.db` | `data/sqlite/logsys.db`（リポジトリルート） |
|---|---|---|
| サイズ | 36,864 bytes | 302,825,472 bytes（約289MB） |
| 生成元 | `backend/scripts/seed_logisys_demo.py`（idempotentなseedスクリプト） | Google Drive同期パイプライン（`connector/google_drive/`, `services/project_service.py`ほか、`backend/`とは別系統の旧システム） |
| テーブル数 | 5（売上明細・仕入明細・案件・顧客マスタ・商品マスタ） | 21（うち11がgdrive同期／importメタデータ、実データは10テーブル） |
| 内容 | 完全な架空データ（Fanatics Japan, BEAMS JAPAN, UNITED ARROWS, ZOZOなど4社×売上明細14件） | 実際の売上199,512行・仕入44,855行・商品10,236行・顧客2,738件などLogsysの本番/履歴データ |
| Reasoning Pipelineからの接続 | **接続されている**（`data_providers.py`のDB_PATHがここを指す） | **接続されていない** |

`data_providers.py` の該当箇所:
```python
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "sqlite" / "logsys.db"
```
これは `backend/services/` を起点に2階層上がるため `backend/data/sqlite/logsys.db`（36KBのデモDB）に解決される。リポジトリルートの289MB本物DBとはファイル名が同じだけで別物。

`knowledge/reference/source_inventory.md` にも同様の記載がある:
> **Current State**: Not yet connected to consultation engine; mock data ... used for Phase 5-1
> Phase 5-3 (Mid-term): Connect logsys.db real data to consultation engine

### 2.2 mock_data系との違い

`GmailProvider` / `ProjectSheetProvider` / `SlackProvider`（`data_providers.py`内）は完全にハードコードされたPythonリストを返すスタブ。これに対し `LogisysProvider` は `sqlite3.connect(DB_PATH)` して実際にSQLを発行しており、実装パターンとしては「本物のDB接続」である。

`backend/services/mock_store.py` は別の旧機能（`/chat`, `/tasks`, `/home`エンドポイント、`backend/business/today_actions.py`）専用のデモデータで、Reasoning/Evidence Pipelineからは一切参照されていない（今回のスコープ外として確認のみ）。

---

## 3. 本物の289MB DBの実態（今回スキーマ調査した結果）

### 3.1 実データテーブル（10テーブル、デモ相当）

| 実テーブル | 行数 | デモ側の対応テーブル | 対応関係 |
|---|---|---|---|
| `売上` | 199,512 | `売上明細`（14行） | 列名が全く異なる（後述） |
| `仕入` | 44,855 | `仕入明細`（4行） | 列名が全く異なる |
| `商品` | 10,236 | `商品マスタ`（6行） | 列名が全く異なる |
| `顧客` | 2,738 | `顧客マスタ`（4行） | 列名が全く異なる。デモの「顧客コード」「別名」列は実テーブルに存在しない |
| `取引先` | 2,148 | （デモ側に対応なし） | 仕入先/取引先マスタ。デモは`仕入先名`のみ埋め込みで別マスタ化していない |
| `集計` | 16,705 | `案件`（5行） | デモの「案件」（ステータス・納期を持つ）に相当する概念が実データ側にはなく、`集計`テーブルは案件名・案件売上・案件粗利の集計行であってステータス/納期列を持たない |
| `発注依頼` | 34,733 | （対応なし） | 生産管理向けの発注案件テーブル。デモには存在しない概念 |
| `顧客担当者` | 3,816 | （対応なし） | 顧客の担当者コンタクト情報 |
| `コード` | 199 | （対応なし） | コードマスタ（ステータスや区分の値を人間可読名に変換するための参照テーブルと推測） |
| `仕入諸掛` | 21,390 | （デモは仕入明細に内包） | 仕入の諸掛（付帯費用）明細。デモでは概念ごと省略されている |

残り11テーブルは `gdrive_sync_registry` / `gdrive_source_catalog` / `import_registry` / `table_schema_registry` / `validation_report` など同期・監査用メタデータで、業務データではない。

### 3.2 列名・データ形式の差異（サンプリングで確認した具体例）

- デモ `売上明細`: `顧客名`, `案件区分`, `金額`, `概算粗利`, `status`（英語カラム名、想定は数値コード）
- 実 `売上`: `得意先名`, `事業分類`, `売上金額`, `粗利`/`明細粗利`, `ステータス`（列名が日本語＆別体系）
- 実データの `ステータス` / `決済方法` は **文字列型の数値コード**（例: `"2"`, `"1"`）。値の分布を確認したところ `ステータス IN ('2','3','5')` と `決済方法` の組み合わせがBR-SALES-STANDARD-001の想定（`status IN (2,3,4,5) AND payment_method != 4`）と概ね整合しており、ルール自体は実データ設計を前提に書かれていたことが確認できた。ただし型が数値ではなく文字列なので、SQLの比較演算子・WHERE句をそのまま流用はできない。
- 金額系カラム（`案件売上`, `案件粗利`など`集計`テーブル）は `"5,000,000"` のようにカンマ区切りの文字列で格納されており、集計前に数値パースが必要（デモDBは素のINTEGER）。
- 顧客名を `顧客名称 LIKE '%Fanatics%'` で検索してもヒットなし — デモの顧客名（Fanatics Japan, BEAMS JAPAN, UNITED ARROWS, ZOZO）は完全に架空で、実データの顧客とは無関係。Q2「Fanatics案件の状況」のような質問は、実データに切り替えた瞬間にEntity Resolutionが破綻する（該当顧客が存在しない）。

### 3.3 案件（プロジェクト）概念のギャップ

デモの `案件` テーブルは `ステータス`・`納期` を持つ「案件マスタ」だが、実データ側にはこれに相当する単一テーブルが存在しない。最も近いのは `集計`（案件名・案件売上・案件粗利の集計スナップショット、ステータス/納期列なし）と `発注依頼`（生産管理の案件、大量の物流・生産管理向け列を持つ）。「案件の状況」を問うQ2/Q3の実装には、案件の定義そのものを再設計する必要がある。

---

## 4. 実DB切り替えに必要な変更（見積もり）

`DB_PATH` の付け替えだけでは動かない。最低限必要な変更:

1. **DB_PATH変更**: `backend/data/sqlite/logsys.db` → 実DBパスへ（ファイルの物理的な置き場所／同期方法は要検討。289MBをbackend配下にコピーするか、リポジトリルートを直接参照するか）
2. **全SQLクエリの書き換え**（`LogisysProvider`の`_sales_lines`, `_purchase_lines`, `_projects`, `_customer_master`, `_product_master`, `_project_classification`, `_cancelled_sales` 相当、計7メソッド）: テーブル名・列名が別体系のため、実質的に新規実装に近い書き直しが必要
3. **型変換処理の追加**: ステータス/決済方法（文字列コード）、金額（カンマ区切り文字列）をSQL/Python側で数値化する処理
4. **「案件」概念の再設計**: `集計`または`発注依頼`のどちらを「案件」として扱うか、あるいは両方を組み合わせるかの業務判断が必要（Step 3で設計方針を提示）
5. **Entity Resolution（顧客名解決）の見直し**: デモ専用の架空顧客名（Fanatics等）を前提にした質問例が実データでは成立しない。対象4問のうちQ2は実データ切り替え後、質問自体か顧客名解決ロジックの見直しが必要
6. **BR-SALES-STANDARD-001等の既存ルールの再検証**: ルールの意図（status/payment_methodフィルタ）は実データと整合していそうだが、値の型・具体的なコード対応表（`コード`テーブル参照）を用いた検証が必要

**規模感**: Provider内の全fetchメソッド（7個）の書き直し＋型変換ヘルパー追加＋案件概念の設計判断、が主な作業。Evidence Integration Layer / Evidence Interpretation Layerは「provider/datasetの組でグルーピングし、facts関数もprovider/dataset単位」で疎結合になっているため、**Provider層の出力さえ現行と同じレコード形状（dict list）で返せば、Integration/Interpretation/Reasoningへの変更は基本的に不要**。影響範囲はProvider層に閉じ込められる。

---

## 5. 影響範囲

- **変更が必要**: `backend/services/data_providers.py`（`LogisysProvider`のみ）
- **変更不要（設計上、疎結合が効いている）**: `evidence_integration.py`, `evidence_interpreter.py`, `reasoning_pipeline.py`, `frontend/app/reasoning/page.tsx`
- **対象外（今回のスコープ外）**: `GmailProvider`, `ProjectSheetProvider`, `SlackProvider`

---

## 6. 推奨する作業順序

1. 実DB（289MB）の物理配置方針を決定（コピー配置 or 直接参照、読み取り専用アクセスの確認）
2. `コード`テーブルの中身を調査し、ステータス/決済方法/事業分類などのコード値マッピング表を確定
3. `売上`/`仕入`/`商品`/`顧客`向けに新しいクエリメソッドを実装（列名マッピング＋型変換）、既存の7メソッドと1:1で置き換え
4. 「案件」概念を`集計`ベースで再定義するか設計判断（Step 3参照）
5. Q1・Q4（OEM粗利、売上首位顧客）から先に実データ切替の動作確認 — 顧客名・案件区分がデモに依存しないため影響が小さい
6. Q2・Q3（Fanatics案件、優先案件）は「案件」概念の再設計が前提のため後回し

---

## 7. Step 3: Provider置き換え設計（Importerパターンは採用しない）

目標構造は変わらず: `Reasoning → Logsys Provider(SQLite直接読み込み) → Evidence → Interpretation`。Logsysは既にDBとして存在しているため、Excel/CSVを介したImport/ETL層を新設する必要はない — `LogisysProvider`が289MBのSQLiteファイルに対して直接SQLを発行する形を維持する（現行の実装パターンをそのまま踏襲）。

設計方針:

- **`LogisysProvider`のインターフェース（`fetch(dataset, params) -> dict`）は変更しない**。Reasoning/Integration/Interpretation層からは今と同じ呼び出し方で使える。
- **DB_PATHのみ環境切り替え可能にする**（例: 環境変数`LOGSYS_DB_PATH`でデモDBと実DBを切り替え、未設定時は現行のデモDBにフォールバック）。これによりデモ環境と実データ環境を共存させたまま段階的に移行できる。
- **各`_xxx`メソッド内部で、実テーブルの列名→デモと同じ出力キー（例: `顧客名`, `金額`, `概算粗利`）へマッピングする変換ロジックを持たせる**。呼び出し側（Evidence Integration/Interpretation）が期待するレコード形状は変えない。
- **コード値変換（ステータス・決済方法など）は`コード`テーブルを参照するヘルパー関数として切り出す**（Provider内の各メソッドが共通利用）。
- **「案件」データセットは`集計`テーブルをベースに再構築**し、ステータス・納期に相当する情報が存在しない場合は`unknown`としてReasoning側に伝える（Decision Gateが「情報不足」を正しく判定できるようにする — 存在しないデータを捏造しない）。
- Importer/ETLパターンを採用しない理由: Logsysは既に構造化されたSQLiteとして存在しており、変換すべきは「ファイル形式」ではなく「クエリのマッピング」のみ。中間テーブルへのバッチ変換を挟むと、同期タイミングのズレ・二重管理のリスクが生じるため、直接クエリで都度マッピングする方が実データの鮮度と単純さを保てる。

---

## 8. Developer Verification

① **Logsysは現在、実SQLiteかmock_dataか？**
実SQLite接続の実装ではあるが、接続先のDBが架空のデモデータ（`backend/data/sqlite/logsys.db`, 36KB）。本物のLogsysデータ（289MB、実売上199,512行等）は別パス（`data/sqlite/logsys.db`）に存在するが未接続。

② **実SQLiteへの切り替えに必要な変更規模は？**
`LogisysProvider`内の7つのfetchメソッド全ての書き直し（テーブル名・列名マッピング、コード値変換、金額の文字列→数値変換）＋「案件」概念の再設計。Evidence Integration/Interpretation/Reasoning/フロントエンドは変更不要（疎結合設計が効いている）。

③ **切り替え後、Reasoningはそのまま使えるか？**
Yes（Provider層のインターフェースと出力レコード形状さえ維持すれば）。ただしQ2（Fanatics案件）はデモ専用の架空顧客名に依存しているため、実データ切り替え後は質問自体か顧客名解決ロジックの見直しが必要になる。Q1・Q4は顧客名や案件区分をデモ値に依存していないため影響が小さい。

④ **次フェーズ候補**:
- 案件管理シート（Google Sheets）接続
- Gmail接続
- Natural Answer生成（現在はConfidence/Fact羅列のみで自然文回答なし）
