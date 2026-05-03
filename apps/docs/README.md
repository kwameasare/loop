# Loop Mintlify docs (apps/docs)

This is the public-facing docs site at `docs.loop.example`. It is a
[Mintlify](https://mintlify.com) project — `mint.json` defines the
navigation, every other file is MDX content.

## Local preview

```bash
npx mintlify@latest dev
```

The dev server reloads on save and exits with non-zero on a broken
link or invalid frontmatter, which is what `tools/check_docs_links.py`
hooks into.

## Deploy

```bash
npx mintlify@latest deploy
```

The deploy command authenticates against the Mintlify CLI and
publishes to the `docs.loop.example` project. CI runs this on every
merge to `main` after `tools/check_docs_links.py` is green.

## Editing rules

- The canonical engineering docs live in
  [`loop_implementation/engineering/`](../../loop_implementation/engineering/)
  and [`docs/`](../../docs/). The pages in this directory are
  intentionally short — they exist to give external readers a
  navigable, branded entry point and link back to the source of
  truth in the repo. **Never duplicate substantive content here**;
  always link.
- Every new MDX page must be added to `mint.json#/navigation` or
  Mintlify will refuse to build.
- Frontmatter is required: `title`, `description`. Both surface in
  search results.

## Story trail

- **S915** — initial Mintlify project with quickstart, 5 concept
  pages, 3 tutorials, 3 operations pages, an API reference, and a
  cookbook recipe.
