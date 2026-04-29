---
name: write-ui-copy
description: Use when authoring any user-facing string — UI labels, button text, error messages, toast text, empty states, docs intros.
when_to_use: |
  - Adding/changing a button label.
  - Adding/changing an error message.
  - Adding an empty-state copy.
  - Adding a toast.
  - Writing a docs page lede.
required_reading:
  - engineering/COPY_GUIDE.md
  - ux/UX_DESIGN.md   # §5.5–§5.7 copy / errors / toasts
applies_to: ux
owner: Designer + author of the change
last_reviewed: 2026-04-29
---

# Write UI copy

## Trigger

Any user-facing string. Loop's voice is part of the product.

## Required reading

`engineering/COPY_GUIDE.md` end-to-end.

## Steps

1. **Apply the six rules** (COPY_GUIDE §2): verb-first; concrete > abstract; what failed + what to do; sentence case; don't anthropomorphize; no marketing voice.
2. **Use canonical words** (COPY_GUIDE §3 table). "agent" not "bot", "trace" not "log", "deploy" not "push".
3. **Errors:** what failed → why → what to do next. Always a recovery path.
4. **Empty states:** lead with what the user can do.
5. **Loading:** none < 1s; skeleton 1–3s; message > 3s; progress + estimate + cancel > 10s.
6. **Toasts:** match variant tone (COPY_GUIDE §5).
7. **Localize:** strings in `apps/studio/locales/<lang>.json`. No literals in components.
8. **Review by Designer** for any net-new pattern.

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Conforms to COPY_GUIDE rules.
- [ ] Recovery path on every error.
- [ ] Localized (en at minimum).
- [ ] Sentence case.
- [ ] No forbidden words ("Awesome!", "Whoops!", "synergy", "frictionless", …).

## Anti-patterns

- ❌ Marketing voice in errors.
- ❌ "Sorry, something went wrong" with no next step.
- ❌ Title Case on buttons.
- ❌ Literal strings in components.

## Related skills

- `ux/add-studio-component.md`, `coding/implement-studio-screen.md`.

## References

- `engineering/COPY_GUIDE.md`.
- `ux/UX_DESIGN.md` §5.5–§5.7.
