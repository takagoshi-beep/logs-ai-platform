# Verified Business Rules

## Knowledge Architecture
- Business Rule
- Business Vocabulary
- Semantic Catalog
- Knowledge Source Layer
- Memory Layer
- Capability Library
- Business Context Resolution
- Intent Resolution
- Meaning Resolution
- Required Knowledge Planning
- Required Memory Planning
- Entity Resolution
- Task Planning
- Execution Planning
- Execution
- Business Concept
- Business KPI
- Business Grain
- Analysis Purpose
- Required Dataset
- Query Planning
- SQL Generation

## Knowledge Flow
- Natural Language
- Intent Resolution
- Meaning Resolution
	- Entity Resolution
	- KPI Resolution
	- Time Resolution
	- Grain Resolution
	- Analysis Purpose Resolution
- Required Knowledge Planning
- Required Memory Planning
- Task Planning
- Capability Selection
- Execution Planning
- Execution
- Validation
- Presentation

## Runtime Design
- intent_resolution
- meaning_resolution
- required_knowledge_planner
- required_memory_planner
- task_planner
- knowledge_retrieval_interface
- memory_retrieval_interface
- capability_registry
- capability_router
- execution_planner
- executor
- validator
- presenter

### Runtime Constraint
- 新しいRuntimeは上記責務に統合し、Intent別/機能別の独立Runtimeを乱立させない。

## Theme 22: Knowledge Source Layer

### Verified Business Rule
- rule_id: BR-KNOWLEDGE-SOURCE-LAYER-027
- status: verified
- scope: Knowledge Architecture
- statement: Knowledge SourceはInternalとExternalに分類し、同一パイプラインで扱う。
- internal_sources:
	- Internal Database
	- Business Dictionary
	- Business Rules
	- Documents
	- Email
	- Slack
	- Calendar
	- CRM
- external_sources:
	- Web Search
	- Official Company Website
	- Press Release
	- News
	- Industry Report
	- Regulation
	- Market Trend
	- Social Trend
	- Weather
	- Exchange Rate
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-KNOWLEDGE-METADATA-028
- status: verified
- scope: Knowledge Source Metadata
- statement: Knowledge Sourceごとに標準Metadataを付与し、Runtime判断に利用する。
- required_metadata:
	- source_type
	- source_name
	- trust_level
	- freshness
	- updated_at
	- retrieval_method
	- cost
	- permission
	- citation_required
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-REQUIRED-KNOWLEDGE-PLANNING-029
- status: verified
- scope: Task Planning連携
- statement: Task PlanningはIntent/Taskに応じてRequired Knowledgeを決定し、Execution Planningへ引き渡す。
- required_knowledge_examples:
	- BEAMSの粗利 -> Internal only
	- BEAMS向け提案作成 -> Internal + External
	- 今年のバッグ市場動向 -> External primary
	- 現在対応すべき案件 -> Internal only
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-KNOWLEDGE-RETRIEVAL-INTERFACE-030
- status: verified
- scope: Runtime Interface
- statement: Web取得実装は追加せず、Knowledge Retrieval Interfaceをスタブとして定義する。
- interface_methods:
	- retrieve_internal()
	- retrieve_external()
	- merge_context()
	- prioritize_sources()
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-KNOWLEDGE-CAPABILITY-MAPPING-031
- status: verified
- scope: Capability Mapping
- statement: CapabilityごとにRequired Knowledge Sourceを定義し、Capability Selectionで参照する。
- mapping:
	- Data Query -> Internal
	- Proposal -> Internal + External
	- Document Generation -> Internal + External
	- Monitoring -> Internal + External
	- Communication -> Internal
	- Workflow -> Internal
	- Knowledge Retrieval -> Internal + External
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 23: Memory Layer

### Verified Business Rule
- rule_id: BR-MEMORY-LAYER-032
- status: verified
- scope: Knowledge/Memory Separation
- statement: Memory LayerはKnowledge Layerと分離し、過去の出来事・判断・経験・学習を扱う。
- knowledge_examples:
	- 実際粗利 = 売上実績 - 仕入実績
	- KPI定義
	- Dataset定義
	- Business Rule
- memory_examples:
	- Fanatics案件では旧正月前の発注遅れが納期遅延につながった
	- GOLDWIN提案ではDPPを最初に確認すると話が早かった
	- BEAMS向け提案では過去に価格より企画性が重視された
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 24: Production UI Architecture

### Verified Business Rule
- rule_id: BR-UI-ARCHITECTURE-039
- status: verified
- scope: Product UI Direction
- statement: End User向けUIはNext.js/Reactを前提とし、実運用で触れる画面を先に構築する。
- frontend_stack:
	- Next.js
	- React
	- TypeScript
	- Tailwind CSS
	- shadcn/ui
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-STREAMLIT-DEBUG-040
- status: verified
- scope: UI Governance
- statement: Streamlitは開発者向けDebug UIに限定し、End User本番UIとしては採用しない。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-UI-INDEPENDENT-RUNTIME-041
- status: verified
- scope: Runtime Independence
- statement: AI Runtime/Knowledge/Memory/Capability/EvaluationはUI非依存で設計する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-UI-BACKEND-SEPARATION-042
- status: verified
- scope: Architecture Boundary
- statement: FrontendとBackend APIを分離し、UIはAPI契約を介してRuntimeへ接続する。
- backend_services:
	- AI Runtime
	- Knowledge Retrieval
	- Memory Retrieval
	- Capability Router
	- Evaluation Logger
	- Auth/Permission
	- File Generator
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-UI-MVP-SCREENS-043
- status: verified
- scope: MVP Scope
- statement: 初期MVPはHome/Chat/Tasks/Proposal Builder/History/Debug Trace Panelを対象とする。
- mvp_screens:
	- Home
	- Chat
	- Tasks
	- Proposal Builder
	- History
	- Debug Trace Panel
	- Documentsは初期はドラフト設計まで
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-UI-API-CONTRACT-044
- status: verified
- scope: Frontend API Contract
- statement: End User UIは標準API群を利用し、実行履歴とTraceを取得可能にする。
- api_endpoints:
	- POST /api/chat
	- POST /api/tasks/recommend
	- POST /api/proposals/draft
	- POST /api/documents/draft
	- GET /api/history
	- GET /api/executions/{id}
	- GET /api/evaluation/summary
	- GET /api/debug/trace/{id}
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-UI-EVALUATION-LINK-045
- status: verified
- scope: Evaluation Integration
- statement: UI操作はEvaluation Eventとして保存し、将来のRegression Testに変換可能にする。
- event_fields:
	- user_input
	- ai_response
	- intent
	- task
	- capability
	- validation
	- user_feedback
	- accepted_rejected
	- corrected_output
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 25: Product and UX Design

### Verified Business Rule
- rule_id: BR-PRODUCT-WORK-ENTRY-046
- status: verified
- scope: Product Vision
- statement: LOGS AI OSはチャットツールではなく、社員が毎日仕事を始める入口として設計する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-WORK-FIRST-UX-047
- status: verified
- scope: UX Principles
- statement: 通常画面は「何ができたか・何を確認すべきか・次に何をすべきか」を中心に表示し、Chatは機能の一つとして扱う。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-ROLE-BASED-HOME-048
- status: verified
- scope: Home UX
- statement: Homeは朝ログイン時に今日やるべき仕事を役割別に提示する。
- core_home_blocks:
	- 今日対応案件
	- 重要アラート
	- おすすめアクション
	- AI提案
	- KPI
	- 進行中タスク
- target_roles:
	- 営業
	- 企画
	- 生産管理
	- 営業事務
	- 経営
	- 管理者
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-PROPOSAL-BUILDER-FLOW-049
- status: verified
- scope: Proposal Builder UX
- statement: Proposal Builderは1画面で顧客選択から送信準備まで完結する。
- proposal_builder_flow:
	- 顧客選択
	- 目的選択
	- 参考データ
	- AIドラフト
	- PowerPoint生成
	- レビュー
	- メール送信
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-TASK-CENTER-WORKSPACE-050
- status: verified
- scope: Core Product Experience
- statement: Task CenterとWorkspaceを中核画面とし、実行コンテキストを統合する。
- task_center_sources:
	- 案件
	- 納期
	- メール
	- Slack
	- 社内依頼
