# AI Learning Questions — Business-Oriented Inquiry

**Date:** 2026-07-02  
**Phase:** 12 — AI as New Employee Learning Logsys  
**Role:** New employee asking business questions  
**Purpose:** Identify knowledge gaps through real business scenarios

---

## Question Format

For each business question, I show:
- **Question** — What a new employee would ask
- **AI理解** — What I currently understand (if anything)
- **分からないこと** — What's unclear (MOST IMPORTANT)
- **Product Ownerへ質問** — Specific questions to close gaps (max 5)
- **なぜ必要か** — Why this knowledge matters

---

## 20 Business Questions

---

### Q1: 今月のOEM粗利を教えて

**Question**
"今月のOEM粗利は? (What's this month's OEM gross profit?)"

**AI理解**
- OEM = custom design business (assumed)
- 粗利 = revenue minus cost
- This month = calendar month (maybe)
- Should aggregate all OEM sales + purchases
- 集計 table might have this

**分からないこと**
- OEM定義: 集計.分類の値は何? どう判定?
- 粗利種別: 論理 vs 実績 どちらを使う?
- 対象期間: 「今月」は正確に何月何日まで?
- 除外条件: キャンセル・返品含める?
- 集計単位: PO単位? 商品単位? 顧客単位?

**Product Ownerへ質問**
① OEM粗利を計算するには、「OEM」をどう判定しますか?
② 「粗利」は実績原価ベース? 論理原価ベース?
③ キャンセル・返品はどう扱いますか?
④ この計数を「月次」で見る場合、対象期間は何月何日から何月何日ですか?
⑤ 「集計」テーブルの案件粗利をそのまま使えますか、それとも再計算が必要ですか?

**なぜ必要か**
- Most common query (Q1 in sample set)
- Wrong calculation → wrong business decision
- Affects P&L reporting, board discussions

---

### Q2: Fanatics案件の状況を教えて

**Question**
"Fanatics案件のステータスと次のアクションは何ですか? (What's the status of Fanatics case and next action?)"

**AI理解**
- Fanatics = customer name
- 案件 = project/case (but multiple granularities exist)
- Should return: current status, next milestone, risk
- Status lives in case master (not found in real DB)

**分からないこと**
- 案件粒度: Fanaticすべての案件? それとも特定のPO?
- 案件識別: 顧客名から案件をどう特定?
- ステータス定義: 有効/進行中/納品待ち/完了 など?
- ステータス所在: どのテーブルにある?
- 期限情報: 次のマイルストーン日はどこに?

**Product Ownerへ質問**
① 「Fanatics案件」と聞いた場合、AIは何を返すべきですか? (全PO? 全商品? 特定PO?)
② 案件のステータスはどこに記録されていますか?
③ 有効な案件ステータス値は何ですか?
④ 案件に期限・次のアクション情報がありますか、どこに?
⑤ 複数のFanatics案件がある場合、どれを返すべきですか?

**なぜ必要か**
- Common query for project status
- Wrong case selected → misleading answer
- Customer interaction → reputation impact

---

### Q3: BEAMS案件の進捗はどこまで進んでますか

**Question**
"BEAMS案件は今どの段階ですか? いつ納品予定ですか? (Where is BEAMS case in its lifecycle? When's delivery scheduled?)"

**AI理解**
- BEAMS = another customer name
- Should return: current phase, deadline
- Status field exists somewhere (unclear)
- Deadline field unclear (not in Phase 10 schema)

**分からないこと**
- 案件ステータス定義: 「段階」とは何の段階?
- ステータス値: 計画中/進行中/納品待ち/完了 か、別の定義か?
- 期限フィールド: 納品予定日はどこに記録?
- 複数PO: BEAMSが複数PO/複数商品あったら?
- 進捗率: 進捗度合いをどう測定?

**Product Ownerへ質問**
① 「進捗段階」は以下のどれですか: 契約確定→生産開始→生産完了→納品→検査→完了?
② 納品予定日(期限)はどのテーブル・カラムにありますか?
③ 複数のBEAMS案件があった場合、最新のものを返すべきですか?
④ 進捗率などの定量情報はどこにありますか?
⑤ ステータス変更の履歴は記録されていますか?

