import simpy

from simpy_fsm.v1 import FSM, process_name

class Car(FSM):
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
        return self.charging

    def charging(self, data):
        with self.charging_station.request() as req:
            yield req

            # Charge the battery
            print("%s starting to charge at %s" % (self.name, self.env.now))
            yield env.timeout(self.charging_time)
            # BCS is the battery charging station
            print("%s leaving the bcs at %s" % (self.name, self.env.now))


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

    env.run(until=15)