- workspace_contents:
	- AI会話
	- 提案書
	- メール
	- タスク
	- 履歴
	- 生成物
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-PRODUCT-KPI-051
- status: verified
- scope: Product Measurement
- statement: Evaluation指標に加えてProduct KPIを定義し、業務価値を継続計測する。
- product_kpis:
	- DAU
	- WAU
	- MAU
	- 提案書作成時間
	- 提案採用率
	- AI利用率
	- ドラフト採用率
	- タスク推薦採用率
	- 回答修正率
	- PowerPoint修正時間
	- 業務削減時間
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-PRODUCT-FEEDBACK-LOOP-052
- status: verified
- scope: Continuous Improvement
- statement: Product AnalyticsからEvaluation、Knowledge/Runtime/UI改善へ閉ループを構築する。
- product_analytics_events:
	- 画面表示
	- クリック
	- 生成開始
	- 生成完了
	- 生成物ダウンロード
	- 修正開始
	- 修正終了
	- 採用
	- 却下
	- AI提案採用
	- AI提案拒否
- improvement_loop:
	- Product Analytics
	- Evaluation
	- Knowledge改善
	- Runtime改善
	- UI改善
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-MEMORY-METADATA-033
- status: verified
- scope: Memory Metadata
- statement: Memoryは標準Metadataを必須保持し、権限・鮮度・信頼度をValidationに連携する。
- required_metadata:
	- memory_id
	- memory_type
	- title
	- summary
	- related_entities
	- related_customers
	- related_projects
	- related_staff
	- related_dates
	- source_type
	- source_name
	- occurred_at
	- recorded_at
	- confidence
	- importance
	- sensitivity
	- permission_scope
	- retention_policy
	- citation_required
	- linked_documents
	- linked_messages
	- linked_tasks
	- tags
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-MEMORY-TYPE-034
- status: verified
- scope: Memory Taxonomy
- statement: Required Memory PlanningはTask Planning前にmemory_typeを決定する。
- memory_types:
	- meeting_memory
	- decision_memory
	- customer_memory
	- project_memory
	- proposal_memory
	- task_memory
	- communication_memory
	- issue_memory
	- feedback_memory
	- learning_memory
	- exception_memory
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-REQUIRED-MEMORY-PLANNING-035
- status: verified
- scope: Task Planning連携
- statement: Task Planning前にIntent/Taskに応じてRequired Memoryを決定し、Execution Planningへ引き渡す。
- required_memory_examples:
	- BEAMS向け提案書を作って -> customer_memory, proposal_memory, project_memory
	- Fanatics案件の状況を教えて -> project_memory, issue_memory, communication_memory, task_memory
	- 今日対応すべき案件を教えて -> task_memory, project_memory, communication_memory
	- GOLDWIN向け提案を考えて -> customer_memory, proposal_memory, meeting_memory
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-MEMORY-RETRIEVAL-INTERFACE-036
- status: verified
- scope: Runtime Interface
- statement: 外部実取得実装は追加せず、Memory Retrieval Interfaceをスタブとして定義する。
- interface_methods:
	- retrieve_memory()
	- retrieve_customer_memory()
	- retrieve_project_memory()
	- retrieve_proposal_memory()
	- retrieve_task_memory()
	- merge_knowledge_and_memory()
	- prioritize_memory()
	- filter_memory_by_permission()
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-MEMORY-VALIDATION-037
- status: verified
- scope: Validation
- statement: Memory利用時は不足・権限・鮮度・信頼度・整合性・機密性を必ず検証する。
- additional_validation_checks:
	- 必要Memoryが不足している
	- 権限外Memoryを参照している
	- 古すぎるMemoryを根拠にしている
	- confidenceが低いMemoryを断定利用している
	- MemoryとKnowledgeが矛盾している
	- 顧客提案に必要な過去提案Memoryが未参照
	- Monitoringでtask/project memoryを参照していない
	- 個人情報・機密情報をPresentationに出しすぎている
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-MEMORY-TRACE-038
- status: verified
- scope: Presentation
- statement: 回答時に必要に応じてMemory Traceを表示し、根拠と利用目的を説明可能にする。
- trace_fields:
	- memory_type
	- title
	- occurred_at
	- confidence
	- permission_scope
	- citation_or_linked_source
	- usage_in_answer
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 20: Capability Library

### Verified Business Rule
- rule_id: BR-CAPABILITY-LAYER-018
- status: verified
- scope: AI OS実行基盤
- statement: AI OSはKnowledge LayerとCapability Layerの2層で設計し、Capability Layerで「何を実行できるか」を定義する。
- layers:
	- Knowledge Layer: 会社理解、業務ルール理解、Entity/KPI/Time/Grain/Intent解決
	- Capability Layer: 業務実行、データ取得、資料作成、伝票作成、通知、タスク化
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-CAPABILITY-CATALOG-019
- status: verified
- scope: Capability分類
- statement: Capability LibraryはData Query/Document Generation/Transaction/Communication/Monitoring Alert/Workflow/Knowledge Retrievalカテゴリで管理する。
- capability_categories:
	- Data Query
	- Document Generation
	- Transaction
	- Communication
	- Monitoring Alert
	- Workflow
	- Knowledge Retrieval
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-CAPABILITY-SCHEMA-020
- status: verified
- scope: Capability定義
- statement: 各Capabilityは標準定義項目を持ち、Task PlanningとExecution Planningの共通インターフェースとして扱う。
- required_fields:
	- capability_id
	- capability_name
	- category
	- description
	- required_inputs
	- optional_inputs
	- output_type
	- required_permission
	- risk_level
	- confirmation_required
	- validation_required
	- related_intents
	- related_tasks
	- execution_mode
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-CAPABILITY-RISK-021
- status: verified
- scope: 実行リスク管理
- statement: Capabilityはexecution_modeとrisk_levelに基づいて実行制御し、high/criticalは自動確定しない。
- execution_modes:
	- read_only
	- draft
	- approval_required
	- direct_execute
- risk_levels:
	- low
	- medium
	- high
	- critical
- high_critical_guardrails:
	- 実行前確認
	- Validation
	- ユーザー承認
	- 実行ログ
	- 自動確定禁止
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-CAPABILITY-RUNTIME-022
- status: verified
- scope: Runtime統合方針
- statement: Capabilityごとの個別Runtimeを増やさず、capability_registry/capability_router/executor/validator/presenterへ統合する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Capability Library

### Capability Category: Data Query
- sample_capabilities:
	- SQL実行
	- データ抽出
	- 集計
	- グラフ生成
	- DataFrame生成

### Capability Category: Document Generation
- sample_capabilities:
	- PowerPoint作成
	- Excel作成
	- PDF作成
	- Word/Markdown作成
	- 提案書ドラフト作成
	- 社内資料作成

### Capability Category: Transaction
- sample_capabilities:
	- 見積作成
	- 発注書作成
	- 売上伝票作成
	- 仕入伝票作成
	- 請求関連作成
- policy: 原則として下書き作成または確認待ちとし、自動確定しない。

### Capability Category: Communication
- sample_capabilities:
	- メール下書き
	- メール送信
	- Slack通知
	- 社内共有文作成
	- 顧客向け文面作成

### Capability Category: Monitoring Alert
- sample_capabilities:
	- 未発注検出
	- 納期遅延検出
	- 粗利悪化検出
	- 未仕入検出
	- 請求漏れ検出
	- 対応漏れ検出

### Capability Category: Workflow
- sample_capabilities:
	- タスク作成
	- 担当者アサイン
	- 承認依頼
	- ステータス変更
	- リマインド
	- カレンダー登録

### Capability Category: Knowledge Retrieval
- sample_capabilities:
	- Gmail検索
	- Slack検索
	- Google Drive検索
	- 議事録検索
	- 過去提案書検索
	- 商品仕様書検索