**なぜ必要か**
- Project management queries
- Tracking accountability
- Delivery commitment management

---

### Q4: 遅れている案件は何件ありますか

**Question**
"今、遅れている案件は何件ですか? 何が遅れてますか? (How many cases are delayed? What's the delay?)"

**AI理解**
- Need: deadline vs actual/planned
- Need: compare to today's date
- Count delayed cases
- But deadline field not in DB

**分からないこと**
- 期限フィールド: どのテーブル・カラム?
- 遅延定義: 何日以上遅れたら「遅延」?
- 比較基準: 納品予定日 vs 実績納品日?
- ステータス: キャンセル・完了済みは含める?
- 遅延原因: 追跡可能?

**Product Ownerへ質問**
① 納品期限(予定納品日)はどこに記録されていますか?
② 「遅れている」の定義は何ですか (予定日超過 vs 2営業日超過)?
③ すでに納品完了した案件は含めないですね?
④ 遅延理由(顧客遅延指示/製造遅延/仕入遅延など)の追跡がありますか?
⑤ 本日日付として何を使いますか (システム日付)?

**なぜ必要か**
- Early warning for delays
- Customer communication
- Supply chain management

---

### Q5: 納期一覧を見たい

**Question**
"納期が近い順に案件を一覧で見たい (Show me all cases sorted by delivery deadline)"

**AI理解**
- Need: deadline field for all cases
- Sort ascending (nearest first)
- Show: case name, deadline, status
- But deadline field missing

**分からないこと**
- 期限フィールド: すべての案件に設定済み?
- 期限更新: 変更されたら追跡可能?
- 複数案件: 同一顧客で複数期限?
- 完了案件: 納品完了したらリストから外す?
- 表示項目: 何を表示すべき?

**Product Ownerへ質問**
① すべての案件に納期が設定されていますか (NULL許可)?
② 表示すべき案件の条件は何ですか (進行中のみ? 完了前のすべて)?
③ 同じ期限の案件の場合、どう順序付けしますか?
④ 過去の期限切れ案件は表示させますか?
⑤ 期限変更があった場合、変更履歴を追跡できますか?

**なぜ必要か**
- Project prioritization
- Workload planning
- Proactive delay management

---

### Q6: 担当者別の粗利を見たい

**Question**
"営業担当者ごとの粗利はいくらですか? (What's the gross profit contribution by sales staff?)"

**AI理解**
- Need: staff assignment for each case
- Need: margin allocation logic
- Aggregate by staff member
- 集計 table has 社員id

**分からないこと**
- 担当者定義: 1案件=1人? 複数人?
- 粗利配分: 複数人なら粗利をどう分ける?
- 同一商品複数PO: 同じ人が担当?
- 期間: 過去何か月分?
- 除外: キャンセル案件は含める?

**Product Ownerへ質問**
① 1案件に複数の営業担当者が関わる場合、粗利をどう分配しますか?
② 今月の「担当者別粗利」は、誰の粗利を見ていることになりますか?
③ 担当者が途中で変わった案件はどう扱いますか?
④ 人事異動で担当者が変わった場合、過去の実績はどの人に帰属させますか?
⑤ 退職者の案件はどう扱いますか?

**なぜ必要か**
- Sales performance evaluation
- Compensation calculation
- Effort attribution

---

### Q7: OEM売上を月別で見たい

**Question**
"OEM事業の売上は過去6か月どう推移してますか? (Show OEM sales trend for last 6 months)"

**AI理解**
- Need: OEM identification
- Need: sales by month
- Need: historical data
- 売上 table has 売上高

**分からないこと**
- OEM判定: 集計.分類の値は?
- 期間: 「過去6か月」は何月から?
- キャンセル: 含める? 除外?
- 返品: 含める? 除外?
- 集計単位: 単純合計でいい?

