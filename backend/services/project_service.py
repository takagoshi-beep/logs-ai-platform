"""Project Service - Orchestrates domain model to build complete project understanding."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from domain.project import (
    GoalEvaluation,
    GoalEvaluations,
    GoalStatus,
    ProjectAction,
    ProjectAggregate,
    ProjectData,
    ProjectDecision,
    ProjectDecisionDetail,
    ProjectEvent,
    ProjectEventType,
    ProjectEvents,
    ProjectGoal,
    ProjectState,
)
from capability.domain import ExecutionStatus
from services.supabase_client import get_connection
from services.trace_store import save_trace
from services.capability_instance import (
    PROJECT_AGGREGATE_CAPABILITY,
    ensure_registered,
    registry as capability_registry,
)


class ProjectService:
    """Service for building complete ProjectAggregate from database."""

    def __init__(self, db_path: Path | None = None):
        """Initialize service. Supabase connection details come from services.supabase_client."""
        self.db_path = db_path

    def _generate_trace_id(self, project_id: str) -> str:
        """Generate deterministic trace ID based on project."""
        project_hash = hashlib.md5(str(project_id).encode()).hexdigest()[:8]
        return f"project-{project_hash}"

    def _query_projects_from_db(self, limit: int = 50, owner_name: str | None = None) -> list[dict[str, Any]]:
        """Query database to find all project candidates (Purchase Orders).

        owner_name: 指定すると、その氏名が「営業担当者名」または
        「営業事務担当者名」と完全一致する案件だけに絞り込む
        （ログイン中の本人の案件をデフォルト表示するための絞り込み、
        docs/architecture.md 14.28）。Noneなら従来通り全件対象。
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                if owner_name:
                    cur.execute(
                        'SELECT DISTINCT "ID" FROM purchase_orders '
                        'WHERE "営業担当者名" = %s OR "営業事務担当者名" = %s '
                        'ORDER BY "ID" DESC LIMIT %s',
                        (owner_name, owner_name, limit),
                    )
                else:
                    cur.execute('SELECT DISTINCT "ID" FROM purchase_orders ORDER BY "ID" DESC LIMIT %s', (limit,))
                rows = cur.fetchall()
            return [{"id": row[0]} for row in rows]
        except Exception as e:
            print(f"Error querying projects: {e}")
            return []
        finally:
            conn.close()

    _PO_SELECT_COLUMNS = (
        '"ID", "PO_No", "仕入先ID", "仕入先名", "顧客ID", "顧客名", '
        '"PO発行日", "顧客納品日", "納品日", "Delivery_納品日", "LOGS_CODE", "案件名", "輸入経費率", "ステータス", '
        '"合計発注金額", "合計売上原価", "合計売上金額"'
    )

    @staticmethod
    def _parse_date(date_val: Any) -> datetime | None:
        if not date_val:
            return None
        if isinstance(date_val, datetime):
            return date_val
        try:
            return datetime.fromisoformat(str(date_val).replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def _format_logs_code_for_project(value: Any) -> str | None:
        """purchase_orders.LOGS_CODEもproducts.LOGS_CODEと同じ理由
        （Supabase上でdouble precision型のため13564が13564.0になる、14.30）
        で正規化が必要。sales/purchasesとの突合キーとして使う前に統一する。
        """
        if value is None:
            return None
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _po_dict_to_project_data(self, project_id: str, po_dict: dict[str, Any]) -> ProjectData | None:
        """Convert an already-fetched purchase_orders row (as a dict) into
        ProjectData. Shared by both the single-project and batch code paths
        so the parsing logic only lives in one place.
        """
        try:
            po_number = po_dict.get("PO_No", "") or ""
            supplier_id = str(po_dict.get("仕入先ID", "") or "unknown")
            supplier_name = po_dict.get("仕入先名", "") or ""
            customer_id = str(po_dict.get("顧客ID", "") or "unknown")
            customer_name = po_dict.get("顧客名", "") or ""
            po_created = self._parse_date(po_dict.get("PO発行日")) or datetime.now()
            # 2026-07-10（14.69修正、Noritsuguの指摘）: 納期判定は以前
            # "顧客納品日"を使っていたが、リピート発注の際に営業担当者が
            # 前回POの"顧客納品日"をコピーしたまま更新し忘れるケースが
            # あり、信頼できないことが判明した（14.57で"顧客納品日は入力
            # 予定日で実際の納品有無とは無関係"と判明していたのと同じ根
            # の問題）。実際のExcel原本には"顧客納品日"とは別に
            # "Delivery／納品日"という列があり（sync時に"／"は"_"に
            # クレンジングされ"Delivery_納品日"になる）、そちらを正式な
            # 納期として使うよう変更した。
            po_required_delivery = self._parse_date(po_dict.get("Delivery_納品日")) or (datetime.now() + timedelta(days=30))

            project_data = ProjectData(
                project_id=project_id,
                po_number=po_number or f"PO-{project_id}",
                supplier_id=supplier_id,
                supplier_name=supplier_name or "Supplier",
                customer_id=customer_id,
                customer_name=customer_name or "Customer",
                po_created_date=po_created,
                po_required_delivery_date=po_required_delivery,
                supplier_phone=None,
                supplier_email=None,
                supplier_address=None,
                customer_phone=None,
                customer_email=None,
                customer_address=None,
                po_required_delivery_date_alt=None,
                actual_delivery_date=self._parse_date(po_dict.get("納品日")),
                invoice_date=None,
                payment_due_date=None,
                actual_payment_date=None,
                products=[],
                po_amount=float(po_dict.get("合計発注金額", 0) or 0),
                supplier_invoice_amount=None,
                cost_amount=float(po_dict.get("合計売上原価", 0) or 0),
                sale_amount=float(po_dict.get("合計売上金額", 0) or 0),
                gross_profit=None,
                gross_profit_margin=None,
                logs_code=self._format_logs_code_for_project(po_dict.get("LOGS_CODE")),
                has_sales=self._parse_date(po_dict.get("sales_date")) is not None,
                has_purchase=self._parse_date(po_dict.get("purchase_date")) is not None,
                production_closed=bool(po_dict.get("production_closed", False)),
                sales_date=self._parse_date(po_dict.get("sales_date")),
                purchase_date=self._parse_date(po_dict.get("purchase_date")),
                project_name=po_dict.get("案件名") or None,
                planned_import_cost_ratio=float(po_dict["輸入経費率"]) if po_dict.get("輸入経費率") is not None else None,
                actual_import_cost_ratio=float(po_dict["actual_import_cost_ratio"]) if po_dict.get("actual_import_cost_ratio") is not None else None,
                po_status=int(po_dict["ステータス"]) if po_dict.get("ステータス") is not None else None,
                actual_cost_total=float(po_dict["actual_cost_total"]) if po_dict.get("actual_cost_total") is not None else None,
            )

            if project_data.cost_amount and project_data.sale_amount:
                project_data.gross_profit = project_data.sale_amount - project_data.cost_amount
                project_data.gross_profit_margin = project_data.profit_margin_pct

            return project_data
        except Exception as e:
            print(f"Error building project data: {e}")
            return None

    def _attach_existence_data(self, conn, po_dicts: list[dict[str, Any]]) -> None:
        """po_dictsの各行に sales_date/purchase_date/production_closed を
        書き込む。1行ごとの相関サブクエリ（以前の実装）ではなく、
        LOGS_CODE/PO_Noのリストをまとめて`= ANY(%s)`で引く**固定回数の
        クエリ**にすることで、行数に関わらずクエリ回数を固定する
        （2026-07-09、14.37）。

        14.33/14.35で導入した1行ごとの相関サブクエリ（EXISTS/MIN）が、
        sales/purchasesのようなインデックスの無い大きいテーブルに対して
        行数分実行され、案件一覧の表示が著しく遅くなっていた実例の修正。
        14.28で学んだ「N回接続ではなく1回にまとめる」の教訓を、今回は
        「1回の接続の中でも、行ごとの重いサブクエリではなくまとめて
        引く」という形で再徹底している。

        LOGS_CODEはdouble precision型のため、SQL側の比較には生の値
        （float）をそのまま使い、Python側の突合キーとしてのみ
        `_format_logs_code_for_project`で正規化する（型不一致を避ける
        ため、14.30・本日複数回遭遇した問題と同じ理由）。

        2026-07-09（14.38修正）: 同じLOGS_CODEを再発注・再納品している
        OEM案件で、活動履歴に一番古い売上/仕入日が表示されてしまう
        不具合を修正（MIN→MAX）。同一商品が複数回発注される場合、
        直近の履歴の方が案件の実態に近いと判断した。

        2026-07-09（14.41修正、Noritsuguの指定）: 仕入登録（has_purchase/
        purchase_date、活動履歴の「仕入登録」イベント、状態バッジの
        「原価未確定」判定）は、商品単位（LOGS_CODE）ではなくPO単位
        （purchases."POnum" = purchase_orders."PO_No"）で判定する。

        2026-07-09（14.52修正、Noritsuguの指定）: 実績輸入経費率・
        実績原価は、同じPO番号の明細を SUM("諸掛込金額円") /
        SUM("仕入金額円") で加重平均する。1行だけ（DISTINCT ON）を
        採用する方式（14.43で一度採用）は、複数明細のうち1行の値しか
        反映されない問題があったため、加重平均に変更した。PO単位に
        する理由は、他のPOに同じ商品が含まれる場合に、その案件と無関係
        な数字が混ざらないようにするため（商品単位で集計すると、他の
        PO・他の案件の仕入まで混ざってしまう。商品単位の集計は商品詳細
        側で別途行う）。
        """
        if not po_dicts:
            return

        raw_logs_codes = [d["LOGS_CODE"] for d in po_dicts if d.get("LOGS_CODE") is not None]
        po_numbers = list({d["PO_No"] for d in po_dicts if d.get("PO_No")})

        # 2026-07-10（14.69修正、Noritsuguの指定）: リピート商品（同じ
        # LOGS_CODEを複数のPOで繰り返し発注している商品）で、過去の別PO
        # の売上入力が今回のPOの「売上確定」と誤判定されてしまう問題が
        # あった。以前はLOGS_CODEごとにMAX("売上入力日")を1つだけ集計し、
        # 同じLOGS_CODEを持つ全てのPOに同じ値を割り当てていたため、
        # 今回のPOがまだ納品されていなくても、過去の別注文の売上入力を
        # 見て「確定済み」と誤判定してしまっていた。個別の売上日を全て
        # 保持しておき、各POのDelivery_納品日（①で信頼できる納期に
        # 変更済み）以降の売上に絞り込んでから判定するよう修正した。
        sales_dates_by_logs_code: dict[str, list[Any]] = {}
        purchase_dates_by_po: dict[str, Any] = {}
        actual_import_cost_ratios_by_po: dict[str, Any] = {}
        actual_cost_totals_by_po: dict[str, Any] = {}
        closed_po_numbers: set[str] = set()

        from services.timing import timed

        # 2026-07-10（14.71修正、Noritsuguが実際の[TIMING]ログで発見）:
        # 14.69で「各POの納期以降の売上だけを対象にする」ためにLOGS_CODE
        # ごとの全ての個別売上行を取得する方式に変えたところ、これが
        # 案件数（50件）ではなく該当商品の**売上行数**（例: n=1302件）に
        # 比例して重くなり、[TIMING]で1.5〜1.8秒という突出したボトル
        # ネックになっていた（他のクエリは70〜90ms程度）。
        # このバッチ内の全POのうち最も古い納期より前の売上は、どのPOの
        # 判定にも絶対に使われない（14.69のロジックは常に「そのPOの納期
        # 以降」しか見ないため）ので、SQL側のWHERE句に追加してあらかじめ
        # 除外する。これにより、リピート販売されている商品でも、この
        # バッチに無関係な古い販売履歴まで転送・保持せずに済む。
        earliest_relevant_delivery_date = None
        for d in po_dicts:
            parsed = self._parse_date(d.get("Delivery_納品日"))
            if parsed and (earliest_relevant_delivery_date is None or parsed < earliest_relevant_delivery_date):
                earliest_relevant_delivery_date = parsed

        try:
            if raw_logs_codes:
                with timed(f"attach_existence_data.sales_query(n={len(raw_logs_codes)})"):
                    with conn.cursor() as cur:
                        if earliest_relevant_delivery_date:
                            cur.execute(
                                'SELECT "LOGS_CODE", "売上入力日" FROM sales '
                                'WHERE "LOGS_CODE" = ANY(%s) AND "売上入力日" >= %s',
                                (raw_logs_codes, earliest_relevant_delivery_date),
                            )
                        else:
                            cur.execute(
                                'SELECT "LOGS_CODE", "売上入力日" FROM sales '
                                'WHERE "LOGS_CODE" = ANY(%s)',
                                (raw_logs_codes,),
                            )
                        for logs_code, sale_date in cur.fetchall():
                            key = self._format_logs_code_for_project(logs_code)
                            sales_dates_by_logs_code.setdefault(key, []).append(sale_date)

            if po_numbers:
                # 仕入登録（活動履歴・状態バッジ用）はPO単位（14.41）。
                with timed(f"attach_existence_data.purchase_date_query(n={len(po_numbers)})"):
                    with conn.cursor() as cur:
                        cur.execute(
                            'SELECT "POnum", MAX("伝票日") FROM purchases '
                            'WHERE "POnum" = ANY(%s) GROUP BY "POnum"',
                            (po_numbers,),
                        )
                        for po_no, max_date in cur.fetchall():
                            purchase_dates_by_po[po_no] = max_date

                # 2026-07-09（14.49・14.52修正、Noritsuguの指定）: 実績原価
                # （予定vs確定の粗利比較用）・実績輸入経費率は、同じPO
                # 番号の明細をまとめてSUM(諸掛込金額円)/SUM(仕入金額円)
                # で加重平均する。purchases."諸掛込金額円"は実際の
                # Supabase列名（Excel原本の見出しは括弧付き"諸掛込金額
                # （円）"だが、sync.pyのクレンジングで括弧が消えている。
                # 実際にinformation_schema.columnsで確認して判明、14.50）。
                #
                # 2026-07-09（14.53修正、Noritsuguが実データで発見）:
                # 国内メーカー（現金仕入等）からの仕入は輸入諸掛が
                # 発生しないため"諸掛込金額円"が入力されずNULLのままに
                # なっており、実績原価・実績輸入経費率が0になっていた。
                # "諸掛込金額円"が無ければ「諸掛が無い（輸入品ではない）」
                # という意味なので、COALESCEで"仕入金額円"にフォールバック
                # する（経費率は1.0相当になる）。
                with timed(f"attach_existence_data.cost_ratio_query(n={len(po_numbers)})"):
                    with conn.cursor() as cur:
                        cur.execute(
                            'SELECT "POnum", SUM(COALESCE("諸掛込金額円", "仕入金額円")), SUM("仕入金額円") '
                            'FROM purchases WHERE "POnum" = ANY(%s) GROUP BY "POnum"',
                            (po_numbers,),
                        )
                        for po_no, total_with_fees, total_base in cur.fetchall():
                            actual_cost_totals_by_po[po_no] = total_with_fees
                            if total_base:
                                actual_import_cost_ratios_by_po[po_no] = total_with_fees / total_base

                with timed(f"attach_existence_data.production_mass_query(n={len(po_numbers)})"):
                    with conn.cursor() as cur:
                        cur.execute(
                            'SELECT DISTINCT "POnum" FROM production_mass '
                            'WHERE "POnum" = ANY(%s) AND "表示"::text = \'0\'',
                            (po_numbers,),
                        )
                        closed_po_numbers = {row[0] for row in cur.fetchall()}
        except Exception as e:
            print(f"Error attaching existence data: {e}")
            # 取得に失敗しても、案件一覧本体の表示は止めない（空のまま進める）。

        for d in po_dicts:
            logs_code = self._format_logs_code_for_project(d.get("LOGS_CODE"))
            # 2026-07-10（14.69修正、Noritsuguの指定）: 「納品日当日以降の
            # 売上がある場合に売上確定」とする。Delivery_納品日が無い
            # POは、従来通り全ての売上を対象にする（フォールバック、
            # 納期不明の案件を過度に厳しく扱わないため）。
            delivery_date = self._parse_date(d.get("Delivery_納品日"))
            candidate_dates = [self._parse_date(dt) for dt in sales_dates_by_logs_code.get(logs_code, [])]
            candidate_dates = [dt for dt in candidate_dates if dt is not None]
            if delivery_date:
                candidate_dates = [dt for dt in candidate_dates if dt >= delivery_date]
            d["sales_date"] = max(candidate_dates) if candidate_dates else None
            d["purchase_date"] = purchase_dates_by_po.get(d.get("PO_No"))
            d["actual_import_cost_ratio"] = actual_import_cost_ratios_by_po.get(d.get("PO_No"))
            d["actual_cost_total"] = actual_cost_totals_by_po.get(d.get("PO_No"))
            d["production_closed"] = d.get("PO_No") in closed_po_numbers

    def _build_project_data(self, project_id: str) -> ProjectData | None:
        """Build ProjectData for a single project by querying purchase_orders
        (real Supabase public schema). For fetching many projects at once
        (list views), use `_build_project_data_batch` instead — each call to
        this method opens its own DB connection, which is fine for a single
        lookup but far too slow in a loop (docs/architecture.md 14.28).
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'SELECT {self._PO_SELECT_COLUMNS} FROM purchase_orders WHERE "ID" = %s',
                    (project_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                columns = [desc[0] for desc in cur.description]
                po_dict = dict(zip(columns, row))
            self._attach_existence_data(conn, [po_dict])
        except Exception as e:
            print(f"Error building project data: {e}")
            return None
        finally:
            conn.close()

        return self._po_dict_to_project_data(project_id, po_dict)

    def _build_project_data_batch(self, project_ids: list[str]) -> dict[str, ProjectData]:
        """Fetch ProjectData for many projects in a single DB round-trip
        (one connection, a fixed small number of queries regardless of
        project count), instead of one connection per project. Added
        2026-07-08 (docs/architecture.md 14.28) after 案件一覧/今日のタスク
        were measured taking 20〜80秒 — almost entirely connection-open
        overhead multiplied by project count. Extended 2026-07-09 (14.37)
        to also batch the sales/purchases/production_mass lookups that
        14.33/14.35 had originally added as one-correlated-subquery-per-row
        (see `_attach_existence_data`).
        """
        if not project_ids:
            return {}

        from services.timing import timed

        conn = get_connection()
        try:
            with timed(f"build_project_data_batch.po_query(n={len(project_ids)})"):
                with conn.cursor() as cur:
                    cur.execute(
                        f'SELECT {self._PO_SELECT_COLUMNS} FROM purchase_orders WHERE "ID" = ANY(%s)',
                        (list(project_ids),),
                    )
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
            po_dicts = [dict(zip(columns, row)) for row in rows]
            with timed(f"build_project_data_batch.attach_existence_data(n={len(po_dicts)})"):
                self._attach_existence_data(conn, po_dicts)
        except Exception as e:
            print(f"Error batch-building project data: {e}")
            return {}
        finally:
            conn.close()

        result: dict[str, ProjectData] = {}
        for po_dict in po_dicts:
            project_id = str(po_dict.get("ID"))
            data = self._po_dict_to_project_data(project_id, po_dict)
            if data:
                result[project_id] = data
        return result

    def _generate_project_events(self, data: ProjectData, trace_id: str) -> ProjectEvents:
        """Generate business events from project data.

        2026-07-09（14.35、Noritsuguの指摘の修正）: 「売上登録」「仕入
        登録」の日付が、実際の入力日ではなくこの処理を実行した瞬間の
        現在時刻（now）になっていた不具合を修正。sales/purchasesの実際
        の日付（sales_date/purchase_date、複数行あれば直近のMAX、2026-07-09 14.38で修正）を使う。

        また、実質常に空のactual_delivery_date/actual_payment_dateに
        依存していた「納品完了」「支払完了」「納期リスク検知」イベント
        と、案件詳細のスコープ外に移した粗利再計算イベントは削除した
        （14.33・14.35で判明・整理済み）。
        """
        events = ProjectEvents(project_id=data.project_id)

        event_id = 1

        events.add_event(ProjectEvent(
            event_id=f"evt-{event_id}",
            project_id=data.project_id,
            event_type=ProjectEventType.PROJECT_CREATED,
            event_time=data.po_created_date,
            source_table="purchase_orders",
            business_meaning="PO作成 - 新規案件始動",
            impact_summary="プロジェクト開始、納期管理開始",
            trace_id=trace_id,
            event_source_type="actual",
            after_state=ProjectState.INITIATED,
            confidence=1.0,
        ))
        event_id += 1

        if data.has_purchase and data.purchase_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.PURCHASE_REGISTERED,
                event_time=data.purchase_date,
                source_table="purchases",
                business_meaning="仕入登録 - 原価確定",
                impact_summary="原価が確定し、粗利を計算可能に",
                trace_id=trace_id,
                event_source_type="actual",
                before_state=ProjectState.INITIATED,
                after_state=ProjectState.COST_UNCONFIRMED,
                confidence=1.0,
            ))
            event_id += 1

        if data.has_sales and data.sales_date:
            events.add_event(ProjectEvent(
                event_id=f"evt-{event_id}",
                project_id=data.project_id,
                event_type=ProjectEventType.SALES_REGISTERED,
                event_time=data.sales_date,
                source_table="sales",
                business_meaning="売上登録 - 納品完了と判断",
                impact_summary="売上が確定し、納品済みと判断",
                trace_id=trace_id,
                event_source_type="actual",
                after_state=ProjectState.COMPLETED,
                confidence=1.0,
            ))
            event_id += 1

        return events

    def _determine_state(self, data: ProjectData) -> ProjectState:
        """Determine a single primary project state, used internally for
        events/actions（related_state）— not the same as the画面表示用の
        `_determine_status_badges`（複数可）。

        2026-07-09（14.39、Noritsuguの指定）: 完了は「売上・仕入とも
        入力済み」の場合のみ。それ以外は原価未確定を優先して1つ返す
        （画面表示では売上未確定と原価未確定が同時に出ることもあるが、
        こちらは内部処理用の単一値なので優先順位をつけている）。
        納期超過は廃止（Noritsuguの判断、実データでは完了/売上未確定/
        原価未確定の3つだけで十分と判断したため）。
        """
        if data.has_sales and data.has_purchase:
            return ProjectState.COMPLETED
        if not data.has_purchase:
            return ProjectState.COST_UNCONFIRMED
        return ProjectState.SALES_UNCONFIRMED

    def _determine_status_badges(self, data: ProjectData) -> list[str]:
        """画面表示用の状態バッジ（複数可）。2026-07-09（14.39、14.42、
        14.48、Noritsuguの指定）:
          - 売上・仕入計上済（旧「完了」）: 売上・仕入とも入力済み
          - 売上未確定: 売上未入力
          - 原価未確定: 仕入未入力
        売上未確定・原価未確定は同時に成立しうる（どちらも未入力の場合、
        両方のバッジが返る）。売上・仕入計上済はこの2つとは排他的。

        別軸として、PO発行済み／PO未発行（purchase_orders."ステータス"
        =4かどうか）を常にどちらか一方追加する（14.42）。

        さらに別軸として、納品完了（生産管理）を追加する（14.48）。
        生産管理『量産』シートで表示OFFにされた（担当者が案件を終了済み
        として扱った印）案件には、売上・仕入の入力状況とは無関係に常に
        このバッジが付く。売上・仕入未入力のまま生産管理側だけ終了済み
        というケースも実際にありうるため、上の2軸とは独立させている。
        """
        if data.has_sales and data.has_purchase:
            badges = [ProjectState.COMPLETED.value]
        else:
            badges = []
            if not data.has_sales:
                badges.append(ProjectState.SALES_UNCONFIRMED.value)
            if not data.has_purchase:
                badges.append(ProjectState.COST_UNCONFIRMED.value)

        if data.production_closed:
            badges.append(ProjectState.DELIVERY_COMPLETED_BY_PRODUCTION.value)

        badges.append(ProjectState.PO_ISSUED.value if data.is_po_issued else ProjectState.PO_NOT_ISSUED.value)
        return badges

    def _evaluate_goals(self, data: ProjectData, state: ProjectState) -> GoalEvaluations:
        """Evaluate business goals for a project.

        2026-07-09（14.33）: 今日のタスクを「売上入力の必要性」「仕入
        入力の必要性」の2種類だけに絞り込むため、それ以外の目標
        （納期遵守・粗利確保・支払処理・顧客満足度）は評価しない
        （どこにも表示されず、Decisionも生成していなかった、
        Noritsuguの確認済み）。CONFIRM_DELIVERY（納品確認=売上入力の
        有無）とCONFIRM_COST（原価確定=仕入入力の有無）の2つだけを
        評価する。
        """
        evals = GoalEvaluations(project_id=data.project_id)

        if data.has_purchase and not data.has_sales:
            evals.evaluations[ProjectGoal.CONFIRM_DELIVERY] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_DELIVERY,
                status=GoalStatus.AT_RISK,
                reason="仕入は入力済みだが売上が未入力",
                confidence=0.9,
            )
        elif data.has_sales:
            evals.evaluations[ProjectGoal.CONFIRM_DELIVERY] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_DELIVERY,
                status=GoalStatus.ACHIEVED,
                reason="売上入力済み（納品済みと判断）",
                confidence=0.9,
            )
        else:
            evals.evaluations[ProjectGoal.CONFIRM_DELIVERY] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_DELIVERY,
                status=GoalStatus.UNKNOWN,
                reason="仕入・売上ともまだ未入力",
                confidence=0.5,
            )

        if data.has_sales and not data.has_purchase and data.is_overdue:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.AT_RISK,
                reason="納期を過ぎ売上は入力済みだが仕入が未入力",
                confidence=0.9,
            )
        elif data.has_purchase:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.ACHIEVED,
                reason="仕入入力済み（原価確定済みと判断）",
                confidence=0.9,
            )
        else:
            evals.evaluations[ProjectGoal.CONFIRM_COST] = GoalEvaluation(
                goal=ProjectGoal.CONFIRM_COST,
                status=GoalStatus.UNKNOWN,
                reason="仕入未入力（まだ納期前、または売上も未入力）",
                confidence=0.5,
            )

        # 2026-07-09（14.42、Noritsuguの指定）: 今日のタスクの3種類目。
        # PO自体がまだ発行されていない（purchase_orders."ステータス"≠4）。
        if not data.is_po_issued:
            evals.evaluations[ProjectGoal.ISSUE_PO] = GoalEvaluation(
                goal=ProjectGoal.ISSUE_PO,
                status=GoalStatus.AT_RISK,
                reason="POが未発行（ステータスが発注済以外）",
                confidence=0.9,
            )
        else:
            evals.evaluations[ProjectGoal.ISSUE_PO] = GoalEvaluation(
                goal=ProjectGoal.ISSUE_PO,
                status=GoalStatus.ACHIEVED,
                reason="PO発行済み",
                confidence=0.9,
            )

        return evals

    def _generate_decisions(self, data: ProjectData, state: ProjectState, goals: GoalEvaluations) -> list[ProjectDecisionDetail]:
        """Generate decisions from goal evaluations.

        2026-07-09（14.33）: 今日のタスクをa/bの2種類だけに絞る
        （Noritsuguの指定）。CONFIRM_DELIVERYがAT_RISK（仕入はあるが
        売上が無い）ならRECORD_SALES、CONFIRM_COSTがAT_RISK（納期後で
        売上はあるが仕入が無い）ならRECORD_PURCHASE。この2つは
        定義上同時には成立しない（前者はhas_salesが偽、後者は真が
        前提のため）。
        """
        decisions = []
        goal_dict = goals.evaluations

        confirm_delivery_eval = goal_dict.get(ProjectGoal.CONFIRM_DELIVERY)
        if confirm_delivery_eval and confirm_delivery_eval.status == GoalStatus.AT_RISK:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.RECORD_SALES,
                priority=1,
                reason="仕入は入力済みだが売上が未入力",
                confidence=0.9,
                triggered_by_goals=[ProjectGoal.CONFIRM_DELIVERY],
                business_rule="SALES_ENTRY_NEEDED",
            ))

        confirm_cost_eval = goal_dict.get(ProjectGoal.CONFIRM_COST)
        if confirm_cost_eval and confirm_cost_eval.status == GoalStatus.AT_RISK:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.RECORD_PURCHASE,
                priority=1,
                reason="納期を過ぎ売上は入力済みだが仕入が未入力",
                confidence=0.9,
                triggered_by_goals=[ProjectGoal.CONFIRM_COST],
                business_rule="PURCHASE_ENTRY_NEEDED",
            ))

        # 2026-07-09（14.42、Noritsuguの指定）: 今日のタスクの3種類目。
        issue_po_eval = goal_dict.get(ProjectGoal.ISSUE_PO)
        if issue_po_eval and issue_po_eval.status == GoalStatus.AT_RISK:
            decisions.append(ProjectDecisionDetail(
                decision=ProjectDecision.ISSUE_PO,
                priority=1,
                reason="POが未発行（ステータスが発注済以外）",
                confidence=0.9,
                triggered_by_goals=[ProjectGoal.ISSUE_PO],
                business_rule="PO_ISSUANCE_NEEDED",
            ))

        return decisions

    def _generate_actions(self, data: ProjectData, state: ProjectState, decisions: list[ProjectDecisionDetail], trace_id: str) -> list[ProjectAction]:
        """Generate concrete actions from decisions.

        2026-07-09（14.33）: 今日のタスクはa（売上入力の必要性）・b
        （仕入入力の必要性）の2種類のみ（Noritsuguの指定）。粗利改善・
        納期急ぎ連絡等の旧アクションは、実データで判定に使えない前提
        （POの納品日/支払日が空、粗利の予定/確定比較はまだ未実装）に
        基づいていたため廃止した。
        """
        actions = []
        action_id = 1
        # 2026-07-09（14.45、Noritsuguの指定）: タスク一覧のタイトル
        # （太字1行目）にもPO#＋案件名を表示する（案件詳細のタイトルや
        # タスクのサブタイトル行では14.40/14.41で既に対応済みだった）。
        po_label = f"{data.po_number}（{data.project_name}）" if data.project_name else data.po_number

        for decision in decisions:
            if decision.decision == ProjectDecision.RECORD_SALES:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"売上入力の必要性: {po_label}",
                    description=f"仕入は入力済みですが、{data.customer_name}への売上がまだ入力されていません。売上の入力をお願いします。",
                    priority="high",
                    related_state=state,
                    related_goal=ProjectGoal.CONFIRM_DELIVERY,
                    decision_source=decision.decision,
                    source_tables=["purchase_orders", "sales", "purchases"],
                    action_type="data_entry",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                    condition=decision.reason,
                ))
                action_id += 1

            elif decision.decision == ProjectDecision.RECORD_PURCHASE:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"仕入入力の必要性: {po_label}",
                    description=f"納期（{data.po_required_delivery_date.strftime('%Y-%m-%d')}）を過ぎ、{data.customer_name}への売上は入力済みですが、{data.supplier_name}への仕入がまだ入力されていません。仕入の入力をお願いします。",
                    priority="high",
                    related_state=state,
                    related_goal=ProjectGoal.CONFIRM_COST,
                    decision_source=decision.decision,
                    source_tables=["purchase_orders", "sales", "purchases"],
                    action_type="data_entry",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                    condition=decision.reason,
                ))
                action_id += 1

            elif decision.decision == ProjectDecision.ISSUE_PO:
                actions.append(ProjectAction(
                    action_id=f"act-{action_id}",
                    project_id=data.project_id,
                    title=f"PO発行が必要: {po_label}",
                    description=f"{data.customer_name}・{data.supplier_name}のPOがまだ発行されていません（ステータスが発注済以外）。POの発行をお願いします。",
                    priority="high",
                    related_state=state,
                    related_goal=ProjectGoal.ISSUE_PO,
                    decision_source=decision.decision,
                    source_tables=["purchase_orders"],
                    action_type="data_entry",
                    trace_id=trace_id,
                    confidence=decision.confidence,
                    condition=decision.reason,
                ))
                action_id += 1

        return actions

    def _determine_delivery_month_bucket(self, data: ProjectData) -> str | None:
        """納品予定月を「今月」「来月」「再来月以降」の3段階で分類する
        バッジ（docs/architecture.md 14.35、2026-07-09 14.38で修正）。

        以前あった健全性・リスク・機会スコアは、POの納品日/支払日が
        実質常に空という実データの制約下では意味を成していなかった
        （14.33で判明、Noritsuguの判断で廃止）。代わりに、今から納品日
        までの月数だけで判定する単純なロジックに置き換えた。

        既に納期を過ぎている場合はNoneを返す（バッジ自体を表示しない）
        — 状態バッジの方で「納期超過」として別途表示されるため、こちら
        で「今月中」に含めると混乱を招くというNoritsuguの指摘を反映
        （14.38、当初は"this_month"に含めていた）。
        """
        if data.is_overdue:
            return None

        now = datetime.now()
        target = data.po_required_delivery_date
        month_diff = (target.year - now.year) * 12 + (target.month - now.month)

        if month_diff <= 0:
            return "this_month"
        if month_diff == 1:
            return "next_month"
        return "month_after_next_or_later"



    def build_project_aggregate(self, project_id: str, record_capability: bool = True) -> ProjectAggregate | None:
        """Build complete ProjectAggregate for a single project.

        This is recorded as a Blueprint Capability execution (Principle 2:
        Capability Driven) via the shared registry in
        `services.capability_instance`, so it is visible/measurable through
        the `/capabilities` API — not just an ad-hoc function call.

        record_capability: 案件を1件だけ詳しく見る場面（/api/projects/{id}
        等）ではTrue（既定）のまま、Capability実行履歴・トレースへの書き込み
        を行う。一方、案件一覧・今日のタスクのように多数の案件をまとめて
        処理する場面では、案件1件ごとにSupabaseへの同期書き込みが複数回
        発生し体感速度を大きく損なうため、呼び出し側からFalseを渡して
        この記録処理自体をスキップできるようにしている
        （docs/architecture.md 14.28、実測で"今日のタスク"が数分かかる
        原因の大半がここだった）。
        """
        if not record_capability:
            return self._build_project_aggregate_impl(project_id)

        ensure_registered(PROJECT_AGGREGATE_CAPABILITY)
        trace_id = self._generate_trace_id(project_id)
        execution = capability_registry.execute_capability(
            capability_id=PROJECT_AGGREGATE_CAPABILITY.capability_id,
            inputs={"project_id": str(project_id)},
            user_id="system",
            project_id=str(project_id),
            trace_id=trace_id,
        )

        try:
            aggregate = self._build_project_aggregate_impl(project_id)
        except Exception as e:
            capability_registry.record_execution_result(
                execution_id=execution.execution_id,
                outputs={},
                status=ExecutionStatus.FAILED,
                error_message=str(e),
            )
            raise

        capability_registry.record_execution_result(
            execution_id=execution.execution_id,
            outputs={
                "found": aggregate is not None,
                "state": aggregate.state.value if aggregate else None,
                "priority": aggregate.priority if aggregate else None,
            },
            status=ExecutionStatus.COMPLETED if aggregate else ExecutionStatus.FAILED,
            error_message=None if aggregate else "project not found",
        )
        return aggregate

    def _build_project_aggregate_impl(self, project_id: str) -> ProjectAggregate | None:
        """Build complete ProjectAggregate for a single project (unwrapped).

        record_capability=Falseで呼ばれた場合はtrace保存もスキップする
        （save_trace自体もSupabase書き込みのため）。
        """
        data = self._build_project_data(project_id)
        if not data:
            return None
        return self._build_aggregate_from_data(project_id, data)

    def _build_aggregate_from_data(
        self, project_id: str, data: ProjectData, save_trace_flag: bool = True
    ) -> ProjectAggregate:
        """Run the (pure-Python, no DB access) event/goal/decision/action/
        health/risk calculations for an already-fetched ProjectData and
        assemble a ProjectAggregate. Split out from `_build_project_aggregate_impl`
        so `build_project_aggregates_bulk` can reuse it against data that was
        fetched in one batched query, instead of one query per project
        (docs/architecture.md 14.28).
        """
        trace_id = self._generate_trace_id(project_id)

        events = self._generate_project_events(data, trace_id)
        state = self._determine_state(data)
        goals = self._evaluate_goals(data, state)
        decisions = self._generate_decisions(data, state, goals)
        actions = self._generate_actions(data, state, decisions, trace_id)
        delivery_month_bucket = self._determine_delivery_month_bucket(data)
        status_badges = self._determine_status_badges(data)

        aggregate = ProjectAggregate(
            project_id=project_id,
            po_number=data.po_number,
            events=events,
            data=data,
            state=state,
            goal_evaluations=goals,
            decisions=decisions,
            actions=actions,
            trace_id=trace_id,
            priority="high" if decisions else "medium",
            delivery_month_bucket=delivery_month_bucket,
            status_badges=status_badges,
        )

        if save_trace_flag:
            try:
                save_trace(trace_id, aggregate.to_dict())
            except Exception:
                # Trace persistence must never block the actual response.
                pass

        return aggregate

    def _query_po_numbers_for_ids(self, ids: list[str]) -> list[str]:
        """指定した案件IDのPO番号だけを軽量に取得する（2026-07-10、14.72、
        Noritsuguの指定）。今日のタスクのGmail/Slack連携検索
        （get_task_signals）は、以前は「アクションが実際に生成された
        案件」のPO番号が確定するのを待ってから（=build_project_
        aggregates_bulk完了後に）実行していたため、Gmail/Slackの応答の
        重さ（1.7〜3秒程度）がそのまま直列に積み上がっていた。

        PO番号だけならbuild_project_aggregates_bulk（複数クエリの集計
        処理）を待たずに軽量なクエリ1本で取得できるため、これを使って
        Gmail/Slack検索を集計処理と並行に開始できるようにした。この
        場合、検索対象は「アクションがある案件」ではなく「このページに
        表示している全案件」に広がる（アクションの有無が確定する前に
        検索を始めるため）が、Gmail/Slackの結果は案件ごとの補足情報
        であり、多少広めに検索しても実害は無い。
        """
        if not ids:
            return []
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT DISTINCT "PO_No" FROM purchase_orders WHERE "ID" = ANY(%s)',
                    (list(ids),),
                )
                return [row[0] for row in cur.fetchall() if row[0]]
        except Exception as e:
            print(f"Error querying PO numbers: {e}")
            return []
        finally:
            conn.close()

    def build_project_aggregates_bulk(self, project_ids: list[str]) -> list[ProjectAggregate]:
        """Build ProjectAggregates for many projects at once, using exactly
        one DB connection/query total (via `_build_project_data_batch`)
        instead of one per project. This is the method list-style call
        sites (/api/projects, /api/today-actions, home's recent projects,
        get_my_projects) should use — `build_project_aggregate()` in a loop
        was measured taking 20〜80秒 for 20〜50 projects, almost entirely
        connection-open overhead (docs/architecture.md 14.28). Trace/
        Capability bookkeeping is always skipped here, matching
        record_capability=False's behavior, since this is inherently a
        bulk/listing code path.

        Returns aggregates in the same order as `project_ids`, skipping any
        id that no longer exists in purchase_orders.
        """
        data_map = self._build_project_data_batch(project_ids)
        aggregates = []
        for project_id in project_ids:
            data = data_map.get(str(project_id))
            if data:
                aggregates.append(self._build_aggregate_from_data(str(project_id), data, save_trace_flag=False))
        return aggregates
        

    def build_project_aggregates(self, limit: int = 50) -> list[ProjectAggregate]:
        """Build ProjectAggregates for multiple projects."""
        project_ids = self._query_projects_from_db(limit=limit)
        aggregates = []

        for proj_record in project_ids[:limit]:
            proj_id = proj_record.get("id")
            if proj_id:
                agg = self.build_project_aggregate(proj_id)
                if agg:
                    aggregates.append(agg)

        return aggregates