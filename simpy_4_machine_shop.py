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

from actor import FSM, process_name


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

UNIMPORTANT_WORK_TIME = 7.0


def spy(x, label=''):
    # print(label, x)
    return(x)


def time_per_part():
    """Return actual processing time for a concrete part."""
    return spy(abs(random.normalvariate(PT_MEAN, PT_SIGMA)), label='normal')


def time_to_failure():
    """Return time until next failure for a machine."""
    return spy(random.expovariate(BREAK_MEAN), label='expo')


class Machine(FSM):
    """A machine produces parts and my get broken every now and then.

    If it breaks, it requests a *repairman* and continues the production
    after the it is repaired.

    A machine has a *name* and a numberof *parts_made* thus far.

    """
    def __init__(self, env, initial_state='working', *,
                 name, id, repairman):
        self.name = name
        self.id = id
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
            return self.awaiting_repairman

    def awaiting_repairman(self):
        # Request a repairman. This will preempt the UnimportantWork that
        # otherwise occupies the repairman.
        self.broken = True
        self.repairman_request = self.repairman.request(priority=1)
        yield self.repairman_request
        return self.being_repaired

    def being_repaired(self):
        yield self.env.timeout(REPAIR_TIME)
        self.repairman.release(self.repairman_request)
        return self.working


class MachineFailure(FSM):

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


class UnimportantWork(FSM):

    def __init__(self, env, initial_state='awaiting_repairman', *, repairman):
        self.repairman = repairman
        self.works_made = 0
        self.prepare_work()
        self.state = initial_state
        super().__init__(env, initial_state)

    def prepare_work(self):
        self.work_left = UNIMPORTANT_WORK_TIME  # how long the unimportant jobs take

    def finish_work_and_prepare_next(self):
        floating_point_error = self.work_left - 0
        self.work_left = 0
        self.works_made += 1
        self.prepare_work()

    def awaiting_repairman(self):
        self.state = 'awaiting_repairman'
        self.repairman_request = self.repairman.request(priority=2)
        x = (yield self.repairman_request)
        print(env.now, x)
        return self.working

    def working(self):
        assert self.process in [u.proc for u in self.repairman.users]
        self.state = 'working'
        """Claim the repairman with low priority"""
        start = self.env.now
        try:
            # Try to work on the job until it is done ...
            x = (yield env.timeout(self.work_left))
            print(env.now, x)
            if env.now >= 28:
                # import ipdb; ipdb.set_trace()  # FIXME
                pass
            # ... (a) if the repairman is not called away, control is
            #     yielded back to us at the time our work is done, and we
            #     resume at *this* point in the code ...

            # This is vulnerable to floating-point errors. See [1], below,
            # for the explanation. For now, finish_work_and_prepare_next()
            # resets self.work_left to 0
            work_done = self.env.now - start
            self.work_left = self.work_left - work_done
            self.finish_work_and_prepare_next()
            return self.working

        # ... (b) but if the repairman is called away, the yield timeout
        #     above gets sent an Interrupt, and we resume at *this* point
        #     in the code.
        #
        # We record where we were, and then try working again -- that will
        # start when we get our repairman back.
        except simpy.Interrupt:
            work_done = self.env.now - start
            self.work_left = self.work_left - work_done
            return self.awaiting_repairman

    def __repr__(self):
        return f"UnimportantWork(works_made={self.works_made}, work_left={self.work_left})"


# Setup and start the simulation
print('Machine shop')
random.seed(RANDOM_SEED)  # This helps reproducing the results

# Create an environment and start the setup process
env = simpy.Environment()
repairman = simpy.PreemptiveResource(env, capacity=1)
unimportant_work = UnimportantWork(env, repairman=repairman)
machines = [
    Machine(env, id=i, name=process_name(i, of=NUM_MACHINES), repairman=repairman)
    for i in range(NUM_MACHINES)
]

def snapshot(env, repairman, unimportant_work, machines):
    broken_machines = [m.id for m in machines if m.broken]
    repairman_processes = [request.proc for request in repairman.users]
    repairman_at = (
        [m.id for m in machines if m.process in repairman_processes] +
        (['unimportant_work']
         if unimportant_work.process in repairman_processes
         else [])
    )
    return f'Repairman at {repairman_at}; broken {broken_machines}; UW state {unimportant_work.state}, made {unimportant_work.works_made}'

# Execute!
prev_info = ''
while env.now < 200:
    info = snapshot(env, repairman, unimportant_work, machines)
    if info[4:] != prev_info[4:]:
        prev_info = info
        print(f'{round(env.now)} {info}')
    env.step()

# Analyis/results
print('Machine shop results after %s weeks' % WEEKS)
for machine in machines:
    print('%s made %d parts.' % (machine.name, machine.parts_made))


# [1] Floating-point errors
#
# == Summary ==
#
# After the following sequence
#
#     start = self.env.now
#     # (yield, and resume after self.work_left ticks)
#     work_done = self.env.now - start
#     self.work_left = self.work_left - work_done,
#
# the new self.work_left is *not* going to be zero, and it's going to be more
# and more different from zero as the simulation progresses.
#
# This is because env.now is an increasing floating point number, and math with
# larger floating point numbers gives larger floating point errors.
#
#
# == Possible solutions ==
#
# - Don't use a floating-point counter. Discretize time and represent it as an
#   integer.
#
# - Track how the (work_left - 0) error grows over simulation time; if the
#   simulation ends before the error grows too large, we don't care.
#
# - Just set work_left to 0 manually after each job, postpone investigation
#   until we start seeing weird behaviour.
#
#
# == Why this is so ==
#
# If computer arithmatic were exact, life would be simple: if we start at
# `t = start`, with `work_left` minutes of work left, we'll be done at
# `t = (start + work_left)`. In math:
#
#                     start + work_left == end
#                             work_left == end - start
#             work_left - (end - start) == 0
#
# But we're working with floating point math, and floating point numbers can
# only approximate most values. Let's write `x = fp(x) + err` to represent that
# x is approximated by its floating-point representation, but an error will
# remain. If we rewrite the equations above for floating point variables, we
# get this:
#
#                 fp(start) + fp(work_left) == fp(end) + err
#                             fp(work_left) == fp(end) - fp(start) + err
#     fp(work_left) - (fp(end) - fp(start)) == 0 + err
#
# As time passes, `start` and `end` are going to become larger, and `fp(start)`
# and `fp(end)` are going to become less precise. So as time passes, `err` is
# going to get larger.
