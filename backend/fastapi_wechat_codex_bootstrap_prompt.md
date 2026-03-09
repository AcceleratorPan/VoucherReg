# Codex / Claude Code Prompt: Bootstrap the Project Structure and Requirements Docs

You are a senior staff-level engineer, technical architect, and pragmatic product-minded developer.

Your job is **not** to write a superficial demo. Your job is to **bootstrap a production-oriented project structure** and generate **high-quality requirement and architecture markdown documents** for a real system.

## Mission

Create the initial project skeleton and documentation for a system with this architecture:

- **Backend:** FastAPI (core backend, owned by a Python backend engineer)
- **Frontend:** WeChat Mini Program (implemented separately by another developer in WeChat DevTools)
- **OCR:** Tencent Cloud OCR
- **Storage:** object storage (initially backend-mediated upload; later can evolve to direct COS upload)
- **Output:** one voucher task produces one named PDF

The goal is to support a workflow where users capture accounting voucher pages in a WeChat Mini Program, upload them to the backend, extract metadata from the **first page only**, generate a final **multi-page PDF**, and name it using extracted fields.

---

## Product Background

The product is for **accounting voucher capture and PDF generation**.

For each voucher task:

1. The user continuously captures images.
2. The **first image** is always the **main voucher page**.
3. The following images are **attachment pages**.
4. The system extracts from the **first page only**:
   - **Subject / Entity**
   - **Month**
   - **Voucher Number**
5. The system generates a final PDF containing all captured pages in order.
6. The final PDF filename is:

`{Subject}-{YYYY-MM}-{VoucherNo}.pdf`

Example:

`海南百迈科医疗科技股份有限公司-2022-07-记470.pdf`

After finishing one voucher, the user can start the next one.

---

## Non-Negotiable Product Decisions

You must follow these decisions unless there is a very strong engineering reason not to:

1. **FastAPI is the core backend.**
2. The frontend is a **WeChat Mini Program**, but in this task you are mainly bootstrapping the backend project and the shared docs.
3. The first version should be **MVP-oriented, stable, and cost-conscious**.
4. The backend should do the heavy work:
   - file receiving
   - storage handling
   - OCR integration
   - OCR text normalization
   - field extraction
   - PDF generation
   - filename generation
5. **Only the first page** is parsed for metadata.
6. **OCR + deterministic rules** is the primary extraction strategy.
7. **LLM is not the primary extraction engine**. It can be mentioned only as a future fallback.
8. A **manual confirmation page** exists on the frontend before final PDF generation, so backend responses should support user review.
9. For MVP, prefer **frontend upload to backend first**, then backend stores files. Do not optimize prematurely with direct COS upload.

---

## What You Need to Generate

Please generate a **backend-first project bootstrap** and the associated markdown documentation.

I want you to create:

### A. Project structure
Create a clean backend project structure for FastAPI, including at least:

- `app/api/`
- `app/core/`
- `app/db/`
- `app/models/`
- `app/schemas/`
- `app/services/`
- `app/utils/`
- `tests/`
- `scripts/`
- `README.md`
- `MVP_SCOPE.md`
- `API_CONTRACT.md`
- `DB_SCHEMA.md`
- `ARCHITECTURE.md`
- `TASK_BOARD.md`
- `.env.example`

If useful, add additional files such as:

- `Dockerfile`
- `docker-compose.yml`
- `alembic.ini`
- migration setup
- `pyproject.toml` or `requirements.txt`

### B. Requirements and architecture documents
Write high-quality markdown documents that are clear, practical, and engineering-ready:

1. `README.md`
2. `MVP_SCOPE.md`
3. `ARCHITECTURE.md`
4. `API_CONTRACT.md`
5. `DB_SCHEMA.md`
6. `TASK_BOARD.md`

These documents should be good enough for real collaboration between backend and frontend developers.

### C. Backend code skeleton
Generate an implementation-ready FastAPI skeleton including:

- `main.py`
- router registration
- health endpoint
- voucher task endpoints
- pydantic schemas
- service abstractions
- config loading
- storage service interface
- OCR service interface
- parsing service skeleton
- PDF service skeleton
- error handling skeleton
- placeholder tests

---

## Business Workflow

Design around this backend workflow:

1. **Create voucher task**
2. **Upload page images** in order
3. **Mark finish upload**
4. **Recognize metadata from first page**
5. **Return extracted fields + filename preview + confidence + needsUserReview**
6. **Accept user-confirmed fields**
7. **Generate final PDF**
8. **Persist final PDF and return URL/path**
9. **List history and task detail**

---

## MVP Scope

The generated docs and structure must reflect the following MVP boundaries.

### In MVP
- create voucher task
- upload multiple images
- store image metadata
- first page OCR only
- deterministic metadata extraction
- manual user confirmation
- multi-page PDF generation
- final filename generation
- list tasks
- task detail
- mockable architecture for frontend parallel development

### Not in MVP
- OpenCV perspective correction
- direct COS upload from Mini Program
- LLM-first extraction
- advanced archive search
- batch export
- complex permissions
- automated page classification beyond “first page vs attachment pages”
- advanced retry orchestration

---

## Required Data Model

Please design at least these entities.

### `voucher_task`
Fields should include at least:

