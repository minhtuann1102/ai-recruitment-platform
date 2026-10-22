# Domain pitfalls and sources

Per track: where to verify, and claims that often go stale. Each "known change" below is a starting point for
the check, not a substitute for it: fetch the current page and quote it, since releases after this file was
written may have changed things again. Prefer official docs and specs over blogs; a blog quote gives at most
`confidence: medium`.

## Frontend (`fe.*`, `hard-frontend.json`)

Sources: react.dev (docs + blog release posts), nextjs.org/docs, web.dev, developer.mozilla.org,
typescriptlang.org/docs, w3.org/WAI (WCAG, ARIA APG), html.spec.whatwg.org, playwright.dev, testing-library.com.

Check closely:
- React version behaviour: automatic batching (React 18 batches updates in timeouts and promises too), StrictMode
  double-invoking effects (development only), React 19 additions (Actions, `use`, `ref` as a prop,
  `useOptimistic`, `useActionState`). An answer that mixes versions without naming them is `outdated` or major.
- Next.js App Router caching changed in Next.js 15 (`fetch` and GET Route Handlers no longer cached by default).
  Server Components vs Client Components boundaries, `"use client"` / `"use server"` semantics.
- Core Web Vitals: INP replaced FID in March 2024. Thresholds: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 (good, at the
  75th percentile). Lab tools vs field data.
- Event loop: one task then all microtasks, rendering opportunity between tasks; `scheduler.yield()` and
  `isInputPending` browser support (check MDN compatibility, not just the explainer).
- TypeScript feature versions (`satisfies` 4.9, `using` 5.2, `const` type parameters 5.0) and strictness flags.
- Accessibility: WCAG 2.2 success criteria numbers and levels, ARIA roles from the APG, not from memory.

## Java (`java.*`, `hard-java.json`)

Sources: docs.oracle.com/en/java/javase, openjdk.org/jeps, the JDK source on github.com/openjdk/jdk,
docs.spring.io, docs.jboss.org/hibernate, jakarta.ee/specifications.

Check closely:
- `HashMap` treeification: `TREEIFY_THRESHOLD = 8`, `UNTREEIFY_THRESHOLD = 6`, `MIN_TREEIFY_CAPACITY = 64`
  (quote the JDK source). Behaviour with keys that are not `Comparable`.
- Virtual threads (final in JDK 21): pinning on `synchronized` was removed by JEP 491 (JDK 24); answers that say
  "virtual threads always pin in synchronized" need a version qualifier.
- GC: G1 default since JDK 9; generational ZGC (JEP 439, JDK 21) became the ZGC default in JDK 23 (JEP 474).
- `ConcurrentHashMap` locking details changed in JDK 8 (no segments); answers describing segments are `outdated`.
- Spring: `@Transactional` self-invocation through the proxy, propagation and rollback rules (runtime exceptions
  by default), Spring Boot 3 needs Java 17 and the `jakarta.*` namespace.
- Hibernate/JPA: N+1 and its fixes (`JOIN FETCH`, `@EntityGraph`, batch size), `open-in-view` default warning.

## Node.js (`node.*`, `hard-nodejs.json`)

Sources: nodejs.org/api, nodejs.org/en/learn, docs.libuv.org, github.com/nodejs/node release notes, v8.dev.

Check closely:
- Event loop phases (timers, pending callbacks, poll, check, close) and where `process.nextTick` and promise
  microtasks run; `setImmediate` vs `setTimeout(0)` ordering (only deterministic inside an I/O callback).
- libuv thread pool: default size 4, `UV_THREADPOOL_SIZE`; which APIs use it (fs, dns.lookup, some crypto, zlib).
- Streams backpressure: `write()` returning false, `'drain'`, `pipeline()`; `highWaterMark` units.
- Version-dependent features: global `fetch`, built-in test runner, `require()` of ES modules (unflagged in
  22.12 and 20.19), permission model, `worker_threads` vs `cluster`.
