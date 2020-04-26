"""
Machine shop example

Covers:

- Interrupts
- Resources: PreemptiveResource

Scenario:
  A workshop has *n* identical machines. A stream of jobs (enough to
  keep the machines busy) arrives. Each machine breaks down
  periodically. Repairs are carried out by one repairman. The repairman
  has other, less important tasks to perform, too. Broken machines
  preempt theses tasks. The repairman continues them when he is done
  with the machine repair. The workshop works continuously.

"""
import random

import simpy

from simpy_fsm.v1 import FSM, process_name


RANDOM_SEED = 42

PT_MEAN = 10.0  # Avg. processing time in minutes
PT_SIGMA = 2.0  # Sigma of processing time

MTTF = 300.0  # Mean time to failure in minutes
BREAK_MEAN = 1 / MTTF  # Param. for expovariate distribution
REPAIR_TIME = 30.0  # Time it takes to repair a machine in minutes

JOB_DURATION = 30.0  # Duration of other jobs in minutes

NUM_MACHINES = 10  # Number of machines in the machine shop
WEEKS = 4  # Simulation time in weeks
SIM_TIME = WEEKS * 7 * 24 * 60  # Simulation time in minutes


rng1 = random.Random()
def time_per_part():
    """Return actual processing time for a concrete part."""
    return abs(rng1.normalvariate(PT_MEAN, PT_SIGMA))


rng2 = random.Random()
def time_to_failure():
    """Return time until next failure for a machine."""
    return rng2.expovariate(BREAK_MEAN)


class Machine(FSM):
    """A machine produces parts and my get broken every now and then.

    If it breaks, it requests a *repairman* and continues the production
    after the it is repaired.

    A machine has a *name* and a numberof *parts_made* thus far.

    """

    def __init__(self, env, initial_state="working", *, name, id, repairman):
        self.name = name
        self.id = id
        self.repairman = repairman
        self.parts_made = 0
        self.broken = False
        self.prepare_part()
        self.breaker = MachineFailure(env, machine=self)
        super().__init__(env, initial_state)

    def prepare_part(self):
        self.work_left = time_per_part()

    def finish_part_and_prepare_next(self):
        self.parts_made += 1
        self.prepare_part()

    def working(self, data):
        """Produce parts as long as the simulation runs.

        While making a part, the machine may break multiple times.
        Request a repairman when this happens.
        """
        self.broken = False
        start = self.env.now
        try:
            # Work on the part, finish it, and start a new one
            yield self.env.timeout(self.work_left)
            self.finish_part_and_prepare_next()
            return self.working
        except simpy.Interrupt:
            # Record how much work was left, and await the repair man
            self.work_left -= self.env.now - start
            return self.awaiting_repairman

    def awaiting_repairman(self, data):
        # Request a repairman. This will preempt the UnimportantWork that
        # otherwise occupies the repairman.
        self.broken = True
        self.repairman_request = self.repairman.request(priority=1)
        yield self.repairman_request
        return self.being_repaired

    def being_repaired(self, data):
        yield self.env.timeout(REPAIR_TIME)
        self.repairman.release(self.repairman_request)
        return self.working


class MachineFailure(FSM):
    def __init__(self, env, initial_state="break_machine", *, machine):
        self.machine = machine
        super().__init__(env, initial_state)

    def break_machine(self, data):
        """Break the machine every now and then."""
        yield self.env.timeout(time_to_failure())
        if not self.machine.broken:
            # Only break the machine if it is currently working.
            self.machine.process.interrupt()
        return self.break_machine


class UnimportantWork(FSM):
    """The repairman's other (unimportant) job."""
    def __init__(self, env, initial_state="awaiting_repairman", *, repairman):
        self.repairman = repairman
        self.works_made = 0
        self.prepare_work()
        self.state = initial_state
        super().__init__(env, initial_state)

    def prepare_work(self):
        self.work_left = JOB_DURATION  # how long the unimportant jobs take

    def finish_work_and_prepare_next(self):
        floating_point_error = self.work_left - 0
        self.work_left = 0
        self.works_made += 1
        self.prepare_work()

    def awaiting_repairman(self, data):
        self.state = "awaiting_repairman"
        self.repairman_request = self.repairman.request(priority=2)
        x = yield self.repairman_request
        return self.working

    def working(self, data):
        assert self.process in [u.proc for u in self.repairman.users]
        self.state = "working"
        """Claim the repairman with low priority"""
        start = self.env.now
        try:
            # Try to work on the job until it is done ...
            x = yield self.env.timeout(self.work_left)
            # ... (a) if the repairman is not called away, control is
            #     yielded back to us at the time our work is done, and we
            #     resume at *this* point in the code ...

            self.finish_work_and_prepare_next()
            return self.working

        # ... (b) but if the repairman is called away, the yield timeout
        #     above gets sent an Interrupt, and we resume at *this* point
        #     in the code.
        #
        # We record where we were, and then try working again -- that will
        # start when we get our repairman back.
        except simpy.Interrupt:
            # FIXME Expressing work_done and work_left as floats vulnerable to
            # floating-point errors: it may lead to negative work_left values.
            # See floating_point_bug.md for a full explanation. For now,
            # `finish_work_and_prepare_next()` regularly resets
            # self.work_left to 0.
            #
            # FIXME There should be a lint that prevents any references
            # to an `env` other than `self.env`: it's easy to forget the
            # `self`, but doing so will lead to computing time from the wrong
            # clock. For example, computing `self.work_left` using `start` from
            # one clock, and `now` from another clock, may cause negative
            # values and so negative timeouts...
            work_done = self.env.now - start
            self.work_left = self.work_left - work_done
            return self.awaiting_repairman

    def __repr__(self):
        return (
            f"UnimportantWork(works_made={self.works_made}, work_left={self.work_left})"
        )


def snapshot(env, repairman, unimportant_work, machines):
    broken_machines = [m.id for m in machines if m.broken]
    repairman_processes = [request.proc for request in repairman.users]
    repairman_at = [m.id for m in machines if m.process in repairman_processes] + (
        ["unimportant_work"] if unimportant_work.process in repairman_processes else []
    )
    return f"Repairman at {repairman_at}; broken {broken_machines}; unimportant_work state {unimportant_work.state}, made {unimportant_work.works_made}"


# Setup and start the simulation
print("Machine shop")

# This helps reproducing the results
rng1.seed(RANDOM_SEED)
rng2.seed(RANDOM_SEED)

# Create an environment and start the setup process
env = simpy.Environment()
repairman = simpy.PreemptiveResource(env, capacity=1)
machines = [
    Machine(env, id=i, name=process_name(i, of=NUM_MACHINES), repairman=repairman)
    for i in range(NUM_MACHINES)
]
unimportant_work = UnimportantWork(env, repairman=repairman)

# Execute!
env.run(until=SIM_TIME)

# Analyis/results
print("Machine shop results after %s weeks" % WEEKS)
for machine in machines:
    print("%s made %d parts." % (machine.name, machine.parts_made))

print(snapshot(env, repairman, unimportant_work, machines))
