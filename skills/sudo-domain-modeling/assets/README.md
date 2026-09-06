# Mermaid Domain Modeling Example

[example.md](example.md) contains a fictional library lending model and corresponding instances, written in Japanese. Its two Mermaid blocks use the default colors and typography defined in [SKILL.md](../SKILL.md).

The domain model shows Member and Loan aggregates. Each Loan references one Member and contains zero or one ReturnRecord. The object diagram shows one member with two distinct loan aggregates: one without a return record and one with a return record. Dates satisfy the stated business rules.

Subgraphs represent aggregate boundaries. Solid links represent associations; labels explicitly identify containment and both endpoint multiplicities. Dashed links attach explanatory notes. The flowchart syntax expresses static structure, not execution order.

To produce `.mmd` files, copy each Mermaid block's contents, including its YAML frontmatter, into a separate file without the Markdown fences. The example is stored only as `.md` to keep one maintained source for both output formats.

Use the notation as a reference; determine business rules and aggregate boundaries from the target task. The example covers loan registration and return recording, with materials represented by identifiers. It does not define catalog management, reservations, or concurrent lending behavior.
