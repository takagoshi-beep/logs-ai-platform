"""Logisys(SQLite)のデモデータ投入スクリプト。

Execution Layer v0.1 用。既にテーブルがあれば何もしない（冪等）。
実行: cd backend && python scripts/seed_logisys_demo.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "sqlite" / "logsys.db"

SCHEMA = {
    "売上明細": """
        CREATE TABLE IF NOT EXISTS 売上明細 (
            id INTEGER PRIMARY KEY,
            売上日 TEXT,
            顧客コード TEXT,
            顧客名 TEXT,
            商品コード TEXT,
            商品名 TEXT,
            案件区分 TEXT,
            数量 INTEGER,
            金額 INTEGER,
            概算粗利 INTEGER,
            status INTEGER,
            payment_method INTEGER
        )
    """,
    "仕入明細": """
        CREATE TABLE IF NOT EXISTS 仕入明細 (
            id INTEGER PRIMARY KEY,
            仕入日 TEXT,
            仕入先名 TEXT,
            商品コード TEXT,
            商品名 TEXT,
            金額 INTEGER
        )
    """,
    "案件": """
        CREATE TABLE IF NOT EXISTS 案件 (
            id TEXT PRIMARY KEY,
            案件名 TEXT,
            顧客コード TEXT,
            顧客名 TEXT,
            案件区分 TEXT,
            ステータス TEXT,
            納期 TEXT
        )
    """,
    "顧客マスタ": """
        CREATE TABLE IF NOT EXISTS 顧客マスタ (
            顧客コード TEXT PRIMARY KEY,
            顧客名 TEXT,
            別名 TEXT
        )
    """,
    "商品マスタ": """
        CREATE TABLE IF NOT EXISTS 商品マスタ (
            商品コード TEXT PRIMARY KEY,
            商品名 TEXT,
            分類 TEXT
        )
    """,
}

CUSTOMERS = [
    ("C001", "Fanatics Japan", "Fanatics"),
    ("C002", "BEAMS JAPAN", "BEAMS"),
    ("C003", "UNITED ARROWS", "UA"),
    ("C004", "ZOZO", ""),
]

PRODUCTS = [
    ("P001", "チームジャージ", "OEM"),
    ("P002", "キャップ", "OEM"),
    ("P003", "別注トートバッグ", "OEM"),
    ("P004", "セレクトTシャツ", "Retail"),
    ("P005", "スニーカー", "Retail"),
    ("P006", "レプリカユニフォーム", "OEM"),
]

# status: 2-5=有効受注, 9=キャンセル / payment_method: 4=集計対象外
SALES = [
    (1, "2026-07-01", "C001", "Fanatics Japan", "P001", "チームジャージ", "OEM", 100, 1200000, 360000, 3, 1),
    (2, "2026-07-02", "C001", "Fanatics Japan", "P002", "キャップ", "OEM", 200, 800000, 240000, 2, 1),
    (3, "2026-07-05", "C001", "Fanatics Japan", "P006", "レプリカユニフォーム", "OEM", 150, 1500000, 450000, 4, 2),
    (4, "2026-07-03", "C002", "BEAMS JAPAN", "P004", "セレクトTシャツ", "Retail", 300, 900000, 270000, 3, 1),
    (5, "2026-07-08", "C002", "BEAMS JAPAN", "P003", "別注トートバッグ", "OEM", 120, 720000, 216000, 3, 1),
    (6, "2026-07-10", "C002", "BEAMS JAPAN", "P005", "スニーカー", "Retail", 80, 960000, 288000, 5, 1),
    (7, "2026-07-12", "C003", "UNITED ARROWS", "P004", "セレクトTシャツ", "Retail", 200, 600000, 180000, 2, 1),
    (8, "2026-07-15", "C003", "UNITED ARROWS", "P003", "別注トートバッグ", "OEM", 60, 360000, 108000, 3, 3),
    (9, "2026-07-18", "C004", "ZOZO", "P005", "スニーカー", "Retail", 500, 6000000, 1800000, 3, 1),
    (10, "2026-07-20", "C004", "ZOZO", "P004", "セレクトTシャツ", "Retail", 400, 1200000, 360000, 4, 1),
    (11, "2026-07-22", "C001", "Fanatics Japan", "P001", "チームジャージ", "OEM", 50, 600000, 180000, 9, 1),
    (12, "2026-07-25", "C002", "BEAMS JAPAN", "P004", "セレクトTシャツ", "Retail", 100, 300000, 90000, 3, 4),
    (13, "2026-06-28", "C001", "Fanatics Japan", "P002", "キャップ", "OEM", 100, 400000, 120000, 3, 1),
    (14, "2026-07-28", "C001", "Fanatics Japan", "P003", "別注トートバッグ", "OEM", 90, 540000, 162000, 2, 1),
]

# P003/P006 は仕入未入力（実績原価なし）のデモ
PURCHASES = [
    (1, "2026-07-03", "サプライヤーA", "P001", "チームジャージ", 780000),
    (2, "2026-07-06", "サプライヤーA", "P002", "キャップ", 500000),
    (3, "2026-07-09", "サプライヤーB", "P004", "セレクトTシャツ", 560000),
    (4, "2026-07-16", "サプライヤーC", "P005", "スニーカー", 3900000),
]

PROJECTS = [
    ("PJ-001", "Fanatics 2026SS OEMジャージ", "C001", "Fanatics Japan", "OEM", "進行中", "2026-07-15"),
    ("PJ-002", "Fanatics キャップ追加ロット", "C001", "Fanatics Japan", "OEM", "納品待ち", "2026-07-05"),
    ("PJ-003", "BEAMS 別注トート", "C002", "BEAMS JAPAN", "OEM", "進行中", "2026-07-25"),
    ("PJ-004", "UA セレクトT補充", "C003", "UNITED ARROWS", "Retail", "準備中", "2026-08-10"),
    ("PJ-005", "ZOZO 夏物スニーカー", "C004", "ZOZO", "Retail", "進行中", "2026-07-10"),
]


def main() -> None:
    con = sqlite3.connect(DB_PATH)
    for ddl in SCHEMA.values():
        con.execute(ddl)

    def seed(table: str, rows: list, placeholders: str) -> None:
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if count == 0:
            con.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
            print(f"seeded {table}: {len(rows)} rows")
        else:
            print(f"skip {table}: already has {count} rows")

    seed("顧客マスタ", CUSTOMERS, "?,?,?")
    seed("商品マスタ", PRODUCTS, "?,?,?")
    seed("売上明細", SALES, "?,?,?,?,?,?,?,?,?,?,?,?")
    seed("仕入明細", PURCHASES, "?,?,?,?,?,?")
    seed("案件", PROJECTS, "?,?,?,?,?,?,?")
    con.commit()
    con.close()
    print("done:", DB_PATH)


if __name__ == "__main__":
    main()
