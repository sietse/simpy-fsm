Summary
-------

Simpy is nice and all, but there is one thing that makes it hard to keep track
of state: it isn't explicit, it is a mere 'where in the control flow are we?'

actor.py solves that: it contains plumbing that lets you write classes with 

- One method per state
- States can yield to simpy like normal
- When a state ends, it returns the state (self.some_method) to transition to;
  the Actor class takes care of running it.


Compare the traditional `simpy_3_old.py` to the rewrites in
`simpy_3_resource.py`, and `simpy_3b_resource_manually.py`, which encode the
objects as Actor instances, with a method per state. `simpy_3_old.py` comes
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

Extract a separate waiting-for-repairman state in simpy_4_machine_shop.py


Solved challenge: work_left is not exactly zero
-----------------------------------------------

This was caused by Floating-point errors. The absolute error got larger as
the floats involved got larger, which is how floats behave.


Solved challenge: negative delays
---------------------------------

Run simpy_4_machine_shop.py. Expected behaviour: no errors. Observed behaviour:

    ValueError: Negative delay -29.08065477559603

What causes this bug? This bug

This happens at line 156:

    class UnimportantWork
        def working
            yield env.timeout(self.work_left)

The solution: move `start = self.env.now` until just after `yield req`. The
unimportant work only starts/resumes once our request for a repairman is
granted. When `start = self.env.now` was recorded before `yield req`, the work
counter started when we started *waiting* for a repairman.


Deeper challenge: Implement a state machine library in Simpy
------------------------------------------------------------

What features should it have?

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
