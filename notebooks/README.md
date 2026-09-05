# Notebooks

Exploratory work only.

Notebooks **must not** contain canonical logic. Anything a result depends on —
a feature definition, a cost model, an accounting rule — lives in `src/qcf`,
under version control, with tests. A notebook may call that code and plot the
output; it may not *be* the code.

The reason is reproducibility rather than tidiness. A notebook's state depends
on the order cells were executed in, which is not recorded in the file. A result
that depends on that order cannot be reproduced, and a result that cannot be
reproduced is not evidence.

No notebooks exist yet. When they do:

- clear outputs before committing;
- never commit market data, credentials, or account information;
- treat any finding worth keeping as a prompt to move the code into `src/qcf`.
