from enum import Enum
from pydantic import BaseModel


# TODO: add stages to find inq. ready to be tracked -> portwatch

class WorkflowStage(str, Enum):
    kyc_pending              = 'kyc_pending'
    rate_check_in_progress   = 'rate_check_in_progress'
    escalated_to_procurement = 'escalated_to_procurement'
    quotation_prep           = 'quotation_prep'
    quotation_sent           = 'quotation_sent'
    customer_response        = 'customer_response'
    booking_request          = 'booking_request'
    booking_confirmed        = 'booking_confirmed' 
    bl_drafting              = 'bl_drafted'
    completed                = 'completed'


class WorkflowStatusNew(BaseModel):
    inq_id: int
    flow_id: int = 1
    stage: WorkflowStage = WorkflowStage.kyc_pending


class WorkflowStatusPatch(BaseModel):
    flow_id: int | None = None
    stage: WorkflowStage | None = None