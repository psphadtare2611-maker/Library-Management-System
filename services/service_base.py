# ============================================================================
# services/service_base.py
# ----------------------------------------------------------------------------
# SERVICE BASE — shared foundation for every service class.
#
# All services return the same "response envelope" so the UI can treat every
# call the same way:
#
#     {"success": bool, "message": str, "data": <result or None>}
#
# Centralizing it here (instead of copying a _response() into each service)
# keeps a single source of truth and follows the DRY principle: if the
# envelope ever changes, it changes in exactly one place.
# ============================================================================


class ServiceBase:
    """Base class providing the standard service response envelope."""

    @staticmethod
    def _response(success, message, data=None):
        """
        Build the standard response dict shared by every service method.

        success : True if the operation succeeded.
        message : a short, user-facing message describing the outcome.
        data    : the payload (model, list, id, dict) or None.
        """
        return {"success": success, "message": message, "data": data}