**Product Ownerへ質問**
① OEM売上を集計するときの条件は何ですか?
② キャンセル・返品を売上から除外しますか?
③ 月の境界は何時点ですか (売上日? 納品日? 入金日)?
④ 「6か月」は過去6か月の完全月ですか、それとも今月含む?
⑤ 同一案件が複数月にまたがる場合、どの月に計上しますか?

**なぜ必要か**
- Business segment tracking
- Trend analysis
- Forecast planning

---

### Q8: Retail売上も同じように見たい

**Question**
"Retail事業の売上の過去6か月推移は? (Show Retail sales trend for last 6 months)"

**AI理解**
- Similar to Q7
- Need: Retail identification
- Same aggregation logic
- But Retail criteria unclear

**分からないこと**
- Retail判定: OEMとの境界は?
- 判定値: 集計.分類で何を見る?
- OEM/Retail混在: 可能? 不可?
- サンプル: OEM? Retail? 中立?
- 集計: OEM+Retail≠全売上?

**Product Ownerへ質問**
① OEMとRetailの分類基準を教えてください (顧客? 商品? 契約?).
② OEMでもなくRetailでもない取引がありますか?
③ 同じ商品がOEM/Retail両方で売られることがありますか?
④ 分類は誰が決定して、どこに記録されますか?
⑤ 分類ルールは時間とともに変わりますか (歴史的な変更)?

**なぜ必要か**
- Business segment comparison
- Strategic decisions
- Pricing strategy

---

### Q9: キャンセルになった案件を見たい

**Question**
"今月キャンセルになった案件は何件ですか? 理由は何ですか? (How many cancellations this month? Why?)"

**AI理解**
- Need: 売上.ステータス = キャンセル
- Need: reason tracking
- Count and analyze
- Reason field unclear

**分からないこと**
- キャンセル記録: 売上.ステータス=キャンセルで判定?
- 理由記録: どこに記録されてる?
- 返金: 何か返金プロセスある?
- 履歴: いつからキャンセル可能?
- 部分キャンセル: 可能?

**Product Ownerへ質問**
① キャンセルの理由は記録されていますか (顧客都合/製造困難/その他)?
② キャンセル後、何かの返金プロセスがありますか?
③ 一度発注した商品を後で注文キャンセルできますか?
④ 何か月前までのキャンセルは記録に残っていますか (全期間)?
⑤ 部分的なキャンセル(一部数量のキャンセル)は記録されていますか?

**なぜ必要か**
- Customer satisfaction tracking
- Revenue variance analysis
- Process improvement

---

### Q10: 返品が発生している案件を見たい

**Question**
"今月返品が発生した案件は何件ですか? 返品理由は何ですか? (How many returns this month? Reasons?)"

**AI理解**
- Need: return flag or separate transaction
- Need: reason tracking
- Impact on margin (negative)
- Return mechanism unclear

**分からないこと**
- 返品記録: どこに記録されてる?
- 理由追跡: 不良/顧客都合/その他?
- 部分返品: 可能?
- 返品期限: いつまで受け付け?
- 返金: すべて返金?

**Product Ownerへ質問**
① 返品はどのように記録されていますか (テーブル? フラグ?)?
② 返品理由(不良/顧客都合/誤納品など)は記録されていますか?
③ 返品後の処理フロー (返金/再納品/廃棄 など)は記録されていますか?
④ 何日以内なら返品受付可能ですか?
⑤ 返品後、在庫に戻しますか、廃棄しますか?

**なぜ必要か**
- Quality tracking
- Customer service
- Cost analysis

---

### Q11: 今日中にやることは何ですか

**Question**
"今日期限の案件は何ですか? (What cases have delivery deadline today?)"

**AI理解**
- Need: deadline = today's date
- Need: deadline field in DB
- Count and list
- But deadline field missing

**分からないこと**
- 期限フィールド: なし?
- 「今日」の定義: システム日付?
- 今日期限でまだ納品できてない案件?
- 優先度: 何から手をつける?
- リマインダー: 誰に通知?

