# Minimal MkDocs implementation plan

**Goal:** Give Doctopus a crisp monochrome documentation site.

**Design:** The user selected crisp monochrome over warm white/lavender and
dark-first alternatives. Use white and near-black surfaces, fine neutral borders,
strong typography, generous spacing, and restrained interactions. Keep Material,
the technical documentation, built-in search, code copying, and theme switching.
Use a two-column introduction with a real Python example, capability strip,
three feature summaries, interface examples, and a short routing sequence.
Stack the layout on mobile. No custom JavaScript or dependencies.

**Tech stack:** MkDocs Material, Markdown with HTML, CSS.

## Tasks

- [x] Update `mkdocs.yml`: consolidate navigation and use two explicit light/dark
  palettes. Preserve existing documentation routes.
- [x] Rewrite `docs/index.md`: clear introduction, working links, accurate claims,
  native code blocks and tabs, and a semantic routing list.
- [x] Replace `docs/stylesheets/extra.css`: neutral tokens, navigation and reading
  styles, homepage layout, responsive breakpoints, keyboard focus, reduced motion.
- [x] Run `.venv/bin/mkdocs build --strict` and fix warnings or broken links.
- [x] Inspect desktop/mobile homepage and documentation; exercise search, tabs,
  theme switching, and mobile navigation in a browser.

## Review focus

Readable contrast in both palettes; mobile overflow and navigation; wide tables
and code scrolling; relative links under the GitHub Pages base path; and native
Material controls after instant navigation. Verify this presentation-only change
with the strict docs build and browser checks.

## Verification

- Strict MkDocs build and `git diff --check`: pass.
- Homepage checked at 320, 390, 768, 1024, and 1440 pixels: no page overflow.
- Engines page checked on desktop and at 390 pixels: table scroll stays contained.
- Light/dark palette, CLI/MCP tabs, mobile drawer, and search verified in Chrome.
- All 36 homepage relative links and assets resolve in the built site.
