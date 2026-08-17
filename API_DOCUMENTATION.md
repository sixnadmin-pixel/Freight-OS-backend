# CL Connect API Documentation

**Base URL:** `http://localhost:8002`
**Framework:** FastAPI (Python 3.12)
**Database:** PostgreSQL (async via psycopg-pool)

This API implements the backend for **Flow 1 (Customer Inquiry to Quotation)** and the **customer response recording step of Flow 2 (Customer Response, Booking, and Confirmation)** of the CL Connect platform.

---

## Table of Contents

1. [Process Flow Overview](#process-flow-overview)
2. [Authentication](#1-authentication)
3. [Clients](#2-clients)
4. [KYC](#3-kyc)
5. [Inquiries](#4-inquiries)
6. [Workflow](#5-workflow--activity-log)
7. [Liners](#6-liners)
8. [Rates — Master](#7-rates--master-persistent)
9. [Rates — Operational](#8-rates--operational-non-persistent)
10. [Rate Requests](#9-rate-requests)
11. [Quotations](#10-quotations)
12. [Error Responses](#error-responses)

---

## Process Flow Overview

### Flow 1 — Customer Inquiry to Quotation

| Step | Business Action | API Module | Key Endpoints |
|------|----------------|------------|---------------|
| 1 | Customer sends inquiry | Inquiries | `POST /inquiries/inquiries-*` |
| 2 | New or existing customer check | Clients | `POST /clients/clients`, `GET /clients/clients` |
| 3 | Log inquiry + set priority | Inquiries | `POST /inquiries/inquiries-*`, `PATCH /inquiries/inquiries/{inq_id}` |
| 4 | KYC / background check (new customers) | KYC | `GET /kyc/kyc-requests/pending`, `POST /kyc/kyc-requests`, `PATCH .../stage` |
| 5 | Multi-step rate check | Rates | `GET /rates/tariff-rates`, `GET /rates/nac-rates`, etc. |
| 6 | Escalate to procurement (optional) | Rate Requests | `POST /rate-requests` |
| 7 | Send multiple quotation options | Quotations | `POST /quotations/`, `PATCH /quotations/{id}/send` |

### Flow 2 — Customer Response (partial)

| Step | Business Action | API Module | Key Endpoints |
|------|----------------|------------|---------------|
| 1 | Customer accepts or rejects quote | Quotations | `PATCH /quotations/{id}/response` |

### Workflow Stages

The inquiry progresses through these stages automatically as API actions are performed:

```
kyc_pending → rate_check_in_progress → escalated_to_procurement → quotation_prep → quotation_sent → customer_response → booking_request → completed
```

---

## Workflow Stage Transitions — How They Work

The backend uses an internal `ActivityLogModule` (stored in the `workflow_stats` table) to track each inquiry's current stage. **Most transitions happen automatically as side effects of API calls** — the frontend does not need to manually advance the workflow in most cases. Below is a complete reference of which API call triggers which transition, the source file responsible, and the mechanism used.

### Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ActivityLogModule                             │
│                                                                      │
│  create_workflow(payload)         → INSERT into workflow_stats        │
│  update_workflow_status(inq_id, patch) → UPDATE workflow_stats        │
│                                                                      │
│  Source: modules/inquiry/activity_log/activity_log.py                 │
│  Table:  workflow_stats (columns: inq_id, flow_id, stage)            │
└──────────────────────────────────────────────────────────────────────┘
         ▲                  ▲                  ▲
         │                  │                  │
   InquiryModule     RateRequestModule    QuotationModule
   (auto-creates)    (calls update)       (calls update)
```

Modules that need to update the workflow receive the `ActivityLogModule` via dependency injection at startup. They call `self.activity_log.update_workflow_status(inq_id, WorkflowStatusPatch(stage=...))` internally after their primary database operation succeeds.

### Transition 1: Inquiry Created (new client) → `rate_check_in_progress` + KYC record initialized

**Trigger:** `POST /inquiries/inquiries-new-new`
**Set by:** `InquiryModule.create_inquiry_case_1()` — directly inserts a `workflow_stats` row and calls `self.kyc.create_kyc_stage(cli_id)`.
**Source:** `modules/inquiry/inquiry.py:45`, `modules/inquiry/inquiry.py:68-70`

```python
# KYC uninitiated record is auto-created for the new client
await self.kyc.create_kyc_stage(cli_id)

# Workflow is set to rate_check_in_progress
workflow_state = {'inq_id': inq_id, 'flow_id': 1, 'stage': 'rate_check_in_progress'}
await cur.execute(build_insert('worflow_stats', workflow_state, 'inq_id'), workflow_state)
```

**Why:** When a new client inquiry is created, a `kyc_request` row with `kyc_stage = kyc_uninitiated` is automatically inserted so Finance can begin the KYC process. The inquiry workflow starts at `rate_check_in_progress` immediately — KYC tracking is now handled in parallel via the KYC module rather than gating the workflow.

**Frontend note:** After calling this endpoint, the inquiry workflow is already at `rate_check_in_progress`. In parallel, the Finance team should be notified to action the pending `kyc_uninitiated` record. Use `GET /kyc/...` or `PATCH /kyc/kyc-requests/clients/{cli_id}/stage` to track KYC progress independently.

---

### Transition 2: Inquiry Created (existing client) → `rate_check_in_progress`

**Trigger:** `POST /inquiries/inquiries-old-new` or `POST /inquiries/inquiries-old-old`
**Set by:** `InquiryModule.create_inquiry_case_2()` and `InquiryModule.create_inquiry_case_3()` — directly inserts a `workflow_stats` row.
**Source:** `modules/inquiry/inquiry.py:141-143` (case 2), `modules/inquiry/inquiry.py:209-211` (case 3)

```python
workflow_state = {'inq_id': inq_id, 'flow_id': 1, 'stage': 'rate_check_in_progress'}
await cur.execute(build_insert('worflow_stats', workflow_state, 'inq_id'), workflow_state)
```

**Why:** The client already exists and KYC is assumed complete. The inquiry skips directly to rate checking.

**Frontend note:** The UI should immediately present rate lookup tools (tariff, NAC, contracted, spot rate searches) to the CS/Sales user.

---

### Transition 3: Rate Request Created → `escalated_to_procurement`

**Trigger:** `POST /rate-requests`
**Set by:** `RateRequestModule.add_rate_request()` — calls `activity_log.update_workflow_status()` after inserting the rate request.
**Source:** `modules/rate_requests/rate_requests.py:35-38`

```python
await self.activity_log.update_workflow_status(
    payload.inq_id,
    WorkflowStatusPatch(stage=WorkflowStage.escalated_to_procurement)
)
```

**Why:** CS/Sales could not find a suitable rate and is escalating to Procurement for better options.

**Frontend note:** This transition is automatic. After the `POST /rate-requests` call returns `201`, the inquiry's `workflow_stage` will already be `escalated_to_procurement`. The UI should reflect this immediately (e.g., show the inquiry in the procurement team's incoming queue). No separate workflow PATCH is needed.

---

### Transition 4: Rate Option Added → `quotation_prep`

**Trigger:** `POST /rate-requests/{request_id}/options`
**Set by:** `RateRequestModule.add_request_option()` — calls `activity_log.update_workflow_status()` after inserting the option and setting `is_given = true` on the parent request.
**Source:** `modules/rate_requests/rate_requests.py:100-103`

```python
await self.activity_log.update_workflow_status(
    inq_id,
    WorkflowStatusPatch(stage=WorkflowStage.quotation_prep)
)
```

**Why:** Procurement has provided at least one rate option. The inquiry is now ready for the Sales/CS team to compile a quotation.

**Frontend note:** Automatic. After the `POST .../options` call returns `201`, the stage is already `quotation_prep`. The UI can transition the inquiry into a quotation-building view.

---

### Transition 4b: Last Rate Option Deleted → `escalated_to_procurement` (rollback)

**Trigger:** `DELETE /rate-requests/{request_id}/options/{option_id}` — only when deleting the **last** remaining option on a request.
**Set by:** `RateRequestModule.delete_rate_request_option()` — checks if remaining options count is 0, then reverts `is_given` to `false` and calls `activity_log.update_workflow_status()`.
**Source:** `modules/rate_requests/rate_requests.py:146-155`

```python
if remaining == 0:
    await cur.execute(
        "UPDATE rate_request SET is_given = false WHERE request_id = %(request_id)s RETURNING inq_id",
        {"request_id": request_id}
    )
    inq_id = (await cur.fetchone())['inq_id']
    await self.activity_log.update_workflow_status(
        inq_id,
        WorkflowStatusPatch(stage=WorkflowStage.escalated_to_procurement)
    )
```

**Why:** All rate options were removed, so the inquiry effectively needs procurement attention again.

**Frontend note:** Automatic. If the delete call removes the last option, the workflow rolls back. The UI should re-fetch the inquiry's workflow stage after any option delete to detect this.

---

### Transition 5: Quotation Sent → `quotation_sent`

**Trigger:** `PATCH /quotations/{quote_id}/send?status=sent`
**Set by:** `QuotationModule.send_quotation()` — calls `activity_log.update_workflow_status()` after updating the quotation status to `sent`.
**Source:** `modules/quotation/quotation.py:140-143`

```python
await self.activity_log.update_workflow_status(
    row['inq_id'],
    WorkflowStatusPatch(stage=WorkflowStage.quotation_sent)
)
```

**Why:** The quotation (with multiple liner options) has been sent to the customer via email/WhatsApp.

**Frontend note:** Automatic. Call `PATCH /quotations/{id}/send?status=sent` and the workflow updates in one round-trip. The UI can show the inquiry as "Awaiting Customer Response."

---

### Transition 6: Customer Response Recorded → `customer_response`

**Trigger:** `PATCH /quotations/{quote_id}/response?status=accepted` or `?status=rejected`
**Set by:** `QuotationModule.record_response()` — calls `activity_log.update_workflow_status()` after updating the quotation status to `accepted` or `rejected`.
**Source:** `modules/quotation/quotation.py:171-174`

```python
await self.activity_log.update_workflow_status(
    row['inq_id'],
    WorkflowStatusPatch(stage=WorkflowStage.customer_response)
)
```

**Why:** The customer has responded to the quotation. This is the last step covered by the current API.

**Frontend note:** Automatic. The endpoint validates that status is either `accepted` or `rejected` (returns `400` otherwise). After calling this, the inquiry stage becomes `customer_response`. This is the final implemented workflow transition — `booking_request` and `completed` stages exist in the enum but are not yet triggered by any backend logic.

---

### Transition 7: Manual Override (any stage)

**Trigger:** `PATCH /inquiries/workflow/{inq_id}`
**Set by:** Directly via the Activity Log router — no business logic side effects.
**Source:** `modules/inquiry/activity_log/activity_log.py:40-61`

**Frontend note:** This is the escape hatch. Use it when:
- KYC completes and the inquiry needs to move from `kyc_pending` to `rate_check_in_progress` (no automatic bridge exists between the KYC module and the workflow).
- A stage needs to be corrected or rolled back manually.
- Future stages (`booking_request`, `completed`) need to be set before their backend logic is implemented.

---

### Complete Transition Map

```
                                           ┌─────────────────────────────┐
                                           │   MANUAL OVERRIDE           │
                                           │   PATCH /inquiries/         │
                                           │   workflow/{inq_id}         │
                                           │   (can set ANY stage)       │
                                           └──────────┬──────────────────┘
                                                      │ can override
                                                      ▼ any transition
┌─────────────────────────┐    ┌─────────────────────────┐
│  rate_check_in_progress  │───▶│escalated_to_procurement │
└─────────────────────────┘    └─────────────────────────┘
  ▲ set by:                      ▲ set by:
  │ POST /inquiries/             │ POST /rate-requests
  │ inquiries-new-new            │   (auto)
  │   (auto, also creates        │
  │    kyc_uninitiated record)   │ DELETE .../options/{id}
  │ POST /inquiries/             │   (auto, if last option)
  │ inquiries-old-new            │
  │ inquiries-old-old            │
  │   (auto)                     │
  │                              │
  │ PATCH /inquiries/            │
  │ workflow/{inq_id}            │
  │   (manual)                   │
  │                  │                           │
  │                  ▼                           ▼
  │           ┌──────────────┐          ┌──────────────┐
  │           │quotation_prep│─────────▶│quotation_sent│
  │           └──────────────┘          └──────────────┘
  │             ▲ set by:                 ▲ set by:
  │             │ POST /rate-requests/    │ PATCH /quotations/
  │             │ {id}/options            │ {id}/send?status=sent
  │             │   (auto)               │   (auto)
  │             │                        │
  │             ▼                        ▼
  │           ┌─────────────────┐   ┌───────────────┐   ┌───────────┐
  │           │customer_response│──▶│booking_request│──▶│ completed │
  │           └─────────────────┘   └───────────────┘   └───────────┘
  │             ▲ set by:             not yet             not yet
  │             │ PATCH /quotations/  implemented         implemented
  │             │ {id}/response
  │             │ ?status=accepted
  │             │ or ?status=rejected
  │             │   (auto)
  └─────────────┘
```

### Summary Table

| From Stage | To Stage | Triggered By | Automatic? | Source File |
|------------|----------|-------------|------------|-------------|
| _(new)_ | `rate_check_in_progress` | `POST /inquiries/inquiries-new-new` (also auto-creates `kyc_uninitiated` record) | yes | `inquiry.py:45,68` |
| _(new)_ | `rate_check_in_progress` | `POST /inquiries/inquiries-old-new` | yes | `inquiry.py:141` |
| _(new)_ | `rate_check_in_progress` | `POST /inquiries/inquiries-old-old` | yes | `inquiry.py:209` |
| `rate_check_in_progress` | `escalated_to_procurement` | `POST /rate-requests` | yes | `rate_requests.py:35` |
| `escalated_to_procurement` | `quotation_prep` | `POST /rate-requests/{id}/options` | yes | `rate_requests.py:100` |
| `quotation_prep` | `escalated_to_procurement` | `DELETE /rate-requests/{id}/options/{id}` (last option) | yes | `rate_requests.py:146` |
| `quotation_prep` | `quotation_sent` | `PATCH /quotations/{id}/send?status=sent` | yes | `quotation.py:140` |
| `quotation_sent` | `customer_response` | `PATCH /quotations/{id}/response?status=accepted\|rejected` | yes | `quotation.py:171` |
| _any_ | _any_ | `PATCH /inquiries/workflow/{inq_id}` | **manual** | `activity_log.py:40` |

### Important Notes for Frontend Developers

1. **You do not need to call the workflow endpoint after most actions.** The transitions listed as "automatic" above happen server-side as part of the API call. After the response returns, the `workflow_stage` field on the inquiry is already updated.

2. **KYC and the inquiry workflow are now tracked independently.** When a new-client inquiry is created (`POST /inquiries/inquiries-new-new`), both the workflow (`rate_check_in_progress`) and a KYC record (`kyc_uninitiated`) are set automatically. Finance advances the KYC stage via `PATCH /kyc/kyc-requests/clients/{cli_id}/stage` on their own timeline. No manual workflow patching is needed to unblock the inquiry.

3. **To read the current stage**, use `GET /inquiries/inquiries/{inq_id}` — the response includes `workflow_stage` as a joined field from `workflow_stats`.

4. **Stages `booking_request` and `completed`** exist in the enum but have no automatic triggers yet. Use the manual workflow endpoint to set them when needed.

5. **The `flow_id` field** defaults to `1` (Flow 1: Customer Inquiry to Quotation). It is stored in `workflow_stats` and can be set via the manual endpoint, but no module currently uses it for branching logic.

---

## KYC Stage Transitions

The KYC module tracks its own stage separately from the inquiry workflow, stored in the `kyc_stage` column of the `kyc_request` table. This stage reflects the compliance review progress for a specific client.

### KYC Stage Enum

```python
class KYCStage(str, Enum):
    kyc_uninitiated     = 'kyc_uninitiated'
    kyc_pending         = 'kyc_pending'
    documents_submitted = 'documents_submitted'
    kyc_completed       = 'kyc_completed'
```

```
kyc_uninitiated → kyc_pending → documents_submitted → kyc_completed
```

### How KYC Stages Are Updated

#### Transition: _(new)_ → `kyc_uninitiated` (automatic, on new-client inquiry creation)

**Trigger:** `POST /inquiries/inquiries-new-new`
**Set by:** `InquiryModule.create_inquiry_case_1()` calls `self.kyc.create_kyc_stage(cli_id)` immediately after inserting the client row.
**Source:** `modules/inquiry/inquiry.py:45`, `modules/kyc/client_kyc.py:137`

```python
# Called inside create_inquiry_case_1 after client is created:
await self.kyc.create_kyc_stage(cli_id)

# Which inserts:
data = {"cli_id": cli_id, "kyc_stage": KYCStage.kyc_uninitiated.value}
await cur.execute(build_insert("kyc_request", data, "kyc_id"), data)
```

**Frontend note:** Automatic. A skeleton `kyc_request` row is created for every new client inquiry so Finance can see and act on it. Finance should then call `POST /kyc/kyc-requests` (with full KYC data) or `PATCH /kyc/kyc-requests/clients/{cli_id}/stage` to advance the stage.

You can also initialize a KYC record manually for any client without creating an inquiry:

**Trigger:** `POST /kyc/kyc-requests/clients/{cli_id}/stage`
**Set by:** `KYCModule.create_kyc_stage()` — inserts a `kyc_request` row with `kyc_stage = kyc_uninitiated`.
**Source:** `modules/kyc/client_kyc.py:137`

---

#### Transition: _(new)_ → `kyc_pending` (automatic, on full KYC request creation)

**Trigger:** `POST /kyc/kyc-requests?cli_id={cli_id}`
**Set by:** The `kyc_stage` field on `KYCRequestNew` defaults to `kyc_pending` when a full KYC request is created.
**Source:** `modules/kyc/client_kyc_types.py:44`

```python
kyc_stage: KYCStage = KYCStage.kyc_pending
```

**Frontend note:** Automatic. Creating a full KYC request sets the stage to `kyc_pending`.

---

#### Transition: `kyc_pending` → `documents_submitted` (automatic, conditional)

This transition is triggered automatically in **two places** when a `br_form` (business registration form) is provided:

**Trigger 1:** `POST /kyc/kyc-requests?cli_id={cli_id}` — if `docs.br_form` is non-empty in the creation payload.
**Source:** `modules/kyc/client_kyc.py:43-47`

```python
if payload.docs.br_form:
    await cur.execute(
        "UPDATE kyc_request SET kyc_stage = %(stage)s WHERE kyc_id = %(kyc_id)s",
        {"stage": KYCStage.documents_submitted.value, "kyc_id": kyc_id}
    )
```

**Trigger 2:** `PATCH /kyc/kyc-requests/{kyc_id}/documents/{doc_id}` — if the patch includes a non-empty `br_form` field.
**Source:** `modules/kyc/client_kyc.py:118-122`

```python
if "br_form" in changes and changes["br_form"]:
    await cur.execute(
        "UPDATE kyc_request SET kyc_stage = %(stage)s WHERE kyc_id = %(kyc_id)s",
        {"stage": KYCStage.documents_submitted.value, "kyc_id": kyc_id}
    )
```

**Frontend note:** Automatic when documents are submitted. The `br_form` field acts as the trigger — once the business registration form is provided (either at creation or via document patch), the stage advances. No separate call is needed.

---

#### Transition: → `kyc_completed` (manual)

**Trigger:** `PATCH /kyc/kyc-requests/clients/{cli_id}/stage?stage=kyc_completed`
**Set by:** `KYCModule.update_kyc_stage()` — directly updates the `kyc_stage` column.
**Source:** `modules/kyc/client_kyc.py:137-148`

```python
await cur.execute(
    "UPDATE kyc_request SET kyc_stage = %(stage)s WHERE cli_id = %(cli_id)s RETURNING *",
    {"cli_id": cli_id, "stage": stage.value}
)
```

**Frontend note:** This is a manual call. Finance reviews the documents and explicitly marks KYC as completed. This endpoint can also set any other stage (e.g., reverting to `kyc_pending` if documents are rejected).

---

#### KYC and Inquiry Workflow — Parallel Tracking

The KYC module and the inquiry workflow module are now **tracked in parallel**. When `POST /inquiries/inquiries-new-new` is called:

- The inquiry workflow is set to `rate_check_in_progress` immediately.
- A `kyc_request` row is automatically created with `kyc_stage = kyc_uninitiated`.

Finance advances the KYC stage on their own schedule using `PATCH /kyc/kyc-requests/clients/{cli_id}/stage`. The inquiry workflow no longer needs to be manually unblocked after KYC completion — both tracks run independently.

### KYC Stage Summary Table

| From | To | Triggered By | Automatic? | Source File |
|------|----|-------------|------------|-------------|
| _(new)_ | `kyc_uninitiated` | `POST /inquiries/inquiries-new-new` (new client) | yes | `inquiry.py:45`, `client_kyc.py:137` |
| _(new)_ | `kyc_uninitiated` | `POST /kyc/kyc-requests/clients/{cli_id}/stage` | **manual** | `client_kyc.py:137` |
| _(new)_ | `kyc_pending` | `POST /kyc/kyc-requests` | yes (default) | `client_kyc_types.py:44` |
| `kyc_pending` | `documents_submitted` | `POST /kyc/kyc-requests` (if `br_form` provided) | yes | `client_kyc.py:43` |
| `kyc_pending` | `documents_submitted` | `PATCH .../documents/{doc_id}` (if `br_form` provided) | yes | `client_kyc.py:118` |
| _any_ | _any_ | `PATCH /kyc/kyc-requests/clients/{cli_id}/stage?stage=...` | **manual** | `client_kyc.py:159` |

---

## Quotation Status Transitions

The quotation module tracks its own status in the `status` column of the `quotation` table. This status reflects the lifecycle of a quotation sent to a customer.

### Quotation Status Enum

```python
class QuotationStatus(str, Enum):
    in_prep  = 'in_prep'
    sent     = 'sent'
    accepted = 'accepted'
    rejected = 'rejected'
```

```
in_prep → sent → accepted
                → rejected
```

### How Quotation Statuses Are Updated

#### Transition: _(new)_ → `in_prep` (automatic)

**Trigger:** `POST /quotations/`
**Set by:** The `status` field on `QuotationNew` defaults to `in_prep`.
**Source:** `modules/quotation/quotation_type.py:20`

```python
status: QuotationStatus = QuotationStatus.in_prep
```

**Frontend note:** Automatic. A new quotation starts in preparation status. The UI should present a quotation-building interface where the user selects rate options to include.

---

#### Transition: `in_prep` → `sent` (explicit call)

**Trigger:** `PATCH /quotations/{quote_id}/send?status=sent`
**Set by:** `QuotationModule.send_quotation()` — updates the quotation `status` to `sent` and **also advances the inquiry workflow to `quotation_sent`** (see workflow transitions above).
**Source:** `modules/quotation/quotation.py:119-143`

```python
# Updates quotation status
await cur.execute(
    "UPDATE quotation SET status = %(status)s WHERE quote_id = %(quote_id)s RETURNING *",
    {"status": payload.value, "quote_id": quote_id}
)

# Also updates inquiry workflow stage
await self.activity_log.update_workflow_status(
    row['inq_id'],
    WorkflowStatusPatch(stage=WorkflowStage.quotation_sent)
)
```

**Frontend note:** This is a single call that does two things: marks the quotation as sent **and** advances the inquiry workflow. No additional calls needed. The quotation should have been sent to the customer via email/WhatsApp before making this call.

---

#### Transition: `sent` → `accepted` or `rejected` (explicit call)

**Trigger:** `PATCH /quotations/{quote_id}/response?status=accepted` or `?status=rejected`
**Set by:** `QuotationModule.record_response()` — updates the quotation `status` and **also advances the inquiry workflow to `customer_response`**.
**Source:** `modules/quotation/quotation.py:147-174`

```python
# Validates only accepted/rejected are allowed
if payload not in (QuotationStatus.accepted, QuotationStatus.rejected):
    raise HTTPException(400, "Status must be 'accepted' or 'rejected'")

# Updates quotation status
await cur.execute(
    "UPDATE quotation SET status = %(status)s WHERE quote_id = %(quote_id)s RETURNING *",
    {"status": payload.value, "quote_id": quote_id}
)

# Also updates inquiry workflow stage
await self.activity_log.update_workflow_status(
    row['inq_id'],
    WorkflowStatusPatch(stage=WorkflowStage.customer_response)
)
```

**Frontend note:** Single call. Both `accepted` and `rejected` set the workflow to `customer_response` — the workflow stage does not distinguish between acceptance and rejection. To know the actual outcome, read the quotation's `status` field. Passing any status other than `accepted` or `rejected` returns `400`.

---

#### Direct status update via PATCH (no workflow side effect)

**Trigger:** `PATCH /quotations/{quote_id}` with `{ "status": "..." }`
**Set by:** `QuotationModule.patch_quotation()` — updates the quotation record directly.
**Source:** `modules/quotation/quotation.py:53-91`

**Frontend note:** This endpoint updates quotation fields but does **not** trigger any workflow transition. Use it for editing quotation details (date, options, channel). To trigger workflow transitions, use the dedicated `/send` and `/response` endpoints instead.

### Quotation Status Summary Table

| From | To | Triggered By | Workflow Side Effect | Source File |
|------|----|-------------|---------------------|-------------|
| _(new)_ | `in_prep` | `POST /quotations/` | none | `quotation_type.py:20` |
| `in_prep` | `sent` | `PATCH /quotations/{id}/send?status=sent` | inquiry → `quotation_sent` | `quotation.py:119` |
| `sent` | `accepted` | `PATCH /quotations/{id}/response?status=accepted` | inquiry → `customer_response` | `quotation.py:147` |
| `sent` | `rejected` | `PATCH /quotations/{id}/response?status=rejected` | inquiry → `customer_response` | `quotation.py:147` |
| _any_ | _any_ | `PATCH /quotations/{id}` (body: `status`) — blocked if `sent` or `accepted` (409) | **none** | `quotation.py:53` |

### How All Three State Machines Relate

```
INQUIRY WORKFLOW         KYC STAGE                QUOTATION STATUS
(workflow_stats)         (kyc_request)            (quotation)
────────────────         ─────────────            ────────────────

kyc_pending ◄──────────► kyc_pending
     │                   kyc_pending
     │                        │
     │                   documents_submitted
     │                        │
     │                   kyc_completed ──── frontend bridges gap
     ▼
rate_check_in_progress
     │
escalated_to_procurement
     │
quotation_prep ─────────────────────────► in_prep
     │                                        │
quotation_sent ◄──────────────────────── sent (auto-links)
     │                                        │
customer_response ◄──────────────────── accepted / rejected
     │                                   (auto-links)
booking_request
     │
completed
```

The arrows marked "auto-links" indicate that calling the quotation `/send` or `/response` endpoints updates **both** the quotation status and the inquiry workflow in a single API call. The KYC-to-workflow bridge requires manual frontend intervention.

---

## 1. Authentication

Azure AD (Entra ID) SSO via OAuth2/OIDC. All protected endpoints require a `Bearer` token in the `Authorization` header.

```
Authorization: Bearer <access_token>
```

**Public endpoints** (no token required): `/auth/login`, `/auth/callback`, `/auth/refresh`, `/docs`, `/openapi.json`, `/`

All other endpoints return `401 Unauthorized` without a valid token.

### `GET /auth/login`

Initiates the Azure AD SSO flow. Returns an authorization URL that the SPA should redirect the user to.

**Response** `200`

```json
{
  "auth_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?client_id=...&state=...&code_challenge=..."
}
```

**Frontend note:** Redirect the user's browser to `auth_url`. After Azure AD authentication, the user is redirected back to `/auth/callback`.

---

### `GET /auth/callback?code={code}&state={state}`

OAuth2 callback endpoint. Validates the OIDC state, exchanges the authorization code for Azure AD tokens, matches the user to an employee record in the database (by `azure_oid` or `mail_id`), issues backend JWTs, and redirects to the SPA.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| `code` | string | Authorization code from Azure AD |
| `state` | string | State parameter for CSRF validation |

**Response** `302` — Redirects to `{FRONTEND_URL}/auth/callback?access_token=...&refresh_token=...`

**Errors:**
- `400` — Invalid or expired state parameter
- `403` — No employee record found for the authenticated email
- `502` — Failed to exchange authorization code or missing id_token

**Frontend note:** Parse the `access_token` and `refresh_token` from the redirect URL query parameters. Store them (e.g., in memory or `sessionStorage`) and include the access token in all subsequent API requests via the `Authorization: Bearer` header.

---

### `POST /auth/refresh`

Exchange a valid refresh token for a new token pair. Implements token rotation — the old refresh token is revoked and a new one is issued.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | yes | The current refresh token |

**Response** `200`

```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:**
- `401` — Refresh token expired, invalid, wrong type, or revoked; or employee no longer exists

**Frontend note:** Access tokens expire after 15 minutes. Call this endpoint before expiry (e.g., at the 12-minute mark) to silently refresh. Store the new token pair and discard the old one.

---

### `GET /auth/me`

Returns the current authenticated user (derived from the JWT in the `Authorization` header).

**Response** `200`

```json
{
  "emp_id": 8,
  "name": "Sales User",
  "desig": "Sales Executive",
  "dept": "sales",
  "mail_id": "sales@clsynergy.com"
}
```

---

### `POST /auth/logout`

Revokes the refresh token. The access token remains valid until it expires (max 15 minutes).

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `refresh_token` | string | no | The refresh token to revoke |

**Response** `200`

```json
{
  "message": "Logged out successfully"
}
```

**Frontend note:** After logout, discard both tokens on the client side and redirect to the login page.

---

## 2. Clients

Manage customer/company records and their contact persons.

### `POST /clients/clients`

Register a new client with a primary contact person.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Company name |
| `assigned_to` | int | no | Employee ID of assigned salesperson |
| `vat_no` | string | no | VAT registration number |
| `tin` | string | no | Tax Identification Number |
| `kyc_completed` | bool | no | KYC approval status (default: `false`) |
| `addr_street_ln` | string | yes | Street address |
| `addr_city` | string | yes | City |
| `addr_country` | string | yes | Country |
| `primary_contact` | object | yes | Primary contact person (see below) |

**`primary_contact` object**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Contact person name |
| `designation` | string | no | Job title |
| `email` | string | no | Email address |
| `whatsapp` | string | no | WhatsApp number |
| `phone` | string | no | Phone number |
| `wechat` | string | no | WeChat ID |

**Response** `201`

```json
{
  "cli_id": 1,
  "cpid": 1
}
```

---

### `PATCH /clients/clients/{cli_id}`

Update client details. Only include fields that need updating.

**Request Body**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Company name |
| `vat_no` | string | VAT number |
| `tin` | string | TIN |
| `kyc_completed` | bool | KYC status |
| `addr_street_ln` | string | Street address |
| `addr_city` | string | City |

**Response** `200` — Returns the full updated client record.

---

### `PATCH /clients/clients/{cli_id}/contacts/{cpid}`

Update a contact person's details.

**Request Body** — All fields optional:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Contact name |
| `designation` | string | Job title |
| `email` | string | Email |
| `whatsapp` | string | WhatsApp number |
| `phone` | string | Phone |
| `wechat` | string | WeChat ID |

**Response** `200` — Returns the updated contact record.

---

### `GET /clients/clients`

List all clients.

**Response** `200`

```json
[
  { "cli_id": 1, "name": "Acme Exports" },
  { "cli_id": 2, "name": "Global Trading Co" }
]
```

---

### `GET /clients/clients/{cli_id}/contacts`

List all contacts for a client.

**Response** `200`

```json
[
  { "cpid": 1, "name": "John Silva" },
  { "cpid": 2, "name": "Maria Fernando" }
]
```

---

### `GET /clients/clients/{cli_id}/kyc-status`

Get KYC completion status for a client. Only returns data for clients assigned to the current user.

**Response** `200`

```json
[{ "kyc_completed": true }]
```

---

## 3. KYC

Know-Your-Customer compliance documentation and verification for new customers. Finance must approve KYC before an inquiry can proceed.

### KYC Stages

```
kyc_uninitiated → kyc_pending → documents_submitted → kyc_completed
```

### `POST /kyc/kyc-requests?cli_id={cli_id}`

Create a KYC request for a client.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| `cli_id` | int | Client ID to create KYC for |

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `br_number` | string | yes | Business registration number |
| `parent_organization` | string | no | Parent company name |
| `emp_id_sales` | int | no | Assigned salesperson employee ID |
| `emp_id_cs` | int | no | Assigned CS employee ID |
| `document_submission_deadline` | date | yes | Deadline for document submission |
| `cli_type` | string | yes | Client type (shipper/buyer/agent/trader) |
| `currency` | string | yes | Operating currency |
| `website` | string | no | Company website |
| `svat_no` | string | no | SVAT number |
| `tax_exemptions` | string | yes | Tax exemption details |
| `sea_imports` | bool | no | Handles sea imports (default: `false`) |
| `sea_exports` | bool | no | Handles sea exports (default: `false`) |
| `trade_lanes` | bool | no | Has trade lane operations |
| `forwarding` | bool | no | Provides forwarding services |
| `cross_trade` | bool | no | Handles cross-trade |
| `air_imports` | bool | no | Handles air imports |
| `air_exports` | bool | no | Handles air exports |
| `general_cargo` | bool | no | Handles general cargo |
| `dangerous_goods` | bool | no | Handles dangerous goods |
| `perishable_goods` | bool | no | Handles perishable goods |
| `contact_person` | object | no | Additional contact (same structure as primary_contact) |
| `docs` | object | yes | Document checklist (see below) |
| `kyc_stage` | string | no | Initial stage (default: `kyc_pending`) |

**`docs` object (DocumentChecklist)**

| Field | Type | Description |
|-------|------|-------------|
| `cli_id` | int | Client ID |
| `br_form` | string | Business registration form (file reference) |
| `vat_certificate` | string | VAT certificate |
| `svat_certificate` | string | SVAT certificate |
| `tin_certificate` | string | TIN certificate |
| `form20` | string | Form 20 document |

**Response** `201` — Returns the created KYC request with `kyc_id`.

---

### `PATCH /kyc/kyc-requests/{kyc_id}`

Update KYC request details.

**Request Body** — Same fields as creation, all optional except `document_submission_deadline`.

**Response** `200` — Returns the updated KYC record.

---

### `PATCH /kyc/kyc-requests/{kyc_id}/documents/{doc_id}`

Update or upload documents in the KYC checklist.

**Request Body**

| Field | Type | Description |
|-------|------|-------------|
| `cli_id` | int | Client ID |
| `br_form` | string | Business registration form reference |
| `vat_certificate` | string | VAT certificate reference |
| `svat_certificate` | string | SVAT certificate reference |
| `tin_certificate` | string | TIN certificate reference |
| `form20` | string | Form 20 reference |

**Response** `200` — Returns the updated document checklist.

---

### `POST /kyc/kyc-requests/clients/{cli_id}/stage`

Initialize a KYC record for a client with stage set to `kyc_uninitiated`. This is called automatically when `POST /inquiries/inquiries-new-new` creates a new client, but can also be called manually.

**Path Parameters**

| Param | Type | Description |
|-------|------|-------------|
| `cli_id` | int | Client ID to initialize KYC for |

**Response** `201` — Returns the created `kyc_request` row with `kyc_id`.

---

### `GET /kyc/kyc-requests/pending`

List all clients with `kyc_stage = kyc_uninitiated`. Intended for the Finance team's queue of new clients awaiting KYC initiation.

**Response** `200`

```json
[
  {
    "name": "Acme Exports",
    "vat_no": "VAT123",
    "tin": "TIN456",
    "credit_limit": null,
    "addr_street_ln": "12 Main St",
    "addr_city": "Colombo",
    "addr_country": "LK"
  }
]
```

---

### `GET /kyc/kyc-requests/requests`

List all KYC requests with their full details.

**Response** `200` — Returns a list of KYC request records.

---

### `PATCH /kyc/kyc-requests/clients/{cli_id}/stage`

Update the KYC stage for a client.

**Query Parameters**

| Param | Type | Values |
|-------|------|--------|
| `stage` | KYCStage | `kyc_uninitiated`, `kyc_pending`, `documents_submitted`, `kyc_completed` |

**Response** `200` — Returns the updated KYC record.

---

## 4. Inquiries

Handle freight inquiries. Supports three creation scenarios depending on whether the client and contact already exist.

### Inquiry Creation Variants

| Endpoint | Scenario | Creates |
|----------|----------|---------|
| `POST /inquiries/inquiries-new-new` | New client, new contact | Client + contact + inquiry |
| `POST /inquiries/inquiries-old-new` | Existing client, new contact | Contact + inquiry |
| `POST /inquiries/inquiries-old-old` | Existing client, existing contact | Inquiry only |

### `POST /inquiries/inquiries-new-new`

Create an inquiry for a brand-new client with a new contact person. Automatically sets workflow to `rate_check_in_progress` and creates a `kyc_request` record with `kyc_stage = kyc_uninitiated` for the new client.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `client` | object | yes | New client info |
| `contact` | object | yes | New contact person |
| `inquiry` | object | yes | Inquiry details |
| `commodities` | array | no | List of commodities (default: `[]`) |
| `containers` | array | no | List of containers (default: `[]`) |

**`client` object**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Company name |
| `kyc_completed` | bool | no | Default: `false` |

**`contact` object**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Contact name |
| `designation` | string | no | Job title |
| `email` | string | no | Email |
| `whatsapp` | string | no | WhatsApp number |
| `phone` | string | no | Phone |
| `wechat` | string | no | WeChat ID |

**`inquiry` object**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `origin` | string | yes | Port of origin (UN/LOCODE) |
| `sbu` | string | no | Strategic business unit |
| `remark` | string | no | General remark |
| `incoterm` | string | no | Incoterm (FOB, CIF, etc.) |
| `cargo_ready_date` | date | no | Cargo readiness date |
| `priority` | string | no | Priority level |
| `preferred_liners` | string | no | Preferred shipping lines |
| `preferred_rate` | float | no | Customer's target rate |
| `service_mode` | string | no | `DOOR_TO_DOOR` or `PORT_TO_PORT` |

**`commodities[]` items**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | no | Commodity name |
| `com_type` | string | no | Commodity type (general, hazardous, perishable) |
| `hs_code` | string | no | Harmonized System code |
| `description` | string | no | Detailed description |
| `weight` | float | no | Weight in KG |
| `remark` | string | no | Additional notes |

**`containers[]` items**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `destination` | string | yes | Port of destination (UN/LOCODE) |
| `commodity_index` | int | no | Index into the `commodities` array to link this container |
| `container_type` | string | no | Container type (20ft, 40ft, open top, flat rack, reefer) |
| `temperature` | int | no | Reefer temperature in Celsius |
| `qty` | int | no | Number of containers (must be > 0) |
| `address` | string | no | Delivery address |
| `zip_code` | string | no | Postal/ZIP code |
| `is_fully_loaded` | bool | no | FCL flag (default: `false`) |
| `free_time` | string | no | Free time allowance |

**Response** `201`

```json
{
  "inq_id": 1,
  "logged_inq_id": 1,
  "cli_id": 1,
  "cpid": 1,
  "com_ids": [1, 2],
  "cont_ids": [1]
}
```

---

### `POST /inquiries/inquiries-old-new`

Create an inquiry for an existing client with a new contact. Automatically sets workflow to `rate_check_in_progress` (KYC assumed complete).

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cli_id` | int | yes | Existing client ID |
| `contact` | object | yes | New contact person |
| `inquiry` | object | yes | Inquiry details |
| `commodities` | array | no | Default: `[]` |
| `containers` | array | no | Default: `[]` |

Nested object structures are identical to `inquiries-new-new`.

**Response** `201` — Same structure as above.

---

### `POST /inquiries/inquiries-old-old`

Create an inquiry for an existing client and existing contact. Automatically sets workflow to `rate_check_in_progress`.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cli_id` | int | yes | Existing client ID |
| `cp_id` | int | yes | Existing contact person ID |
| `inquiry` | object | yes | Inquiry details |
| `commodities` | array | no | Default: `[]` |
| `containers` | array | no | Default: `[]` |

**Response** `201` — Same structure as above.

---

### `PATCH /inquiries/inquiries/{inq_id}`

Update inquiry fields. Supports partial updates (only send changed fields).

**Request Body** — All fields optional:

| Field | Type | Description |
|-------|------|-------------|
| `sbu` | string | Strategic business unit |
| `remark` | string | Remark |
| `origin` | string | Port of origin |
| `incoterm` | string | Incoterm |
| `cargo_ready_date` | date | Cargo ready date |
| `priority` | string | Priority level |
| `preferred_liners` | string | Preferred liners |
| `preferred_rate` | float | Target rate |
| `service_mode` | string | `DOOR_TO_DOOR` or `PORT_TO_PORT` |

**Response** `200` — Returns the full updated inquiry record.

---

### `PATCH /inquiries/inquiries/{inq_id}/commodities/{com_id}`

Update a commodity within an inquiry.

**Request Body** — All fields optional:

| Field | Type | Description |
|-------|------|-------------|
| `com_type` | string | Commodity type |
| `hs_code` | string | HS code |
| `description` | string | Description |
| `weight` | float | Weight |
| `remark` | string | Remark |

**Response** `200` — Returns the updated commodity record.

---

### `PATCH /inquiries/inquiries/{inq_id}/containers/{cont_id}`

Update a container within an inquiry.

**Request Body** — All fields optional:

| Field | Type | Description |
|-------|------|-------------|
| `container_type` | string | Container type |
| `temperature` | int | Temperature |
| `qty` | int | Quantity (must be > 0) |
| `destination` | string | Destination port |
| `address` | string | Delivery address |
| `zip_code` | string | ZIP code |
| `is_fully_loaded` | bool | FCL flag |
| `free_time` | string | Free time |

**Response** `200` — Returns the updated container record.

---

### `GET /inquiries/inquiries/{inq_id}`

Fetch a single inquiry with all related client, commodity, container, and workflow data joined.

**Response** `200` — Returns a list of rows (one per commodity-container combination):

```json
[
  {
    "cli_id": 1,
    "inq_id": 1,
    "workflow_stage": "rate_check_in_progress",
    "name": "Acme Exports",
    "kyc_completed": true,
    "sbu": "FCL",
    "origin": "LKCMB",
    "incoterm": "FOB",
    "priority": "high",
    "service_mode": "PORT_TO_PORT",
    "cargo_ready_date": "2026-08-15",
    "preferred_liners": "CMA CGM",
    "preferred_rate": 1200.0,
    "com_id": 1,
    "commodity_name": "Textiles",
    "commodity_type": "general",
    "hs_code": "6302",
    "commodity_weight": 18000.0,
    "cont_id": 1,
    "container_type": "40ft",
    "temperature": null,
    "qty": 2,
    "destination": "DEHAM",
    "zip_code": null,
    "address": null,
    "is_fully_loaded": true,
    "free_time": "14 days"
  }
]
```

---

### `GET /inquiries/inquiries`

List all inquiries with joined data. Includes `kyc_stage` from the joined `kyc_request` table (in addition to the fields returned by the single inquiry endpoint).

**Additional field in response:**

| Field | Type | Description |
|-------|------|-------------|
| `kyc_stage` | string | Current KYC stage for the client (`kyc_uninitiated`, `kyc_pending`, `documents_submitted`, `kyc_completed`) |

**Response** `200` — Same row structure as the single inquiry endpoint, plus `kyc_stage`.

---

### `DELETE /inquiries/inquiries/{inq_id}`

Delete an inquiry. Only the employee who created the inquiry can delete it.

**Response** `200`

```json
{ "inq_id": 1 }
```

---

## 5. Workflow / Activity Log

Track inquiry progression through workflow stages. Stages are updated automatically by other modules (inquiry creation, rate requests, quotations) but can also be set manually.

### `POST /inquiries/workflow`

Create an initial workflow record for an inquiry.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inq_id` | int | yes | Inquiry ID |
| `flow_id` | int | no | Flow identifier (default: `1`) |
| `stage` | string | no | Initial stage (default: `kyc_pending`) |

**Stage values:** `kyc_pending`, `rate_check_in_progress`, `escalated_to_procurement`, `quotation_prep`, `quotation_sent`, `customer_response`, `booking_request`, `completed`

**Response** `201` — Returns the created workflow record.

---

### `PATCH /inquiries/workflow/{inq_id}`

Manually update the workflow stage for an inquiry.

**Request Body** — All fields optional:

| Field | Type | Description |
|-------|------|-------------|
| `flow_id` | int | Flow identifier |
| `stage` | string | New workflow stage |

**Response** `200` — Returns the updated workflow record.

---

## 6. Liners

Manage shipping line (carrier) records.

### `GET /liners`

List all registered liners.

**Response** `200`

```json
[
  {
    "lin_id": 1,
    "name": "CMA CGM",
    "has_portal": true,
    "is_on_intra": true
  }
]
```

---

### `POST /liners`

Register a new shipping liner.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Liner name |
| `has_portal` | bool | no | Has online booking portal (default: `false`) |
| `is_on_intra` | bool | no | Available on INTTRA middleware (default: `false`) |

**Response** `201` — Returns the created liner record.

---

## 7. Rates — Master (Persistent)

Long-lived rate records maintained by the pricing team. These correspond to the rate checking sequence in Flow 1: contracted rates are checked first, then tariff rates, then NAC rates for named accounts.

### Tariff Rates

Standard tariff templates maintained in the rate database.

#### `POST /rates/tariff-rates`

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lin_id` | int | yes | Liner ID |
| `tr_ln_id` | int | yes | Trade lane ID |
| `updated_by` | int | yes | Employee ID of updater |
| `salesperson` | int | yes | Assigned salesperson employee ID |
| `origin` | string | yes | Origin port |
| `destination` | string | yes | Destination port |
| `valid_from` | date | yes | Validity start |
| `valid_to` | date | yes | Validity end |
| `max_weight` | int | yes | Maximum weight (KG) |
| `container_type` | string | yes | Container type |
| `rate` | float | yes | Rate amount (all-in) |
| `currency` | string | yes | Currency code (USD, EUR, etc.) |
| `free_time` | string | no | Free time allowance |
| `iwe` | string | no | Import/Warehouse Equipment |
| `transit` | string | no | Transit time |
| `note` | string | no | Notes |
| `special_remark` | string | no | Special remarks |
| `surcharges` | array | no | List of surcharges |

**`surcharges[]` items (SurchargeNew)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `rate_id` | int | yes | Parent rate ID |
| `type` | string | yes | Surcharge type |
| `amt` | float | yes | Surcharge amount |
| `currency` | string | yes | Currency |

**Response** `201` — Returns the created tariff with `tar_id`.

#### `GET /rates/tariff-rates`

List all tariff rates. Response includes any associated surcharges via LEFT JOIN.

**Additional surcharge fields in response:**

| Field | Type | Description |
|-------|------|-------------|
| `sur_id` | int \| null | Surcharge ID |
| `surcharge_type` | string \| null | Surcharge type |
| `surcharge_amt` | float \| null | Surcharge amount |
| `surcharge_currency` | string \| null | Surcharge currency |

**Response** `200`

#### `GET /rates/tariff-rates/{tar_id}`

Get a single tariff rate. **Response** `200`

#### `PATCH /rates/tariff-rates/{tar_id}`

Update a tariff rate. All fields optional. **Response** `200`

#### `DELETE /rates/tariff-rates/{tar_id}`

Delete a tariff rate. **Response** `200` — `{ "tar_id": 1 }`

---

### NAC Rates (Named Account Contract)

Special negotiated rates for key accounts (~10 customers). Valid 6-12 months. Restricted visibility to assigned salesperson and procurement only.

#### `POST /rates/nac-rates`

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cli_id` | int | yes | Client ID (named account) |
| `lin_id` | int | yes | Liner ID |
| `tr_ln_id` | int | yes | Trade lane ID |
| `nac_ref_id` | string | yes | NAC reference identifier |
| `origin` | string | yes | Origin port |
| `destination` | string | yes | Destination port |
| `valid_from` | date | yes | Validity start |
| `valid_to` | date | yes | Validity end |
| `container_type` | string | yes | Container type |
| `rate` | float | yes | Rate amount |
| `currency` | string | yes | Currency |
| `contracted_volume` | int | yes | Contracted TEU volume |
| `emp_id_sales` | int | yes | Assigned salesperson |
| `emp_id_cs` | int | yes | Assigned CS employee |
| `max_weight` | int | no | Max weight |
| `free_time` | string | no | Free time |
| `iwe` | string | no | IWE |
| `transit` | string | no | Transit time |
| `note` | string | no | Notes |
| `special_remark` | string | no | Special remarks |
| `surcharges` | array | no | Surcharges |

**Response** `201` — Returns with `nac_id`.

#### `GET /rates/nac-rates`

List all NAC rates. Response includes any associated surcharges via LEFT JOIN.

**Additional surcharge fields in response:**

| Field | Type | Description |
|-------|------|-------------|
| `sur_id` | int \| null | Surcharge ID |
| `surcharge_type` | string \| null | Surcharge type |
| `surcharge_amt` | float \| null | Surcharge amount |
| `surcharge_currency` | string \| null | Surcharge currency |

**Response** `200`

#### `GET /rates/nac-rates/{nac_id}`

Get a single NAC rate. **Response** `200`

#### `GET /rates/nac-rates/client/{cli_id}`

Get all NAC rates for a specific client. **Response** `200`

#### `PATCH /rates/nac-rates/{nac_id}`

Update a NAC rate. All fields optional except `updated_by` (required). **Response** `200`

#### `DELETE /rates/nac-rates/{nac_id}`

Delete a NAC rate. **Response** `200` — `{ "nac_id": 1 }`

---

### Contracted Rates

Pre-agreed rates with liners, typically monthly or quarterly validity. Checked first in the rate lookup sequence.

#### `POST /rates/contracted-rates`

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lin_id` | int | yes | Liner ID |
| `tr_ln_id` | int | yes | Trade lane ID |
| `contract_ref_id` | string | yes | Contract/RA reference number |
| `valid_from` | date | yes | Validity start |
| `valid_to` | date | yes | Validity end |
| `contracted_volume` | int | yes | Contracted TEU volume |
| `container_type` | string | yes | Container type |
| `updated_by` | int | yes | Employee ID |
| `origin` | string | yes | Origin port |
| `destination` | string | yes | Destination port |
| `rate` | float | yes | Rate amount |
| `currency` | string | yes | Currency |
| `emp_id_sales` | int | yes | Assigned salesperson |
| `emp_id_cs` | int | yes | Assigned CS employee |
| `inq_id` | int | no | Linked inquiry ID |
| `iwe` | string | no | IWE |
| `transit` | string | no | Transit time |
| `free_time` | string | no | Free time |
| `max_weight` | int | no | Max weight |
| `note` | string | no | Notes |
| `special_remark` | string | no | Special remarks |
| `client_ids` | int[] | no | Linked client IDs |
| `surcharges` | array | no | Surcharges |

**Response** `201` — Returns with `crate_id`.

#### `GET /rates/contracted-rates`

List all contracted rates. Response includes any associated surcharges via LEFT JOIN.

**Additional surcharge fields in response:**

| Field | Type | Description |
|-------|------|-------------|
| `sur_id` | int \| null | Surcharge ID |
| `surcharge_type` | string \| null | Surcharge type |
| `surcharge_amt` | float \| null | Surcharge amount |
| `surcharge_currency` | string \| null | Surcharge currency |

**Response** `200`

#### `GET /rates/contracted-rates/{crate_id}`

Get a single contracted rate. **Response** `200`

#### `GET /rates/contracted-rates/client/{cli_id}`

Get contracted rates for a specific client. **Response** `200`

#### `PATCH /rates/contracted-rates/{crate_id}`

Update a contracted rate. All fields optional. **Response** `200`

#### `DELETE /rates/contracted-rates/{crate_id}`

Delete a contracted rate. **Response** `200` — `{ "crate_id": 1 }`

---

## 8. Rates — Operational (Non-Persistent)

Short-lived, inquiry-linked rates. These are spot rates, vessel-specific rates, and commodity-specific rates that change frequently.

### Vessel-by-Vessel Rates

Voyage-specific spot rates. Validity ranges from 24 hours to vessel departure. Changes frequently.

#### `POST /rates/vessel-rates`

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inq_id` | int | yes | Linked inquiry ID |
| `voyage` | string | yes | Voyage number |
| `vessel_name` | string | yes | Vessel name |
| `eta` | date | yes | Estimated time of arrival |
| `etd` | date | yes | Estimated time of departure |
| `rate` | float | yes | Rate amount |
| `currency` | string | yes | Currency |
| `fcl_opening` | datetime | yes | FCL booking opening time |
| `fcl_cutoff` | datetime | yes | FCL booking cutoff time |
| `origin` | string | yes | Origin port |
| `destination` | string | yes | Destination port |
| `tr_ln_id` | int | yes | Trade lane ID |
| `container_type` | string | yes | Container type |
| `volume` | int | yes | Available TEU volume |
| `iwe` | string | no | IWE |
| `free_days` | string | no | Free days |
| `max_weight` | int | no | Max weight |
| `note` | string | no | Notes |
| `special_remark` | string | no | Remarks |
| `issold` | bool | no | Whether this rate slot is sold |
| `iscancelled` | bool | no | Whether booking was cancelled |
| `cancellationreason` | string | no | Cancellation reason |
| `cancellationfee` | float | no | Cancellation fee amount |
| `surcharges` | array | no | Surcharges |

**Response** `201` — Returns `{ "srid": 1 }`

#### `GET /rates/vessel-rates`

List all vessel rates. Response includes any associated surcharges via LEFT JOIN.

**Additional surcharge fields in response:**

| Field | Type | Description |
|-------|------|-------------|
| `sur_id` | int \| null | Surcharge ID |
| `surcharge_type` | string \| null | Surcharge type |
| `surcharge_amt` | float \| null | Surcharge amount |
| `surcharge_currency` | string \| null | Surcharge currency |

**Response** `200`

#### `PATCH /rates/vessel-rates/{srid}`

Update a vessel rate. **Response** `200`

#### `DELETE /rates/vessel-rates/{srid}`

Delete a vessel rate. **Response** `200` — `{ "srid": 1 }`

---

### FAK Rates (Freight All Kinds)

Volume-based container load rates. Applicable for mixed cargo not covered by commodity-specific pricing.

#### `POST /rates/fak-rates`

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lin_id` | int | yes | Liner ID |
| `tr_ln_id` | int | yes | Trade lane ID |
| `inq_id` | int | yes | Linked inquiry ID |
| `valid_from` | datetime | yes | Validity start |
| `valid_to` | datetime | yes | Validity end |
| `volume` | int | yes | TEU volume |
| `container_type` | string | yes | Container type |
| `origin` | string | yes | Origin port |
| `destination` | string | yes | Destination port |
| `rate` | float | yes | Rate amount |
| `currency` | string | yes | Currency |
| `iwe` | string | no | IWE |
| `transit` | string | no | Transit time |
| `free_time` | string | no | Free time |
| `max_weight` | int | no | Max weight |
| `note` | string | no | Notes |
| `special_remark` | string | no | Remarks |
| `issold` | bool | no | Sold flag |
| `surcharges` | array | no | Surcharges |

**Response** `201` — Returns `{ "fak_id": 1 }`

#### `GET /rates/fak-rates`

List all FAK rates. Response includes any associated surcharges via LEFT JOIN.

**Additional surcharge fields in response:**

| Field | Type | Description |
|-------|------|-------------|
| `sur_id` | int \| null | Surcharge ID |
| `surcharge_type` | string \| null | Surcharge type |
| `surcharge_amt` | float \| null | Surcharge amount |
| `surcharge_currency` | string \| null | Surcharge currency |

**Response** `200`

#### `PATCH /rates/fak-rates/{srid}`

Update a FAK rate. **Response** `200`

#### `DELETE /rates/fak-rates/{srid}`

Delete a FAK rate. **Response** `200` — `{ "srid": 1 }`

---

### Special Rates

Commodity-specific rates, linked to both an inquiry and a specific commodity. Used for hazardous goods, perishables, or other cargo requiring premium pricing.

#### `POST /rates/special-rates`

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `lin_id` | int | yes | Liner ID |
| `tr_ln_id` | int | yes | Trade lane ID |
| `inq_id` | int | yes | Linked inquiry ID |
| `com_id` | int | yes | Linked commodity ID |
| `valid_from` | datetime | yes | Validity start |
| `valid_to` | datetime | yes | Validity end |
| `rate` | float | yes | Rate amount |
| `origin` | string | yes | Origin port |
| `destination` | string | yes | Destination port |
| `container_type` | string | yes | Container type |
| `volume` | int | yes | TEU volume |
| `currency` | string | yes | Currency |
| `transit` | string | no | Transit time |
| `iwe` | string | no | IWE |
| `free_days` | string | no | Free days |
| `max_weight` | int | no | Max weight |
| `note` | string | no | Notes |
| `special_remark` | string | no | Remarks |
| `issold` | bool | no | Sold flag |
| `surcharges` | array | no | Surcharges |

**Response** `201` — Returns `{ "sprid": 1 }`

#### `GET /rates/special-rates`

List all special rates. Response includes any associated surcharges via LEFT JOIN.

**Additional surcharge fields in response:**

| Field | Type | Description |
|-------|------|-------------|
| `sur_id` | int \| null | Surcharge ID |
| `surcharge_type` | string \| null | Surcharge type |
| `surcharge_amt` | float \| null | Surcharge amount |
| `surcharge_currency` | string \| null | Surcharge currency |

**Response** `200`

#### `PATCH /rates/special-rates/{sprid}`

Update a special rate. **Response** `200`

#### `DELETE /rates/special-rates/{sprid}`

Delete a special rate. **Response** `200` — `{ "sprid": 1 }`

---

### Rate Lookup (Generic)

#### `GET /rates/rate/{rate_id}?rate_type={type}`

Look up a single rate by its ID and type.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| `rate_type` | string | Rate table identifier (e.g. `vessel_by_vessel_rate`, `fak_rates`, `special_rate`) |

**Response** `200` — Returns the rate record.

---

## 9. Rate Requests

Escalate an inquiry to the procurement team when no suitable rate is found, or to request better rate options. Procurement responds by attaching rate options.

### `POST /rate-requests`

Create a rate request. Automatically transitions the inquiry workflow to `escalated_to_procurement`.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inq_id` | int | yes | Inquiry ID to escalate |
| `emp_id_requested` | int | yes | Procurement employee ID to assign |
| `is_given` | bool | no | Whether rates have been provided (default: `false`) |
| `remark` | string | yes | Description of what rates are needed |

**Response** `201`

```json
{ "request_id": 1 }
```

---

### `GET /rate-requests/incoming`

List all rate requests assigned to the current user (procurement). Sorted by creation date descending.

**Response** `200` — Returns a list of rate request records.

---

### `DELETE /rate-requests/{request_id}`

Delete a rate request.

**Response** `200` — `{ "request_id": 1 }`

---

### `POST /rate-requests/{request_id}/options`

Add a rate option to a request. Automatically sets `is_given = true` on the parent request and transitions the inquiry workflow to `quotation_prep`.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | int | yes | Parent rate request ID |
| `rate_type` | string | yes | Type of rate (e.g. `tariff_rates`, `nac`, `vessel_by_vessel_rate`) |
| `rate_id` | int | yes | ID of the rate record |

**Response** `201`

```json
{ "option_id": 1 }
```

---

### `PATCH /rate-requests/{request_id}/options/{option_id}`

Update a rate option.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `updated_by` | int | yes | Employee ID making the update |
| `rate_type` | string | no | New rate type |
| `rate_id` | int | no | New rate ID |

**Response** `200` — Returns the updated option record.

---

### `DELETE /rate-requests/{request_id}/options/{option_id}`

Delete a rate option. If this was the last option on the request, `is_given` reverts to `false` and the workflow moves back to `escalated_to_procurement`.

**Response** `200` — `{ "option_id": 1 }`

---

## 10. Quotations

Create and manage quotations sent to customers. Multiple liner options can be included so the customer can choose. This module covers the final step of Flow 1 (sending the quotation) and the response recording step of Flow 2.

### `POST /quotations/`

Create a new quotation with rate options.

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inq_id` | int | yes | Inquiry ID |
| `quote_date` | date | yes | Date of quotation |
| `sent_via` | string | yes | Channel (`email`, `whatsapp`, `phone`) |
| `status` | string | no | Initial status (default: `in_prep`) |
| `is_follow_up` | bool | no | Whether this is a follow-up quote (default: `false`) |
| `acceptence_deadline` | date | no | Deadline for customer response |
| `options` | array | yes | Rate options included in the quotation |

**`options[]` items**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `inq_id` | int | yes | Inquiry ID |
| `rate_id` | int | yes | Source rate record ID |
| `option_id` | int | yes | Rate request option ID |
| `amt` | float | yes | Quoted amount (all-in) |
| `currency` | string | yes | Currency |

**Response** `201`

```json
{ "quote_id": 1 }
```

---

### `GET /quotations/`

List all quotations with their options joined.

**Response** `200` — Returns a list of rows (one per quotation-option combination). Quotations without options appear once with null option fields.

```json
[
  {
    "quote_id": 1,
    "inq_id": 1,
    "status": "in_prep",
    "quote_date": "2026-08-12",
    "is_follow_up": false,
    "acceptence_deadline": "2026-08-20",
    "sent_via": "email",
    "option_id": 1,
    "rate_id": 5,
    "amt": 1200.0,
    "option_currency": "USD",
    "option_inq_id": 1
  }
]
```

---

### `GET /quotations/{quote_id}`

Fetch a single quotation with its options joined.

**Response** `200` — Same row structure as the list endpoint, filtered to the given `quote_id`.

**Error** `404` — Quotation not found.

---

### `PATCH /quotations/{quote_id}`

Update quotation details and/or replace its options. **Quotations with status `sent` or `accepted` cannot be modified** — returns `409 Conflict`.

**Request Body** — All fields optional:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `in_prep`, `sent`, `accepted`, `rejected` |
| `quote_date` | date | Quotation date |
| `is_follow_up` | bool | Follow-up flag |
| `acceptence_deadline` | date | Response deadline |
| `sent_via` | string | Channel |
| `options` | array | Replaces all existing options |

**Response** `200` — Returns the updated quotation record.

**Error** `409` — `"Cannot modify quotation with status 'sent'"` or `'accepted'`.

---

### `DELETE /quotations/{quote_id}`

Delete a quotation.

**Response** `200` — `{ "quote_id": 1 }`

---

### `PATCH /quotations/{quote_id}/send`

Mark a quotation as sent to the customer. Transitions the inquiry workflow to `quotation_sent`.

**Query Parameters**

| Param | Type | Values |
|-------|------|--------|
| `status` | QuotationStatus | `sent` |

**Response** `200` — Returns the updated quotation record.

---

### `PATCH /quotations/{quote_id}/response`

Record the customer's response to a quotation. When accepting, validates that the selected option exists for this quotation. Transitions the inquiry workflow to `customer_response`. **This is the final step covered by this API (Flow 2, Step 2).**

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | yes | Must be `accepted` |
| `option` | int | yes | The `rate_id` of the accepted quotation option |

**Response** `200` — Returns the updated quotation record.

**Errors:**
- `400` — Status is not `accepted` or `rejected`
- `422` — The selected option does not exist for this quotation

---

## Error Responses

All endpoints use consistent error response formats.

### Standard HTTP Error Codes

| Code | Meaning | When |
|------|---------|------|
| `400` | Bad Request | No fields provided for update, or invalid status value |
| `404` | Not Found | Resource does not exist |
| `409` | Conflict | Unique constraint violation (duplicate record), or attempting to modify a finalized quotation (`sent`/`accepted`) |
| `422` | Unprocessable Entity | Foreign key, check, not-null, or column constraint violation |
| `503` | Service Unavailable | Database connection failure |

### Constraint Violation Response (422)

```json
{
  "detail": {
    "error": "constraint_violation",
    "constraint": "inquiry_origin_fkey",
    "message": "insert or update on table \"inquiry\" violates foreign key constraint"
  }
}
```

### Conflict Response (409)

```json
{
  "detail": {
    "constraint": "client_name_key",
    "message": "duplicate key value violates unique constraint"
  }
}
```

### Database Unavailable Response (503)

```json
{
  "detail": {
    "error": "database_unavailable",
    "message": "connection to server failed"
  }
}
```
