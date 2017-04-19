import simpy
import types


# * a dict of generators (not generator functions) to dip into


class Car:

    def to_generator(self, f):
        coro = f()
        f.send(None)
        return f

    def parking(self):
        print('parking... at', self.env.now)
        parking_duration = 5
        yield self.env.timeout(parking_duration)
        return 'driving'

    def driving(self):
        print('driving... at', self.env.now)
        driving_duration = 2
        yield self.env.timeout(driving_duration)
        return 'parking'

    def __init__(self, env):
        self.env = env
        self.states = {
            'parking': self.parking,
            'driving': self.driving,
        }

    def process(self):
        # This is a trampoline function
        state_name = 'parking'
        # create a generator for the initial state
        state = self.states[state_name]()
        while True:
            try:
                # run the generator
                yield next(state)
            except StopIteration as e:
                # The state has ended;
                # create a generator for the new state
                state = self.states[e.value]()
            except KeyboardInterrupt:
                return


if __name__ == '__main__':
    env = simpy.Environment()
    env.process(Car(env).process())
    env.run(until=15)
