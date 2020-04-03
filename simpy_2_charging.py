import simpy
import enum

from actor import FSM


class Signal(enum.Enum):
    drive = 0


class Car(FSM):

    def __init__(self, env, initial_state='charging'):
        super().__init__(env, initial_state)

    def charging(self):
        print('Car: start parking and charging at', self.env.now)
        charge_duration = 5
        try:
            yield self.env.timeout(charge_duration)
            return self.driving
        except simpy.Interrupt as interrupt:
            if interrupt.cause is Signal.drive:
                print("Car: rudely interrupted at {}!".format(self.env.now))
                return self.driving
            else:
                raise interrupt

    def driving(self):
        print('Car: start driving at', self.env.now)
        trip_duration = 2
        yield self.env.timeout(trip_duration)
        return self.charging


class Driver(FSM):

    def __init__(self, env, car, initial_state='impatient'):
        self.car = car
        super().__init__(env, initial_state)

    def impatient(self):
        yield self.env.timeout(3)
        print('Driver: I want to drive now')
        self.car.process.interrupt(Signal.drive)
        return None


if __name__ == '__main__':
    env = simpy.Environment()
    car = Car(env)
    driver = Driver(env, car)

    env.run(until=15)
