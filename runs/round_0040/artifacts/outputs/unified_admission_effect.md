# Unified Admission And Authorization Effect

- Raw memory admission rate: 100.00%
- Strict gold-memory admission rate: 100.00%

| pool | n | A6 visibility-only | A7 + unified authorization | delta |
|---|---:|---:|---:|---:|
| strict_stable_wrong | 867 | 271/867 (31.26%) | 290/867 (33.45%) | +2.19% |
| visible_supported | 737 | 202/737 (27.41%) | 219/737 (29.72%) | +2.31% |
| serialization_loss | 130 | 69/130 (53.08%) | 71/130 (54.62%) | +1.54% |

## Paired McNemar

| pool | b | c | p |
|---|---:|---:|---:|
| strict_stable_wrong | 76 | 57 | 0.11824011046976109 |
| visible_supported | 65 | 48 | 0.13192429082426047 |
| serialization_loss | 11 | 9 | 0.8238029479980469 |
