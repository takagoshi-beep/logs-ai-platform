"""表示速度の遅延がどこで発生しているかを特定するための、軽量な計測
ユーティリティ (docs/architecture.md 14.56)。

2026-07-09、Noritsuguから「案件一覧・商品一覧・詳細ページが5〜10秒
かかる」という報告があり、コネクションプール化(14.54・14.55)で改善
したものの、まだ遅延が残っている。「DBクエリ自体が遅いのか」「クエリ
回数が多いのか」「Gmail/Slack連携の呼び出しが遅いのか」を推測ではなく
Renderのログから直接特定するために導入した。

`time.perf_counter()`を使った単純な計測で、標準出力にログを出すだけ
（オーバーヘッドはマイクロ秒単位で無視できる）。しばらく運用してみて、
どこが実際に遅いか分かったら、原因が特定された部分だけを個別に最適化
し、このログ自体は残してもよいし外してもよい。
"""
from __future__ import annotations

import time
from contextlib import contextmanager


@contextmanager
def timed(label: str):
    """withブロックの実行時間を計測し、標準出力にログを出す。

    例:
        with timed("projects_list.db_fetch"):
            ...
    Renderのログには次のような行が出る:
        [TIMING] projects_list.db_fetch: 1234ms
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[TIMING] {label}: {elapsed_ms:.0f}ms")
