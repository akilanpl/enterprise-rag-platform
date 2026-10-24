import json
import logging

logger = logging.getLogger("enterprise_rag")


def log_request(request_id, route, status, duration):
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "route": route,
                "status": status,
                "duration_seconds": duration,
            }
        )
    )