**Product Ownerへ質問**
① 納品期限が本日の案件を抽出できますか (期限フィールドが必要)?
② 期限と実績納品日の比較で、遅延判定できますか?
③ 本日中にやるべき優先順序は何ですか (顧客重要度? 利益? その他)?
④ 毎日朝、これを確認する人は誰ですか (営業? 生産? 経営)?
⑤ 期限までに完了できなかった案件はどう追跡しますか?

**なぜ必要か**
- Daily operations
- Task prioritization
- Accountability tracking

---

### Q12: 先月との利益比較で上位ランキングを見たい

**Question**
"今月の利益ランキング (商品別)は? 先月と比べてどう? (Top profitable products this month vs last month?)"

**AI理解**
- Need: profit by product
- Need: month-over-month comparison
- Rank descending
- But aggregation logic unclear

**分からないこと**
- 商品定義: 型番単位? 色別? サイズ別?
- 粗利: 実績? 論理? 担当別?
- 先月: 何月?
- ランキング: 絶対額? 率?
- 部分: 商品Aで複数PO/顧客あったら?

**Product Ownerへ質問**
① 「商品別利益ランキング」は何を基準に順位付けしますか (粗利額? 粗利率?)?
② 同じ商品が複数PO・複数顧客で売られている場合、すべて集計しますか?
③ 先月との「比較」は増減額ですか、増減率ですか?
④ 売上数量が少ない商品と、多い商品の比較をどう見ますか?
⑤ ランキングから外れた商品(売上0等)を見たいことはありますか?

**なぜ必要か**
- Product portfolio analysis
- Performance management
- Strategic focus areas

---

### Q13: 顧客別に売上を見たい

**Question**
"顧客別の売上ランキングは? 今月TOP 10は? (Show top 10 customers by sales this month)"

**AI理解**
- Need: sales aggregated by customer
- Need: rank descending
- Count: top 10
- 顧客 table available

**分からないこと**
- 顧客特定: 顧客名? 顧客ID?
- 複数名義: 同じ顧客、違う名前で登録されてたら?
- 期間: 「今月」の定義?
- 返品: 含める?
- キャンセル: 含める?

**Product Ownerへ質問**
① 顧客を「顧客名」で集計していいですか、それとも「顧客ID」で集計すべきですか?
② 同じ顧客なのに複数の名前で登録されていることはありますか?
③ 返品・キャンセルは売上から差し引きますか?
④ 「今月TOP 10」の「月」は何月ですか (カレンダー月? 会計月)?
⑤ 内訳を見る場合(その顧客のどの商品の売上など)、どこまでドリルダウンできますか?

**なぜ必要か**
- Customer value analysis
- Relationship management
- Pricing decisions

---

### Q14: 商品別に売上を見たい

**Question**
"商品別の売上ランキングは? 今月の売上トップ商品は? (Show top products by sales this month)"

**AI理解**
- Need: sales by product
- Need: rank descending
- Product = SKU (型番+色+サイズ assumed)
- 商品 table available

**分からないこと**
- 商品粒度: 型番のみ? 色別? サイズ別?
- 複数商品: 類似商品の集計?
- 売上: 数量ベース? 金額ベース?
- 期間: 「今月」?
- フィルタ: OEM/Retail別に見たい?

**Product Ownerへ質問**
① 「商品」の定義は何ですか (型番? 型番+色? 型番+色+サイズ?)?
② 売上ランキングは金額ベースですか、数量ベースですか?
③ 関連商品(例: 同じ型番の色違い)をまとめて見たい場合がありますか?
④ OEM商品とRetail商品を分けて見たいですか?
⑤ 商品ごとの利益率(粗利率)も一緒に見たいですか?

**なぜ必要か**
- Product performance
- Inventory management
- Production planning

---

### Q15: 仕入コストの分析をしたい

**Question**
"仕入コストが高い商品は何ですか? 先月との比較は? (Which products have high procurement costs? Month-over-month trend?)"

**AI理解**
- Need: cost by product
- Need: 実績原価 vs 論理原価
- Identify trends
- 仕入 table available (44k rows)

**分からないこと**
- 原価種別: 論理? 実績? 当月取得可?
- 商品粒度: 型番単位? 色単位?
- 変動理由: 原価が上がったなぜ?
- 仕入先: 複数? どこから買ってる?
- 割増: 運賃/関税も含める?

