# Infra Gym scoreboard (hard)

| Model | Episodes | Diag. (%) | Mit. (%) | E2E (%) | TTD (s) | TTM (s) | Tokens | Clean (%) | Worse | $/solved |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | 12 | 100.0 | 91.7 | 91.7 | - | - | 221K | 91.7 | 1 | 0.25 |
| gemini-3.8-flash | 12 | 75.0 | 8.3 | 8.3 | 197 | 252 | 852K | 8.3 | 2 | 4.00 |

Diagnosis judge: claude-opus-5-5. Mitigation is the verifier's PASS, with no LLM involved.
- claude-opus-5-5: 12 episode(s) ran before timing was recorded (no TTD/TTM)
TTD and TTM include the model's own thinking and API time, so faster providers score better.
