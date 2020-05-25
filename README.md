## Simpy and Finite State Machines.

This repository shows how to write complex Simpy process as a flat state machine class with one method per state, instead of as a single function with nested loops and try-blocks.

The more states a Simpy process has, and the more complicated the transition paths between them, the more you may get out of state machine notation. Returning the next state is a clearer way to specify a transition than breaking out of a loop, setting a sentinel variable, or treating another state as a child process. But for simple processes, state machine notation is probably overkill.

I'm still exploring the design space, so the repository contains multiple implementations that differ in their internals and/or their method signatures. Feedback is welcome! Leave a comment on this repo, or e-mail sbbrouwer@gmail.com.


## Example

### Example 1: a car that drives and parks

Here is a simple Simpy process that simulates a car with two states: parking and driving.

(The code snippets are shown side-by-side; scroll right if you can't see them both.)

<table><tr> <td>
Traditional Simpy process function:

<!-- The blank lines at the end are to make the code blocks equally tall. -->
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

</td>

<td>
Rephrased as a state machine:

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

</td>
</tr>
</table>

### Example 2: A machine that breaks

Here is a more complex example: it's a machine that usually produces parts.
Sometimes it gets broken, and must await a repairman. The repairman
subsequently needs some time to fix the machine.

To focus on the essence, the code below omits the repairman resource and the machine-breaking
process. You can find the full example at
[`examples/4-preemptive-resource`](tree/master/examples/4-preemptive-resource).

(The code snippets are shown side-by-side; scroll right if you can't see them both.)

<table><tr><td>
Traditional Simpy process function:

<!-- The blank lines at the end are to make the code blocks equally tall. -->
```python
import simpy

class Machine(object):

  ## Init method and other details omitted.

  def run_machine(self, repairman):
    """Produce parts as long as the simulation runs.

    While making a part, the machine may break,
    multiple times. Request a repairman when this
    happens.
    """
    while True:
      # Start making a new part
      done_in = time_per_part()
      while done_in:
        try:
          # Working on the part
          start = self.env.now
          yield self.env.timeout(done_in)
          done_in = 0  # Set to 0 to exit the loop.

        except simpy.Interrupt:
          self.broken = True
          # How much time left?
          done_in -= self.env.now - start

          # Request a repairman. This will preempt
          # the UnimportantWork that otherwise
          # occupies the repairman.
          with repairman.request(priority=1) as req:
            yield req
            yield self.env.timeout(REPAIR_TIME)

          self.broken = False

      # Part is done.
      self.parts_made += 1



```

</td>

<td>
Rephrased as a state machine:

```python
import simpy
from simpy_fsm import FSM

class Machine(FSM):

  ## Init method and other details omitted.

  def working(self):
    """Produce parts as long as the simulation runs.

    While making a part, the machine may break multiple
    times. Request a repairman when this happens.
    """
    self.broken = False
    start = self.env.now
    try:
      # Work on the part, finish it, start a new one
      yield self.env.timeout(self.work_left)
      self.parts_made += 1
      self.work_left = time_per_part()
      return self.working
    except simpy.Interrupt:
      # The machine broke. Record how much work was
      # left, and await the repair man
      self.work_left -= self.env.now - start
      return self.awaiting_repairman

  def awaiting_repairman(self):
    # Request a repairman. This will preempt the
    # UnimportantWork that otherwise occupies the
    # repairman.
    self.broken = True
    self.repairman_request = \
      self.repairman.request(priority=1)
    yield self.repairman_request
    return self.being_repaired

  def being_repaired(self):
    yield self.env.timeout(REPAIR_TIME)
    self.repairman.release(self.repairman_request)
    return self.working
```

</td>
</tr>
</table>


## What can I find in this repository?

The purpose of this repository is to explore the design space for a finite state machine class and/or trampoline function that takes care of
- Exposing the current state for inspection
- Passing data from state to state
- Making sure the two items above work for hierarchical state machines, too.

Relevant files in this repository:

- `simpy_fsm/`: installed with `pip install PATH_TO_REPO_ROOT/setup.py`, use with `from simpy_fsm import FSM, SubstateFSM`. Needs Python 3.3 or later.
- `examples/standalone_example.py`: a small self-contained example file that contains both an example state machine _and_ the definition of its a trampoline function. Works in Python 2+3
- `examples/hierarchical_fsm.py`: this example shows we can also write hierarchical FSMs by implementing a stoplight that has Red/Yellow/Green as substates of On.
- `examples/{other folders}` Various examples from the [simpy docs](https://simpy.readthedocs.io/en/4.0.1/simpy_intro/index.html), both the original code and the FSM-style code. For comparison purposes.
- `worklog.md` -- my working notes. Used to be README.md, until I decided to publish, at which point I thought a tidier front page might be a good idea.


## How does the state machine combine the state methods into one process?

The state machine code has one method per state, and uses a trampoline function to compose the methods into a single process.

The core trampoline function is so short that we can reproduce it here in its entirety.
It is a generator function: calling it returns a generator, so a Simpy environment can use it as a process.
The generator starts by yielding from the first state's subgenerator; when that subgenerator is done, it `return`s the next generator function to yield from.
This lets you write a multi-state process as multiple subgenerators, one per state, that transition into each other.

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

In the examples further above, starting the trampoline and creating a Simpy
process is handled by the `FSM` superclas.

Here is an illustration of the resulting flow of control for the Car example.
The 'hindmost', long, bars indicate for how long the generator objects exist.
The smaller bars atop them show when the flow of control passes through each
generator.

![](trampoline-sequence-diagram.png?raw=true)

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
