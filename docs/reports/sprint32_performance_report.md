# Sprint32 Performance Report


<!-- SNAPSHOT-BANNER -->
> **📌 Point-in-time snapshot.** This document records the state of the
> project as of the date/phase named in its title or body. It has not been
> updated since, and may not reflect the current code. Verify claims against
> the current source before relying on them. For the maintained, current
> architecture reference, see `docs/architecture.md` and `docs/system_manifest.md`.

## Sync

- /api/sync response elapsed_time: 0.441548
- Harness elapsed_seconds: 0.487227

## Chat

- 売上トップ10は？: 0.115146s, layers=Validation, Context, Intent, Question, Planner, Workflow, Business, BusinessQuery, BusinessToolSelection, RepositoryQuery, Storage, Formatter, AnswerSource, Answer, Runtime
- ABC社との取引履歴: 0.0627s, layers=Validation, Context, Intent, Question, Planner, Workflow, BusinessQuery, AnswerSource, Answer, Runtime
- バッグ商品の一覧: 0.060755s, layers=Validation, Context, Intent, Question, Planner, Workflow, Business, BusinessQuery, BusinessToolSelection, RepositoryQuery, Storage, Formatter, AnswerSource, Answer, Runtime
- 今月受注金額: 0.072206s, layers=Validation, Context, Intent, Question, Planner, Workflow, BusinessQuery, AnswerSource, Answer, Runtime

## Stage Observations

- Sync timing is captured at the API boundary and persisted in sync status.
- Business answer timing is visible in trace records for Answer / RepositoryQuery / Storage.
- Storage trace records include source_information for the answered tables.
