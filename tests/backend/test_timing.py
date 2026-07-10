"""Tests for `backend/services/timing.py` (docs/architecture.md 14.56).

This exists purely to help diagnose where the 5-10 second page loads
Noritsugu reported are actually spent (DB query time vs. query count vs.
Gmail/Slack calls vs. something else) — logged to stdout so it shows up
in Render's logs without needing a real APM tool.
"""
from __future__ import annotations

import time

from services.timing import timed


def test_timed_logs_elapsed_time_to_stdout(capsys):
    with timed("some_label"):
        pass

    captured = capsys.readouterr()
    assert "[TIMING] some_label:" in captured.out
    assert "ms" in captured.out


def test_timed_measures_actual_elapsed_time(capsys):
    with timed("sleep_test"):
        time.sleep(0.05)

    captured = capsys.readouterr()
    # "[TIMING] sleep_test: 53ms" のような行から数値部分を取り出す。
    line = [l for l in captured.out.splitlines() if "sleep_test" in l][0]
    ms = float(line.split(":")[-1].replace("ms", "").strip())
    assert ms >= 40  # 50msスリープしたので、それに近い値が出るはず


def test_timed_still_logs_when_the_body_raises(capsys):
    """例外が起きても計測ログは出す（finally節のため）。時間がかかった
    末に失敗したケースも、原因調査のログとして残したいため。"""
    try:
        with timed("failing_label"):
            raise ValueError("boom")
    except ValueError:
        pass

    captured = capsys.readouterr()
    assert "[TIMING] failing_label:" in captured.out


def test_timed_reraises_the_original_exception():
    with_error_raised = False
    try:
        with timed("label"):
            raise ValueError("boom")
    except ValueError:
        with_error_raised = True
    assert with_error_raised