**Product Ownerへ質問**
① 仕入原価を分析する場合、「実績原価」をいつから取得できますか?
② コスト上昇の理由(仕入先変更/数量減/為替など)は追跡されていますか?
③ 同じ商品でも仕入先が複数ある場合、どう扱いますか?
④ 仕入諸掛(運賃/関税など)の変動も追跡していますか?
⑤ 原価低減の目標・施策の進捗は記録されていますか?

**なぜ必要か**
- Cost management
- Supplier relationship
- Margin improvement

---

### Q16: 粗利率の比較がしたい

**Question**
"今月の商品別粗利率は? 先月と比べてどの商品が利益率悪化してますか? (Product margin ratios - which ones worsened vs last month?)"

**AI理解**
- Need: 粗利 ÷ 売上 * 100% = 粗利率
- Need: by product
- Need: month-over-month change
- But calculation logic unclear

**分からないこと**
- 粗利率公式: 粗利÷売上? 粗利÷売上原価?
- 分子: 実績? 論理? 担当別?
- 分母: 売上高? 売上原価?
- 悪化: 率低下? 絶対額低下?
- 分析: なぜ悪化した理由を追跡?

**Product Ownerへ質問**
① 粗利率の計算公式は何ですか (粗利÷売上×100%ですか)?
② 分母に「売上原価」を使う場合がありますか?
③ 粗利率が「悪化した」ことをどのように判定していますか?
④ 悪化の原因(売上減? コスト上昇? その他)の追跡がありますか?
⑤ 粗利率の目標値は設定されていますか?

**なぜ必要か**
- Pricing analysis
- Product profitability
- Strategic decisions

---

### Q17: PO発注でまだ納品されていない案件を見たい

**Question**
"発注したけどまだ納品されていないPOはどれですか? 何日かかってますか? (Which POs not yet delivered? How many days)?)"

**AI理解**
- Need: PO status tracking
- Need: compare order date vs expected delivery
- Need: actual delivery tracking
- 発注依頼 table exists

**分からないこと**
- 発注日: po発行日時?
- 納期: どこに?
- 納品: 実績納品日?
- 状態: 進行中とはステータスどこ見る?
- 遅延: 許容日数は?

**Product Ownerへ質問**
① PO発注日(po発行日時)から納品までの「目安日数」は商品ごとに異なりますか?
② 納期(期待納品日)はどこに記録されていますか?
③ 実績納品日と計画納期の差分を追跡していますか?
④ 遅延の理由(仕入先遅延/品質問題/その他)は記録されていますか?
⑤ 遅延しているPOに対して、催促などのアクション履歴がありますか?

**なぜ必要か**
- Supply chain management
- Production planning
- Vendor performance

---

### Q18: 売上と入金のギャップを見たい

**Question**
"売上計上してから入金まで何日かかってますか? 売上債権はいくら? (How many days from sales recognition to payment? Outstanding receivables?)"

**AI理解**
- Need: 売上日 vs 入金日
- Need: outstanding receivables tracking
- Payment terms management
- But payment field unclear

**分からないこと**
- 売上日: 売上.期?
- 入金日: どこに記録?
- 未回収: 売上-入金?
- 期限: 何日以内に入金すべき?
- 回収率: どれくらい遅れがある?

**Product Ownerへ質問**
① 売上認識日と入金日がそれぞれどこに記録されていますか?
② 入金は全額一括ですか、分割ですか?
③ 顧客別に支払い条件(〇〇日後払いなど)がありますか?
④ 回収遅延している売上(未入金)を追跡していますか?
⑤ 何か月以上未回収なら「要注意」としていますか?

**なぜ必要か**
- Cash flow management
- Credit risk
- Collection management

---

### Q19: 予定と実績のズレを見たい

**Question**
"計画していた売上 vs 実績売上は何がどれくらいズレてますか? (Planned vs actual sales - what's the gap?)"

**AI理解**
- Need: forecast/plan data
- Need: actual sales
- Compare and analyze variance
- But plan data location unclear

