a few covnersations about adding th e9 gated orchestraotr to the city brain, tha tproject eveolved over multiple stages and code bases, an early version is this text and the resat is pasted

Viewed CURRENT-STATE-ARCHITECTURE.md:1-800



Edited handover_summary.md



I have compiled a comprehensive handover summary of the architectural evolution and contract changes from the April 2026 cleanup sprints. 



You can review the full details in the newly created artifact: [handover_summary.md](file:///C:/Users/hazem/.gemini/antigravity/brain/bbdd84b0-0eae-4211-a8f9-dc657c25e89e/handover_summary.md).



### High-Level Summary



The project underwent a "surgical cleanup" to address significant architectural drift. 



**The Initial Problem:** The orchestrator had ballooned into a fragile 9-stage system. The LLM Planner was doing too much heavy lifting (intent extraction, entity binding, and generating complex execution graphs), which resulted in high latency, imprecise outputs, and the need for expensive "Repair Loops" inside the orchestrator to fix bad plans.



**The Solution:** The architecture was strictly separated into two deterministic layers to replace the freeform planner:



1.  **The Intent Resolver (Upstream):** Replaced the LLM planner's job of "understanding the user." It uses a "Hero-Pattern First" approach (regex/deterministic matching) to quickly anchor the user's query to a specific community and metric, producing a strict **Validated Request Contract**. It fails fast if it cannot resolve the intent, eliminating repair loops.



2.  **The Execution Planner / Compiler (Downstream):** Acts as a compiler rather than a "thinker." It takes the Validated Request Contract and blindly maps it to flat, parallel data fetches (Scatter-Gather), emitting an **Execution Plan Package**. This explicitly removed complex, multi-hop graph execution in favor of speed and stability.



As a result, `orchestrator.js` was stripped of all its "patching" and coercion logic, returning to its intended role as a lean runtime shell that just coordinates these bounded stages.



another version

an command: `git log --since="2026-03-20" --until="2026-04-20" --stat`

Viewed dld_orchestrator_technical_spec.md:1-142

Viewed UNREAL_INTEGRATION.md:1-91



Here is a handover summary of the DLD AI Agentic Orchestrator's evolution, architecture, and contracts during the intensive development period in early to mid-April 2026. 



### 1. Initial Design & Vision

The project started with a clear goal: to build the **RTX-Ollama Hardened Baseline with Neural Audio**. The objective was to create a high-performance middleware that bridges natural language intent with Dubai Land Department (DLD) transaction data and Unreal Engine visualizations. 



We targeted **sub-5 second perceptual latency** on high-end hardware (specifically RTX 5090) while maintaining strict deterministic accuracy. The initial stack was established using Node.js, `better-sqlite3` in WAL mode for lightning-fast caching/memory, `fuzzysort` for high-performance entity RAG, and a dual-model LLM inference strategy combining native `node-llama-cpp` and external Ollama APIs.



### 2. Architectural Evolution: The 6-Stage Pipeline

The architecture rapidly evolved into a highly optimized, deterministic **6-stage pipeline** to balance agentic reasoning with strict data accuracy:



1. **Recall & Static RAG (Pre-processing):** Before hitting the LLM, the system performs "Narrow RAG" using fuzzy matching against 150+ Communities and 130+ Master Projects. A composite cache key enables sub-50ms responses for cached queries.

2. **Intent Mapping (The Planner):** A fast 3B model (e.g., Llama-3.2-3B) acts as the planner, converting natural language into a machine-readable JSON intent using strict GBNF grammars or schema-constrained formats.

3. **Data Execution (The Skill Layer):** The orchestrator maps the JSON to deterministic tools (e.g., `get_trend`, `compare_periods`, `get_summary`) to compute complex metrics like YoY deltas and Price/SQM averages.

4. **Parallel Tracks (Visualization & Synthesis):** To minimize latency, the pipeline forks. Track B deterministically builds an Apache ECharts configuration. Track C streams the data into an 8B synthesizer (e.g., Llama-3.1-8B) to generate a persona-driven narrative.

5. **Deterministic Action Resolver:** Converts the resolved data into concrete Unreal Engine actions (e.g., if "Dubai Marina" is the top result, it emits a `focus_community` action for the camera).

6. **Distillation & Memory (Post-Turn):** A background non-blocking distiller updates a SQLite database with user traits and session state for future context.



### 3. Hardening & Production Safeguards

As the pipeline matured, we introduced several critical safeguards to prevent LLM hallucinations and ensure production readiness:

* **The Repair Pass:** If the Planner generates invalid JSON, the system traps the error and re-invokes the Planner once with the error as feedback (eliminating ~90% of structural hallucination issues).

* **Confidence Gates:** Every plan includes a confidence score. Anything below a `0.6` threshold bypasses execution and triggers a clarification fallback.

* **No-LLM "Hero" Fallback:** High-frequency, standard queries (like "Top 5 communities") use regex matching to bypass the LLM entirely, yielding <50ms latency.

* **Anti-Drift Prompting:** The Synthesizer model was strictly constrained to prevent it from renaming metrics or creating causal implications for simple data trends.

* **Automated QA:** We built a data-driven validation framework featuring a **Golden Set** of 50 bilingual (English/Arabic) test queries to benchmark regression, pass/fail matrices, and latency.



### 4. Neural Audio Integration (TTS)

We implemented a local text-to-speech infrastructure using the **Piper TTS engine**. This involved deploying a local HTTP wrapper server (port 5000) and integrating a `ttsService.js` to enable real-time, sentence-level audio streaming directly into the narrative synthesis pipeline.



### 5. Contract Changes: Unreal Engine Integration

The contract between the Orchestrator and the Unreal Engine client was codified over WebSockets (defaulting to port 3000). The architecture shifted to a highly event-driven streaming model.



**Unreal Request Contract:**

```json

{

  "type": "request",

  "question": "Show me sales volume in Dubai Marina for this year",

  "sessionId": "UE_Client_01"

}

```



**Agent Response Streams (Multiple payloads sent per turn):**

1. **Narrative Text (`answer_chunk`):** Streamed text tokens for UI captioning.

2. **Audio Stream (`audio_chunk`):** Sentence-level binary buffers (WAV 16-bit, 22050Hz Mono) ready to be fed directly into Unreal's `SoundWaveProcedural`.

3. **Unreal Actions (`unreal_actions`):** Metadata instructing the Unreal client to change camera focus, adjust UI sliders, or open specific chart widgets.

    * *Example:* `{ "action": "focus_community", "params": { "community": "Dubai Marina" } }`

4. **Data Visualization (`chart`):** A complete Apache ECharts `option` object to be passed directly into an Unreal WebBrowser widget.



***



*Note: All background agents and subtasks have been stopped due to a server restart. If you had any active tasks running prior to this, they will need to be revived.*

another # Spark Orchestrator: Architectural Handover Summary (April 2026 Sprints)



## 1. Initial State & Architectural Drift (Pre-Cleanup)



Prior to the cleanup sprints, the Spark Orchestrator had evolved from a lean 5-stage pipeline into a complex, fragile **9-stage system**. The architecture suffered from significant "drift," primarily centered around the **Planner**.



*   **The "Bloated" Planner:** The LLM-driven planner was tasked with too much responsibility. It attempted to understand user intent, extract entities, determine metrics, and generate complex "Graph-Based Execution" plans (`steps`, `depends_on`, `output_aliases`).

*   **The "Patching" Orchestrator:** Because the planner's freeform JSON output was often imprecise or missing critical constraints (like a geographic community anchor), `orchestrator.js` grew massively to compensate. It housed extensive logic for "plan coercion," "default patching," and expensive LLM-on-LLM **Repair Loops**.

*   **Performance & Reliability Hits:** The reliance on the LLM to generate multi-stage investigative workflows for routine queries resulted in high latency and frequent validation failures.



## 2. Architectural Evolution: The "Surgical Cleanup"



The core objective of the 2-week sprint was to strip the complex graph reasoning out of the hot path and split the monolithic planner into two distinct, deterministic layers.



### A. The Intent Resolver (Upstream)

The responsibility for "understanding the user" was moved out of the LLM planner and into a new, fast **Intent Resolver**.

*   **Hero-Pattern First:** Prioritizes deterministic regex/pattern matching for benchmark queries. The LLM is relegated to a "Bounded Field Completer" only when fields are missing.

*   **Mandatory Anchoring:** It enforces that no query can proceed without being anchored to the data model (specifically, a `community_id`).

*   **Fail-Fast:** If intent cannot be resolved to a strict contract, it fails early or clarifies, eliminating the need for downstream repair loops.



### B. The Execution Planner / Compiler (Downstream)

The role of planning execution was shifted to a **Compiler**.

*   **No Reinterpretation:** It takes the validated intent and blindly maps it to execution operators. It does not guess what the user meant.

*   **Flattened Execution:** Graph-based sequential reasoning (`INVESTIGATION`, `DECOMPOSED` modes) was deprecated for common routes. Execution was flattened into flat, parallel fetches (Scatter-Gather modes like `simple_parallel` and `cross_domain_parallel`).



### C. The Lean Orchestrator (Runtime Shell)

`orchestrator.js` was stripped of all planner-fixing logic. Its sole job reverted to bounded runtime coordination: sequence stages, execute fetches, enforce timeouts, and stream outputs.



## 3. The New Contract Architecture



To enforce the new boundaries, loose JSON payloads were replaced with strict, schema-driven contracts handed between layers.



### 1. Validated Request Contract (Output of Intent Resolver)

A strict definition of what the user wants, anchored to the data model.

*   **Key Fields:** `intent_class`, `route_family` (e.g., `direct_fact`, `comparison`), `community_id_primary`, `metric_primary`, `time_window`.

*   **Rule:** The orchestrator will not proceed without this valid contract.



### 2. Execution Plan Package (Output of Execution Compiler)

The mapped actions required to fulfill the Request Contract.

*   **Key Fields:** `fetch_contracts` (the exact data API calls to make), `parallel_groups` (what can be fetched concurrently), `derived_features` (e.g., comparison delta computations), and an `answer_contract`.

*   **Rule:** Replaces the LLM-generated `steps` array.



### 3. Evidence Packet (Assembled by Orchestrator)

The normalized bundle of fetched data and derived signals, passed to the Renderer/Narrator.

*   **Key Fields:** Entity identity, metric values, trend series, data sufficiency flags, and proactive signal flags.



## 4. Key Handover Decisions & Implications



*   **Decision: Removal of Repair Loops.** 

    *   *Implication:* Massive latency reduction and predictable failure modes. The system now degrades cleanly to "insufficient evidence" or clarification rather than stalling.

*   **Decision: Deprecation of Sequential Graph Planning.** 

    *   *Implication:* While flattening to parallel fetches makes the system incredibly fast and stable for benchmark queries, it explicitly removes the system's ability to perform multi-hop reasoning (e.g., "Find the highest sales area, *then* look up its permits"). This is a known trade-off prioritizing executive demo stability over open-ended generative intelligence.

*   **Decision: Session Memory for Continuity.**

    *   *Implication:* Introduced lightweight session memory to track the `active_entities` and `active_thread`. This allows follow-up queries to feel conversational (e.g., "What about permits?") without requiring a heavy long-term memory architecture.

and one more 

Yep — I dug through the April history cluster and the validation artifacts, and the story is actually pretty coherent.
Scope
One honest caveat: the local git history is compressed into four April commits, but the artifacts and pack outputs show a much richer two-week architecture sprint.
So this summary is a handover of the design decisions, architecture evolution, and contract changes from that April buildout period.
I’m treating the April RTX checkpoint as the main end-state of that sprint, not the newer July Spark stage-split work.
Initial Design
The project started as a deterministic analytics pipeline for two data domains:DLD real-estate transaction intelligence
DM municipal / operational intelligence

The core design was:query -> deterministic normalization/grounding -> intent resolution -> retrieval -> optional investigation -> answer -> visual response

The original big decision was: facts stay deterministic.The system could use an LLM to help the resolver when needed, but not to invent metrics, communities, periods, or results.

From day 1, it was built as a contracted system, not a chatbot:strict route families
strict packet types
validation harness
benchmark runner
failure envelopes
replayable artifacts

What The First Architecture Established
A strong typed intent layer with:intent class
route family
answer shape
canonical metric
canonical period
resolved entities
missing/blocked slots

A whitelisted Retrieval V1 model:only specific route families are executable
retrieval builds evidence packets, not prose

An optional investigation layer:extra grounded context
never a freeform planner
capped step count

A deterministic answer composerit rendered facts/compare/ranking/breakdown/trend/no-data from evidence

A separate visual response layerchart/table/KPI decisions were made after answer generation

A full validation and benchmark frameworkstaged runs
orchestrator runs
packet snapshots
mismatch logs
replay support
cold/warm benchmark modes

How The Architecture Evolved
The next phase was not feature sprawl; it was resolver hardening by family.
The team pushed the system away from broad brittle heuristics and toward:explicit route families
explicit fallback policies
explicit scoped screeners
explicit audit categories

That evolution happened in roughly five architectural waves.
Wave 1: Deterministic Core Hardening
Community normalization got much stronger:alias handling
deformed-name recovery
industrial shorthand support
ordinal normalization

Metric resolution got more explicit:deterministic alias collapse
implied metric handling
bounded qualitative-to-metric mapping

Period handling got upgraded:relative periods
period-vs-period support
fallback normalization for expressions like previous month / previous quarter

Routing became more deliberate:compare preserved as compare
ranking preserved as ranking
breakdown preserved as breakdown
citywide fallback added where appropriate

This is where the system stopped behaving like “best effort parsing” and started behaving like a route-contract engine.
Wave 2: Validation Became A First-Class Product Surface
A major architectural choice was to treat validation as part of the product, not just QA.
The system gained:scored scenario packs
review artifacts
tail audits
family-level failure slicing
pack-level summaries
stage timings

That changed the development loop from:“fix a bug and spot check”

into:“identify a failure family, patch it narrowly, rerun the exact slice, then rerun the relevant pack”

Wave 3: Audit / Reporting Was Separated From Correctness
Once broad correctness improved, the reporting layer itself became noisy.
So the architecture was changed to separate:true failures
product-quality / polish
taxonomy/reporting mismatches
audit uncertainty

This produced the severity model:Severity 0 clean
Severity 1 taxonomy/reporting only
Severity 2 acceptable but weak
Severity 3 audit uncertain
Severity 4 real failure

This was a big architectural decision:a run with zero real failures should not look broken
taxonomy-only rows should not trigger error-style signaling

Wave 4: Scale-Up Through The 10k Suite
The 10,000-question suite changed the architecture conversation.
It exposed that the system was no longer mainly suffering from random misses; it was suffering from recurring families.
That led to:the overnight 10k runner
per-pack artifacts
family slices
targeted validation packs
checkpointed reruns
latency tracking by stage:intent resolver
data/retrieval
final answer


Architecturally, this is when the project became a family-fix system rather than a general cleanup system.
Wave 5: Long-Tail Became Its Own Phase
The long-tail pack was flat while curated/mutations/adversarial were improving.
That forced a separate architectural decision:long-tail is not “more of the same”
it needs its own bounded policy layer

So the system introduced explicit long-tail families like:bounded investigation clarify
citywide strategic screener
mixed-domain collision screener
anchored neighborhood screener
forward-proxy workload screener
resilience watchlist screener
operational stability compare/screener

The crucial decision here:do not answer everything
do not clarify everything
instead, answer supported strategic prompts through bounded screeners and use one targeted clarification when a family is unsupported

This was also the point where “around X” anchoring and forward-looking proxy semantics became formal architecture, not prompt hacks.
What Changed In Practice
Exact/deformed DM scope bugs were fixed by making deformed names commit to canonical scope early enough for retrieval/materialization.
Pairwise compare prompts were preserved as compare instead of collapsing into lookup.
Ranking prompts preserved citywide/top-N shape.
Long-tail anchored prompts preserved around X semantics instead of being forced back to citywide.
Forward-looking prompts stopped being treated as literal forecasts and were handled as proxy screeners.
Contract Changes That Matter
The most important handover point is that the project became much more contract-heavy over those two weeks.
1. Intent Contract
IntentPacket became the central resolver contract.
It carries:resolved route family
resolved answer shape
canonical metric
canonical periods
resolved entities and candidates
clarification questions
candidate options
ambiguity flags
proactive flags
resolver LLM telemetry

The important evolution was that resolved_slots stopped being just simple lookup slots and became the place where advanced routing state lived:citywide
compare sides
geo anchor
candidate-set scope
long-tail family
screener id
secondary metric
dimension/filter state

2. Retrieval Contract
RetrievalInputV1 and ResolvedRetrievalRequest formalized the handoff into retrieval.
Retrieval is only allowed for executable route families.
EvidencePacket became the source of truth for everything downstream:facts
rows
series
comparison block
lineage
confidence
gaps/warnings
no_data
partial_result
truncated

This is one of the strongest design decisions in the whole project:downstream layers are supposed to consume evidence packets, not reinterpret the raw query.

3. Investigation Contract
InvestigationPacket stayed bounded and grounded.
It contains:public plan
executed step packets
findings
candidate explanations
confidence
warnings/gaps

The key decision:investigation is an evidence-extender, not a freeform chain-of-thought planner.

4. Answer Contract
In the April sprint state, the answer contract became more explicit even though the answer renderer was still deterministic at that point.
AnswerPacket and ClarificationPacket separated:answered outputs
bounded clarification outputs

The answer contract includes:answer shape
source domain
answer text
chart hint
no-data / partial flags
grounding refs
generation metadata

Later Spark-prep work built on this, but the important April decision was already there:answers are grounded renderings of deterministic evidence, not freeform outputs.

5. Orchestrator Envelope
miniOrchestrator became the canonical stage envelope:intent_result
clarification
invalid_input
internal_error

It also carries:stage failures
degraded response decision
stage timings

This matters because the system was explicitly designed to degrade gracefully rather than just “throw”.
6. Validation Contracts
ValidationRunManifest, ValidationEvent, PacketSnapshotRecord, StageRunRecord, and RequestExecutionResult formalized replayable test execution.
Resolver scenario contracts evolved into a richer run/result/review format:expected status/route/metric/domain/period/scope
actual final disposition
semantic triage flags
tail families
latency aggregates

Tail audit contracts were the biggest late addition:tail bucket
recommended action
severity tier
issue family
booleans for true failure / taxonomy / polish / uncertainty

Key Architectural Decisions That Survived
Deterministic truth pipeline stays the source of truth.
LLM usage is bounded and subordinate to contracts.
Retrieval is route-whitelisted, not open-ended.
Clarification policy should prefer:one targeted clarification
not shotgun clarification

No-data is a valid, first-class answer state.
Around-X anchoring is real product behavior, not metadata noise.
Forward-looking prompts must use proxy semantics, not fake forecasting.
Validation and benchmark artifacts are part of the architecture, not just tooling.
True failures must be separated from taxonomy/polish/audit residue.
The Big Inflection Points
Broad deterministic packs were stabilized first.
Exact/deformed was then repaired, especially on DM deformed-name scope carry.
The 10k run reframed the work around failure families.
Long-tail was split out into its own LLM-assisted bounded-screener phase.
By the end of that sprint window:confirmation was effectively green
curated and mutations had recovered strongly
exact/deformed improved materially
long-tail moved from “mostly clarifying” to “mostly answering through bounded screeners”

What I’d Tell The Next Engineer
Don’t think of this system as “a prompt + a database.”
Think of it as a contracted analytics runtime with six layers:intent
retrieval
investigation
answer
visual
validation/audit

The hardest-won design principle is:family-specific narrow fixes beat broad cleverness

The second hardest-won principle is:audit truth matters as much as runtime truth

A run can look bad for two very different reasons:product is wrong
reporting is noisy

The architecture was reshaped specifically so those two are no longer confused.
If Someone Wants To Inspect The Implementation
Start with the orchestration flow in D:\SparkAgent_V2\src\orchestrator\miniOrchestrator.ts
Then the resolver contract in D:\SparkAgent_V2\src\intent\types.ts
Then retrieval contracts in D:\SparkAgent_V2\src\retrieval\retrievalTypes.ts
Then investigation contracts in D:\SparkAgent_V2\src\investigate\investigationTypes.ts
Then answer contracts in D:\SparkAgent_V2\src\answer\answerTypes.ts
Then validation/run contracts in D:\SparkAgent_V2\src\validation\validationTypes.ts
Then resolver pack / tail audit contracts in D:\SparkAgent_V2\src\validation\resolverScenarioTypes.ts
Bottom Line
The initial design was a deterministic analytics engine with optional LLM assistance at intent time.
Over that sprint, it evolved into a family-driven, validation-led, contract-heavy decision system.
The biggest architectural maturation was not “more AI.”
It was:tighter truth contracts
better scope/route preservation
explicit long-tail policy families
explicit audit severity
benchmarkable, replayable validation