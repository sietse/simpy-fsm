import simpy

from actor import Actor, process_name


class Car(Actor):
    """Like Car, but handles the resource itself instead of with a context
    manager."""

    def __init__(self, env, initial_state='driving', *,
            name, charging_station, driving_time, charging_time):
        self.name = name
        self.charging_station = charging_station
        self.driving_time = driving_time
        self.charging_time = charging_time
        super().__init__(env, initial_state)

    def driving(self):
        yield env.timeout(self.driving_time)
        print('%s arriving at %d' % (self.name, self.env.now))
        return self.awaiting_battery

    def awaiting_battery(self):
        self.charging_request = self.charging_station.request()
        yield self.charging_request
        print('%s starting to charge at %s' % (self.name, self.env.now))
        return self.charging

    def charging(self):
        try:
            yield env.timeout(self.charging_time)
            print('%s leaving the bcs at %s' % (self.name, self.env.now))
        finally:
            # import pudb
            # pudb.set_trace()
            self.charging_station.release(self.charging_request)
        return self.driving


if __name__ == '__main__':
    env = simpy.Environment()
    bcs = simpy.Resource(env, capacity=2)
    cars = [
        Car(env,
            name=process_name(i, of=4),
            charging_station=bcs,
            driving_time=i * 2,
            charging_time=5
        )
        for i in range(4)
    ]

    env.run(until=15)
