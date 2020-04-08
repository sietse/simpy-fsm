from types import SimpleNamespace

class FSM:
    """To write a Simpy process in finite state machine style, inherit from
    this class.

    This is how you define such a class:

    >>> class Car(FSM):
    >>>     '''Drive for 1 hour, park for 11 hours, repeat'''
    >>>
    >>>     def driving(self, data):
    >>>         yield self.env.Timeout(1)
    >>>         data.n_trips = getattr(data, 'n_trips', 0) + 1
    >>>         return self.parked
    >>>
    >>>     def self.parked(self, data)
    >>>         try:
    >>>             yield self.env.timeout(11)
    >>>             return self.driving
    >>>         except simpy.Interrupt as interrupt:
    >>>             if interrupt.cause == 'Get driving':
    >>>                 return self.driving

    This is how you use it:

    >>> import simpy
    >>> env = simpy.Environment
    >>> car1 = Car(env, initial_state='parked')  # also creates a Simpy process
    >>> env.run(until=13)
    >>> car1.data.n_trips
    1
    >>> car1.process.interrupt('Get driving') # interrupt the Simpy process
    >>> env.run(until=15)
    >>> car1.data.n_trips
    2
    """

    def __init__(self, env: 'simpy.core.Environment', initial_state: str,
            data=None, activate=True):
        """Create state machine instance, and create its Process as
        `self.process`.
        """

        self.env = env
        self.data = data if data is not None else SimpleNamespace()
        # Eureka!! Lesson 5: if we don't automatically turn the generator into
        # a Simpy Process with env.process, then it can also function as a
        # substate if a higher-level state calls `yield from` on it.
        if activate:
            # Create a process; add it to the env; and make it accessible on self.
            self.process = env.process(self._trampoline(
                data=self.data,
                initial_state=initial_state
            ))

    def _trampoline(self, data, initial_state: str):
        """Create this state machine's generator.

        You can pass the resulting generator to Simpy's `env.process(...)` to
        create a corresponding Simpy Process.

        If this FSM represents substates in a hierarchical state machine, the
        higher-level state can yield from the generator to pass control to this
        substatemachine. `yield from substate_fsm._trampoline()`

        How this _trampoline() method works:
        - It's a generator, so it can be passed to `env.process`.
        - It delegates to the subgenerator (the current state method) via
          `yield from state()`. This statement opens a two-way communication
          channel between the subgenerator and Simpy's env simulation-runner.
          When a state yields, it yields control to the Simpy environment.
        - When a state is done, it can `return self.my_next_state` this returns
          control to the _trampoline() function, which delegates to the new
          subgenerator.

        Example structure:
        """
        state_func = getattr(self, initial_state)
        state = state_func(data)
        while True:
            state_func = (yield from state)
            if state_func is None:
                break
            state = state_func(data)


class SubstateFSM(FSM):

    def __init__(self, env: 'simpy.core.Environment', initial_state: str,
            data=None):
        """Create state machine instance, and create its Process as
        `self.process`.
        """

        self.env = env
        # Create `self.data` as a public handle of the `data` object
        self.data = data if data is not None else SimpleNamespace()
        self.generator = self._trampoline(
            data=self.data,
            initial_state=initial_state
        )


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
