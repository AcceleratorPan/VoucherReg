# AGENT.md

## Purpose
This repository contains a FastAPI backend and a WeChat Mini Program frontend for voucher capture, OCR-based metadata extraction, manual confirmation, and final PDF generation.

This file is the project-level guide for future agents working in this repo. It is intended to reduce re-discovery cost, prevent contract drift, and keep backend and frontend changes aligned.

## Scope
- Backend: `/backend`
- Frontend: `/frontend`
- Product flow: create voucher task -> upload ordered page images -> finish upload -> OCR first page -> parse voucher metadata -> user confirms or edits fields -> generate final PDF -> view history/detail

## Source Of Truth
When sources conflict, use this order:

1. Running code in `/backend/app` and `/frontend/pages` plus `/frontend/utils/http.js`
2. Backend tests in `/backend/tests`
3. Backend API and architecture docs in `/backend/*.md`
4. Frontend docs in `/frontend/*.md`
5. Historical bootstrap/spec files such as `/backend/SPEC_PLAN.md` and `/backend/fastapi_wechat_codex_bootstrap_prompt.md`

Important:
- `/backend/AGENT.md` is a backend bootstrap/specification document, not the best source for current whole-project behavior.
- `/frontend/API_CONTRACT.md` and parts of `/frontend/WECHAT_MINI_INTEGRATION_README.md` are stale relative to the implemented backend auth model.
- `/frontend/app.py` is a legacy Flask prototype and is not part of the current FastAPI + Mini Program architecture.

## Repository Map
### Backend
- `/backend/app/main.py`: FastAPI app factory, lifespan setup, static file mount for `/files`
- `/backend/app/api/routes`: HTTP endpoints
- `/backend/app/api/deps.py`: dependency wiring, provider selection, bearer auth resolution
- `/backend/app/services/voucher_task_service.py`: main workflow orchestration and state transitions
- `/backend/app/services/auth`: WeChat login exchange and custom token service
- `/backend/app/services/ocr`: OCR providers
- `/backend/app/services/parsing/parser.py`: deterministic metadata extraction
- `/backend/app/services/pdf/service.py`: ordered image-to-PDF generation
- `/backend/app/services/storage`: storage abstraction plus local implementation
- `/backend/app/models`: SQLAlchemy models
- `/backend/app/schemas`: Pydantic response/request models with camelCase aliases
- `/backend/alembic`: migrations
- `/backend/tests`: unit and integration coverage

### Frontend
- `/frontend/app.js`: Mini Program app lifecycle and local storage setup
- `/frontend/config.js`: backend base URL
- `/frontend/utils/http.js`: request wrappers and API helpers
- `/frontend/pages/home`: landing page
- `/frontend/pages/index`: capture/upload flow
- `/frontend/pages/confirm`: manual confirmation and batch generate flow
- `/frontend/pages/history`: completed task listing and clear-history flow
- `/frontend/pages/detail`: task detail and PDF entry point
- `/frontend/pages/pdf-preview`: PDF download/open flow
- `/frontend/pages/download`: selected download result page

## Product Architecture
The product is split into a workflow backend and a client-side upload/confirmation shell:

- FastAPI owns task lifecycle, persistence, OCR orchestration, parsing, PDF generation, and file serving.
- The Mini Program owns image capture, temporary client-side task batching, manual review UI, and navigation.
- Files are uploaded to the backend one page at a time.
- OCR is performed on the first uploaded page only.
- Final PDFs are generated server-side from the ordered set of uploaded images.

## Backend Architecture
### Runtime shape
- App factory in `/backend/app/main.py`
- Static files are served from `LOCAL_STORAGE_ROOT` under `/files`
- Database is SQLAlchemy 2.x
- Default dev database is SQLite at `./data/app.db`
- API models use camelCase externally through `/backend/app/schemas/base.py`

### Layer boundaries
- API layer: validates requests, applies dependencies, returns schema models
- Dependency layer: selects OCR/storage/auth providers and resolves the current user from bearer token
- Service layer: enforces workflow status transitions and coordinates storage, OCR, parser, and PDF generation
- Model layer: persists task/page state
- Utility layer: casing and filename sanitation

### Central workflow service
`/backend/app/services/voucher_task_service.py` is the main business entry point. Keep state-machine logic here instead of spreading it into routes or utility modules.

Current nominal status path:
- `draft`
- `uploaded`
- `recognized`
- `confirmed`
- `pdf_generated`

Error state:
- `failed`

