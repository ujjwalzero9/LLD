**Parking Lot System Design**

---

## Requirements

1. **Multiple Levels:** A parking lot can have one or more levels (floors).
2. **Multiple Spots per Level:** Each level contains multiple parking spots.
3. **Vehicle Categories:** The lot supports different vehicle types (e.g., cars, buses, motorcycles), with dedicated spot sizes for each category.
4. **Availability Lookup:** Users can query available spots filtered by vehicle type.
5. **Parking Operations:** Users can park and unpark vehicles.
6. **Ticket Issuance:** Upon entry, the system issues a ticket recording the assigned level, spot number, and entry timestamp.
7. **Fare Calculation:** Upon exit, the system calculates and provides the total parking fee based on duration and spot type.

---

## Core Classes & Design Structure

1. **ParkingLot (Singleton)**

   * Ensures a single instance throughout the application.
   * Manages all levels, tickets, and global operations.

2. **Level**

   * Attributes: `levelId` (floor number), `spots` (collection of ParkingSpot).
   * Responsibilities: Track occupancy status and delegate spot assignments.

3. **ParkingSpot**

   * Attributes: `spotId`, `spotType` (enum: CAR, BUS, MOTORCYCLE), `isOccupied` (bool).
   * Methods: `assignSpot()`, `releaseSpot()`.

4. **Vehicle (Abstract)**

   * Defines common interface: `vehicleId`, `requiredSpotType()`.
   * Subclasses: `Car`, `Bus`, `Motorcycle`.

5. **VehicleFactory (Factory Pattern)**

   * Creates appropriate `Vehicle` instances based on input type.

6. **Ticket**

   * Attributes: `ticketId`, `vehicleId`, `spotId`, `entryTime`.
   * Used for tracking active parking sessions.

7. **Receipt**

   * Attributes: `ticketId`, `exitTime`, `amountDue`.
   * Generates final billing details.

---

## Relationships & Multiplicity

* **ParkingLot** 1 ↔ \* **Level**
* **Level** 1 ↔ \* **ParkingSpot**
* **Vehicle** (abstract) ←|-- **Car**, **Bus**, **Motorcycle**
* **Ticket** 1 ↔ 1 **Receipt**

---

## UML Class Diagram

Below is a simplified ASCII‐style UML diagram illustrating the main classes and their relationships:

```
        <<interface>>       Vehicle
        -------------------------------
        + vehicleId: String
        + requiredSpotType(): SpotType
                    ^
        ------------|--------------
        |           |             |
      +---+       +---+       +-----------+
      |Car|       |Bus|       |Motorcycle |
      +---+       +---+       +-----------+

+----------------------+    1      *    +----------------+
|      ParkingLot      |----------------|      Level     |
|----------------------|                +----------------+
| - levels: List<Level>|                | - levelId      |
| - tickets: Map<…>    |                | - spots: List<Spot> |
| + parkVehicle(v)     |                +----------------+
| + exitVehicle(id)    |                       |
+----------------------+                       |
         | uses                                   | 1      *
         v                                        v
     +---------------+                   +----------------+
     |    Ticket     |-------------------|   ParkingSpot  |
     +---------------+     assigns 1    +----------------+
     | - ticketId    |                   | - spotId      |
     | - vehicleId   |                   | - spotType    |
     | - spotId      |                   | - isOccupied  |
     | - entryTime   |                   +----------------+
     +---------------+                           |
             | 1                                 |
             v                                   |
     +---------------+                          |
     |    Receipt    |<-------------------------+
     +---------------+
     | - exitTime    |
     | - amountDue   |
     +---------------+
```

This ASCII diagram captures:

* **Vehicle** as an interface implemented by `Car`, `Bus`, and `Motorcycle`.
* **ParkingLot** aggregating multiple **Level** instances.
* Each **Level** containing multiple **ParkingSpot**s.
* **Ticket** issued for a single spot and resulting in one **Receipt** upon exit.

## Design Patterns & Considerations

* **Singleton:** Ensures one global `ParkingLot` instance.
* **Factory:** `VehicleFactory` decouples vehicle creation from usage.
* **Thread Safety:** Use locks around spot assignment/release in multithreaded environments.
* **Extensibility:** Easily add new vehicle types, spot types, or pricing strategies.
* **Pricing Strategy (Optional):** Inject different `PricingStrategy` implementations for variable rate calculations.

