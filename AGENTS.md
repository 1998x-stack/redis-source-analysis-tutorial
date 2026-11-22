# AGENTS.md — Redis Source Analysis Tutorial
## Mission
Maintain 28 standalone, evidence-grounded Chinese Redis source tutorials. Optimize for reader understanding, not promotional landing pages. An article must make sense to a reader who lands on it directly.
## Repository / publishing
- `docs/` is the canonical GitHub Pages publish directory; `docs/index.html` is the course home. `docs/chapters/NN.html` are canonical articles. `docs/assets/css/site.css` is the source of shared styling; `docs/assets/js/` is progressive enhancement; `docs/assets/svg/` has original standalone diagrams.
- `docs/01.html`…`docs/28.html` and historical root links redirect to canonical articles. Do not break existing public URLs.
- Chapters 06–28 are preserved legacy material pending audit; do not silently assert they are validated. They use `docs/chapters/theme.css` compatibility styling.
- Avoid server-specific tooling or remote fonts/scripts: pages must render statically from file paths or GitHub Pages subpath.
## Technical correctness
- The first five articles pin source links to Redis **7.2.4**; distinguish Redis 7.2 implementation from Redis 8. Redis 7.4 licensing differs, Redis 8 has multi-license options: do not conflate versions.
- Verify every symbol / signature / layout against version-pinned Redis upstream source. Differentiate Redis object encodings (embstr/raw/int) from SDS header types.
- Never state every Redis allocation has a prefix: `HAVE_MALLOC_SIZE` determines the zmalloc path.
- Redis 7.2 List may use direct listpack or quicklist; do not state quicklist is the sole List encoding.
- Include runnable minimal commands, expected observations, caveats, and primary-source references.
## Olah-style workflow
Follow https://github.com/1998x-stack/Olah-style-posts/tree/main/skills/olah-style-paper-posts/SKILL.md and the relevant references (narrative, SVG, HTML, evidence, browser QA).
Progression: problem → mechanism → multi-step original diagrams → source/code trace → reproducible minimal experiment → boundaries → references. Original diagrams only; no copied Colah assets.
Every figure needs a source-grounded claim, standalone SVG `xmlns/viewBox/title/desc`, font-safe labels and a visible caption. Figures communicate without JS. Keep one H1 and a usable internal TOC per article; `main/article/section` semantics, accessible focus, mobile and print rules.
Do not surface AI/toolchain/style credits or production notes in an article byline.
## Validation gates
Run `python3 scripts/validate_site.py` before a PR. Check all 28 article links, local media, XML SVG parsing, titles/H1/section hierarchy and absence of broken relative links. Capture 1440px desktop and 390px and 360px mobile in Chromium when available, check overflow and JS console errors, and record any unverified QA.
GitHub Actions: CI validates the site; Pages workflow deploys `docs/` if GitHub Pages source is set to GitHub Actions. A workflow file alone does not guarantee Pages is live.
## Editing rules
Use branches and PRs, preserve 28-article coverage and historical URLs. Do not use page-local 28-item sidebar duplication for rewritten articles. Update the catalog status only after evidence and browser review; never claim a test passed unless executed.