Current behavior details:
- Pages can only be uploaded while task status is `draft`
- The first page must be `pageIndex=0`
- `finish-upload` requires at least one page
- `recognize` is allowed only from `uploaded`
- `confirm-generate` is allowed only from `recognized`
- `confirm-generate` sets `confirmed` before PDF generation, then advances to `pdf_generated`

### Persistence model
Two core tables:

- `voucher_task`
  - task identity, user ownership, recognized fields, final PDF metadata, status, OCR text, confidence
- `voucher_page`
  - ordered page metadata, storage path/URL, size, first-page flag

Key constraint:
- `(task_id, page_index)` is unique

### Auth model
Current backend auth is token-based:

1. Mini Program calls `wx.login()`
2. Mini Program sends the `code` to `POST /auth/wechat/login`
3. Backend resolves or mocks the WeChat `openid`
4. Backend returns a custom signed bearer token
5. All `/voucher-tasks` endpoints require `Authorization: Bearer <token>`

Do not add or preserve `userId` query/body transport for protected voucher routes unless the product explicitly decides to revert the auth model. The code and tests currently expect bearer auth.

### OCR and parsing
- OCR providers live under `/backend/app/services/ocr`
- Default settings point to `rapidocr`
- Tests override OCR with `MockOCRService`
- Parsing is deterministic, regex-based, and intentionally narrow
- Parsing extracts:
  - subject
  - month in `YYYY-MM`
  - voucher number like `记470`
- Filename preview and final filename come from shared filename utilities

### Storage and files
- Local storage is implemented in `/backend/app/services/storage/local.py`
- Uploaded pages and generated PDFs are stored under user/task-specific paths
- Public file access is via the `/files/...` mount
- `COSStorageService` exists only as a placeholder and returns `501`

### PDF generation
- `/backend/app/services/pdf/service.py` creates one PDF page per uploaded image
- Each PDF page size is set to the original image dimensions
- Preserve upload order when making any changes here

## Frontend Architecture
### Page flow
- `home` -> choose whether to process new vouchers or view history
- `index` -> capture first page and attachment pages, upload, finish upload, recognize, cache pending results locally
- `confirm` -> edit recognized fields for one or more pending tasks and trigger PDF generation
- `download` or `pdf-preview` -> consume generated output
- `history` -> read completed tasks from backend
- `detail` -> inspect one task

### Frontend state model
The Mini Program stores workflow state in `wx` storage:
- `userId`
- `currentTaskId`
- `pendingTasks`
- `selectedTasksForDownload`
- `shouldResetIndex`
- `recreateTask`

The frontend batches recognized tasks locally before final confirmation. That means UI behavior is partly server-driven and partly local-storage-driven. Be careful not to break these assumptions when changing navigation or task lifecycle.

### Current frontend contract state
The frontend implementation is not fully aligned with the backend:

- `/frontend/utils/http.js` still sends `userId` in request bodies and query params for voucher APIs
- The backend routes ignore `userId` on protected endpoints and instead require bearer auth
- The frontend helper still references unimplemented endpoints:
  - `POST /voucher-tasks/batch-download`
  - `GET /voucher-tasks/{taskId}/first-image`
- `frontend/pages/confirm/confirm.js` calls those helpers
- The backend does not currently expose those routes

Future agents must treat this as active contract drift, not as an intended supported dual mode.

## Known Drift And Pitfalls
### Auth drift
Backend:
- bearer token required for voucher APIs

Frontend:
- still built mostly around `userId` transport

If you touch auth or any voucher route, you must decide whether to:
- migrate the frontend fully to bearer auth, or
- intentionally add compatibility behavior to the backend

Do not update only one side and leave the repo in a more inconsistent state.

### Unsupported frontend endpoints
The frontend assumes these APIs exist:
- batch download
- first-image lookup

They do not exist in `/backend/app/api/routes/voucher_tasks.py`.

If a task involves download previews or first-image review, either:
- implement the backend endpoints and tests, or
- remove or replace the frontend behavior

### Legacy frontend prototype
`/frontend/app.py` is a standalone Flask file unrelated to the current architecture. Do not extend it unless the user explicitly asks to revive or remove it.

### Status transition sensitivity
Most workflow bugs will come from bypassing service-layer guards. Do not perform direct model updates in routes.

### External field casing
- Python code: `snake_case`
- Public API JSON: `camelCase`

When adding fields:
- define them in schemas using `snake_case`
- rely on alias generation for JSON output
- verify frontend access patterns use camelCase names

