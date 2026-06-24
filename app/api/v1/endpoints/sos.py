"""SOS emergency alert API endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_user
from app.models.sos import (
    SOSAlert,
    SOSAlertCreate,
    SOSAlertResponse,
    AlertSeverity,
    TriggerType,
)
from app.models.user import User
from app.services.sos import sos_service

router = APIRouter()


@router.post(
    "/send",
    summary="Trigger SOS alert",
    description="Sends an emergency SOS alert to the user's configured emergency contacts "
    "via SMS and email. Subject to a 30-minute cooldown between alerts.",
    response_model=SOSAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_sos(
    reason: str = Body(None, embed=True, max_length=500),
    current_user: User = Depends(get_current_user),
):
    """Trigger an SOS emergency alert."""
    alert_data = SOSAlertCreate(
        trigger_type=TriggerType.MANUAL,
        severity=AlertSeverity.HIGH,
        reason=reason,
        emotion_data={},
    )

    alert = await sos_service.create_alert(current_user.id, alert_data)

    if alert is None:
        # Check if it was a cooldown block
        cooldown = await sos_service.get_cooldown_status(current_user.id)
        if cooldown["active"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"SOS cooldown active. Please wait {cooldown['remaining_seconds']} seconds "
                    "before sending another alert."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create SOS alert. Please try again.",
        )

    return SOSAlertResponse(
        alert_id=alert.id,
        status=alert.status,
        message="SOS alert sent successfully. Your emergency contacts have been notified.",
    )


@router.post(
    "/cancel/{alert_id}",
    summary="Cancel an SOS alert",
    description="Cancel a pending SOS alert before it is fully processed.",
)
async def cancel_sos(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending SOS alert."""
    cancelled = await sos_service.cancel_alert(alert_id, current_user.id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or cannot be cancelled.",
        )
    return {"message": "SOS alert cancelled successfully."}


@router.post(
    "/resolve/{alert_id}",
    summary="Resolve an SOS alert",
    description="Mark an active or acknowledged SOS alert as resolved.",
)
async def resolve_sos(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """Resolve an SOS alert."""
    resolved = await sos_service.resolve_alert(alert_id)
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or cannot be resolved.",
        )
    return {"message": "SOS alert resolved successfully."}


@router.get(
    "/history",
    summary="Get SOS alert history",
    description="Returns paginated SOS alert history for the authenticated user.",
    response_model=List[SOSAlert],
)
async def get_sos_history(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the user's SOS alert history."""
    return await sos_service.get_user_alerts(current_user.id, page=page, size=size)


@router.get(
    "/cooldown-status",
    summary="Get SOS cooldown status",
    description="Returns whether the SOS cooldown is active, the remaining seconds, "
    "and the timestamp of the last alert.",
    response_model=Dict[str, Any],
)
async def get_cooldown_status(
    current_user: User = Depends(get_current_user),
):
    """Check SOS cooldown status for the current user."""
    return await sos_service.get_cooldown_status(current_user.id)