### Capability Template
- capability_id: CAP-DATA-QUERY-001
- capability_name: SQL実行
- category: Data Query
- description: Meaning Resolution済み条件でSQLを実行してデータを取得する。
- required_inputs:
	- canonical_filters
	- query_objective
	- dataset_scope
- optional_inputs:
	- time_range
	- grain
	- chart_preference
- output_type: table/chart/dataframe
- required_permission: data_read
- risk_level: low
- confirmation_required: false
- validation_required: true
- related_intents:
	- Analysis
	- Monitoring
- related_tasks:
	- 顧客別粗利分析
	- 納期遅延検出
- execution_mode: read_only

### Task Planning Capability Mapping
- Intent: Analysis
	- Task: 顧客別粗利分析
	- capability_stack: Data Query, Chart Generation, Presentation
- Intent: Proposal
	- Task: 顧客向け提案書作成
	- capability_stack: Knowledge Retrieval, Data Query, Document Generation
- Intent: Document
	- Task: 発注書作成
	- capability_stack: Entity Resolution, Transaction Draft, Validation, Approval
- Intent: Monitoring
	- Task: 納期遅延確認
	- capability_stack: Data Query, Monitoring Alert, Task Creation

## Theme 21: Evaluation Suite

### Verified Business Rule
- rule_id: BR-EVALUATION-SUITE-023
- status: verified
- scope: 継続評価基盤
- statement: Knowledge LibraryとCapability Libraryは継続的に評価・改善し、SQL単体ではなく理解から提示まで段階評価する。
- evaluation_stages:
	- Knowledge Understanding
	- Meaning Resolution
	- Intent Resolution
	- Task Planning
	- Capability Selection
	- Execution Planning
	- Validation
	- Presentation
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-EVALUATION-CASE-SCHEMA-024
- status: verified
- scope: テストケース定義
- statement: Evaluationケースは構造化データで管理し、将来pytest接続可能な形式を維持する。
- required_fields:
	- test_id
	- category
	- user_input
	- expected_intent
	- expected_entities
	- expected_kpi
	- expected_time
	- expected_grain
	- expected_analysis_purpose
	- expected_task
	- expected_capabilities
	- expected_execution_mode
	- expected_validation_status
	- expected_clarification_required
	- expected_should_generate_sql
	- expected_should_execute
	- expected_output_type
	- notes
- runtime_output_contract:
	- interpreted_intent
	- resolved_meaning
	- task_plan
	- selected_capabilities
	- execution_plan
	- validation_result
	- presentation_summary
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-EVALUATION-SCORING-025
- status: verified
- scope: 評価指標
- statement: Evaluation結果は判定ステータスと精度メトリクスで記録する。
- status_labels:
	- pass
	- fail
	- warning
	- needs_clarification
	- blocked_by_validation
- score_dimensions:
	- intent_accuracy
	- meaning_accuracy
	- entity_resolution_accuracy
	- kpi_resolution_accuracy
	- planning_accuracy
	- capability_selection_accuracy
	- validation_accuracy
	- presentation_quality
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-EVALUATION-REGRESSION-026
- status: verified
- scope: Regression管理
- statement: Knowledge更新後は既存要件が壊れていないことをRegressionケースで確認する。
- regression_targets:
	- 粗利定義
	- 営業担当費用の利用制限
	- Entity Resolution Gate
	- Canonical Key優先
	- Meaning Resolution必須
	- Capability risk guardrail
	- high/critical操作の自動実行禁止
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 01: 標準売上集計ルール

### Verified Business Rule
- rule_id: BR-SALES-STANDARD-001
- status: verified
- scope: 標準売上集計（月次売上、担当別売上、顧客別売上などの一般的な売上分析）
- statement: 売上集計時は「売上ステータス IN (2,3,4,5)」かつ「決済方法 != 4」を適用する。
- note: このルールは全売上共通ではない。請求管理・売掛管理・監査・データ照合は例外業務として別条件を許容する。
- source: reference/03_application/streamlit/app.py
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-SALES-RULESET-002
- status: verified
- scope: 売上集計全体
- statement: 売上集計には、集計目的ごとのルールセットが存在する。
- note: 標準売上集計と例外業務（請求管理・売掛管理・監査・データ照合）を区別して適用する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 02: 標準売上集計の明細基準ルール

### Verified Business Rule
- rule_id: BR-SALES-DETAIL-003
- status: verified
- scope: 標準売上集計
- statement: 売上金額・粗利・粗利率は伝票ヘッダーではなく明細データを基準に計算する。
- note: 集計精度維持のため、分析・集計ロジックではヘッダー集計値を原則利用しない。ヘッダー値は表示用・参照用として扱う。
- formula_standard:
	- 売上金額 = SUM(売上金額)
	- 粗利 = SUM(明細粗利)
	- 粗利率 = SUM(明細粗利) / NULLIF(SUM(売上金額), 0)
- source: reference/03_application/streamlit/app.py + user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 03: 商品属性解釈の優先参照と推定ルール

### Verified Business Rule
- rule_id: BR-MASTER-PRODUCT-004
- status: verified
- scope: 商品分析
- statement: productsは商品属性の優先参照先（Primary Source）とするが、絶対的な正解としては扱わない。
- note: productsはユーザー登録・更新データのため、商品分類・ブランド・シリーズに誤登録、未更新、運用揺れがあり得る。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-MASTER-INFERENCE-005
- status: verified
- scope: 商品分析
- statement: 商品分類・ブランド・シリーズ判断は単一カラムに依存せず、複数属性を総合して推定する。
- inference_signals:
	- 商品コード
	- 商品名
	- 品番
	- ブランド
	- 商品分類
	- 商品名キーワード
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 05: 期間表現と基準日のルールセット

### Verified Business Rule
- rule_id: BR-TIME-RULESET-006
- status: verified
- scope: 期間指定を伴う分析全般
- statement: 期間解釈は単一固定ルールではなく、優先順位を持つルールセットとして管理する。
- period_ruleset_priority:
	- 1) 明示期間（例: 2026-01-01〜2026-03-31）
	- 2) 業務語彙ベース期間（今月、前月、前年同月、直近3か月、直近12か月、今年、昨年、年度、四半期）
	- 3) 文脈補完期間（会話履歴・レポート定義に基づく補完）
	- 4) 判定不能時はユーザー確認
- note: 標準売上分析での「最近/直近」は直近3か月を優先解釈する。
- source: reference/03_application/streamlit/app.py + user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-TIME-BASIS-DATE-007
- status: verified
- scope: 期間評価ロジック
- statement: 期間評価は基準日を伴う業務ルールとして管理する。
- basis_date_types:
	- 営業日基準
	- 受注日基準
	- 売上日基準
	- 出荷日基準
	- 請求日基準
- note: 期間語彙だけでなく、基準日種別を必ずセットで解釈する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 07: budget_forecast区分と仕入実績構造ルール

### Verified Business Rule
- rule_id: BR-BF-CATEGORY-009
- status: verified
- scope: budget_forecast利用分析
- statement: budget_forecastは単純な予算・予定テーブルではなく、予算/予定/費用の3区分を持つデータセットとして扱う。
- categories:
	- 予算
	- 予定
	- 費用
- canonical_internal_codes:
	- 01 = 予算
	- 02 = 予定
	- 05 = 費用
- exclusion_codes:
	- 03 = 発注（budget_forecastには存在しない）
	- 04 = 実績（budget_forecastには存在しない）
- note: 費用はlogsysの発注・仕入・売上実績ではなく、会計連携された営業担当別費用実績である。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-COST-COVERAGE-010
- status: verified
- scope: 利益計算
- statement: 費用は利益計算で控除対象として扱う。
- formula_standard:
	- 利益 = 売上 - 原価 - 費用
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-PROCUREMENT-COMPONENT-011
- status: verified
- scope: 仕入実績分析
- statement: 仕入実績は「仕入明細」と「輸入諸掛明細」の2構造を目的別に使い分ける。
- rule_matrix:
	- 仕入実績合計金額: 仕入明細を参照
	- 輸入経費込み仕入金額: 仕入明細を参照
	- 輸入経費内訳: 輸入諸掛明細を参照
	- 構成分析（仕入金額+輸入経費）: 仕入明細と輸入諸掛明細を組み合わせ参照