**分からないこと**
- 計画: どこに記録?
- 対象: 全案件? 商品別?
- 粒度: 日単位? 月単位?
- 金額: 数量ベース?
- 分析: 原因追跡できる?

**Product Ownerへ質問**
① 売上計画(フォーキャスト)はどこに記録されていますか (Logsys? Google Sheets? 別システム?)?
② 計画は何レベルで立てられていますか (商品別? 顧客別? 全社別?)?
③ 計画と実績のズレを誰が毎月追跡していますか?
④ ズレが大きい案件がある場合、原因を分析していますか (顧客遅延? 製造遅延? 需要減?)?
⑤ 計画の見直しはどのタイミングで行いますか?

**なぜ必要か**
- Forecast accuracy
- Planning process
- Performance management

---

### Q20: 部門別・事業別の利益を見たい

**Question**
"OEM部門の利益 vs Retail部門の利益は? どちらが会社に貢献してますか? (Division profitability - OEM vs Retail?)"

**AI理解**
- Need: business segment classification
- Need: profit aggregation by segment
- Compare performance
- But segment definition unclear

**分からないこと**
- 部門定義: OEM vs Retail だけ?
- 判定: 集計.分類?
- 粗利: 実績?
- 売上: 売上高?
- 他費用: 部門別配分?

**Product Ownerへ質問**
① 会社として「部門」はいくつありますか (OEM/Retail だけ? 他にもありますか?)?
② 各部門の定義・判定基準は何ですか?
③ 本社経費(販売管理費など)を部門別に配分していますか?
④ 経営判断でどちらに注力すべきかはどのKPIを見ていますか (売上? 利益? 利益率?)?
⑤ 部門ごとに異なる経営戦略(価格/品質/納期等)がありますか?

**なぜ必要か**
- Strategic planning
- Resource allocation
- Business decision making

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| **Total Questions** | 20 |
| **Questions per Category** | Business-oriented scenarios |
| **Unknowns per Question** | 3-5 key gaps |
| **Total PO Questions** | 100 (5 per question) |
| **Most Unclear Topics** | Case granularity, deadline field, cost basis |

---

## Knowledge Gaps Ranked by Frequency

| Gap | Appears in # Qs | Urgency |
|-----|-----------------|---------|
| 案件粒度 (Case granularity) | 6 (Q2, Q3, Q4, Q5, Q6, Q19) | 🔴 Critical |
| 期限フィールド (Deadline field) | 5 (Q4, Q5, Q11, Q17, Q19) | 🔴 Critical |
| OEM/Retail判定 (Classification) | 4 (Q1, Q7, Q8, Q20) | 🔴 Critical |
| ステータス定義 (Status values) | 4 (Q2, Q3, Q9, Q17) | 🔴 Critical |
| 粗利種別 (Profit variant) | 5 (Q1, Q6, Q12, Q15, Q16) | 🔴 Critical |
| 実績原価 (Actual cost) | 4 (Q1, Q15, Q16) | 🔴 Critical |
| 返品・キャンセル処理 | 3 (Q9, Q10, Q14) | 🟠 High |
| 期間定義 (Period) | 3 (Q1, Q7, Q8) | 🟠 High |
| 商品粒度 (Product unit) | 3 (Q6, Q13, Q14) | 🟠 High |
| 計画データ位置 (Plan location) | 2 (Q19) | 🟡 Medium |

---

## Top 5 Questions Requiring Most Clarification

1. **Q1: 今月のOEM粗利** — Requires understanding OEM, 粗利 variant, period, filters
2. **Q2: Fanatics案件の状況** — Requires case granularity, status field, deadline, disambiguation logic
3. **Q19: 予定 vs 実績** — Requires plan data location, forecasting process, variance tracking
4. **Q4: 遅れている案件** — Requires deadline field, delay definition, status tracking
5. **Q20: 部門別利益** — Requires business segment definition, allocation logic, strategy

---

**Status:** Ready for Product Owner responses  
**Next Step:** PO fills in answers to each question's 5 sub-questions  
**AI Learning:** AI will update understanding after each explanation

