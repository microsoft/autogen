import json
import logging
import os
import uuid

from posthog import Posthog

import embedchain
from embedchain.constants import CONFIG_DIR, CONFIG_FILE


class AnonymousTelemetry:
    def __init__(self, host="https://app.posthog.com", enabled=True):
        self.project_api_key = "phc_PHQDA5KwztijnSojsxJ2c1DuJd52QCzJzT2xnSGvjN2"
        self.host = host
        self.posthog = Posthog(project_api_key=self.project_api_key, host=self.host)
        self.user_id = self._get_user_id()
        self.enabled = enabled

        # Check if telemetry tracking is disabled via environment variable
        if "EC_TELEMETRY" in os.environ and os.environ["EC_TELEMETRY"].lower() not in [
            "1",
            "true",
            "yes",
        ]:
            self.enabled = False

        if not self.enabled:
            self.posthog.disabled = True

        # Silence posthog logging
        posthog_logger = logging.getLogger("posthog")
        posthog_logger.disabled = True

    @staticmethod
    def _get_user_id():
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                if "user_id" in data:
                    return data["user_id"]

        user_id = str(uuid.uuid4())
        with open(CONFIG_FILE, "w") as f:
            json.dump({"user_id": user_id}, f)
        return user_id

    def capture(self, event_name, properties=None):
        default_properties = {
            "version": embedchain.__version__,
            "language": "python",
            "pid": os.getpid(),
        }
        properties.update(default_properties)

        try:
            self.posthog.capture(self.user_id, event_name, properties)
        except Exception:
            logging.exception(f"Failed to send telemetry {event_name=}")
