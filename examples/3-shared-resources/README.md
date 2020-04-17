## Shared resources

This example comes from the the Simpy docs, section "Simpy in 10
Minutes", subsection ["Shared Resources"][1].

[1]: https://simpy.readthedocs.io/en/latest/simpy_intro/shared_resources.html


### Scenario

There is a Battery Charging Station, which is treated as a resource with 2
slots.

There are 4 cars. Every car drives for a different number of minutes, then
arrives at the charging station, where it requests a slot.  Once the car has
received a charging slot, it charges for 5 minutes, releases its slots, and
ends its process.

It is possible that a car cannot get a charging slot immediately, because they
are all occupied. In that case, the car must wait until it is assigned a slot.


### Discussion

An acquired resource must always be released; `old.py` and `new1.py` both
guarantee that by using the resource request's context manager interface in the
*charging* state.

On the other hand, *waiting for a charging station* and *charging* are arguably
two different states. This is the tack `new2.py` takes: it requests the
resource in the *awaiting_battery* state, and once it gets a slot it
transitions to the *charging* state. The charging state manually releases the
slot when it's done.


#### How to pass information between states?

An interesting design question for the `new2.py` state machine formulation: how
to pass data from the *awaiting_battery* state to the *charging* state?
Specifically, in Simpy you need the original request object to release a
resource slot, so we must find some way to pass that object from the
*awaiting_battery* method to the *charging* method. The current solution is to
use `self` as a dead-drop: *awaiting_battery* sets an attribute on `self`,
*charging* accesses it.

The request object could also be set and retrieved via the `data` object that
`fsm.trampoline` diligently passes to each method. This is not materially
different from using `self`, except perhaps that `data` is more clearly meant
to pass around.

Perhaps state methods could return a `next_state, kwargs` tuple instead, if
`trampoline` then initializes each state method as `state_generator =
next_state(kwargs)`?