- risk_note: 仕入明細には輸入経費が合算済みのため、単純合算は二重計上リスクを生む。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 17: Entity Resolution失敗時の標準応答ルール

### Verified Business Rule
- rule_id: BR-ENTITY-RESOLUTION-GATE-012
- status: verified
- scope: Entity条件付き分析全般
- statement: Entity Resolutionが成功するまでSQL生成へ進めない。失敗時はSQL生成を保留し、候補提示またはユーザー確認へ遷移する。
- sql_generation_block_conditions:
	- Canonical Keyが一意に確定できない
	- 候補が複数存在する
	- 表示名/略称/通称のみでEntity確定しようとしている
	- Entity Typeが不明（顧客/ブランド/工場など未確定）
	- Semantic Catalog上に正規表示名はあるがCanonical Keyが未設定
	- Entity Resolution候補が低信頼度
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 18: Business Context Resolution

### Verified Business Rule
- rule_id: BR-MEANING-RESOLUTION-013
- status: verified
- scope: SQL生成前の意味解決
- statement: Business Context Resolutionは概念として管理し、RuntimeではMeaning Resolution内部責務として統合実装する。独立Runtimeを乱立させない。
- integration_policy:
	- Business Context ResolutionはKnowledge Library上の概念レイヤ
	- Runtime実装はMeaning Resolutionに統合
	- Entity/KPI/Time/Grain/Analysis Purposeの解決を単一処理で実行
	- 未解決Contextがある場合はSQL生成へ進めない
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Theme 19: Task Planning（業務計画）

### Verified Business Rule
- rule_id: BR-TASK-PLANNING-015
- status: verified
- scope: Business AI OS拡張
- statement: Knowledge基盤はAnalysis専用に限定せず、Proposal/Document/Monitoring/Workflow/Search/Explanationを含むBusiness Task全体を扱う。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-INTENT-FIRST-016
- status: verified
- scope: 実行経路選択
- statement: Natural Language入力はまずIntent Resolutionで分類し、Intent確定後にMeaning ResolutionとTask Planningへ進む。
- intents:
	- Analysis
	- Proposal
	- Document
	- Monitoring
	- Workflow
	- Search
	- Explanation
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-EXECUTION-PLANNING-017
- status: verified
- scope: 技術実装変換
- statement: Execution PlanningはTaskを実行可能形式へ変換する技術実装層とし、Intent別に最終実行形式を決定する。
- execution_mapping:
	- Analysis -> SQL
	- Proposal -> PowerPoint構成
	- Document -> 伝票生成
	- Monitoring -> Alert生成
	- Workflow -> 業務処理
	- Search -> 検索クエリ
	- Explanation -> 説明文生成
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-CONTEXT-NORMALIZATION-014
- status: verified
- scope: 業務曖昧語の正規化
- statement: 粗利/売上/利益/実績/予定/予算/今年/今月/今期/先月/前年比/担当者別/顧客別/ブランド別などの業務曖昧語はSQL生成前にMeaning Resolutionで正規化する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business Rule
- rule_id: BR-TIME-REPORT-SPLIT-008
- status: verified
- scope: 分析レポート定義
- statement: 分析レポートごとに基準日が異なる場合、Business Ruleを分離して管理する。
- note: 期間知識はSQL生成専用ではなく、Validation・Semantic Catalog・Interpretationで共通利用する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Business Vocabulary
- 売上
- 仕入金額
- 輸入諸掛
- 概算粗利
- 実際粗利
- 営業担当費用
- 担当者粗利
- 工場コード
- 工場名
- 今月
- 前月
- 前年同月
- 直近3か月
- 直近12か月
- 今年
- 昨年
- 年度
- 四半期
- 予算
- 予定
- 費用
- 仕入明細
- 輸入諸掛明細
- 輸入経費
- 営業担当別費用実績
- 費用配賦
- 配賦優先順位
- 配賦対象

## Entity Resolution

### Verified Entity Resolution Rule
- rule_id: ER-CANONICAL-001
- status: verified
- scope: 全Business Entity
- statement: 正式コードが存在するEntityはCanonical Keyを唯一の確定キーとして使用する。
- applicable_entities:
	- 顧客
	- 商品
	- ブランド
	- 担当者
	- 工場
	- 仕入先
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Entity Resolution Rule
- rule_id: ER-NO-CODE-002
- status: verified
- scope: コード欠落時
- statement: Canonical Keyが取得できない場合のみ表示名をSemantic Catalogで正規化し、一意確定時のみBusiness Entityを確定する。
- fallback_policy:
	- 一意確定: 採用可
	- 複数候補: ユーザー確認またはValidation Error
	- 一致なし: ユーザー確認またはValidation Error
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Entity Resolution Rule
- rule_id: ER-NO-GUESS-003
- status: verified
- scope: Entity確定
- statement: AIは推測でEntityを確定しない。Entity Resolutionを経由しない確定と表示名のみでのSQL条件確定を禁止する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Entity Resolution Rule
- rule_id: ER-ERROR-TYPE-004
- status: verified
- scope: 失敗状態分類
- statement: Entity Resolution失敗は標準Error Typeで分類し、分類に応じて確認質問と候補提示を行う。
- error_types:
	- ENTITY_NOT_FOUND: 入力名称に該当候補がない
	- ENTITY_AMBIGUOUS: 複数候補が存在し一意確定できない
	- ENTITY_TYPE_AMBIGUOUS: Entity Type（顧客/ブランド/工場等）が判別不能
	- CANONICAL_KEY_MISSING: 正規表示名は存在するがCanonical Key未設定
	- LOW_CONFIDENCE_MATCH: 候補はあるが採用閾値未満
	- DISPLAY_NAME_ONLY: 表示名のみでCanonical Key未確定
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Entity Resolution Rule
- rule_id: ER-RESPONSE-005
- status: verified
- scope: 失敗時応答
- statement: Entity Resolution失敗時は標準応答を返し、何が未確定か・候補一覧・確認質問・SQL保留を明示する。
- response_contract:
	- unresolved_reason
	- candidate_list
	- candidate.entity_type
	- candidate.canonical_key
	- candidate.canonical_name
	- followup_question
	- sql_generation_status: pending
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Meaning Resolution

### Verified Meaning Resolution Rule
- rule_id: MR-SCOPE-001
- status: verified
- scope: 統合意味解決
- statement: Meaning ResolutionはEntity/KPI/Time/Grain/Analysis Purposeを単一責務として解決し、Query Planningへ標準payloadを引き渡す。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Meaning Resolution Rule
- rule_id: MR-GATE-002
- status: verified
- scope: SQL生成ゲート
- statement: Meaning Resolutionで未解決Contextが1つでも残る場合、Query PlanningおよびSQL Generationへ遷移しない。
- unresolved_context_examples:
	- KPI未確定（粗利種別未決定など）
	- 期間未確定（今年/今期の境界不明など）
	- 粒度未確定（担当者別/顧客別/ブランド別の未確定）
	- Entity未確定（Entity Resolution失敗）
	- Analysis Purpose未確定
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Intent Resolution

### Verified Intent Resolution Rule
- rule_id: INR-CLASSIFICATION-001
- status: verified
- scope: 要求分類
- statement: Intent Resolutionはユーザー要求をAnalysis/Proposal/Document/Monitoring/Workflow/Search/Explanationのいずれかへ分類する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Intent Resolution Rule
- rule_id: INR-GATE-002
- status: verified
- scope: 実行前検証
- statement: Intentが未確定または複数競合の場合はTask Planningへ進まず、確認質問へ遷移する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Task Planning

