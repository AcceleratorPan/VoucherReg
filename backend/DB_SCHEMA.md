# DB Schema

## 1) Table: `voucher_task`
Purpose: Lifecycle and final output metadata for one voucher workflow.

Columns:
- `id` (PK, string)
- `user_id` (nullable, string)
- `subject` (nullable, string)
- `voucher_month` (nullable, string `YYYY-MM`)
- `voucher_no` (nullable, string)
- `file_name` (nullable, string)
- `pdf_url` (nullable, string)
- `status` (string)
- `page_count` (int)
- `raw_ocr_text` (nullable, text)
- `confidence` (nullable, float)
- `created_at` (timestamp)
- `updated_at` (timestamp)

Recommended indexes (future):
- `(created_at DESC)` for history listing
- `(user_id, created_at DESC)` for per-user queries
- `(status)` for operational filtering

## 2) Table: `voucher_page`
Purpose: Ordered page metadata under one voucher task.

Columns:
- `id` (PK, string)
- `task_id` (FK -> `voucher_task.id`)
- `page_index` (int, ordered position)
- `image_path` (string, internal storage path)
- `image_url` (string, API-returned URL)
- `thumb_url` (nullable, string)
- `is_first_page` (bool)
- `width` (nullable, int)
- `height` (nullable, int)
- `created_at` (timestamp)
- `updated_at` (timestamp)

Constraints:
- Unique: `(task_id, page_index)`
- FK cascade delete on task removal

## Status Definitions (`voucher_task.status`)
- `draft`: task created, accepting page uploads.
- `uploaded`: user finished upload.
- `recognized`: first-page OCR and parsing completed.
- `confirmed`: reserved for explicit confirmation checkpoint.
- `pdf_generated`: final PDF generated and stored.
- `failed`: terminal error state.

## Transition Rules
- Allowed nominal path: `draft -> uploaded -> recognized -> confirmed -> pdf_generated`
- `confirm-generate` writes `confirmed` first, then transitions to `pdf_generated` after successful file persistence.
- Non-terminal states may transition to `failed` on fatal errors.