---

## Example Python Implementation

```python
import threading
import uuid
from datetime import datetime, timedelta
from enum import Enum, auto


class SpotType(Enum):
    MOTORCYCLE = auto()
    CAR = auto()
    BUS = auto()


class Vehicle:
    def __init__(self, plate):
        self.vehicle_id = plate
    def required_spot_type(self):
        raise NotImplementedError


class Car(Vehicle):
    def required_spot_type(self): return SpotType.CAR

class Bus(Vehicle):
    def required_spot_type(self): return SpotType.BUS

class Motorcycle(Vehicle):
    def required_spot_type(self): return SpotType.MOTORCYCLE


class VehicleFactory:
    @staticmethod
    def create(vtype, plate):
        return {
            'car': Car,
            'bus': Bus,
            'motorcycle': Motorcycle
        }.get(vtype.lower(), Vehicle)(plate)


class ParkingSpot:
    def __init__(self, spot_id, spot_type):
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.is_occupied = False
        self.lock = threading.Lock()

    def assign_spot(self):
        with self.lock:
            if not self.is_occupied:
                self.is_occupied = True
                return True
        return False

    def release_spot(self):
        with self.lock:
            self.is_occupied = False


class Level:
    def __init__(self, level_id, spots_per_type):
        self.level_id = level_id
        self.spots = []
        for st, count in spots_per_type.items():
            for i in range(count):
                sid = f"L{level_id}-{st.name[:1]}{i+1}"
                self.spots.append(ParkingSpot(sid, st))

    def find_and_assign_spot(self, vehicle):
        rtype = vehicle.required_spot_type()
        for spot in self.spots:
            if spot.spot_type == rtype and spot.assign_spot():
                return spot
        return None


class Ticket:
    def __init__(self, vehicle, spot):
        self.ticket_id = str(uuid.uuid4())
        self.vehicle_id = vehicle.vehicle_id
        self.spot_id = spot.spot_id
        self.entry_time = datetime.now()


class Receipt:
    def __init__(self, ticket, exit_time, amount):
        self.ticket_id = ticket.ticket_id
        self.exit_time = exit_time
        self.amount_due = amount
    def __str__(self):
        return f"Receipt({self.ticket_id}): ${self.amount_due:.2f}"


class ParkingLot:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, levels_config=None):
        if hasattr(self, '_initialized'): return
        self.levels = [Level(i+1, levels_config or {SpotType.CAR:10, SpotType.BUS:2, SpotType.MOTORCYCLE:5}) for i in range(2)]
        self.tickets = {}
        self._initialized = True

    def park_vehicle(self, vehicle):
        for lvl in self.levels:
            spot = lvl.find_and_assign_spot(vehicle)
            if spot:
                ticket = Ticket(vehicle, spot)
                self.tickets[ticket.ticket_id] = ticket
                return ticket
        raise Exception("Parking Full")

    def exit_vehicle(self, ticket_id):
        ticket = self.tickets.pop(ticket_id, None)
        if not ticket:
            raise KeyError("Invalid Ticket")
        exit_time = datetime.now()
        duration = (exit_time - ticket.entry_time) / timedelta(hours=1)
        rate = {SpotType.CAR:2, SpotType.BUS:5, SpotType.MOTORCYCLE:1}[self.get_spot_type(ticket.spot_id)]
        amount = max(1, duration) * rate
        # release spot
        for lvl in self.levels:
            for spot in lvl.spots:
                if spot.spot_id == ticket.spot_id:
                    spot.release_spot()
        return Receipt(ticket, exit_time, amount)

    def get_spot_type(self, spot_id):
        for lvl in self.levels:
            for spot in lvl.spots:
                if spot.spot_id == spot_id:
                    return spot.spot_type
        return None

# Demo
if __name__ == '__main__':
    lot = ParkingLot({SpotType.CAR:5, SpotType.BUS:1, SpotType.MOTORCYCLE:3})
    v = VehicleFactory.create('car','ABC123')
    t = lot.park_vehicle(v)
    print("Parked at:", t.spot_id, "Ticket:", t.ticket_id)
    # simulate wait
    import time; time.sleep(1)
    r = lot.exit_vehicle(t.ticket_id)
    print(r)
```
