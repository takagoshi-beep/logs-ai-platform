-- 2026-07-10（14.71、Noritsuguが実際の[TIMING]ログで発見した遅延の
-- 対策）: 案件一覧・今日のタスクで、LOGS_CODE単位の売上履歴取得
-- （sales_query）が突出して遅かった（他のクエリが70〜90msなのに対し
-- 1.5〜1.8秒）。SQL側で"LOGS_CODE" = ANY(%s) AND "売上入力日" >= %s
-- という条件になったため、この2列の複合インデックスを追加する。

CREATE INDEX IF NOT EXISTS idx_sales_logs_code_sales_date
    ON sales ("LOGS_CODE", "売上入力日");
