# Behaviour is identical to simpy_3_resource.py. The difference in
# implementation: Awaiting a charging station + using it is not one
# state that starts with a context manager, but it is two separate
# states. awaiting_battery() awaits the slot; charging() takes the slot,
# charges, and releases the slot.

import simpy

from simpy_fsm import FSM, process_name

class Car(FSM):
    """Like Car, but handles the resource itself instead of with a context
    manager."""

    def __init__(
        self,
        env,
        initial_state="driving",
        *,
        name,
        charging_station,
        driving_time,
        charging_time
    ):
        self.name = name
        self.charging_station = charging_station
        self.driving_time = driving_time
        self.charging_time = charging_time
        super().__init__(env, initial_state)

    def driving(self, data):
        yield env.timeout(self.driving_time)
        print("%s arriving at %d" % (self.name, self.env.now))
        return self.awaiting_battery

    def awaiting_battery(self, data):
        # Wait for the charging station and acquire it
        self.charging_request = self.charging_station.request()
        yield self.charging_request
        print("%s starting to charge at %s" % (self.name, self.env.now))
        # Instead of invisibly passing `charging_request` via `self` to
        # the `charging` state, can we make the flow of data clearer
        # by making `charging_request` part of the thunk we return?
        # Something like this:
        #
        #     return (self.charging, charging_request)
        #
        # which fsm.trampoline would then handle appropriately.
        return self.charging

    def charging(self, data):
        # The charging station has been acquired;
        try:
            yield env.timeout(self.charging_time)
            # BCS is the battery charging station
            print("%s leaving the bcs at %s" % (self.name, self.env.now))
        finally:
            self.charging_station.release(self.charging_request)
        return None


if __name__ == "__main__":
    env = simpy.Environment()
    bcs = simpy.Resource(env, capacity=2)
    cars = [
        Car(
            env,
            name=process_name(i, of=4),
            charging_station=bcs,
            driving_time=i * 2,
            charging_time=5,
        )
        for i in range(4)
    ]

    env.run()
