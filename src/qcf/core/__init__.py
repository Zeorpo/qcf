"""Foundation primitives shared by every QCF component.

This package holds the things that must mean the same thing everywhere:
operating modes, the exception hierarchy, explicit unknown values, deterministic
fingerprints, configuration, logging, and version metadata.

It contains no market, strategy, execution, risk, or compliance logic, and it
must not acquire any: components depend on ``core``, so anything placed here is
depended upon by everything.
"""
