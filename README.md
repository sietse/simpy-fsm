## Simpy and Finite State Machines.

This repository explores using continuation passing style to break complex Simpy processes into flat (or hierarchical) state machines.
The resulting code has one method per state, and uses a trampoline function to compose the methods into a single process.

The more states a Simpy process has, and the more complicated the transition paths
between them, the more you're going to get out of switching to state machine
notation.

The purpose of this repository is to explore the design space for a finite state machine class and/or trampoline function that takes care of
- Exposing the current state for inspection
- Passing data from state to state
- Making sure the two items above work for hierarchical state machines, too.

Compatibility: Most of the repository needs Python >= 3.3, because that's when using `yield` and `return` in the same function was introduced. The design at `examples/standalone_example.py`, however, works with Python 2.

## What can I find in this repository?

- `simpy_fsm/`: installed with `pip install PATH_TO_REPO_ROOT/setup.py`, use with `from simpy_fsm import FSM, SubstateFSM`.
- `examples/standalone_example.py`: a small self-contained example file that contains both an example state machine _and_ the definition of its a trampoline function.
- `examples/hierarchical_fsm.py`: this example shows we can also write hierarchical FSMs by implementing a stoplight that has Red/Yellow/Green as substates of On.
- `examples/{other folders}` Various examples from the [simpy docs](https://simpy.readthedocs.io/en/4.0.1/simpy_intro/index.html), both the original code and the FSM-style code. For comparison purposes.
- `worklog.md` -- my working notes. Used to be README.md, until I decided to publish, at which point I thought a tidier front page might be a good idea.

## Example

Here is an example

```python
import simpy

def old_car(env):
    while True:
        parking_duration = 2
        yield env.timeout(parking_duration)
        driving_duration = 5
        yield env.timeout(driving_duration)

env = simpy.Environment()
env.process(old_car())
env.run(until=15)
```

into this:

```python
import simpy
from simpy_fsm import FSM

class Car(FSM):
    def parking(self):
        parking_duration = 5
        yield self.env.timeout(parking_duration)
        return self.driving

    def driving(self):
        driving_duration = 2
        yield self.env.timeout(driving_duration)
        return self.parking

env = simpy.Environment()
car = Car(env, 'parking')
env.run(until=15)
```


## How does it work?

The core trampoline function is so short that we can reproduce it here in its entirety.
It is a generator function: calling it returns a generator, so a Simpy environment can use it as a process.
The generator starts by yielding from the first state's subgenerator; when that subgenerator is done, it `return`s the next generator function to yield from.
This lets you write a multi-state process as multiple subgenerators, one per state, that transition into each other.

In the car example above, starting the trampoline and creating a Simpy process is handled by the FSM superclass.

```python
def trampoline(data, initial_state):
    state_generator = initial_state(data)
    while True:
        # Inside the brackets: `yield from` connects the state's generator
        # directly to our process's driver, a Simpy Environment.
        #
        # Eventually, the generator will `return`; at that point, control
        # returns here, and we use the return value as the next state function.
        state_func = (yield from state_generator)
        if state_func is None:
            break
        state_generator = state_func(data)
```


## Open design questions

- How shall we make sure that a nested FSM does not overwrite its parent's `state` variable, but appends the substate to the `state` list?

- Should the trampoline function always update the `obj.state` variable, or should we also offer a minimalist FSM class for people who Want To Go Fast?

- Should the trampoline function only be used as part of the FSM class, or should we make it public for people who want to compose multiple generators but don't want a class?

- How to pass data around / what should the signature of every state be?
  - `mystate(self) -> next_state`: pass data by mutating self; for CSMs (child state machines), parent sets `nsm.parent = self`.
  - `mystate(self, obj) -> next_state`: `obj` is the object representing the process/entity/actor: for top-level FSMs `obj` is `self`, but for CSMs `obj` is `parent`
  - `mystate(self, data) -> next_state`: usually `obj` is `self`, but for CSMs `obj` is `parent`
  - `mystate(self, arg1, arg2, kwarg3=...) -> next_state, next_state_args, next_state_kwargs`

- Should we use `return self.next_state` or `raise Transition(self.next_state)`?
  The former is less noisy, the latter is Python 2-compatible.

- Should we choose `yield from mysubstate.generator` or `yield from mysubstate`?
  In other words: should the `mysubstate` instance _have_ a generator, or _be_ a generator?

- TODO: benchmark the relative performance of a Simpy function, an FSM instance, and a DIY 'trampoline + generator functions' construction with no object.

- TODO: benchmark the relative performance of an FSM instance with 4 states, and a hierarchical state machine where some of the states are moved onto a child FSM.

- TODO: make issues for the questions above.
