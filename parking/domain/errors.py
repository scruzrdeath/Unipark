"""Domain errors. Pure Python, no framework dependencies."""


class DomainError(Exception):
    """Base class for all business-rule violations."""


class SpotNotFound(DomainError):
    pass


class ReservationNotFound(DomainError):
    pass


class SpotNotAvailable(DomainError):
    """The spot cannot be reserved because it is not FREE."""


class InvalidTransition(DomainError):
    """A state change that the business rules do not allow."""


class UserAlreadyHasReservation(DomainError):
    pass


class ReservationExpired(DomainError):
    pass


class ExternalServiceUnavailable(DomainError):
    """An external API failed (after retries) or could not be reached."""


class CircuitOpen(ExternalServiceUnavailable):
    """The circuit breaker is open: the call was rejected without trying."""


class UnknownDataSource(DomainError):
    pass


class InvalidQuery(DomainError):
    pass
