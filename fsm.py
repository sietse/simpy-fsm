class FSM:
    def __init__(self, env: 'simpy.core.Environment', initial_state: str,
            activate=True):
        """
        Create a process for the instance, and add it to the env.
        """
        self.env = env
        # Eureka!! Lesson 5: if we don't automatically turn the generator into
        # a Simpy Process with env.process, then it can also function as a
        # substate if a higher-level state calls `yield from` on it.
        if activate:
            # Create a process; add it to the env; and make it accessible on self.
            self.process = env.process(self.main(initial_state))

    def main(self, initial_state: str):
        """
        Each actor is/has a single process. This process instantiates a
        generator for the current state, and yields from it -- `yield from`
        opens a two-way communication channel between the subgenerator (the
        state) and the actor process's runner (the simpy environment).

            def some_state(self):
                try:
                    # pass control to the Environment: this represents spending
                    # time in the current state
                    yield self.env.timeout(99)
                    # return the state to transition to when we are reactivated
                    return self.driving
                except simpy.Interrupt as interrupt:
                    # Catch interrupts and and act on them
                    if interrupt.cause is Signal.drive:
                        print("Car: rudely interrupted at {}!".format(self.env.now))
                        # Often, an interrupt results in a state transition.
                        return self.driving
                    else:
                        # Unknown signal
                        raise interrupt
                finally:
                    # Actions to take on exiting state
                    ...
        """
        state_func = getattr(self, initial_state)
        state = state_func()
        while True:
            state_func = (yield from state)
            if state_func is None:
                break
            state = state_func()


def process_name(i: int, of: int) -> str:
    """Return e.g. '| | 2 |': an n-track name with track `i` (here i=2) marked.

    This makes it easy to follow each process's log messages, because you just
    go down the line until you encounter the same number again.

    Example: The interleaved log of four processes that each simulate a car
    visiting a charging station. The processes have been named with
    `process_name()`, and their log messages start with their `self.name`.
    (Car #2 does not turn up in this snippet.)

        | | | 3 arriving at 6
        | 1 | | starting to charge at 7
        0 | | | starting to charge at 7
        | 1 | | leaving the bcs at 9
    """
    lines = ['|'] * of
    lines[i] = str(i)
    return ' '.join(lines)