### Verified Task Planning Rule
- rule_id: TPR-TASK-ROUTING-001
- status: verified
- scope: Intent連動タスク決定
- statement: Task PlanningはIntentに応じてBusiness Taskを決定し、Execution Planningへ引き渡す。
- task_examples:
	- Analysis: 分析計画
	- Proposal: 提案資料構成 -> 必要データ -> 参考案件 -> 商品候補 -> PowerPoint Draft
	- Document: 見積/売上/仕入/発注/請求
	- Monitoring: 未発注/納期遅延/粗利悪化/タスク抽出
	- Workflow: 案件進行/担当者確認/ステータス変更/承認
	- Search: 検索対象決定/検索条件定義
	- Explanation: 説明対象決定/説明粒度決定
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Task Planning Rule
- rule_id: TPR-GATE-002
- status: verified
- scope: SQL生成ゲート
- statement: Task Planningで必要情報が不足または未確定の場合、Execution PlanningおよびExecutionへ遷移しない。
- required_task_payload:
	- intent
	- task_type
	- required_inputs
	- missing_inputs
	- meaning_payload
	- confidence
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Task Planning Rule
- rule_id: TPR-CAPABILITY-SELECTION-003
- status: verified
- scope: Capability選択
- statement: Task PlanningはIntent/Taskに応じてCapability Libraryから必要Capabilityを選択し、Execution Planningへ渡す。
- required_payload:
	- intent
	- task_type
	- selected_capabilities
	- missing_capabilities
	- risk_profile
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Task Planning Rule
- rule_id: TPR-REQUIRED-KNOWLEDGE-004
- status: verified
- scope: Knowledge Source決定
- statement: Task PlanningはCapability選択と同時にRequired Knowledge（internal_only/hybrid/external_primary）を決定する。
- required_payload:
	- required_knowledge_scope
	- required_internal_sources
	- required_external_sources
	- citation_required
	- freshness_requirement
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Execution Planning

### Verified Execution Planning Rule
- rule_id: EPR-PLAN-FORMAT-001
- status: verified
- scope: 実行計画生成
- statement: Execution PlanningはTaskを実行可能なPlanへ変換し、plan_typeごとにexecutorへ引き渡す。
- plan_types:
	- sql_plan
	- proposal_plan
	- document_plan
	- monitoring_plan
	- workflow_plan
	- search_plan
	- explanation_plan
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Execution Planning Rule
- rule_id: EPR-GATE-002
- status: verified
- scope: 実行遷移
- statement: Execution Planが生成不能な場合はExecutionへ進まず、Validationエラーまたは確認フローへ遷移する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Execution Planning Rule
- rule_id: EPR-CAPABILITY-BINDING-003
- status: verified
- scope: 実行束縛
- statement: Execution Planningはselected_capabilitiesを実行順へ束縛し、共通executorで実行可能なplanへ変換する。
- binding_requirements:
	- capability_id
	- execution_mode
	- risk_level
	- required_permission
	- confirmation_required
	- validation_required
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Execution Planning Rule
- rule_id: EPR-KNOWLEDGE-BINDING-004
- status: verified
- scope: Knowledge Binding
- statement: Execution PlanningはRequired KnowledgeをKnowledge Retrieval Interfaceへ束縛し、prioritize_sourcesで採用順を決定する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Business Concept
- 予算
- 予定
- 発注
- 実績
- 売上実績
- 仕入実績
- 費用実績
- 売上原価
- 輸入諸掛
- 概算粗利
- 実際粗利
- 営業担当費用
- 担当者粗利
- 工場コード
- 工場表示名

## Business Grain
- 担当者
- 商品
- 顧客
- ブランド
- 工場
- 会社
- 期間

### Grain Constraint
- 営業担当費用（budget_forecast 05）は「担当者×月」粒度でのみ成立する。
- 顧客/商品/ブランド/工場粒度へ営業担当費用を配賦して担当者粗利を算出してはならない。

## Business KPI

### Verified Business KPI
- kpi_id: KPI-METRIC-001
- status: verified
- name: ログズ業務KPI（Metric Set）
- metrics:
	- 売上
	- 仕入金額
	- 輸入諸掛
	- 概算粗利
	- 実際粗利
	- 営業担当費用
	- 担当者粗利
- note: Business KPIは分析軸ごとに増殖させない。分析結果は Business KPI × Business Grain で決定する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Business KPI
- kpi_id: KPI-METRIC-002
- status: verified
- name: KPI計算構造
- definition: 粗利は1種類ではなく、概算粗利・実際粗利・担当者粗利を分離して扱う。
- formula_standard:
	- 概算粗利 = sales上の粗利（仕入入力済みは実績原価、未入力は論理原価を含む可能性）
	- 実際粗利 = 売上金額 - 仕入金額（purchases）
	- 担当者粗利 = 実際粗利 - 営業担当費用（budget_forecast 05）
- procurement_rule:
	- purchasesは輸入経費込み仕入金額を保持する。
	- purchase_surchargesは輸入諸掛内訳確認用であり、purchasesへ単純加算してはならない。
- naming_rule: 会計用語の営業利益はKnowledge Library内で使用しない。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Analysis Purpose
- 担当者評価
- 商品分析
- ブランド分析
- 顧客分析
- 工場分析

## Required Dataset

### KPI Grain Dataset Requirements
- Analysis Purpose: 担当者評価
	- business_grain: 担当者, 期間
	- business_kpi: 売上, 実際粗利, 営業担当費用, 担当者粗利
	- required_dataset: sales, purchases, purchase_surcharges, budget_forecast(05)
- Analysis Purpose: 商品分析
	- business_grain: 商品, 期間
	- business_kpi: 売上, 概算粗利 または 実際粗利
	- required_dataset: sales, purchases, purchase_surcharges
- Analysis Purpose: ブランド分析
	- business_grain: ブランド, 期間
	- business_kpi: 売上, 概算粗利 または 実際粗利
	- required_dataset: sales, purchases, purchase_surcharges
- Analysis Purpose: 顧客分析
	- business_grain: 顧客, 期間
	- business_kpi: 売上, 概算粗利 または 実際粗利
	- required_dataset: sales, purchases, purchase_surcharges
- Analysis Purpose: 工場分析
	- business_grain: 工場, 期間
	- business_kpi: 売上, 実際粗利
	- required_dataset: sales, purchases, purchase_surcharges
	- note: 担当者業績分析以外では営業担当費用（budget_forecast 05）を使用しない。

## Query Planning Rules

### Verified Query Planning Rule
- rule_id: QPR-PURPOSE-DATASET-001
- status: verified
- scope: Query Architecture
- statement: 参照テーブルを直接決めるのではなく、分析目的から参照データセットを選択する。
- architecture:
	- Analysis Purpose
	- Primary Dataset
	- Optional Dataset
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-SQL-FLOW-002
- status: verified
- scope: SQL生成フロー
- statement: SQL生成時は「Business Vocabulary → Semantic Catalog → Entity Resolution → Business Concept → Business KPI → Business Grain → Analysis Purpose → Required Dataset → Query Planning → SQL Generation → Validation → Presentation」の順で実行する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-BF-CATEGORY-003
- status: verified
- scope: budget_forecast参照クエリ
- statement: budget_forecastを使う場合、予算/予定/費用のどの区分を使うかを必ず先に判定する。
- category_dataset_mapping:
	- 予算を見る: budget_forecast(区分コード=01)
	- 予定を見る: budget_forecast(区分コード=02)
	- 営業担当別費用実績を見る: budget_forecast(区分コード=05)
	- 売上実績を見る: sales
	- 発注実績を見る: purchase_orders
	- 仕入実績を見る: purchases
