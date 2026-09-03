# QCF — Quant Currency Futures

Private research repository. **Bootstrap commit — Stage 00 in progress.**

QCF is a research and paper-simulation system for studying CME Euro FX futures
(`6E`). It exists to test whether an apparent edge is false, fragile, overfit,
too costly, or operationally unsafe — not to produce a profitable-looking
backtest.

## Boundary

QCF **must not** transmit a real order.

There is no live operating mode, no broker or prop-firm authentication, no
financial-account credentials, and no order-routing capability. Permitted
operating modes are `DISABLED`, `RESEARCH`, `BACKTEST`, `REPLAY`, and `PAPER`;
the default is `DISABLED`. Any future discussion of real deployment belongs to a
separate project under a separate authorization and review process.

This file is intentionally minimal: it is part of the documented
empty-repository bootstrap commit. The full project README is added on the
Stage 00 branch.

## Licensing

No open-source license is granted. See [LICENSE_POLICY.md](LICENSE_POLICY.md).
