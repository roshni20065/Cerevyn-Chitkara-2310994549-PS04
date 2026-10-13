# Sample data and expected labels

`tickets.json` contains 30 fictional ticket messages across Billing, Technical, Access and General. The `train` split has 20 examples; the `test` split has 10 examples. Each row's `category` is the expected category label. The test split is used by `GET /evaluation` and is not inserted into the ticket database automatically.

Observed result on this version of the keyword rules: **10/10 correct (100%)** on this small synthetic holdout. This result is only a smoke-test baseline: the dataset is small and synthetic, so it is not evidence of production performance. Priority is determined separately by the documented priority keyword policy.
