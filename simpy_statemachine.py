import simpy
import types


class Car:

    def to_generator(self, f):
        coro = f()
        f.send(None)

    def parking(self):
        parking_duration = 5
        yield self.env.timeout(parking_duration)
        return 'driving'

    def driving(self):
        driving_duration = 2
        yield self.env.timeout(driving_duration)
        return 'parking'

    def __init__(self, env):
        self.env = env
        states = {
            'parking': self.parking,
            'driving': self.driving,
        }
        next_state_name = 'parking'
        while True:
            next_state = states[next_state_name]()
            next_state_name = next_state.send(None)

if __name__ == '__main__':
    env = simpy.Environment()
    env.process(Car(env))
    env.run(until=15)
