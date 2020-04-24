from types import SimpleNamespace
from typing import Callable, Generator, TypeVar, Any, Optional, Iterator

import simpy  # Only used for type annotations


# Create a few helper aliases to prevent recursive type definitions:
Data = Any

FsmGen = Generator[simpy.Event, Any, Any]
FsmGenFunc = Callable[[Data], FsmGen]


def _trampoline(data: Data, initial_state: FsmGenFunc) -> FsmGen:
    """Tie multiple subgenerators into one generator that passes control
    between them.

    The trampoline generator starts by yielding from the first
    subgenerator; when that subgenerator is done, it `return`s the next
    generator function to yield from. This lets you write a multi-state
    process as multiple subgenerators, one per state, that transition into
    each other.

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

    Example usage:

        SimpleNamespace(count=1)

        def f1(data):
            yield "One"
            data.count += 1
            if 7 < data.count:
                return
            return f2

        def f2(data):
            yield "Two"
            data.count += 2
            return f1

        process = _trampoline(None, f1)
        # yields "One", "Two", "One", ...; stops after the counter reaches 7
    """
    state_generator: FsmGen = initial_state(data)
    while True:
        # Inside the brackets: `yield from` connects the state's generator
        # directly to our process's driver, a Simpy Environment.
        #
        # Eventually, the generator will `return`; at that point, control
        # returns here, and we use the return value as the next state function.
        state_func: Optional[FsmGenFunc] = (yield from state_generator)
        if state_func is None:
            break
        state_generator: FsmGen = state_func(data)  # type: ignore


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

    def __init__(self, env: "simpy.core.Environment", initial_state: str, data=None):
        """Init state machine instance, and init its Process as
        `self.process`.
        """

        self.env = env
        # Create `self.data` as a public handle of the `data` object
        self.data = data if data is not None else SimpleNamespace()
        # Create a process; add it to the env; and make it accessible on self.
        self.process = env.process(
            _trampoline(data=self.data, initial_state=getattr(self, initial_state))
        )


class SubstateFSM:
    def __init__(self, env: "simpy.core.Environment", initial_state: str, data):
        """Init sub-state machine instance, and init its generator as
        `self.generator`.

        data: Any
            The parent's `data` object
        """

        self.env = env
        # Create our generator, and make it accessible on self.
        self.generator = _trampoline(
            data=data, initial_state=getattr(self, initial_state)
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
    lines = ["|"] * of
    lines[i] = str(i)
    return " ".join(lines)
