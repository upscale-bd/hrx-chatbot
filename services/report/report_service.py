"""Excel report generation — in-memory only, stored in Redis with TTL."""
import io
import uuid
from typing import Optional, List

import pandas as pd
import redis as redis_sync

from common.logger import get_logger
from config.config import settings

logger = get_logger("report_service")

REPORT_TTL_SECONDS = 300  # 5 minutes — then auto-deleted from Redis
REPORT_KEY_PREFIX = "report:"

# Sync Redis client for binary data (no decode_responses so bytes are preserved)
_redis = redis_sync.from_url(
    settings.CELERY_RESULT_BACKEND,
    decode_responses=False,
)


def generate_excel(
    data: list,
    columns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    prefix: str = "report",
) -> Optional[str]:
    """Build Excel in memory, store bytes in Redis, return report_id.
    Returns None if data is empty or generation fails.
    The file is NEVER written to disk.
    
    Args:
        data: List of records (dicts)
        columns: Specific columns to include (if None, all except excluded)
        exclude_patterns: List of column name patterns to exclude (e.g., ['id', '_id', 'uuid', 'photo'])
        prefix: Report prefix for logging
    """
    logger.info(f"[report_service] generate_excel | records={len(data) if data else 0} prefix='{prefix}'")
    if not data:
        logger.warning("[report_service] No data — skipping report generation")
        return None
    try:
        logger.info(f"[report_service] Building DataFrame from {len(data)} records")
        df = pd.DataFrame(data)
        logger.info(f"[report_service] DataFrame shape: {df.shape} | columns={list(df.columns)}")

        # If specific columns requested, use them; otherwise filter out excluded columns
        if columns:
            available = [c for c in columns if c in df.columns]
            logger.info(f"[report_service] Columns requested={columns} available={available}")
            if available:
                df = df[available]
                logger.info(f"[report_service] DataFrame filtered to {len(available)} columns")
        else:
            # Auto-exclude columns matching patterns
            if exclude_patterns is None:
                exclude_patterns = ['id', '_id', 'uuid', 'photo', 'image', 'url', 'link']
            
            cols_to_exclude = []
            for col in df.columns:
                # Check if column name contains any exclude pattern (case-insensitive)
                if any(pattern.lower() in col.lower() for pattern in exclude_patterns):
                    cols_to_exclude.append(col)
            
            if cols_to_exclude:
                logger.info(f"[report_service] Auto-excluding columns: {cols_to_exclude}")
                df = df.drop(columns=cols_to_exclude)
                logger.info(f"[report_service] DataFrame after exclusion: {len(df.columns)} columns remain")

        # Write to in-memory buffer — never touches disk
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        file_bytes = buf.getvalue()
        logger.info(f"[report_service] Excel generated in memory | size={len(file_bytes)} bytes")

        # Store in Redis with TTL
        report_id = uuid.uuid4().hex
        redis_key = f"{REPORT_KEY_PREFIX}{report_id}"
        _redis.setex(redis_key, REPORT_TTL_SECONDS, file_bytes)
        logger.info(f"[report_service] Stored in Redis | key={redis_key} TTL={REPORT_TTL_SECONDS}s")

        # Return the download path — caller builds the full URL
        download_path = f"/report/download/{report_id}"
        logger.info(f"[report_service] Download path: {download_path}")
        return download_path

    except Exception as exc:
        logger.error(f"[report_service] Report generation failed: {exc}")
        return None


class ReportService:
    """Stateless helper used by ChatUsecase."""

    def __init__(self, db=None):
        # Kept for compatibility with callers that pass a DB session.
        self.db = db

    def generate(
        self,
        data,
        chat_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        tool_used: Optional[str] = None,
        columns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Optional[str]:
        logger.info(f"[report_service] ReportService.generate | records={len(data) if isinstance(data, list) else 0}")
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.info("[report_service] No list data — skipping report")
            return None
        logger.info("[report_service] Delegating to generate_excel")
        download_path = generate_excel(data, columns, exclude_patterns=exclude_patterns, prefix="chat_report")
        if not download_path:
            return None

        # ChatUsecase expects only the raw report_id here.
        report_id = download_path.rsplit("/", 1)[-1]
        logger.info(
            f"[report_service] Report generated | report_id={report_id} chat_id={chat_id} org={organization_id} tool={tool_used}"
        )
        return report_id