- guardrail:
	- budget_forecastに区分コード03/04を期待しない
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-BF-CODE-NORMALIZATION-005
- status: verified
- scope: budget_forecast区分正規化
- statement: ユーザー入力の表示名（予算/予定/費用）はSemantic Catalogで内部コード（01/02/05）へ正規化してからSQL生成する。
- sql_generation_policy:
	- SQLでは表示名ではなく区分コードを使用する
	- 表示名はUI/回答文脈のみで使用する
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-OFFICIAL-DATASET-006
- status: verified
- scope: Analysis Purpose別データソース選定
- statement: 予算/予定/発注/売上実績/仕入実績/費用実績は正式データソースに従って選択する。
- official_sources:
	- 予算: budget_forecast(01)
	- 予定: budget_forecast(02)
	- 発注: purchase_orders
	- 売上実績: sales
	- 仕入実績: purchases + purchase_surcharges
	- 費用実績: budget_forecast(05)
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-ACTUAL-CONTEXT-007
- status: verified
- scope: 「実績」解釈
- statement: 「実績」は単一テーブル概念ではなく、Analysis Purpose依存でデータセットを切り替える。
- actual_by_purpose:
	- 売上実績: sales
	- 仕入実績: purchases + purchase_surcharges
	- 業績実績: sales + purchases + purchase_surcharges + budget_forecast(05)
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-ORDER-PROGRESS-008
- status: verified
- scope: 発注進捗分析
- statement: 発注進捗は「予定→発注」の比較で定義し、実績比較へ混在させない。
- comparison_pair:
	- baseline: budget_forecast(02)
	- target: purchase_orders
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-PROFIT-CORE-009
- status: verified
- scope: 利益分析
- statement: 粗利系分析では、まず「概算粗利・実際粗利・担当者粗利」のどれを求めるかを判定してからデータセットを選択する。
- profit_dataset_structure:
	- 概算粗利: sales（粗利カラム）
	- 実際粗利: sales（売上） + purchases（仕入金額）
	- 担当者粗利: sales + purchases + budget_forecast(05)
- default_policy:
	- 粗利種別が不明な場合は概算粗利を返す。
	- 回答時に「概算粗利であること」を必ず注記する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-KPI-FIRST-010
- status: verified
- scope: KPI連動SQL生成
- statement: Analysis Purposeが「担当者評価」「商品分析」「ブランド分析」「顧客分析」「工場分析」の場合、Dataset選択の前提としてBusiness KPIを先に確定し、そのRequired GrainとRequired DatasetからSQLを生成する。
- target_purposes:
	- 担当者評価
	- 商品分析
	- ブランド分析
	- 顧客分析
	- 工場分析
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-STAFF-EXPENSE-GRAIN-012
- status: verified
- scope: 費用適用可否判定
- statement: 営業担当費用（budget_forecast 05）は担当者×月粒度のみで使用し、顧客/商品/ブランド/工場分析には適用しない。
- prohibited_cases:
	- 顧客別粗利に営業担当費用を配賦
	- 商品別粗利に営業担当費用を配賦
	- ブランド別粗利に営業担当費用を配賦
	- 工場別粗利に営業担当費用を配賦
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-ENTITY-RESOLUTION-013
- status: verified
- scope: Entity条件付きSQL生成
- statement: Query PlanningおよびSQL GenerationではCanonical Keyのみを条件キーとして使用し、表示名はPresentation層でのみ使用する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-ENTITY-RESOLUTION-GATE-014
- status: verified
- scope: Query Planning遷移条件
- statement: Query PlanningへはEntity Resolution成功時のみ遷移し、失敗時は確認フローへ遷移する。
- required_resolution_payload:
	- entity_type
	- canonical_key
	- canonical_name
	- original_user_input
	- confidence
	- resolution_method
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-MEANING-PAYLOAD-015
- status: verified
- scope: Query Planning入力標準化
- statement: Query PlanningはMeaning Resolutionの標準payloadのみを受け付け、未解決Contextを含むpayloadを拒否する。
- required_meaning_payload:
	- analysis_purpose
	- entity_type
	- canonical_key
	- canonical_name
	- kpi_id
	- kpi_variant
	- time_range
	- time_basis
	- grain
	- original_user_input
	- confidence
	- resolution_method
	- unresolved_contexts
- gate_policy:
	- unresolved_contextsが空でない場合は確認フローへ遷移
	- 表示名のみ条件は拒否
	- Canonical Key欠落条件は拒否
	- intentがAnalysis以外の場合はSQL専用Query Planningを強制しない
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-ANALYSIS-SCOPE-016
- status: verified
- scope: Query Planning適用範囲
- statement: Query PlanningはAnalysis IntentのExecution Planning（sql_plan）でのみ必須適用し、他IntentはTask種別に応じたPlanへ遷移する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-KPI-GRAIN-011
- status: verified
- scope: KPI前提条件
- statement: Query PlanningはDataset有無の判定ではなく、Business KPIが要求するBusiness Grainで全Datasetが成立していることを前提に進む。
- flow:
	- Analysis Purpose
	- Business KPI
	- Business Grain
	- Required Dataset
	- Query Planning
	- SQL Generation
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Query Planning Rule
- rule_id: QPR-PURCHASE-COMPONENT-004
- status: verified
- scope: 仕入/輸入経費分析クエリ
- statement: 仕入分析は目的ラベルを先に判定し、参照データセットを切り替える。
- purpose_dataset_mapping:
	- 仕入実績合計: purchases
	- 仕入実績内訳: purchases（分類軸追加）
	- 輸入経費内訳: purchase_surcharges
	- 輸入経費を含む仕入金額: purchases
	- 輸入経費を除いた仕入金額: purchases + purchase_surcharges（控除計算）
- guardrail: purchases と purchase_surcharges の単純合算を禁止し、重複加算防止ロジックを必須とする。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Analysis Purpose Dataset Mapping
- 売上分析:
	- primary_dataset: sales
	- optional_dataset: products, customers, staff, code_master
- 粗利分析:
	- primary_dataset: sales
	- optional_dataset: products, customers, staff, code_master, budget_forecast(費用区分)
- 発注分析:
	- primary_dataset: purchase_orders
	- optional_dataset: products, suppliers, staff, code_master
- 予実分析:
	- primary_dataset: budget_forecast
	- optional_dataset: sales, purchase_orders, purchases, staff, customers

- 予定実績比較:
	- primary_dataset: budget_forecast(02)
	- optional_dataset: sales, staff, customers

- 発注進捗分析:
	- primary_dataset: budget_forecast(02)
	- optional_dataset: purchase_orders, products, suppliers, staff
- 在庫分析:
	- primary_dataset: products
	- optional_dataset: purchases, purchase_orders, code_master
- 仕入分析:
	- primary_dataset: purchases
	- optional_dataset: purchase_surcharges, products, suppliers, code_master

- 費用分析（営業担当別）:
	- primary_dataset: budget_forecast(費用区分)
	- optional_dataset: staff, customers

- 利益分析（担当者業績評価）:
	- primary_dataset: sales
	- optional_dataset: purchases, purchase_surcharges, budget_forecast(05), staff, customers, products

- 業績実績:
	- primary_dataset: sales
	- optional_dataset: purchases, purchase_surcharges, budget_forecast(05), staff, customers

- 担当者評価:
	- primary_dataset: sales
	- optional_dataset: purchases, purchase_surcharges, budget_forecast(05), staff

- 工場分析:
	- primary_dataset: sales
	- optional_dataset: purchases, purchase_surcharges, products

## Interpretation Rules

### Verified Interpretation Rule
- rule_id: IR-MASTER-CONFLICT-001
- status: verified
- scope: マスターデータ解釈
- statement: マスター情報と名称情報（商品名等）に矛盾がある場合、マスターを優先しつつ名称情報も参照して推論する。
- escalation: 判定不能時はOpen Questionとしてユーザー確認へエスカレーションする。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Interpretation Rule
- rule_id: IR-MASTER-GENERAL-002
- status: verified
- scope: 全マスターデータ（顧客・仕入先・担当者・ブランド・商品）
- statement: Primary Source優先だが絶対視しない解釈方針は、productsに限らず名称検索全般に一般適用する。
- integration_note: Theme 03の商品属性解釈ルールを上位抽象化し、名称解釈ルールの共通基盤として扱う。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Interpretation Rule
- rule_id: IR-NAME-RESOLUTION-003
- status: verified
- scope: 名称検索全般（顧客・仕入先・担当者・ブランド・商品）
- statement: 完全一致を前提にせず、入力情報に応じた柔軟解釈を行う。
- resolution_priority:
	- 1) コード一致（顧客コード等）
	- 2) 正式名称一致
	- 3) 略称一致
	- 4) 部分一致
	- 5) 旧社名・通称・表記ゆれ一致
	- 6) AI意味推定
