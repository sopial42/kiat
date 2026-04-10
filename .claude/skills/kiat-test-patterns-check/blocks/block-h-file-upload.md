# Block H — File Upload / S3 / MinIO

**Trigger:** any file upload, any S3 / MinIO interaction

## Mandatory rules

- **Client-side compression** for images BEFORE upload (reduce payload, faster UX, less bandwidth). Use a canvas-based compressor with a max dimension (e.g., 1280px) and JPEG quality 0.85.
- **Retry S3 errors** with exponential backoff — but not indefinitely. Max 3 retries, then surface the error to the user.
- **Cleanup on parent delete**: `DELETE cascade` at the DB level must also remove the corresponding S3 objects. Orphan objects are silent storage leaks.
- E2E test MUST cover the full lifecycle: **seed → upload → read → verify → cleanup**. Partial tests (just upload) miss the cleanup bugs.
- Validate file type and size **on both client and backend**. Client-side is UX; backend is security.

## Required acknowledgment (paste verbatim)

> I will compress images client-side, retry S3 errors with backoff, cascade delete S3 objects when parent resource is deleted, and write an E2E test covering the full upload lifecycle.

## Common drift caught by reviewers

- Upload endpoint accepts files up to 20MB without client compression — reviewer flags: UX regression + bandwidth waste
- No retry logic on S3 errors — reviewer flags: acknowledged rule required exponential backoff
- DB cascade delete deletes the row but S3 object stays — reviewer flags: orphan storage, not covered
- E2E test covers upload but not cleanup — reviewer flags: partial lifecycle only, acknowledged rule required full lifecycle
