## Charging car, impatient driver

This example comes from the the Simpy docs, section "Simpy in 10
Minutes", subsection ["Process Interaction"][1].

[1]: https://simpy.readthedocs.io/en/latest/simpy_intro/process_interaction.html

### Scenario

There is one car; it alternates autonomously between driving for 2 minutes, and charging for 5 minutes. It starts out in charging mode.

There is a driver who gets impatient: 3 minutes after the driver's process is started, they'll send the car an interrupt that they want to start driving.

When the car catches this interrupt, it switches from charging mode to driving mode.

### Comparing the process notation and the state machine notation.

#### Brevity

The Car process is about equally long written as a process, or as a state
machine: 21-22 lines. For the driver process, the state machine notation adds
about 6 lines of overhead, most of it instance initialization code.

#### Number of processes per entity

In `new.py`, there is only one process that represents the car. In `old.py`, the car's 'charging' state is a second Simpy process that the 'driving' process waits on.

#### Are the states interchangeable?

In `old.py`, the car runner always calls charging mode first -- to start the car in driving mode, it's `.run()` process would have to be rewritten. In `new.py`, the car can be started in driving mode via `Car(env, initial_state='driving')`

#### States as methods vs states as lines in a function

In `old.py`, the 'charging' state corresponds to the first 9 lines of the `run()` method plus the `charge` method, and the 'driving' state correponds to the `run()` method's last 3 lines. The transitions between them are encoded in the control flow: charging comes first, followed by driving, and then a loop back to charging.

In `new.py`, there is one method for `charging()` and one method for `driving()`. The transition logic is part of the state's method, and mentions the next state explicitly (e.g. `return self.driving`). Because logic is per-state, it's a little more obvious that the car's `driving` state can't handle the driver's interrupt.