- Memory: V8 heap limits and flags (`--max-old-space-size`), heap snapshots; claims of exact default heap size
  depend on version and machine memory.

## Python (`py.*`, `hard-python.json`)

Sources: docs.python.org/3, peps.python.org, the CPython source, docs.djangoproject.com, fastapi.tiangolo.com,
docs.sqlalchemy.org.

Check closely:
- GIL: free-threaded build (PEP 703) experimental in 3.13; PEP 779 made it supported (not default) in 3.14.
  Per-interpreter GIL (PEP 684, 3.12). "Python cannot run threads in parallel" needs a qualifier now.
- asyncio: `TaskGroup` and `timeout()` (3.11), cancellation semantics, blocking calls in the loop,
  `asyncio.to_thread`.
- Memory: reference counting plus generational cycle GC; `__del__` and cycles; `sys.getrefcount` caveats.
- Data model: descriptors, MRO (C3), `__slots__`, mutable default arguments, `is` vs `==` with interning.
- Framework claims (Django ORM N+1 with `select_related`/`prefetch_related`, FastAPI sync vs async endpoints run
  in a thread pool) must be quoted from that framework's docs.

## DevOps (`devops.*`, `hard-devops.json`)

Sources: kubernetes.io/docs, docs.docker.com, developer.hashicorp.com/terraform, prometheus.io/docs,
docs.github.com/actions, opentelemetry.io/docs, cloud vendor docs for vendor-specific claims.

Check closely:
- Kubernetes: liveness vs readiness vs startup probes, rolling update `maxSurge`/`maxUnavailable`, HPA
  (`autoscaling/v2`), PodDisruptionBudget, requests vs limits and CPU throttling vs OOMKill, QoS classes.
  Removed features: dockershim (1.24), PodSecurityPolicy (1.25, replaced by Pod Security Admission).
- Docker: layer caching order, multi-stage builds, BuildKit, `COPY` vs `ADD`, running as non-root.
- Terraform: state locking, drift, `for_each` vs `count`, import blocks (1.5+), licence change to BSL in 1.6
  (OpenTofu fork) if the answer mentions it.
- Observability: Prometheus pull model, histogram vs summary, cardinality; SLI/SLO/error budget definitions from
  the Google SRE book.
- Vendor-specific numbers (limits, prices, quotas) are the most likely to be stale: quote the vendor page or mark
  `unverified`.

## AI (`ai.*`, `hard-ai.json`)

Sources: modelcontextprotocol.io/specification (latest revision and changelog), platform.openai.com/docs,
docs.anthropic.com, ai.google.dev, huggingface.co/docs, arxiv.org (original papers), pytorch.org/docs,
the vector database's own docs (pgvector README, etc.).

Check closely:
- Vendor features and limits change fastest: model names, context windows, structured outputs, prompt caching,
  batch APIs, pricing. A claim tied to one vendor must name the vendor and be quoted from its current docs, or be
  rewritten vendor-neutral.
- MCP: transports (stdio, Streamable HTTP; HTTP+SSE deprecated), tools vs resources vs prompts, `isError` for tool
  execution errors vs JSON-RPC protocol errors, authorization (OAuth 2.1 resource server, no token passthrough),
  structured tool output. Quote the spec revision you used.
- RAG: chunking trade-offs, hybrid search (BM25 + vector), reranking, evaluation metrics (recall@k, MRR, nDCG;
  faithfulness/groundedness), embedding dimensions per model (`text-embedding-3-small` = 1536).
- Training/ML: attention complexity, KV cache, quantization formats, LoRA/QLoRA, RLHF vs DPO: quote the paper or
  library docs; exact hyperparameter defaults are version-dependent.
- Agents: tool-call loops, guardrails, prompt injection defences. Claims of "best practice" need a source or
  should be phrased as one option among trade-offs.
