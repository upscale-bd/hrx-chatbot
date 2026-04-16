import requests
from common.logger import get_logger
from config.config import settings
from services.auth.hrx_auth import HRXAuthService

logger = get_logger("hrx_service")


class HRXService:
    @staticmethod
    def call(endpoint: str, method: str, body: dict):
        hrx_base_url = settings.HRX_BASE_URL.rstrip("/")
        url = f"{hrx_base_url}/{endpoint.lstrip('/')}"
        logger.info(f"[hrx_service] Calling HRX API | method={method.upper()} url={url}")
        logger.info(f"[hrx_service] Request params/body: {body}")

        # Build Authorization header
        headers = {"Content-Type": "application/json"}
        
        # Get token from cache ONLY (must be set via POST /auth/hrx-token)
        token = HRXAuthService.get_cached_token()
        
        if not token:
            logger.error("[hrx_service] ❌ No bearer token set! Use POST /auth/hrx-token to authorize first.")
            return {"error": "No authorization token. Call POST /auth/hrx-token first."}
        
        headers["Authorization"] = f"Bearer {token}"
        logger.info("[hrx_service] Bearer token attached to request")

        try:
            if method.upper() == "POST":
                logger.info("[hrx_service] Sending POST request")
                r = requests.post(url, json=body, headers=headers, timeout=30)
            else:
                logger.info("[hrx_service] Sending GET request")
                r = requests.get(url, params=body, headers=headers, timeout=30)

            logger.info(f"[hrx_service] Response status_code={r.status_code}")
            r.raise_for_status()
            raw = r.json()
            logger.info(f"[hrx_service] Raw response keys: {list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__}")

            # Unwrap HRX envelope: { success, message, data: { count, data: [...] } }
            if isinstance(raw, dict) and raw.get("success") is True:
                inner = raw.get("data", {})
                if isinstance(inner, dict) and "data" in inner:
                    records = inner["data"]
                    logger.info(f"[hrx_service] Unwrapped HRX envelope | count={inner.get('count')} records={len(records)}")
                    return records
                elif isinstance(inner, list):
                    logger.info(f"[hrx_service] HRX data is direct list | records={len(inner)}")
                    return inner
                else:
                    logger.info("[hrx_service] HRX data is a single object, wrapping in list")
                    return [inner] if inner else []
            elif isinstance(raw, dict) and raw.get("success") is False:
                error_msg = raw.get("message", "HRX returned success=false")
                logger.warning(f"[hrx_service] HRX API returned success=false: {error_msg}")
                return {"error": error_msg}
            else:
                # Response is already plain list or unknown format — return as-is
                logger.info(f"[hrx_service] Response not wrapped, returning raw | type={type(raw).__name__}")
                return raw

        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else "N/A"
            logger.error(f"[hrx_service] HTTP error [{method} {url}] status={status}: {exc}")
            return {"error": "upstream_http_error", "details": str(exc), "status": status}
        except requests.RequestException as exc:
            logger.error(f"[hrx_service] Request failed [{method} {url}]: {exc}")
            return {"error": "upstream_unreachable", "details": str(exc)}