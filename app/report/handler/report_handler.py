import io

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config.config import settings
from common.logger import get_logger
from services.report.report_service import REPORT_KEY_PREFIX, REPORT_TTL_SECONDS

logger = get_logger("report_handler")

router = APIRouter(prefix="/report", tags=["Report"])

# Async Redis client — decode_responses=False to handle raw bytes
_redis = aioredis.from_url(
    settings.CELERY_RESULT_BACKEND,
    decode_responses=False,
)


@router.get(
    "/download/{report_id}",
    summary="Download a generated Excel report",
    description=(
        f"Fetches the Excel file from Redis and streams it to the client. "
        f"The file is deleted from Redis immediately after download. "
        f"Reports expire automatically after {REPORT_TTL_SECONDS} seconds if not downloaded."
    ),
)
async def download_report(report_id: str):
    redis_key = f"{REPORT_KEY_PREFIX}{report_id}"
    logger.info(f"[report_handler] Download requested | report_id={report_id}")

    try:
        file_bytes: bytes = await _redis.get(redis_key)
    except Exception as exc:
        logger.error(f"[report_handler] Redis GET failed | key={redis_key} | error={exc}")
        raise HTTPException(status_code=503, detail="Report storage unavailable. Please try again later.")

    if not file_bytes:
        logger.warning(f"[report_handler] Report not found or expired | key={redis_key}")
        raise HTTPException(
            status_code=404,
            detail="Report not found or has already expired. Please request a new report.",
        )

    logger.info(f"[report_handler] Report fetched from Redis | key={redis_key} size={len(file_bytes)} bytes")
    # Do NOT delete — Redis TTL will auto-expire after 5 minutes

    filename = f"report_{report_id[:8]}.xlsx"
    logger.info(f"[report_handler] Streaming file as '{filename}'")

    try:
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_bytes)),
            },
        )
    except Exception as exc:
        logger.error(f"[report_handler] StreamingResponse build failed | report_id={report_id} | error={exc}")
        raise HTTPException(status_code=500, detail="Failed to stream report file.")
