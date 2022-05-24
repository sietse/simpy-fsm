import simpy

from simpy_fsm.v1 import FSM, process_name

class Car:

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
        self.state = initial_state
        self.env = env
        self.process = self.env.process(self.run())

    def run(self):
        while True:
            if self.state == 'driving':
                yield env.timeout(self.driving_time)
                print("%s arriving at %d" % (self.name, self.env.now))
                self.state = 'awaiting_battery'

            elif self.state == 'awaiting_battery':
                self.charging_request = self.charging_station.request()
                yield self.charging_request
                self.state = 'charging'

            elif self.state == 'charging':
                print("%s starting to charge at %s" % (self.name, self.env.now))
                yield env.timeout(self.charging_time)
                print("%s leaving the bcs at %s" % (self.name, self.env.now))
                self.charging_station.release(self.charging_request)
                self.state = 'driving'
            else:
                raise Exception(f'Invalid state: {self.state}')


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

    env.run(until=200_000)
