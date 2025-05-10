import threading
import uuid
from datetime import datetime, timedelta
from enum import Enum, auto
from abc import ABC, abstractmethod


class SpotType(Enum):
    MOTORCYCLE = auto()
    CAR = auto()
    BUS = auto()


class Vehicle(ABC):
    def __init__(self, plate: str):
        self.vehicle_id = plate

    @abstractmethod
    def required_spot_type(self) -> SpotType:
        """Return the SpotType required for this vehicle."""
        pass


class Car(Vehicle):
    def required_spot_type(self) -> SpotType:
        return SpotType.CAR


class Bus(Vehicle):
    def required_spot_type(self) -> SpotType:
        return SpotType.BUS


class Motorcycle(Vehicle):
    def required_spot_type(self) -> SpotType:
        return SpotType.MOTORCYCLE


class VehicleFactory:
    @staticmethod
    def create(vtype: str, plate: str) -> Vehicle:
        """Factory method to create a Vehicle subclass based on type string."""
        mapping = {
            'car': Car,
            'bus': Bus,
            'motorcycle': Motorcycle
        }
        cls = mapping.get(vtype.lower())
        if cls is None:
            raise ValueError(f"Unknown vehicle type: {vtype}")
        return cls(plate)


class ParkingSpot:
    def __init__(self, spot_id: str, spot_type: SpotType):
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.is_occupied = False
        self.lock = threading.Lock()

    def assign_spot(self) -> bool:
        """Atomically assign this spot if free, returning True on success."""
        with self.lock:
            if not self.is_occupied:
                self.is_occupied = True
                return True
        return False

    def release_spot(self) -> None:
        """Atomically release this spot."""
        with self.lock:
            self.is_occupied = False


class Level:
    def __init__(self, level_id: int, spots_per_type: dict[SpotType, int]):
        self.level_id = level_id
        self.spots: list[ParkingSpot] = []
        for st, count in spots_per_type.items():
            for i in range(count):
                sid = f"L{level_id}-{st.name[:1]}{i + 1}"
                self.spots.append(ParkingSpot(sid, st))

    def find_and_assign_spot(self, vehicle: Vehicle) -> ParkingSpot | None:
        """Find the first free spot matching the vehicle's requirement and assign it."""
        needed = vehicle.required_spot_type()
        for spot in self.spots:
            if spot.spot_type == needed and spot.assign_spot():
                return spot
        return None


class Ticket:
    def __init__(self, vehicle: Vehicle, spot: ParkingSpot):
        self.ticket_id = str(uuid.uuid4())
        self.vehicle_id = vehicle.vehicle_id
        self.spot_id = spot.spot_id
        self.entry_time = datetime.now()


class Receipt:
    def __init__(self, ticket: Ticket, exit_time: datetime, amount: float):
        self.ticket_id = ticket.ticket_id
        self.exit_time = exit_time
        self.amount_due = amount

    def __str__(self) -> str:
        return f"Receipt({self.ticket_id}): ${self.amount_due:.2f}"


class ParkingLot:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, levels_config: dict[SpotType, int] | None = None):
        if hasattr(self, '_initialized'):
            return
        default_config = {SpotType.CAR: 10, SpotType.BUS: 2, SpotType.MOTORCYCLE: 5}
        config = levels_config or default_config
        self.levels = [Level(i + 1, config) for i in range(2)]
        self.tickets: dict[str, Ticket] = {}
        self._initialized = True

    def park_vehicle(self, vehicle: Vehicle) -> Ticket:
        """Park a vehicle, returning a Ticket or raising if full."""
        for level in self.levels:
            spot = level.find_and_assign_spot(vehicle)
            if spot:
                ticket = Ticket(vehicle, spot)
                self.tickets[ticket.ticket_id] = ticket
                return ticket
        raise Exception("Parking Full")

    def exit_vehicle(self, ticket_id: str) -> Receipt:
        """Release the parked vehicle by ticket ID and return a Receipt."""
        ticket = self.tickets.pop(ticket_id, None)
        if not ticket:
            raise KeyError("Invalid Ticket")

        exit_time = datetime.now()
        hours = (exit_time - ticket.entry_time) / timedelta(hours=1)
        spot_type = self.get_spot_type(ticket.spot_id)
        rates = {SpotType.CAR: 2.0, SpotType.BUS: 5.0, SpotType.MOTORCYCLE: 1.0}
        rate = rates.get(spot_type, 0)
        amount = max(1, hours) * rate

        # Release the spot
        for level in self.levels:
            for spot in level.spots:
                if spot.spot_id == ticket.spot_id:
                    spot.release_spot()
                    break

        return Receipt(ticket, exit_time, amount)

    def get_spot_type(self, spot_id: str) -> SpotType | None:
        """Lookup the SpotType by spot ID."""
        for level in self.levels:
            for spot in level.spots:
                if spot.spot_id == spot_id:
                    return spot.spot_type
        return None


# Demo usage
if __name__ == '__main__':
    lot = ParkingLot({SpotType.CAR: 5, SpotType.BUS: 1, SpotType.MOTORCYCLE: 3})
    vehicle = VehicleFactory.create('car', 'ABC123')
    ticket = lot.park_vehicle(vehicle)
    print(f"Parked at: {ticket.spot_id}  Ticket: {ticket.ticket_id}")

    import time
    time.sleep(1)

    receipt = lot.exit_vehicle(ticket.ticket_id)
    print(receipt)
