from enum import Enum
from pydantic import BaseModel


class WorkflowStage(str, Enum):
    inquiry_received         = 'inquiry_received'
    customer_check_pending   = 'customer_check_pending'
    kyc_pending              = 'kyc_pending'
    kyc_approved             = 'kyc_approved'
    kyc_rejected             = 'kyc_rejected'
    rate_check_in_progress   = 'rate_check_in_progress'
    escalated_to_procurement = 'escalated_to_procurement'
    quotation_prep           = 'quotation_prep'
    quotation_sent           = 'quotation_sent'
    customer_response        = 'customer_response'
    booking_request          = 'booking_request'
    completed                = 'completed'


class WorkflowStatusNew(BaseModel):
    inq_id: int
    flow_id: int = 1
    stage: WorkflowStage = WorkflowStage.inquiry_received


class WorkflowStatusPatch(BaseModel):
    flow_id: int | None = None
    stage: WorkflowStage | None = None