from .celery_app import celery_app
from services.report.report_service import generate_excel
from common.logger import get_logger

logger = get_logger("report_worker")


@celery_app.task(name="worker.generate_report")
def generate_report_task(data, columns, prefix="report"):
    logger.info(f"[report_worker] generate_report_task received | records={len(data) if isinstance(data, list) else 0} prefix='{prefix}'")
    logger.info(f"[report_worker] Columns requested: {columns}")
    result = generate_excel(data, columns, prefix=prefix)
    if result:
        logger.info(f"[report_worker] Report ready | download_path={result}")
    else:
        logger.warning("[report_worker] Report generation returned None (empty data or error)")
    return result  # returns '/report/download/{report_id}' or None
