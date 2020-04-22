import simpy


def old_car(env):
    while True:
        parking_duration = 2
        yield env.timeout(parking_duration)
        driving_duration = 5
        yield env.timeout(driving_duration)


class Transition(Exception):
    def __init__(self, to):
        self.to = to


class Car:
    def __init__(self, env):
        self.env = env

    def _process(self):
        # This is a trampoline function
        state_generator = self.parking()
        while True:
            self.state = state_generator.__name__
            try:
                # run the generator
                yield next(state_generator)
            except Transition as e:
                # The state has ended, and told us what state to transition to.
                state_generator = e.to()

    def parking(self):
        parking_duration = 5
        yield self.env.timeout(parking_duration)
        raise Transition(self.driving)

    def driving(self):
        driving_duration = 2
        yield self.env.timeout(driving_duration)
        raise Transition(self.parking)


if __name__ == "__main__":
    env = simpy.Environment()
    car = Car(env)
    car.process = env.process(car._process())
    while env.now < 15:
        env.step()
        print(env.now, car.state)
