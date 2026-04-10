# Block H — File upload (S3 / MinIO)

**Trigger:** any file upload, any S3 or MinIO interaction.

## Rules and reasons

**Compress images client-side before upload.** Use a canvas-based compressor with a max dimension (typically 1280px) and JPEG quality around 0.85.

> *Why*: a raw photo from a modern phone is 4-12 MB. Uploading that over a mobile connection is slow, bandwidth-expensive, and usually pointless because the app displays a smaller version anyway. Client-side compression typically reduces the payload 10x with no visible quality loss.

**Retry S3 errors with exponential backoff, up to 3 attempts**, then surface the error to the user.

> *Why*: transient S3 errors happen (network blips, brief throttling). A single retry with a short delay catches most of them; three attempts handle almost all the rest. Past 3, the problem is unlikely to resolve on its own and the user deserves to know something is wrong rather than watching an indefinite spinner.

**When the parent resource is deleted, the corresponding S3 objects are deleted too.** Cascade delete at the DB level must also trigger S3 cleanup.

> *Why*: orphan S3 objects are silent storage leaks. You don't notice them until the monthly S3 bill arrives with an extra zero. The cleanup has to be explicit because the DB cascade doesn't know about S3.

**The E2E test covers the full lifecycle: seed → upload → read → verify → cleanup.** Not just the upload step.

> *Why*: the bugs are in the transitions. An "upload works" test passes on day one but misses the read-after-write race, the cleanup-orphans bug, and the deletion-cascade failure. Full-lifecycle tests catch all three because they exercise the full path the user takes.

**File type and size are validated on both the client and the backend.** Client-side validation is UX; backend validation is security.

> *Why*: client-side validation alone is bypassable (curl, Postman, malicious page). Backend-only validation means the user sees "invalid file" only after the full upload completes, wasting their time. Both is redundant but cheap.

## Required acknowledgment (paste verbatim)

> I will compress images client-side, retry S3 errors with backoff, cascade delete S3 objects when the parent resource is deleted, and write an E2E test covering the full upload lifecycle.

## Common drift caught by reviewers

- Upload endpoint accepts 20 MB files without client compression — reviewer flags: UX regression and bandwidth waste.
- No retry logic on S3 errors — reviewer flags: acknowledged rule required exponential backoff.
- DB cascade delete removes the row but leaves S3 objects behind — reviewer flags: orphan storage.
- E2E test covers upload but not cleanup — reviewer flags: partial lifecycle, acknowledged rule required the full flow.
