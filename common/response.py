from pydantic import BaseModel
from typing import Optional, Any
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Generic, TypeVar
T = TypeVar("T")


class APIResponseModel(BaseModel, Generic[T]):
    success: bool
    status_code: int
    message: str
    data: Optional[T] = None
    error: Optional[Any] = None
    meta: Optional[Any] = None

def api_response(
    data: Optional[T] = None,
    message: str = "Success",
    status_code: int = 200,
    error: Optional[Any] = None,
    meta: Optional[Any] = None
) -> JSONResponse:
    success = status_code < 400
    # If data is a Pydantic model, convert to dict
    if hasattr(data, "dict"):
        data = data.dict()
    api_response = APIResponseModel(
        success=success,
        status_code=status_code,
        message=message,
        data=data if success else None,
        error=error if not success else None,
        meta=meta,
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(api_response.model_dump(mode='json'))
    )