## Working Rules For Future Agents
### When changing backend APIs
Update all relevant layers:
- routes
- schemas
- service logic
- tests
- backend docs
- frontend request helpers
- affected frontend pages

Minimum files to inspect for API changes:
- `/backend/app/api/routes/voucher_tasks.py`
- `/backend/app/schemas/voucher_task.py`
- `/backend/app/services/voucher_task_service.py`
- `/backend/tests/integration/test_voucher_flow.py`
- `/frontend/utils/http.js`
- any impacted page under `/frontend/pages`

### When changing auth
Inspect and keep aligned:
- `/backend/app/api/deps.py`
- `/backend/app/services/auth/wechat.py`
- `/backend/app/services/auth/token.py`
- `/backend/tests/integration/test_auth.py`
- `/backend/API_CONTRACT.md`
- `/backend/WECHAT_MINI_INTEGRATION_README.md`
- `/frontend/utils/http.js`
- `/frontend/app.js`

### When changing OCR/parsing behavior
Inspect and keep aligned:
- `/backend/app/services/ocr/*`
- `/backend/app/services/parsing/parser.py`
- `/backend/app/utils/filename.py`
- `/backend/tests/unit/test_parsing_service.py`
- `/backend/tests/unit/test_rapidocr_service.py`

Preserve these business constraints unless explicitly changing product scope:
- OCR uses first page only
- parsing remains deterministic first
- manual confirmation can override recognition
- final filename is generated from confirmed fields

### When changing storage or PDF logic
Inspect and keep aligned:
- `/backend/app/services/storage/*`
- `/backend/app/services/pdf/service.py`
- `/backend/app/main.py`
- `/backend/app/services/voucher_task_service.py`

Preserve:
- ordered page upload semantics
- `/files` static serving behavior
- cleanup on task delete and clear-history

### When changing frontend flow
Inspect and keep aligned:
- `/frontend/utils/http.js`
- `/frontend/app.js`
- `/frontend/pages/index/index.js`
- `/frontend/pages/confirm/confirm.js`
- `/frontend/pages/history/history.js`
- `/frontend/pages/detail/detail.js`
- `/frontend/pages/pdf-preview/pdf-preview.js`

Frontend changes should account for:
- local storage keys
- task batching behavior in `pendingTasks`
- navigation assumptions between `index`, `confirm`, `download`, and `history`

## Development Commands
### Backend setup
From `/backend`:

```bash
python -m pip install -e '.[dev]'
alembic upgrade head
./scripts/run_dev.sh
```

Alternative:

```bash
python scripts/run_dev.py
```

### Backend tests
From `/backend`:

```bash
pytest
```

### Frontend
The frontend is a WeChat Mini Program project. Open `/frontend` in WeChat DevTools.

Config entry points:
- `/frontend/project.config.json`
- `/frontend/project.private.config.json`
- `/frontend/config.js`

## Verification Expectations
For meaningful backend changes, run at least:

```bash
cd backend
pytest
```

For API or integration changes, also validate:
- create task
- upload first page with `pageIndex=0`
- finish upload
- recognize
- confirm generate
- list/detail
- auth rejection without bearer token

For frontend contract changes, manually verify the affected page flow in WeChat DevTools.

## Documentation Expectations
When behavior changes, update the docs that future contributors will actually read:
- `/AGENT.md` for project-wide operating guidance
- `/backend/README.md` for local setup
- `/backend/API_CONTRACT.md` for request/response shapes
- `/backend/WECHAT_MINI_INTEGRATION_README.md` for Mini Program integration

Update `/frontend/API_CONTRACT.md` and `/frontend/WECHAT_MINI_INTEGRATION_README.md` only if you are actively bringing them back into sync with the implemented backend. Do not leave them half-updated.

## Practical Guidance
- Prefer extending existing services and schemas over creating parallel abstractions.
- Keep status enforcement centralized in `VoucherTaskService`.
- Keep API JSON camelCase through schema aliases, not manual field conversion in routes.
- Do not introduce frontend-only API assumptions without backend routes and tests.
- Do not rely on historical docs when code and tests disagree.
- If a user asks for a new feature that spans API and Mini Program behavior, plan for backend, frontend helper, UI page, and doc updates together.

## Short Summary
This is a FastAPI-centered voucher workflow system with a WeChat Mini Program client. The backend architecture is coherent and test-backed. The main technical risk in this repo is backend/frontend contract drift, especially around auth and a few unimplemented frontend endpoints. Future agents should treat cross-layer consistency as a primary responsibility, not a cleanup task for later.
