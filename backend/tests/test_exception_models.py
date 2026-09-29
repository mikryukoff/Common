from backend.app.application.exceptions import UnauthorizedError, UserNotFoundError
from backend.app.shared.exceptions import ApplicationError, TooManyRequestsError


def test_shared_and_application_errors_share_base() -> None:
    assert issubclass(UnauthorizedError, ApplicationError)
    assert issubclass(TooManyRequestsError, ApplicationError)
    assert issubclass(UserNotFoundError, ApplicationError)
    assert UserNotFoundError(3).error_code == "user_not_found"
    assert UnauthorizedError("x").status_code == 401
