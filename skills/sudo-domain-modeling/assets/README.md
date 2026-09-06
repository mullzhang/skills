# Domain Modeling Example

[example.drawio](example.drawio) is an editable, two-page Japanese example of a small library lending domain. It is an original fictional example, not a reproduction of the source article's diagrams.

## Pages

- **ドメインモデル図**: Member and Loan aggregate boundaries, aggregate roots, representative attributes, Japanese/English concept names, multiplicities, business rules, and assumptions.
- **オブジェクト図**: One member with two separate loan aggregates at the same point in time. Loan A has no return record; Loan B has one return record.

## What to Look For

| Model element | Concrete example |
| --- | --- |
| Each Loan has exactly one Member; a Member has zero or more Loans | Member A is linked to Loans A and B; each loan has one borrower |
| Each Loan contains zero or one ReturnRecord | Loan A has none; Loan B contains Return B |
| A ReturnRecord belongs to exactly one Loan | Return B belongs only to Loan B |
| Due dates and return dates must not precede the loan date | Both due dates and Return B's date satisfy these rules |
| Each Loan is a separate aggregate | Loans A and B have separate boundaries despite sharing a borrower |

Filled diamonds mark containment at the Loan end. Outer boxes mark aggregates; dashed lines attach notes. Japanese labels distinguish rules and assumptions independently of color.

## Scope and Limits

The example covers registering loans and recording returns. Materials are represented only by their identifiers. Catalog management, reservations, overdue fees, and prevention of concurrent loans of the same material are outside scope.

The snapshot illustrates valid structure and values. It does not test a member with no loans, equal-date boundaries, rejection of duplicate returns, or concurrency. Static object diagrams do not prove operation behavior.

## Use as a Reference

Use this file to understand notation and correspondence between the two diagrams. Its colors follow the default palette defined in [SKILL.md](../SKILL.md). Do not inherit its business rules, aggregate decisions, or sample values without evaluating the target domain. Preserve this bundled example and save task-specific diagrams at the user's output destination.

Read the separate `draw-io` skill before inspecting or adapting the diagram. It owns the XML and layout procedures; this example does not replace that dependency.