- escalation: 上記優先順位で判定不能な場合のみユーザーへ確認する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Interpretation Rule
- rule_id: IR-COST-ALLOCATION-004
- status: verified
- scope: 利益分析/採算分析
- statement: 費用配賦は一律ルールではなく、Analysis Purposeに応じて配賦ルールを切り替える。
- purpose_allocation_policy:
	- 担当者別利益分析: 担当者に直接紐づく費用を優先配賦
	- 商品別利益分析: 商品に直接紐づく費用を優先配賦
	- 顧客別利益分析: 顧客に紐づく費用を優先配賦
	- ブランド分析: ブランドに配賦
	- 部門分析: 部門に配賦
	- 会社全体利益分析: 配賦せず実績費用として扱う場合を許容
- conflict_resolution: 配賦対象が複数候補の場合は配賦優先順位を適用し、決定不能時はユーザー確認へ遷移する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Interpretation Rule
- rule_id: IR-COST-SIGN-005
- status: verified
- scope: 費用データ解釈
- statement: budget_forecastの費用は保存上は負値でも、Business Meaningは正の費用概念（Cost）として解釈する。
- handling:
	- 保存形式とビジネス意味を分離する
	- 利益計算時は符号整合を維持し、費用を控除対象として扱う
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Storage Rules

### Verified Storage Rule
- rule_id: SR-COST-NEGATIVE-001
- status: verified
- scope: budget_forecast(費用区分)
- statement: 費用はデータ保存形式としてマイナス値で保持する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Presentation Rules

### Verified Presentation Rule
- rule_id: PR-COST-DISPLAY-001
- status: verified
- scope: ユーザー表示
- statement: 費用表示はABSによる絶対値表示を標準とし、必要時のみマイナス表示を選択可能とする。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Presentation Rule
- rule_id: PR-GROSS-PROFIT-LABEL-002
- status: verified
- scope: 粗利回答表示
- statement: 粗利回答では「概算粗利」「実際粗利」「担当者粗利」のいずれかを必ず明示し、「粗利」とだけ表示してはならない。
- note_templates:
	- 概算粗利: 「この粗利はsales上の概算粗利です。仕入未入力分は論理原価を含む可能性があります。」
	- 実際粗利: 「この粗利は実際粗利です。売上金額から仕入金額（輸入経費込み）を差し引いて計算しています。」
	- 担当者粗利: 「この粗利は担当者粗利です。実際粗利から営業担当費用を控除しています。」
	- 顧客/商品/ブランド/工場分析: 「この粗利は営業担当費用を含まない粗利です。」
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Presentation Rule
- rule_id: PR-ENTITY-RESOLUTION-003
- status: verified
- scope: Entity回答表示
- statement: 必要に応じてEntity Resolution結果（Canonical Key、正規化表示名、複数候補確認事項）を回答へ明示する。
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Presentation Rule
- rule_id: PR-ENTITY-TRACE-004
- status: verified
- scope: Entity利用結果表示
- statement: 回答時は必要に応じて採用Entityのトレース情報を表示し、候補選択を経由した場合はその旨を明示する。
- trace_fields:
	- used_entity
	- canonical_name
	- canonical_key
	- entity_type
	- original_user_input
	- selected_from_candidates
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Presentation Rule
- rule_id: PR-MEANING-TRACE-005
- status: verified
- scope: 回答トレース表示
- statement: 回答時は必要に応じてMeaning Resolutionで採用したKPI/期間/粒度/Entityを明示する。
- trace_fields:
	- used_kpi
	- used_time_range
	- used_time_basis
	- used_grain
	- used_entity
	- canonical_name
	- canonical_key
	- entity_type
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Presentation Rule
- rule_id: PR-INTENT-FORMAT-006
- status: verified
- scope: Intent別出力形式
- statement: PresentationはIntentに応じて出力形式を切り替える。
- output_mapping:
	- Analysis -> グラフ
	- Proposal -> PowerPoint
	- Document -> 帳票
	- Monitoring -> ダッシュボード
	- Workflow -> タスク一覧
	- Search -> 検索結果一覧
	- Explanation -> 構造化説明
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Presentation Rule
- rule_id: PR-CAPABILITY-TRACE-007
- status: verified
- scope: Capability実行表示
- statement: 実行前後にCapability実行計画と検証結果を表示し、次に必要なユーザー確認を明示する。
- trace_fields:
	- selected_capabilities
	- execution_summary
	- input_payload
	- expected_outputs
	- risk_level
	- confirmation_required
	- validation_result
	- next_user_confirmation
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

### Verified Presentation Rule
- rule_id: PR-KNOWLEDGE-TRACE-008
- status: verified
- scope: Knowledge Source表示
- statement: 回答時は必要に応じてKnowledge Trace（Internal/External、Confidence、Freshness、Citation）を表示する。
- trace_fields:
	- knowledge_used_internal
	- knowledge_used_external
	- source_confidence
	- source_freshness
	- citation
- source: user_confirmation
- confirmed_by: user
- confirmed_on: 2026-06-30

## Open Questions
- OQ-SALES-EXCEPTION-001: 例外業務（請求管理・売掛管理・監査・データ照合）ごとの具体的なフィルタ条件は未確定。
- OQ-SALES-HEADER-002: ヘッダー値を分析ロジックで利用する例外業務がある場合の適用条件（業務名、対象指標、優先順位）が未確定。
- OQ-MASTER-CONFLICT-003: マスター値と推定値が矛盾した際の最終判定基準（閾値、強制採用条件、部門別ルール）は未確定。
- OQ-MASTER-ESCALATION-004: 判定不能時に確認すべき最小質問テンプレート（エンティティ別の必須項目、確認順序）は未確定。
- OQ-TIME-REPORT-BASIS-005: レポート別の基準日マッピング（どのレポートが営業日/受注日/売上日/出荷日/請求日を使うか）は未確定。
- OQ-QUERY-PLANNING-006: Analysis Purposeの判定競合時（例: 売上分析と粗利分析の同時要求）の優先順位は未確定。
- OQ-COST-ALLOCATION-008: 複数配賦候補が同一優先度となるケースのタイブレーク規則（按分ルール、期間粒度、丸め基準）は未確定。
- OQ-COST-SIGN-009: 画面/帳票ごとの費用表示モード（絶対値標準か符号表示標準か）の既定値は未確定。
- OQ-PLAN-ACTUAL-010: 「予実比較」と「予定実績比較」を同時要求された際の優先計算順序は未確定。

