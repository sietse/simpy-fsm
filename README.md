Summary
-------

Simpy is nice and all, but there is one thing that makes it hard to keep track
of state: it isn't explicit, it is a mere 'where in the control flow are we?'

fsm.py solves that: it contains plumbing that lets you write classes with

- One method per state
- States can yield to simpy like normal
- When a state ends, it returns the state (self.some_method) to transition to;
  the FSM class takes care of running it.


Compare the traditional `simpy_3_old.py` to the rewrites in
`simpy_3_resource.py`, and `simpy_3b_resource_manually.py`, which encode the
objects as FSM instances, with a method per state. `simpy_3_old.py` comes
from Simpy's introduction:
https://simpy.readthedocs.io/en/latest/simpy_intro/basic_concepts.html


Design to try out
-----------------

- [x] ProcessFSM has a .process attribute, much like now.
- [x] `data` object is passed as arg to state methods.
- [ ] keep a process log on the data object:
      - ID is implicit
      - time
      - new state (possibly nested)


Design space
------------

Questions/dimensions:
- How do I instantiate an FSM meant to have a process? Do I start a process for
  it manually, or is that automatically done at the instance's initialization?

- How do I, given an FSM instance, find its Process?
  - my_fsm.process
  - pair = (my_fsm, process)
- How do I, given an FSM instance, get its data?
- How do I, given an FSM instance

### 1. ProcessFSM: How do I instantiate FSM and Process?

- [ ] The FSM *is* a Process

    # Awaiting a new car process
    yield Car()

    # Creating a new car
    car1 = Car()
    car1.interrupt()

  - No need to remember which object to address
  - Mixes the state machine behaviour and the Process interface together
    in one object
  - No need to track both FSM and process objects
  - Lot of reserved names that can't be used for state names:
    defused, fail, interrupt, is_alive, ok, processed,
    property, succeed, target, trigger, triggered, value,
  - Hides detail of process creation
  - Can't create object in advance and start process later.


- [ ] Instantiating the FSM automatically instantiates the process

    # Awaiting a new car process
    yield Car().process

    # Creating a new car
    car1 = Car()
    car1.process.interrupt

  - Keeps separate FSM and Process APIs as 2 separate objects.
  - Can always get process from FSM -- no need for separate table.
  - Hides detail of process creation
  - Can't create object in advance and start process later.
  - Must remember to inspect car1, but interrupt car1.process.

- [ ] Create the process manually from the generator

    # Awaiting a new car process
    yield env.process(Car().generator)

    # Creating a new car (store process separately)
    car1 = Car()
    process = env.process(car1.generator)
    process.interrupt()

    # Creating a new car (store process on car)
    car1 = Car()
    car1.process = env.process(car1.generator)
    car1.process.interrupt()

  - User must keep track of FSM + process pair
  - Makes process creation mechanism explicit
  - Can create object in advance and start process later -- but do you want to?
  - reserved name `generator`, used only in process init incantation
  - Possible to accidentally create multiple processes pushing the same generator?


- [ ] Create the process manually from the generator function

    # Awaiting a new car process
    yield env.process(Car().generator)

    # Creating a new car (store process separately)
    car1 = Car()
    process = env.process(car1.main())
    process.interrupt

    # Creating a new car (store process on car)
    car1 = Car()
    car1.process = env.process(car1.main())
    car1.process.interrupt()

  - Most explicitest about process creation mechanism
  - Reserved name `main`, used only in process init incantation
  - `main` is an okay name for a state, people might want to use it themselves
  - Possible to accidentally create multiple processes mutating the same object


### 2. SubstateFSM: How do I expose a SubstateFSM instance as a generator to yield from?

- [ ] The FSM instance is a generator

    yield from StoplightOn()

- [ ] The FSM instance has a generator

    yield from StoplightOn().generator

- [ ] The FSM instance has a generator function that the caller turns into a
  generator.

    yield from StoplightOn().main()


### 3. FSM: where does an FSM's associated data live?

- [ ] attributes on `self`
- [ ] attributes on `self.data`
- [ ] on a `data` object passed into the state method: `def mystate(self, data)`


### 4. SubstateFSM: when writing a SubstateFSM, how does it access its parent's data?

- [ ] By passing the same `data` object to parent and child alike.
  I like this option
- [ ] Set `.parent` on the substateFSM; then state methods can access
  `self` and `self.parent`, or `self.data` and `self.parent.data`.


Refactoring
-----------

- Create two ways to initialize an FSM:
  - as a Process (`env.process(x)`)
  - as a subprocess (`yield from x`)
- Keep a log of state transitions on the object


Current challenge
-----------------

- [x] Extract a separate waiting-for-repairman state in simpy_4_machine_shop.py
- [x] Rename `actor` to `FSM`, or `Machine`, or something else like '(Finite) State Machine'



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
