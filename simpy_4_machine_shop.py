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

from actor import Actor, process_name


RANDOM_SEED = 42

PT_MEAN = 10.0         # Avg. processing time in minutes
PT_SIGMA = 2.0         # Sigma of processing time

MTTF = 300.0           # Mean time to failure in minutes
BREAK_MEAN = 1 / MTTF  # Param. for expovariate distribution
REPAIR_TIME = 30.0     # Time it takes to repair a machine in minutes

JOB_DURATION = 30.0    # Duration of other jobs in minutes

NUM_MACHINES = 10      # Number of machines in the machine shop
WEEKS = 4              # Simulation time in weeks
SIM_TIME = WEEKS * 7 * 24 * 60  # Simulation time in minutes

UNIMPORTANT_TIME = 7


def spy(x, label=''):
    # print(label, x)
    return(x)


def time_per_part():
    """Return actual processing time for a concrete part."""
    return spy(abs(random.normalvariate(PT_MEAN, PT_SIGMA)), label='normal')


def time_to_failure():
    """Return time until next failure for a machine."""
    return spy(random.expovariate(BREAK_MEAN), label='expo')


class Machine(Actor):
    """A machine produces parts and my get broken every now and then.

    If it breaks, it requests a *repairman* and continues the production
    after the it is repaired.

    A machine has a *name* and a numberof *parts_made* thus far.

    """
    def __init__(self, env, initial_state='working', *,
                 name, repairman):
        self.name = name
        self.repairman = repairman
        self.parts_made = 0
        self.broken = False
        self.prepare_part()
        self.breaker = MachineFailure(env, machine = self)
        super().__init__(env, initial_state)

    def prepare_part(self):
        self.work_left = time_per_part()

    def finish_part_and_prepare_next(self):
        self.parts_made += 1
        self.prepare_part()

    def working(self):
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
            return self.awaiting_repair

    def awaiting_repair(self):
        # Request a repairman. This will preempt its "other_job".
        self.broken = True
        try:
            with self.repairman.request(priority=1) as req:
                yield req
                yield self.env.timeout(REPAIR_TIME)
        finally:
            return self.working



class MachineFailure(Actor):

    def __init__(self, env, initial_state='break_machine', *, machine):
        self.machine = machine
        super().__init__(env, initial_state)

    def break_machine(self):
        """Break the machine every now and then."""
        yield self.env.timeout(time_to_failure())
        if not self.machine.broken:
            # Only break the machine if it is currently working.
            self.machine.process.interrupt()
        return self.break_machine


class UnimportantWork(Actor):

    def __init__(self, env, initial_state='working', *, repairman):
        self.repairman = repairman
        self.works_made = 0
        self.prepare_work()
        super().__init__(env, initial_state)

    def prepare_work(self):
        self.work_left = UNIMPORTANT_TIME
        print('work is prepared', self.work_left)

    def finish_work_and_prepare_next(self):
        self.works_made += 1
        self.prepare_work()

    def working(self):
        """Claim the repairman with low priority"""
        # Start a new job
        # Retry the job until it is done.
        # Its priority is lower than that of machine repairs.
        start = self.env.now
        with self.repairman.request(priority=2) as req:
            yield req
            try:
                print('starting work', self.work_left)
                yield env.timeout(self.work_left)
                print('control yielded back', self.work_left)
                self.work_left = 0
                print('have set work to 0', self.work_left)
                self.finish_work_and_prepare_next()
                print('done_preparing work', self.work_left)
                return self.working
            except simpy.Interrupt:
                print('interrupted', self.work_left)
                work_done = self.env.now - start
                print('start', start)
                print('now', self.env.now)
                print('work done', work_done)
                self.work_left = self.work_left - work_done
                print('after interrupt updated work', self.work_left)
                return self.working


# Setup and start the simulation
print('Machine shop')
random.seed(RANDOM_SEED)  # This helps reproducing the results

# Create an environment and start the setup process
env = simpy.Environment()
repairman = simpy.PreemptiveResource(env, capacity=1)
unimportant_work = UnimportantWork(env, repairman=repairman)
machines = [
    Machine(env, name=process_name(i, of=NUM_MACHINES), repairman=repairman)
    for i in range(NUM_MACHINES)
]

# Execute!
env.run(until=SIM_TIME)

# Analyis/results
print('Machine shop results after %s weeks' % WEEKS)
for machine in machines:
    print('%s made %d parts.' % (machine.name, machine.parts_made))