## Validation Impact Notes
- SQL生成時に「集計目的」を必須判定し、未判定時は BR-SALES-STANDARD-001 をデフォルト適用する。
- Validationで「標準売上集計なのにステータス条件または決済方法条件が欠落」をエラー検知する。
- 例外業務と判定された場合は、標準条件の強制を避け、目的別ルールセットを参照する。
- Validationで「標準売上集計なのにヘッダー重複カラム（売上合計金額、粗利、粗利率）を集計に利用」をエラー検知する。
- Validationで「標準売上集計の粗利率が SUM(明細粗利) / SUM(売上金額) 以外」を警告検知する。
- 属性判定時は単一カラム依存を警告し、複数シグナル参照（コード/名称/品番/ブランド/分類/キーワード）を満たさない場合は信頼度低下として扱う。
- マスター値と推定値が矛盾した場合は、Primary Source優先で処理しつつ、矛盾フラグと根拠を検証ログに残す。
- 判定不能ケースは自動確定せず、Open Questionとしてユーザー確認に遷移することを検証する。
- 名称解釈は IR-NAME-RESOLUTION-003 の優先順位（コード→正式名→略称→部分一致→旧称/表記揺れ→AI推定）を満たすことを検証する。
- 完全一致不成立のみを理由に失敗させず、優先順位に沿って候補探索した記録がない場合を警告とする。
- 期間指定は BR-TIME-RULESET-006 の優先順位に従って評価し、基準日未指定時は警告または確認遷移を行う。
- 基準日を要する分析で日付軸（営業日/受注日/売上日/出荷日/請求日）が未確定のままSQL生成しないことを検証する。
- レポート定義に基準日ルールがある場合は BR-TIME-REPORT-SPLIT-008 に基づき、他レポートへ流用しないことを検証する。
- SQL生成前にAnalysis Purposeが確定され、QPR-PURPOSE-DATASET-001のデータセット選択が実行されていることを検証する。
- Primary Dataset未選択でSQL生成に進んだ場合はエラーとし、Optional Datasetのみで主分析を成立させない。
- 予実分析ではbudget_forecastをPrimary Datasetとして維持し、実績補完時のみsales/purchase_ordersをOptionalとして結合することを検証する。
- budget_forecastを使うSQLでは、予算/予定/費用の区分指定が明示されていない場合をValidationエラーとする。
- budget_forecastを使うSQLで表示名（予算/予定/費用）を直接WHERE条件に埋め込んだ場合はValidationエラーとする。
- budget_forecastを使うSQLで区分コード（01/02/05）へ正規化されていない場合はValidationエラーとする。
- budget_forecast区分に03/04を参照・期待するSQLをValidationエラーとする。
- 「費用実績」を問い合わせたSQLでsales/purchase_orders/purchasesのみ参照し、budget_forecast(費用区分)を未参照の場合はValidation警告とする。
- 仕入分析でpurchasesとpurchase_surchargesをJOINまたは合算するSQLは、二重計上リスク検知を必須化する。
- 二重計上検知は「purchases金額に輸入経費が内包済みである前提」と「surcharges再加算の有無」を検証し、違反時はValidationエラーとする。
- 費用配賦を伴う分析では、Analysis Purposeと配賦方法の整合（IR-COST-ALLOCATION-004）を検証し、不一致時はValidationエラーとする。
- 会社全体利益分析で配賦を行わないモードを選択した場合、配賦ロジック適用を強制しないことを検証する。
- 費用計算で符号を二重反転していないことを検証する（例: 負値費用にさらにマイナスを掛ける誤り）。
- ABS()の利用箇所を検証する。表示系は許可し、利益計算など計算系での無条件ABS適用はエラーとする。
- 利益計算時の符号整合（利益 = 売上 - 原価 - 費用）を検証し、費用の加算扱いをエラー検知する。
- 発注進捗分析でsalesを比較対象に混在させたSQLはValidation警告とする（予定→発注比較の逸脱）。
- 利益分析にもかかわらず salesのみ、または sales+purchasesのみのSQLはValidation警告とする。
- Analysis Purposeが「業績実績」「利益分析」「担当者評価」の場合、KPI構成項目（売上実績、仕入実績、費用実績）が欠落するSQLをValidation警告とする。
- KPI構成で「仕入実績 = purchases + purchase_surcharges」を満たさないSQLをValidation警告とする。
- Validationは「Datasetが存在するか」ではなく「Business KPIが要求するBusiness Grainで全Datasetが揃っているか」を検証する。
- 粒度不一致（例: 売上/仕入は担当者粒度、費用は会社粒度）のままKPIを算出するSQLをValidation警告とする。
- KPI前提粒度（Required Grain）に未対応のDatasetを混在させるSQLをValidation警告とする。
- 実際粗利を求めているのにsales上の粗利のみを使うSQLをValidation警告とする。
- 担当者粗利を求めているのに営業担当費用（budget_forecast 05）が含まれていないSQLをValidation警告とする。
- 顧客別/商品別/ブランド別/工場別分析で営業担当費用を使用するSQLをValidation警告とする。
- purchasesとpurchase_surchargesを単純加算するSQLをValidationエラーまたは警告とする。
- 粗利回答で「概算粗利/実際粗利/担当者粗利」の区別が表示されていない場合をValidation警告とする。
- 工場分析ではBusiness Grain（工場）とBusiness KPI（実際粗利）が一致していることを検証する。
- 工場分析でsales上の粗利のみを使った場合はValidation警告とし、概算粗利注記の有無を検証する。
- Canonical KeyなしでSQL生成している場合をValidationエラーとする。
- 表示名を直接WHERE条件に使用している場合をValidationエラーとする。
- 複数候補があるのに一意確定している場合をValidationエラーまたは警告とする。
- Entity Resolutionを通さずにBusiness Entityを確定した場合をValidationエラーとする。
- Entity Resolution失敗状態（ENTITY_NOT_FOUND/ENTITY_AMBIGUOUS/ENTITY_TYPE_AMBIGUOUS/CANONICAL_KEY_MISSING/LOW_CONFIDENCE_MATCH/DISPLAY_NAME_ONLY）でSQL生成している場合をValidationエラーとする。
- Entity Type未確定のままSQL生成している場合をValidationエラーとする。
- LOW_CONFIDENCE_MATCHを自動採用してSQL生成している場合をValidationエラーまたは警告とする。
- Query Planning入力にentity_type/canonical_key/canonical_name/original_user_input/confidence/resolution_methodが不足している場合をValidationエラーとする。
- Meaning Resolution未実施のままSQL生成している場合をValidationエラーとする。
- unresolved_contextsが非空のままSQL生成している場合をValidationエラーとする。
- KPI/期間/粒度/Entityのいずれかが未確定のままSQL生成している場合をValidationエラーとする。
- Query Planning入力にanalysis_purpose/kpi_id/kpi_variant/time_range/time_basis/grainが不足している場合をValidationエラーとする。
- Intent未解決のままTask Planningへ遷移している場合をValidationエラーとする。
- IntentとTaskの不一致（例: Proposal intentでsql_plan強制）をValidationエラーまたは警告とする。
- Taskに必要情報が不足したままExecution Planningへ遷移している場合をValidationエラーとする。
- Execution Planが生成不能なのにExecutionへ遷移している場合をValidationエラーとする。
- Analysis以外のIntentでSQL生成を強制している場合をValidationエラーまたは警告とする。
- Capability実行前にrequired_inputs不足がある場合をValidationエラーとする。
- required_permission不足でCapability実行しようとしている場合をValidationエラーとする。
- risk_levelに応じたconfirmation_required/validation_requiredが未設定の場合をValidationエラーとする。
- Meaning Resolution未完了でCapability実行しようとしている場合をValidationエラーとする。
- Canonical Key未確定または対象非一意のままCapability実行しようとしている場合をValidationエラーとする。
- high/criticalのCapabilityを自動実行しようとしている場合をValidationエラーとする。
- high/criticalのCapabilityで実行ログ未記録の場合をValidationエラーまたは警告とする。
- EvaluationケースでEntity/KPI/Time未確定のままSQL生成を許容している場合はfailとする。
- Evaluationケースで表示名WHEREまたはCanonical Key未使用を許容している場合はfailとする。
- Evaluationケースでlow confidence entity自動採用を許容している場合はfailとする。
- EvaluationケースでAnalysis以外IntentへのSQL強制を許容している場合はfailとする。
- Evaluationケースでhigh/critical capability無承認実行を許容している場合はfailとする。
- Required Knowledgeが不足しているのにExecution Planningへ遷移した場合はValidationエラーとする。
- Citation requiredなのにSource Citationが無い場合はValidationエラーまたは警告とする。
- Freshness requirement未達（例: external_primaryで古い情報）の場合はValidationエラーまたは警告とする。
- External利用禁止TaskでExternal sourceを参照した場合はValidationエラーとする。
- Internal限定TaskでWeb Searchを必須化した場合はValidationエラーとする。
- Validationは以下を必須検証とする:
	- Business Grainで取得可能か
	- Business KPIに必要なDatasetが揃っているか
	- Business GrainとDatasetの粒度が一致しているか
