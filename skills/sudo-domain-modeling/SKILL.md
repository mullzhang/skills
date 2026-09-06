---
name: sudo-domain-modeling
description: Create and update Japanese domain model diagrams and corresponding object diagrams using sudo modeling. Derive concepts, attributes, relationships, multiplicities, aggregates, and business rules from business descriptions, specifications, use cases, or existing models, and validate them against concrete examples. Delegate diagram rendering to the draw-io skill.
---

# sudo Domain Modeling

Build a domain model from business descriptions, validate it with corresponding concrete examples, and deliver an editable `.drawio` file.
Cover the domain model and object diagrams of sudo modeling. Do not require system context or use case diagrams as prerequisites.

## Output Language

Write the generated draw.io diagrams in Japanese, including page titles, attributes, relationship labels, aggregate names, rules, constraints, scenario descriptions, and notes.
Use Japanese concept names with their English equivalents alongside them. Preserve established identifiers, proper names, and values that should not be translated. English instructions in this skill do not imply English diagram output.

## Division of Responsibilities with draw-io

This skill handles model semantics, example selection, and consistency between the diagrams.
Delegate XML structure, shapes, connectors, coordinates, layout, file creation, editing, and opening to `draw-io`.

Before rendering or reading existing diagrams, locate and read the `draw-io` skill's `SKILL.md` through the available skill catalog, then follow its applicable workflow and references. Do not hardcode an installation path.
If it is unavailable, continue organizing the model and examples, then report the missing dependency required for rendering. Do not substitute an independent XML generation procedure.

## Inputs and Scope

Use the business descriptions, target use cases, specifications, business rules, examples, and existing diagrams supplied or designated by the user. Do not require a fixed input format.

- Narrow the business scope and use cases for this iteration, distinguishing what is out of scope.
- Extract Japanese and English concept names, representative attributes, relationships, rules, and examples. Prefer established terminology.
- Separate confirmed facts, assumptions, and open questions. Label provisional translations and generated fictional examples accordingly.
- Make progress where information is sufficient. Ask necessary questions about business decisions that materially affect the model, and do not depict them as settled before receiving answers.

## Build the Model and Examples

Start by abstracting concrete examples or by instantiating an existing model. Iterate between the two to resolve inconsistencies.

### Domain Model Diagram

- Represent business concepts as boxes labeled with Japanese names and corresponding English names.
- Include representative attributes. Do not require an exhaustive field list or methods.
- Show relationships and multiplicities at both ends. Check optionality and permitted counts against business rules.
- Attach rules and constraints as callouts or notes to the relevant concepts or relationships.
- Include assumptions and open business questions only when grounded in the task and relevant to understanding or deciding the model. Distinguish them from confirmed rules with labels, not color alone. Do not invent open questions to demonstrate notation.
- Determine aggregate boundaries after organizing concepts and rules. Identify aggregate names and roots, and explain each grouping as a unit for maintaining business consistency.
- Mark tentative aggregate boundaries in the diagram. Do not group concepts into one aggregate merely because they are related.

Do not turn the task into producing an ER diagram or an implementation class inventory. Distinguish entities and value objects when useful for a decision, without forcing uncertain classifications.

### Object Diagram

- Name each instance so its type is clear, for example, `注文A : 注文 (Order)`.
- Populate representative model attributes with concrete values and draw actual links between instances.
- Show the boundary of each aggregate instance. Depict separate instances as separate groups even when they share an aggregate type.
- Briefly describe the scenario and the point in time represented. Do not mix states that cannot coexist at that time.
- Do not fix the number of examples. Supplement representative examples as needed to cover significant state differences and relationship count boundaries.
- Static diagrams cannot prove operation preconditions or state transitions. When necessary, supplement them with separate before-and-after examples and notes.

## Check Correspondence

Before rendering and after editing, verify the following:

1. Every instance maps to a model concept, with consistent attribute names, type meanings, and Japanese/English terminology across both diagrams.
2. Every link maps to a model relationship, and each instance's link counts satisfy the multiplicities at both ends.
3. Aggregate membership and references across aggregate boundaries agree between the diagrams.
4. Concrete attribute values, states, and combinations obey confirmed business rules.
5. It is clear which examples exercise important rules, and any aspects not checked by examples remain documented.

If invalid examples are requested, label them with the rules they violate so they cannot be mistaken for valid examples.
When an inconsistency appears, use the inputs to decide whether to revise the model or the example. Do not weaken a confirmed rule simply to make an example pass.

## Render and Update

By default, use one `.drawio` file with pages named `ドメインモデル図` and `オブジェクト図`. Split examples into scenario-specific pages when needed. Honor user-specified destinations and organization.

Use the following default colors consistently across both diagrams, unless the user specifies a different palette:

| Element | Fill | Border |
| --- | --- | --- |
| Domain concepts and object instances | Blue `#dae8fc` | `#6c8ebf` |
| Aggregate boundaries | Gray `#f5f5f5` | `#666666` |
| Notes and callouts | Yellow `#fff2cc` | `#d6b656` |

Prepare box labels and attributes, relationship endpoints and multiplicities, aggregate groups, note targets, and page organization for `draw-io`.
Render domain concept names and object instance headings in bold, including their English equivalents. Center-align all text inside concept and instance boxes.
After generation, inspect the appearance using available viewing or export tools. Correct clipped text, overlaps, and ambiguous connectors or notes. If visual inspection is unavailable, report that it was not performed.

When updating an existing diagram, check examples corresponding to changed concepts, attributes, relationships, and rules, and apply necessary changes to them as well.

Deliver the file link with a brief account of major assumptions, open questions, and verification limits. Treat the model as a hypothesis to validate and revise through implementation; do not expand the work indefinitely in pursuit of a perfect first version.

## Source and Additional Design Choices

For a concrete example of notation and correspondence, read [assets/README.md](assets/README.md) and inspect [assets/example.drawio](assets/example.drawio) using `draw-io`. The two Japanese pages show a fictional lending model and matching instances. Use them as a reference, not as business requirements; preserve the bundled sample when creating task-specific output.

Source: [Simple DDD Modeling — Domain-Driven Design](https://little-hands.hatenablog.com/entry/2022/06/01/ddd-modeling) (little hands' lab, June 1, 2022; article in Japanese).

Use the source's notation and its approach of iterating between concrete examples and abstract models. Correspondence checks, explicit assumption labels, page organization, and rendering delegation are this skill's operational choices, not mandatory procedures prescribed by the source. Do not carry the source's recruitment-specific rules or color scheme into other business domains.
