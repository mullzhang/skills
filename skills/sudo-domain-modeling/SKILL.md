---
name: sudo-domain-modeling
description: Create and update Japanese domain model diagrams and corresponding object diagrams using sudo modeling and Mermaid. Derive concepts, attributes, relationships, multiplicities, aggregates, and business rules, then validate them against concrete examples. Deliver Markdown (.md) by default or Mermaid source (.mmd) when requested.
---

# sudo Domain Modeling with Mermaid

Build a domain model from business descriptions and validate it with corresponding concrete examples. Cover the domain model and object diagrams of sudo modeling without requiring system context or use case diagrams.

## Output Format and Language

- Default to one `.md` file with headings `ドメインモデル図` and `オブジェクト図`, each followed by a fenced `mermaid` block. Add scenario subheadings when multiple object diagrams are needed.
- When `.mmd` is requested or supplied as the output extension, save one diagram per file, for example, `domain-model.mmd` and `object-diagram.mmd`. Use raw Mermaid source without Markdown fences or prose. Give each diagram its Japanese title using Mermaid YAML frontmatter. If only one output path is supplied, use it for the domain model and derive a sibling path for the object diagram, reporting both paths.
- Write visible labels, attributes, aggregate names, rules, notes, and scenario descriptions in Japanese. Include English equivalents alongside Japanese concept names. Preserve established identifiers, proper names, and values.

## Inputs and Scope

Use business descriptions, target use cases, specifications, business rules, examples, and existing diagrams supplied or designated by the user.

- Narrow the scope for this iteration and prefer established terminology.
- Extract concepts, representative attributes, relationships, rules, and examples.
- Separate confirmed facts, assumptions, and open questions. Label fictional examples and provisional translations accordingly.
- Progress where information is sufficient. Ask necessary questions about business decisions that materially affect the model instead of silently settling them.

## Build the Model and Examples

Start with concrete examples or an existing model, then iterate between them to resolve inconsistencies.

### Domain Model Diagram

- Represent concepts with Japanese and English names and representative attributes. Methods and exhaustive field lists are not required.
- Show relationships and multiplicities for both ends, checking optionality and permitted counts against business rules.
- Attach rules and constraints to the relevant concepts or relationships.
- Include assumptions and open business questions when grounded in the task and useful to understanding or deciding the model. Distinguish them from confirmed rules.
- Determine aggregate boundaries after organizing concepts and rules. Identify aggregate roots and explain groupings as units for maintaining business consistency. Mark tentative boundaries accordingly.

Do not turn the task into an ER diagram or implementation class inventory. Distinguish entities and value objects when useful without forcing uncertain classifications.

### Object Diagram

- Make the type of every instance clear, for example, `注文A : 注文 (Order)`.
- Populate representative attributes with concrete values and draw links between actual instances.
- Show separate boundaries for separate aggregate instances, even when their aggregate type is the same.
- Identify the scenario and time represented. Do not mix states that cannot coexist.
- Select representative examples and add significant state differences or relationship count boundaries when useful. Do not fix the number of examples.
- Use separate before-and-after examples when needed to explain operations; a static diagram alone cannot prove operation behavior.

## Mermaid Notation

Use `flowchart` syntax as a structural modeling notation so aggregate boundaries, bold names, centered attributes, and notes share a consistent representation across both diagrams. These are domain and object diagrams, not process flows.

- Use stable ASCII node IDs and quoted Japanese display labels.
- Represent each aggregate with a named `subgraph`; explicitly label its root. Create a separate subgraph for each aggregate instance in object diagrams.
- Use Markdown string labels with a bold first line for concept names or instance headings, including English equivalents. Center-align all text inside concept and instance boxes with `text-align:center` in the node class.
- Use solid undirected links for associations. In domain diagrams, label each relationship with endpoint names and counts, such as `利用者 1 : 貸出 0..*`, so multiplicities cannot be confused with link direction.
- Express containment explicitly in the link label, such as `包含：貸出 1 : 返却記録 0..1`. In object diagrams, label containment links `包含` and show concrete instance links instead of type-level multiplicities. This is a textual equivalent of composition, not a UML diamond arrow.
- Use separate note nodes and dashed links to their subjects. Keep model elements and notes distinct.
- Choose `LR` or `TB` for readability. External links can override a subgraph's direction; inspect the rendered result rather than assuming a local direction is honored.

Use these default colors consistently unless the user specifies otherwise:

| Element | Fill | Border |
| --- | --- | --- |
| Concepts and instances | `#dae8fc` | `#6c8ebf` |
| Aggregate boundaries | `#f5f5f5` | `#666666` |
| Notes | `#fff2cc` | `#d6b656` |

Apply node colors through `classDef` and aggregate colors through `style` statements. Keep diagram-specific configuration inside each Mermaid block or source file so it remains self-contained.

## Check and Deliver

Before delivery and after updates, check that:

1. Every instance maps to a model concept with matching attributes and Japanese/English terminology.
2. Every link maps to a model relationship and concrete link counts satisfy both endpoint multiplicities.
3. Aggregate membership and references across boundaries agree between the diagrams.
4. Concrete values and states obey confirmed rules.
5. The important rules illustrated by the examples are identifiable.

Label invalid examples explicitly when requested. Resolve inconsistencies using the inputs; do not weaken confirmed rules to make examples pass. Update affected examples when the model changes.

Parse or render each diagram using the available Mermaid tooling. Inspect bold headings, centered text, Japanese labels, aggregate boundaries, and connector readability when rendering is available. Report any verification limits in the delivery message.

Deliver links to the requested `.md` or `.mmd` files with a concise account of major assumptions and open questions. Treat the model as a hypothesis to revise through implementation.

## Example and Sources

Read [assets/README.md](assets/README.md) and [assets/example.md](assets/example.md) for a Japanese lending model and matching instances. For `.mmd` output, save the contents of each fenced block as its own file. Preserve the bundled example and evaluate the target domain independently of its sample rules and values.

- Modeling basis: [Simple DDD Modeling — Domain-Driven Design](https://little-hands.hatenablog.com/entry/2022/06/01/ddd-modeling) (little hands' lab, June 1, 2022; Japanese).
- Mermaid syntax: [Flowcharts](https://mermaid.js.org/syntax/flowchart.html), including subgraphs, Markdown strings, and styling.

The Mermaid representation, output packaging, and default styling are this skill's design choices rather than requirements of the original modeling article.