- `id`
- `user_id`
- `subject`
- `voucher_month`
- `voucher_no`
- `file_name`
- `pdf_url`
- `status`
- `page_count`
- `raw_ocr_text`
- `confidence`
- `created_at`
- `updated_at`

### `voucher_page`
Fields should include at least:

- `id`
- `task_id`
- `page_index`
- `image_url`
- `thumb_url`
- `is_first_page`
- `width`
- `height`
- `created_at`
- `updated_at`

### Optional: `voucher_recognition_log`
For OCR/debugging/audit.

---

## Required Task Status Flow

Use and document a clear task status machine.

At minimum support:

- `draft`
- `uploaded`
- `recognized`
- `confirmed`
- `pdf_generated`
- `failed`

Document valid transitions and basic validation rules.

---

## Required API Design

Please define and scaffold these endpoints:

1. `POST /voucher-tasks`
2. `POST /voucher-tasks/{task_id}/pages`
3. `POST /voucher-tasks/{task_id}/finish-upload`
4. `POST /voucher-tasks/{task_id}/recognize`
5. `POST /voucher-tasks/{task_id}/confirm-generate`
6. `GET /voucher-tasks`
7. `GET /voucher-tasks/{task_id}`
8. `GET /health`

### Important conventions
- Public API JSON fields should be **camelCase**.
- Python internal code can use **snake_case**.
- Clearly document request and response schemas.
- Include failure responses.
- Include a standard error envelope.

Suggested recognize response shape:

```json
{
  "taskId": "vt_123",
  "subject": "海南百迈科医疗科技股份有限公司",
  "month": "2022-07",
  "voucherNo": "记470",
  "fileNamePreview": "海南百迈科医疗科技股份有限公司-2022-07-记470.pdf",
  "confidence": 0.93,
  "needsUserReview": true
}
```

Suggested error response shape:

```json
{
  "code": "OCR_FAILED",
  "message": "OCR recognition failed",
  "detail": {}
}
```

---

## OCR and Parsing Strategy

Design the backend so that OCR and parsing are separate concerns.

### OCR service
Create a service abstraction such as:

- `OCRService`
- `MockOCRService`
- `TencentOCRService`

### Parsing service
Create a separate parser service responsible for:

- OCR text normalization
- subject extraction
- month extraction
- voucher number extraction
- filename building
- confidence estimation

### Extraction expectations

#### Subject / Entity
Prefer labels like:
- 核算单位
- 单位名称
- 公司名称

#### Month
Extract from date and normalize to:
- `YYYY-MM`

Example:
- `2022-07-31` -> `2022-07`
- `2022年7月31日` -> `2022-07`

#### Voucher Number
Support variants such as:
- `记-470`
- `记470`
- `记—470`

Normalize to a consistent canonical value:
- `记470`

### Important engineering principle
The parser is a core business component. Keep it deterministic, testable, and easy to evolve.

---

## PDF Strategy

Design a backend PDF service that:

- reads task pages ordered by `page_index`
- places one image on one PDF page
- preserves order
- saves the PDF to storage
- returns the final path/URL

Also provide a filename sanitization utility that:

- removes illegal filename characters
- trims whitespace
- truncates overlong subject names if needed
- uses safe fallbacks for missing fields

---

## Storage Strategy

For MVP, design the backend assuming:

- frontend uploads files to backend
- backend stores original files
- backend can later be switched to COS-backed storage without changing business logic

So create a storage abstraction such as:

- `StorageService`
- `LocalStorageService`
- optional placeholder `COSStorageService`

---

## Testing Requirements

Generate test scaffolding for:

### Unit tests
- text normalization
- subject extraction
- month extraction
- voucher number extraction
- filename sanitization

### Basic integration tests
- create task
- upload page
- finish upload
- recognize
- confirm generate
- get detail

Make the system mock-friendly so frontend and backend can develop in parallel.

---

## Output Quality Requirements

Your output must be:

- production-minded
- pragmatic
- modular
- readable
- well named
- easy for a Python backend engineer to continue from
- suitable for collaboration with a separate frontend Mini Program developer

Do **not** produce a toy project.
Do **not** over-engineer with unnecessary complexity.
Do **not** hide key assumptions.

---

## Important Documentation Quality Standard

The markdown documents must be high quality.

That means:
- clear headings
- concrete explanations
- practical field descriptions
- explicit endpoint contracts
- explicit status flow
- explicit MVP boundaries
- specific responsibilities per module
- realistic next steps

I want docs that can be sent directly to a teammate.

---

## Implementation Preferences

Prefer the following stack unless there is a strong reason not to:

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- httpx
- Pillow
- PyMuPDF or ReportLab for PDF generation
- pytest

If you choose alternatives, explain why.

---

## Expected Deliverables

Please output your work in this order:

1. Project tree
2. Key architectural explanation
3. Markdown document contents for all required `.md` files
4. Backend code skeleton
5. Example config / environment variables
6. Test skeleton
7. Suggested next steps

If the code is too large, prioritize:
- project tree
- markdown docs
- backend skeleton
- test skeleton

---

## Final Instruction

Bootstrap this as if a skilled Python backend engineer will continue implementing it immediately after your output.

Be concrete.
Be systematic.
Be implementation-oriented.
Write the markdown docs as real documents, not placeholders.
