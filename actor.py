class Actor:
    def __init__(self, env, initial_state):
        """
        Create a process for the instance, and add it to the env.
        """
        self.env = env
        # Create a process; add it to the env; and make it accessible on self.
        self.process = env.process(self._process(initial_state))

    def _process(self, initial_state):
        """
        Each actor is/has a single process. This process instantiates a
        generator for the current state, and yields from it -- `yield from`
        opens a two-way communication channel between the subgenerator (the
        state) and the actor process's runner (the simpy environment).

            def some_state(self):
                try:
                    # pass control to the Environment
                    yield self.env.timeout()
                    # return the state to transition to
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
