# API contract (sketch)

[← Back to the index](README.md)

| Method & path | Purpose | Responses |
|---|---|---|
| `GET /api/lawyers` | Identity picker | 200 `[ {id, name, title} ]` |
| `GET /api/plan` | Plan counter | 200 `{limit, completed, running, available, period:"2026-11", resets_at}` |
| `GET /api/documents` | List (F1) | 200 `[ {id, title, type, pages, uploaded_at, uploaded_by, supersedes, superseded_by, latest_review:{id,status,failure_reason,requested_by,requested_at,finished_at,findings_count?}, current_result:{review_id, finished_at, findings_count}?} ]` |
| `GET /api/documents/{id}` | Detail | 200 / 404 |
| `POST /api/documents/{id}/reviews` | Request (F2). Header `X-Lawyer-Id`. | 201 `review` · 400 `UNKNOWN_LAWYER` · 404 · 409 `REVIEW_IN_PROGRESS {review}` · 409 `PLAN_EXHAUSTED {resets_at, completed, running}` |
| `GET /api/reviews/{id}` | Follow (F2) and read (F3) | 200 `{id, document_id, status, failure_reason, requested_by, requested_at, deadline_at, finished_at, server_now, is_final, findings:[{seq, clause, title, severity, excerpt, explanation}]}` |

Response rules:

- `findings` is returned for `running` (`is_final=false`) and `completed` (`is_final=true`). For `failed`, it is always `[]`, so no client can display a failed review's partial findings.
- `GET /api/documents` returns both `latest_review` (any status, for the list badge) and `current_result` (latest completed, for the main screen).
- Every read applies lazy expiry (BR-8).
- Error body: `{code, message, details}`, with stable `code` values that the UI maps to copy.
