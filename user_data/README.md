# User Data Layer

This is the default user-facing knowledge surface for Abyss.

It is **Obsidian-first**: notes should be easy to open, edit, link, search, and review directly inside Obsidian.

Recommended vault shape:

```text
Home.md
_inbox/
_templates/
_attachments/
directions/
projects/
decisions/
summaries/
promoted/
```

Conventions:

- Use Markdown `.md` as the primary format.
- Use YAML frontmatter for `type`, `status`, `created`, `updated`, `source`, `tags`, `aliases`, and `related` when useful.
- Prefer Obsidian wiki links such as `[[Project Name]]` for internal relationships.
- Keep images and binary attachments under `_attachments/` and link them relatively.
- Keep `Home.md` as the default human entry point and lightweight active-area map.
- Put reusable note templates under `_templates/`.
- Put archive material promoted into the active surface under `promoted/`, with provenance.

This layer is for:

- current directions
- active project notes
- working summaries
- decision records intended for daily use
- focused excerpts promoted from the storage layer

Real personal notes in this directory are ignored by Git by default. Keep only structural documentation in version control unless explicitly intended otherwise.

Implementation internals and bulk archives should not be placed here directly. If archived material becomes relevant, Abyss should promote or materialize a focused, provenance-preserving Markdown note into this layer.
