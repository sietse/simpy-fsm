import simpy

class Car(object):
    def __init__(self, env):
        self.env = env
        self.action = env.process(self.run())

    def run(self):
        while True:
            print('Car: Start parking and charging at %d' % self.env.now)
            charge_duration = 5
            # We may get interrupted while charging the battery
            try:
                yield self.env.process(self.charge(charge_duration))
            except simpy.Interrupt:
                # When we received an interrupt, we stop charging and
                # switch to the "driving" state
                print('Car: Was interrupted at %d. Hope, the battery is full enough ...' % self.env.now)

            print('Car: Start driving at %d' % self.env.now)
            trip_duration = 2
            yield self.env.timeout(trip_duration)

    def charge(self, duration):
        yield self.env.timeout(duration)


def driver(env, car):
    yield env.timeout(3)
    print("Driver: I want to drive now")
    car.action.interrupt()


if __name__ == '__main__':
    env = simpy.Environment()
    car = Car(env)
    env.process(driver(env, car))

    env.run(until=15)