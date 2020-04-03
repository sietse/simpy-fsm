Summary
-------

Simpy is nice and all, but there is one thing that makes it hard to keep track
of state: it isn't explicit, it is a mere 'where in the control flow are we?'

actor.py solves that: it contains plumbing that lets you write classes with

- One method per state
- States can yield to simpy like normal
- When a state ends, it returns the state (self.some_method) to transition to;
  the FSM class takes care of running it.


Compare the traditional `simpy_3_old.py` to the rewrites in
`simpy_3_resource.py`, and `simpy_3b_resource_manually.py`, which encode the
objects as FSM instances, with a method per state. `simpy_3_old.py` comes
from Simpy's introduction:
https://simpy.readthedocs.io/en/latest/simpy_intro/basic_concepts.html

Refactoring
-----------

- Rename `actor` to `FSM`, or `Machine`, or something else like '(Finite) State Machine'
- Create two ways to initialize an FSM:
  - as a Process (`env.process(x)`)
  - as a subprocess (`yield from x`)


Current challenge
-----------------

- Extract a separate waiting-for-repairman state in simpy_4_machine_shop.py



Solved challenge: work_left is not exactly zero
-----------------------------------------------

This was caused by Floating-point errors. The absolute error got larger as
the floats involved got larger, which is how floats behave.


Solved challenge: negative delays
---------------------------------

Run simpy_4_machine_shop.py. Expected behaviour: no errors. Observed behaviour:

    ValueError: Negative delay -29.08065477559603

What causes this bug? This is where and how the bug happens (simplified)

    class UnimportantWork:
        def working(self):

            # BUG step 1: waiting for the repair person is not the
            # same as working
            start = self.env.now

            with self.repairman.request(priority=2) as req:
                yield req  # Wait until we get a repairman

                # BUG mitigation: here is where we should record the `start` time.

                try:

                    # BUG step 3: Try to wait for a negative `work_left` time.
                    # Try to work on the job until it is done ...
                    yield env.timeout(self.work_left)

                except simpy.Interrupt:

                    # BUG step 2: `now - start` is more than `work left`,
                    # because we add the time we were waiting for the
                    # repairperson. As a result `self.work_left` is set to a
                    # negative value.
                    work_done = self.env.now - start
                    self.work_left = self.work_left - work_done

                    return self.working

The solution: move `start = self.env.now` until just after `yield req`. The
unimportant work only starts/resumes once our request for a repairman is
granted. When `start = self.env.now` was recorded before `yield req`, the work
counter started when we started *waiting* for a repairman.


Deeper challenge: Implement a state machine library in Simpy
------------------------------------------------------------

- What features should it have?
- What features do other state machine libraries have?
- It should definitely have plotting features:
  - Generate `dot` plots of supported transitions (and signals)?
    - Or even generate Harel State Charts?
  - Generate diagrams of states over time.
    - per-Process:
        - One or more Process's state transitions (a sequence diagram, or any
          multi-line diagram, might be good for this if there are few states)
        - Messages (interrupts) sent between Processes.
    - Aggregated over many processes:
        - Over time, for a process type, the number of processes in each state.
        - Messages sent, per message type, over time
        - total process*time spent in each state


Deeper challenge: a Task class that keeps track of countdown
------------------------------------------------------------

http://simpy.readthedocs.io/en/latest/simpy_intro/process_interaction.html?highlight=interrupt
http://simpy.readthedocs.io/en/latest/topical_guides/process_interaction.html#sleep-until-woken-up

Design a Task class

* When you start the task, it has state 'running'
* When the running task yields, it will be awoken when 'work_remaining' will be 0
* When you query the running task, its 'work_remaining' depends on the time

* When you interrupt a running task, its state is 'suspended'
* When the suspended task yields, it will be awoken when the suspension ends.
  It awaits an event?
* When you query the suspended task, its 'work_remaining' is the last value

Currently Simpy models the start of suspensions explicitly, but the end is
kind of implicit. This is what happens when a process suspends:

* receive an interrupt
* move forward to the next yield point
* that yield point should be resumed when the interruption ends. I guess the
  process is interrupted twice: once to suspend it, once to resume it.


For example, resumption could be triggered by a resource becoming availabe:

    with repairman.request(priority=2) as req:
        yield req

Alternatively, passivate by awaiting an event

    yield some_event

The worker can then reactivate the task by triggering that event when she
becomes available.

    some_event.trigger()

Alternatively alternatively, send two interrupts:
`myprocess.interrupt('suspend')` and `myprocess.interrupt('resume')`, which
can be differentiated by examining `myinterrupt.cause`.

    try:
        yield env.timeout(...)
    except simpy.Interrupt as signal:
        if signal.cause == 'suspend':
            ...
        if signal.cause == 'resume':
            ...
        else:
            raise
