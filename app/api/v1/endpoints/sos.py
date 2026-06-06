from fastapi import APIRouter, Depends, status
from datetime import datetime
from app.sos import send_sos_sms
from app.api.v1.endpoints.auth import get_current_user
from app.models.sos import SOSAlertResponse, AlertStatus

router = APIRouter()

@router.post(
    '/trigger',
    summary="Trigger Emergency SOS SMS Notification",
    response_model=SOSAlertResponse,
    status_code=status.HTTP_200_OK
)
async def trigger_sos_broadcast(current_user = Depends(get_current_user)):
    """Triggers an instantaneous emergency manual alert payload dispatched via Twilio infrastructure channels."""
    alert_status_str, success_message = await send_sos_sms(current_user)
    
    # Pack parameters to conform with your defined SOSAlertResponse schema model
    return SOSAlertResponse(
        alert_id="SOS_" + str(int(datetime.utcnow().timestamp())),
        status=AlertStatus.SENT,
        message=success_message
    )
