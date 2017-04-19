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
            'parking': self.parking(),
            'driving': self.driving(),
        }

    def process(self):
        state_name = 'parking'
        state = self.states[state_name]
        while True:
            try:
                yield next(state)
            except StopIteration as e:
                state_name = e.value
                state = self.states[state_name]
            except KeyboardInterrupt:
                return


if __name__ == '__main__':
    import pudb
    # pudb.set_trace()
    env = simpy.Environment()
    env.process(Car(env).process())
    env.run(until=15)
