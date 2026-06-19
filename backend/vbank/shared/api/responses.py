from typing import Any


def success_response(data: Any, request_id: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "data": data,
    }


def page_response(
    data: list[Any],
    *,
    request_id: str,
    limit: int,
    offset: int,
    total: int,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "data": data,
        "page": {
            "limit": limit,
            "offset": offset,
            "total": total,
        },
    }


def error_response(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None,
    request_id: str,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
        "request_id": request_id,
    }
