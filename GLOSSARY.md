# Glossary

Use these words exactly in code, tests, and UI copy. Do not substitute synonyms.

| Word | Meaning |
|---|---|
| Contract | The source text the freelancer pastes. Evidence quotes come from it. |
| Plan | The proposed set of milestones, before or after human approval. |
| Milestone | One payable stage in the plan, with an amount, due date, and evidence quote. |
| Evidence quote | A verbatim sentence from the Contract that supports a milestone amount and date. |
| Check | A fixed code check, such as currency, sum, date, or quote matching. |
| Gate | A human approval step. The model can never pass a gate. |
| Invoice | The PayPal Invoicing v2 draft or sent invoice for one milestone. |
| Paid | Confirmed only by a fresh PayPal invoice GET returning PAID with matching merchant, currency, and amount. |
| Unlock | The next milestone becomes available after the previous one is Paid. |
| Trust boundary | The line between what the model may propose and what only code, the human, or PayPal may confirm. |
| Demo mode | Fixture contract, fixture model output, and simulated PayPal. No real funds move. |
| Fixture | Deterministic sample data used in demo mode, labelled by the demo banner. |
