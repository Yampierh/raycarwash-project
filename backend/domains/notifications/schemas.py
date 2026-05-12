from pydantic import BaseModel, Field

from domains.notifications.models import DevicePlatform


class RegisterDeviceTokenRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=512)
    platform: DevicePlatform


class RegisterDeviceTokenResponse(BaseModel):
    message: str = "Device token registered."
