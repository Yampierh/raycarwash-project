from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.service import get_current_user
from domains.notifications.models import DeviceToken
from domains.notifications.repository import DeviceTokenRepository
from domains.notifications.schemas import RegisterDeviceTokenRequest, RegisterDeviceTokenResponse
from domains.users.models import User
from infrastructure.db.session import get_db

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.post(
    "/device-token",
    response_model=RegisterDeviceTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or refresh a device push token",
)
async def register_device_token(
    payload: RegisterDeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegisterDeviceTokenResponse:
    repo = DeviceTokenRepository(db)
    await repo.upsert(
        user_id=current_user.id,
        token=payload.token,
        platform=payload.platform,
    )
    return RegisterDeviceTokenResponse()


@router.delete(
    "/device-token",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unregister a device push token (call on logout)",
)
async def unregister_device_token(
    payload: RegisterDeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = DeviceTokenRepository(db)
    await repo.delete_by_token(payload.token)
