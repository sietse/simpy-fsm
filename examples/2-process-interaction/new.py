import simpy

from simpy_fsm import FSM


class Car(FSM):
    def __init__(self, env, initial_state="charging"):
        super().__init__(env, initial_state)

    def charging(self, data):
        print("Car: start parking and charging at %d" % self.env.now)
        charge_duration = 5
        # We may get interrupted while charging the battery
        try:
            yield self.env.timeout(charge_duration)
            return self.driving
        except simpy.Interrupt as interrupt:
            # When we received an interrupt, we stop charging and
            # switch to the "driving" state
            print('Car: Was interrupted at %d. Hope, the battery is full enough ...' % self.env.now)
            return self.driving

    def driving(self, data):
        print('Car: Start driving at %d' % self.env.now)
        trip_duration = 2
        yield self.env.timeout(trip_duration)
        return self.charging


class Driver(FSM):
    def __init__(self, env, car, initial_state="impatient"):
        self.car = car
        super().__init__(env, initial_state)

    def impatient(self, data):
        yield self.env.timeout(3)
        print("Driver: I want to drive now")
        self.car.process.interrupt(Signal.drive)
        return None


if __name__ == "__main__":
    env = simpy.Environment()
    car = Car(env)
    driver = Driver(env, car)

    env.run(until=15)
