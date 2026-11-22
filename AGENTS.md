# AGENTS.md — Redis Source Analysis Tutorial
## Mission
Maintain 28 standalone, evidence-grounded Chinese Redis source tutorials. Optimize for reader understanding, not promotional landing pages. An article must make sense to a reader who lands on it directly.
## Repository / publishing
- `docs/` is the canonical GitHub Pages publish directory; `docs/index.html` is the course home. `docs/chapters/NN.html` are canonical articles. `docs/assets/css/site.css` is the source of shared styling; `docs/assets/js/` is progressive enhancement; `docs/assets/svg/` has original standalone diagrams.
- `docs/01.html`…`docs/28.html` and historical root links redirect to canonical articles. Do not break existing public URLs.
- Chapters 21–28 are preserved legacy material pending audit; do not silently assert they are validated. They use `docs/chapters/theme.css` compatibility styling.
- Avoid server-specific tooling or remote fonts/scripts: pages must render statically from file paths or GitHub Pages subpath.
## Technical correctness
- The first twenty articles pin source links to Redis **7.2.4**; distinguish Redis 7.2 implementation from Redis 8. Redis 7.4 licensing differs, Redis 8 has multi-license options: do not conflate versions.
- Verify every symbol / signature / layout against version-pinned Redis upstream source. Differentiate Redis object encodings (embstr/raw/int) from SDS header types.
- Never state every Redis allocation has a prefix: `HAVE_MALLOC_SIZE` determines the zmalloc path.
- Redis 7.2 List may use direct listpack or quicklist; do not state quicklist is the sole List encoding.
- Include runnable minimal commands, expected observations, caveats, and primary-source references.
## Olah-style workflow
Follow https://github.com/1998x-stack/Olah-style-posts/tree/main/skills/olah-style-paper-posts/SKILL.md and the relevant references (narrative, SVG, HTML, evidence, browser QA).
Progression: problem → mechanism → multi-step original diagrams → source/code trace → reproducible minimal experiment → boundaries → references. Original diagrams only; no copied Colah assets.
Every figure needs a source-grounded claim, standalone SVG `xmlns/viewBox/title/desc`, font-safe labels and a visible caption. Figures communicate without JS. Keep one H1 and a usable internal TOC per article; `main/article/section` semantics, accessible focus, mobile and print rules.
Do not surface AI/toolchain/style credits or production notes in an article byline.
- Redis 7.2.4 dict uses ht_table/ht_used/ht_size_exp arrays and default SipHash; do not apply older dictht/MurmurHash2 descriptions.
- Redis 7.2.4 Set can be intset, listpack or HT; ZSET listpack or skiplist. Redis Hash Field Expiration belongs to 7.4+, not 7.2.4.
- For blocking List commands, model client state transitions, not blocking the event loop; explain no built-in acknowledgement guarantee for BLPOP.
- Redis 7.2 Stream uses rax/listpack and two referenced PEL indices (group and consumer); XACK removes pending status, not the Stream entry.
- GEOADD encodes coordinates as a 52-bit sortable score and calls ZADD; actual radius queries require distance filtering.
- HyperLogLog is a special String-valued format: 2^14 registers × 6 bits = 12288 bytes dense payload plus header; estimates are not exact set membership.
- Redis 7.2 aeTimeEvent is an *unsorted doubly linked list*, not a timer heap; serverCron is a time-event callback with dynamic-hz and per-task budgets.
- Redis 7.2 I/O threads process selected network reads/writes via fan-out/fan-in. Do not claim arbitrary parallel command execution; replies can remain buffered after addReply.
- Redis 7.2.4 `resp_parser.c` parses replies returned by RM_Call / Lua `redis.call()`; client request parsing is in `networking.c`.
- RDB 7.2.4 uses `RDB_VERSION 11`; distinguish RDB type codes from in-memory object encodings. `rdbSaveBackground` forks a child; COW copies pages modified after fork, not the whole dataset at fork time.
- Multi-Part AOF has existed since Redis 7.0. Redis 7.2 uses a manifest with BASE / INCR / HISTORY; during rewrite the parent opens a new INCR before the child builds BASE. Do not apply the pre-7.0 in-memory rewrite-diff-buffer explanation to 7.2.
- Redis 7.2 AOF BASE may be RDB preamble (`.base.rdb`) or command AOF (`.base.aof`); INCR files contain later command stream.
- Expiration and maxmemory eviction are independent. `db->expires` stores absolute expiration times; replicas logically hide expired keys but do not independently delete them in read-only mode. Active expiry is sampled and budgeted.
- Redis 7.2 eviction supports noeviction, allkeys/volatile LRU, LFU, random and volatile-ttl; do not include later LRM policies. LRU/LFU are approximate.
- Redis 7.2 replication uses shared refcounted `replBufBlock` list and rax block index; avoid claiming it is literally a standalone fixed byte-array ring. `replid2` is valid only through `second_replid_offset`.
- Replication is asynchronous; WAIT reduces loss probability but is not a strong-consistency consensus protocol.
## Validation gates
Run `python3 scripts/validate_site.py` before a PR. Check all 28 article links, local media, XML SVG parsing, titles/H1/section hierarchy and absence of broken relative links. Capture 1440px desktop and 390px and 360px mobile in Chromium when available, check overflow and JS console errors, and record any unverified QA.
GitHub Actions: CI validates the site; Pages workflow deploys `docs/` if GitHub Pages source is set to GitHub Actions. A workflow file alone does not guarantee Pages is live.
## Editing rules
Use branches and PRs, preserve 28-article coverage and historical URLs. Do not use page-local 28-item sidebar duplication for rewritten articles. Update the catalog status only after evidence and browser review; never claim a test passed unless executed.