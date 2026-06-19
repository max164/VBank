from typing import Annotated

from fastapi import APIRouter, Depends

from vbank.auth.api import auth_router
from vbank.shared.api.dependencies import get_request_id, get_settings
from vbank.shared.api.responses import success_response
from vbank.shared.config import Settings

api_v1_router = APIRouter(prefix="/api/v1", tags=["api"])
api_v1_router.include_router(auth_router)


@api_v1_router.get("")
def api_root(
    request_id: Annotated[str, Depends(get_request_id)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return success_response(
        {
            "service": settings.app_name,
            "environment": settings.environment,
        },
        request_id=request_id,
    )
