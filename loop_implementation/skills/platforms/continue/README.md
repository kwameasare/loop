# Continue.dev adapter

[Continue.dev](https://continue.dev) supports per-rule files in `.continue/rules/`.

## Install

```bash
mkdir -p .continue/rules
cp -r loop_implementation/skills/platforms/continue/rules/*.md .continue/rules/
```

## Format

Continue's rules are plain Markdown with optional `<rule>` XML wrappers for scoping. Loop's rules are written as the canonical skill bodies, with a small Continue-specific preamble:

```markdown
<rule name="implement-runtime-feature">
<scope>
  <files>packages/runtime/**, packages/sdk-py/**</files>
</scope>

# Implement runtime feature

<canonical skill body — Trigger, Required reading, Steps, Definition of done, Anti-patterns, References>

</rule>
```

## Generated from

Each `.md` rule mirrors `loop_implementation/skills/<category>/<name>.md`. Re-run:

```bash
python tools/build_platform_adapters.py --target=continue
```

## Always-on rule

`_base.md` has no `<scope>` — it applies globally. It contains the SKILL_ROUTER content + the hard rules. The other rule files are file-scoped via the `<scope>` tag.

## Skills location

The canonical skills are in `loop_implementation/skills/`. The Continue rules folder is generated from them; never edit the rules directly.
