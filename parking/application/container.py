from dataclasses import dataclass
from typing import Optional

from parking.application.open_data_service import OpenDataService
from parking.application.services import (
    AccessService,
    OccupancyService,
    ReservationService,
    SensorService,
)


@dataclass
class Services:
    """Bundle of use-case services handed to the API (built in the composition root)."""
    reservations: ReservationService
    access: AccessService
    sensors: SensorService
    occupancy: OccupancyService
    open_data: Optional[OpenDataService] = None
