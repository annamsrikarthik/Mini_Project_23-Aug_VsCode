# Lead Intelligence System data

All three CSVs use these columns: `name`, `company`, `company_size`, `industry`,
`source`, and `last_interaction_date` (`YYYY-MM-DD`). They are classroom sample
data for the documented qualification rubric, not a live Salesforce export.

| File | Rows | Purpose |
| --- | ---: | --- |
| `leads_training.csv` | 29 | Original development examples. |
| `leads_testing.csv` | 23 | Original edge cases, including missing fields and large companies. |
| `leads_100_demo.csv` | 100 | Both original files unchanged, followed by 48 labeled synthetic rows. |

The 48 added rows repeat twelve explicit rubric cases four times with unique
sample identities. They cover company-size boundaries (19, 20, 500, 501),
interaction recency boundaries (30, 90, 91 days), a missing size, and several
lead sources and decisions. See `demo_100_manifest.json` for every expected
score and decision, source-file hashes, and the combined-file hash. Recreate the
file with `python build_demo_100.py` from this project folder.

Use `--as-of 2024-01-20` when reproducing the reported outcomes. The dates
describe a historical sample and should not be interpreted as current interest.
Missing company size receives a warning and zero size points; invalid or
unknown scoring fields route a lead to human review. The synthetic records are
for throughput and boundary testing, not evidence of real buyer interest or
sales conversion.
