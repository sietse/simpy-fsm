import simpy


def old_car(env):
    while True:
        parking_duration = 2
        yield env.timeout(parking_duration)
        driving_duration = 5
        yield env.timeout(driving_duration)


class Car:
    def __init__(self, env):
        self.env = env

    def process(self):
        # This is a trampoline function
        state = self.parking()
        while True:
            try:
                # run the generator
                yield next(state)
            except StopIteration as e:
                # The state has ended, and told us what state to transition to.
                # Create a generator for the new state
                state = e.value()

    def parking(self, data):
        print("parking... at", self.env.now)
        parking_duration = 5
        yield self.env.timeout(parking_duration)
        return self.driving

    def driving(self, data):
        print("driving... at", self.env.now)
        driving_duration = 2
        yield self.env.timeout(driving_duration)
        return self.parking


if __name__ == "__main__":
    env = simpy.Environment()
    env.process(Car(env).process())
    env.run(until=15)
