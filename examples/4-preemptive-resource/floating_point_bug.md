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
