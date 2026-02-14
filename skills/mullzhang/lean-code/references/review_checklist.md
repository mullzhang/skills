# Code Review Checklist

After generating code, review the items below. If any item applies, revision is required.

## Over-Defensiveness Check

- [ ] No unreachable fallback paths exist (for example, handling a legacy format that does not exist)
- [ ] No exceptions that should never occur are silently swallowed inside `try-except`
- [ ] "Just in case" default values are not hiding bugs
- [ ] No branch paths are impossible in the current codebase

## DRY Check

- [ ] Identical or near-identical logic does not exist in two or more places
- [ ] No copy-pasted functions with only minor edits
- [ ] Logic that can be shared is not expanded inline repeatedly

## YAGNI Check

- [ ] No functions/methods currently have zero call sites
- [ ] No abstraction layers are added for requirements that do not exist yet
- [ ] No unused parameters, options, or configuration values remain
