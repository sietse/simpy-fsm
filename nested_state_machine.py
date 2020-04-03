import simpy

from fsm import FSM



class TurnOn:
    """This class is used by as a signal/symbol: Turn a stoplight on."""
    pass


class TurnOff:
    """This class is used by as a signal/symbol: Turn a stoplight on."""
    pass


class Stoplight(FSM):
    """A state machine: a stoplight you can turn on and off."""

    def __init__(self, env, initial_state='off'):
        super().__init__(env, initial_state)

    def on(self):
        self.state = 'on'
        try:
            substate = StoplightOn(self, activate=False)
            # Lesson 1: yielding the process of a nested state machine (NSM)
            # runs the NSM, but it doesn't delegate to it: any Interrupt is
            # sent to us, not to the nested process.
            #
            # yield substate.process('green')

            # Lesson 4: Hooray this works!
            yield from substate._process('green')
        # Lesson 2: can't create custom Interrupt types, but can customize via
        # Interrupt.cause.
        except simpy.Interrupt as interrupt:
            if interrupt.cause is TurnOn:
                # Lesson 1 (cont'd): if we forward the interrupt to the NSM,
                # the program will end if the NSM does not handle the
                # interrupt. Which is a pity, because the entire point of
                # hierarchical state machines is that the child state does not
                # have write code for signals handled by their parent state.
                return self.on
            if interrupt.cause is TurnOff:
                return self.off

    def off(self):
        self.state = 'off'
        self.colour = None
        try:
            yield simpy.Timeout(self.env, 100)
            return self.off
        except simpy.Interrupt as interrupt:
            if interrupt.cause is TurnOn:
                return self.on
            if interrupt.cause is TurnOff:
                return self.off


class StoplightOn(FSM):
    """A state machine: A turned-on stoplight that cycles between
    green/yellow/red. These states are substates of `Stoplight.on`.
    """

    def __init__(self, parent, initial_state='green', activate=False):
        self.parent = parent
        super().__init__(parent.env, initial_state, activate)

    def green(self):
        self.parent.colour = 'green'
        yield simpy.Timeout(self.env, 3)
        return self.yellow

    def yellow(self):
        self.parent.colour = 'yellow'
        yield simpy.Timeout(self.env, 1)
        return self.red

    def red(self):
        self.parent.colour = 'red'
        yield simpy.Timeout(self.env, 4)
        return self.green


if __name__ == '__main__':
    env = simpy.Environment()
    stoplight = Stoplight(env)
    for i in range(2):
        env.run(until=env.now + 100)
        # Again, lesson 2: can't create custom Interrupt types, but can
        # customize via Interrupt.cause.
        stoplight.process.interrupt(TurnOn)
        print(f'{env.now}: {stoplight.state} ({stoplight.colour})')
        for i in range(12):
            env.run(until=env.now + 1)
            print(f'{env.now}: {stoplight.state} ({stoplight.colour})')
        stoplight.process.interrupt(TurnOff)
        print(f'{env.now}: {stoplight.state} ({stoplight.colour})')
        for i in range(12):
            env.run(until=env.now + 1)
            print(f'{env.now}: {stoplight.state} ({stoplight.colour})')
