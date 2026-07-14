# Format-boundary coordinator

Run one bounded compatibility probe. Delegate the reference lookup to
`format-boundary-worker`; do not answer the marker from memory or inspect the
reference yourself. Return the worker's marker and its evidence label.

If the worker cannot be invoked, report the runtime and exact failure. Do not
substitute inline work, because successful delegation is the behavior under test.
