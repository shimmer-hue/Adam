# Tradition Embedding Guide

Adam is designed so that any community can embed their own tradition's interpretive tools, value hierarchies, and reasoning patterns as first-class components of the runtime. This guide shows you how, using the Tanakh/Hebrew module as a worked example.

The Tanakh module is not a product feature. It is a pattern. It demonstrates how one tradition -- rabbinical Judaism -- was embedded into EDEN's runtime. Everything it does, your tradition can do too. This document walks through the pattern and then shows you how to replicate it.

## What a Tradition Module Does

A tradition module provides four things to the EDEN runtime:

1. **Domain-specific text analysis.** These are interpretive operations your tradition applies to text. For Hebrew, this means gematria (numerical letter values), notarikon (acronym extraction from initial or final letters), and temurah (letter substitution ciphers like At-Bash). For your tradition, it means whatever analytical operations your interpretive framework uses to extract meaning from language.

2. **Value priority hierarchies.** When obligations or principles conflict, every tradition has an ordering. The membrane -- EDEN's post-generation control surface -- can enforce these priorities. Your module defines the hierarchy; the runtime applies it.

3. **Graph organization categories.** EDEN stores identity in a persistent graph of memes (behavioral units) and information (knowledge units). Your tradition module defines how knowledge is categorized, what kinds of relationships are meaningful, and what counts as a "behavior" versus "information" within your framework.

4. **Hermeneutic tools invocable during the turn loop.** Optionally, your module can provide analysis functions that the runtime calls during document ingestion, retrieval, or export -- enriching the graph with tradition-specific structure.

## The Tanakh Module as Pattern

The Tanakh module exists in two implementations: an Idris2 version (`eden-idris/src/Eden/Tanakh.idr`) with compile-time totality guarantees, and a Python version (`eden/tanakh/service.py`) with full corpus management and observatory integration. Both follow the same architectural pattern.

### Text Analysis Functions

The Idris2 module defines three core hermeneutic operations:

**Gematria** computes the numerical value of Hebrew text. Each of the 22 Hebrew letters has a standard value (aleph = 1, bet = 2, ... tav = 400). The function normalizes final letter forms to their standard counterparts, sums the values, and returns the total.

```idris
-- Pure function: String -> Int
-- No side effects, guaranteed termination
gematria : String -> Int
gematria = foldl (\acc, c => acc + letterValue c) 0 . unpack
```

**Notarikon** extracts acronyms. Roshei teivot takes the first Hebrew letter of each word; sofei teivot takes the last. These are standard rabbinical tools for finding hidden meanings in letter sequences.

```idris
-- Pure function: String -> String
rosheiTeivot : String -> String
sofeiTeivot  : String -> String
```

**Temurah** applies letter substitution ciphers. The At-Bash cipher mirrors the alphabet (aleph swaps with tav, bet with shin, and so on through all 11 pairs). This is a classical tool for discovering textual connections.

```idris
-- Pure function: Char -> Char
-- Non-Hebrew characters pass through unchanged
atBash : Char -> Char
```

The critical design constraint: every function is **pure and total**. The module declares `%default total` at the top. These functions take input, produce output, and do nothing else. No state mutation, no IO, no exceptions. The Idris2 compiler verifies totality at build time -- if any function could fail to terminate, the build fails.

The Python version implements the same operations with additional features -- multiple gematria schemes (standard and gadol), preprocessing modes (strip pointing, keep vowels, keep cantillation), word-level position tracking, and provenance hashing for every result. But the core pattern is the same: pure transformations over text.

### Combined Analysis

Both implementations provide a combined analysis function that runs all operations at once:

```idris
record HebrewAnalysis where
  constructor MkHebrewAnalysis
  inputText      : String
  strippedText   : String    -- nikkud removed
  gematriaValue  : Int       -- numerical value
  rosheiResult   : String    -- first-letter acronym
  sofeiResult    : String    -- last-letter acronym
  atBashResult   : String    -- cipher substitution
  letterCount    : Nat       -- Hebrew letter count

analyzeHebrew : String -> HebrewAnalysis
```

This record type captures everything the tradition's text analysis produces. Your module will define an analogous record for your tradition's analysis results.

### Integration Points

The Tanakh module connects to the EDEN runtime at four points:

**Document ingestion.** When Hebrew text is ingested through the ingest pipeline (`Eden.Ingest`), the Tanakh module's analysis functions can be called on each chunk. Gematria values, notarikon results, and temurah mappings become metadata attached to the memes created during ingestion. In the Python implementation, the `TanakhService` is instantiated by the runtime and passed to both the exporter and the observatory service.

**The graph.** Analysis results become memes with domain-specific edges. A Hebrew word's gematria value can link it to other words with the same numerical value -- a connection meaningful within rabbinical hermeneutics but invisible to generic text analysis. The graph categories defined by your tradition module determine what edge types are created and how knowledge is organized.

**The active set.** During retrieval, tradition-specific metadata can influence candidate scoring. If the operator is working within a Hebrew textual context, gematria connections can boost the relevance of related memes. This is where the regard mechanism (see `docs/REGARD_MECHANISM.md`) intersects with tradition-specific structure.

**Export.** The Python implementation produces a Tanakh "surface bundle" as a sidecar in the observatory export family. This includes passage text, analysis results, provenance chains, and visualization parameters. Your tradition module can define its own export sidecar with whatever data your community's tools need to consume.

### The Purity Constraint

This is the most important architectural decision in the tradition module pattern: **everything in the tradition module should be pure functions.**

The runtime calls them. They return results. They do not reach into the graph directly. They do not perform IO. They do not maintain state.

Why this matters:

- **Portable.** Pure functions work identically in Idris2 and Python. They can be tested in isolation, composed with other modules, and moved between implementations without behavioral changes.
- **Testable.** A pure function's correctness can be verified with simple input/output tests. The Idris2 version goes further: the `%default total` pragma means the compiler proves termination. You do not need to trust that the function handles all cases -- the type checker verifies it.
- **Composable.** Multiple tradition modules can coexist in the same runtime because they do not compete for state. A gematria function and an Arabic root extraction function can both analyze the same text without interfering with each other.
- **Auditable.** For communities deploying AI in consequential domains -- healthcare, credit, agriculture, governance -- the ability to inspect and verify every analytical function independently is not a convenience. It is a trust requirement.

The runtime code in `Eden.Runtime`, `Eden.Pipeline`, and `Eden.Export` handles the impure operations: reading from the graph, writing memes, updating edges, persisting results. The tradition module provides the analytical logic. The boundary between them is the function signature.

## Building Your Own Tradition Module

### Step 1: Define Your Tradition's Text Analysis Functions

Start by identifying the interpretive operations your tradition applies to text. Every tradition has them, even if they are not usually formalized as algorithms.

**Arabic root extraction** for Islamic jurisprudence: Arabic words derive from trilateral (sometimes quadrilateral) roots. Identifying the root of a word connects it to an entire semantic field. A function `extractRoot : String -> Maybe (Char, Char, Char)` would be the foundation for connecting Quranic vocabulary to its jurisprudential commentary.

**Relational-entity identification** for Ubuntu philosophy: Ubuntu's core insight is that identity is constituted through relationships -- "I am because we are." A text analysis function for Ubuntu would identify relational entities: who is in relationship with whom, what obligations flow between them, what communal context they share. This is fundamentally different from Western NLP's focus on individual named entities.

**Role-relationship mapping** for Confucian ethics: The Five Relationships (wu lun) structure Confucian moral reasoning. A text analysis function would identify which of the five relationships a passage invokes, what obligations each party holds, and how the passage positions authority and reciprocity.

**Case-precedent identification** for common law traditions: Identify references to prior rulings, extract the ratio decidendi, and map the chain of authority.

Write these as pure functions with clear type signatures:

```
-- Your tradition's core analysis type
Text -> YourAnalysisResult
```

In Idris2, mark the module `%default total` and let the compiler verify that your functions terminate on all inputs. In Python, write unit tests that cover edge cases.

### Step 2: Define Your Tradition's Value Priorities

Every tradition has a hierarchy for resolving conflicts between competing obligations. This hierarchy is what makes a tradition a tradition rather than an ad hoc collection of preferences.

The Halacha (Jewish law) example is instructive because it is explicit:

- Pikuach nefesh (saving life) overrides nearly all other obligations
- Biblical commandments outweigh rabbinic enactments
- Positive commandments override negative commandments (in specific circumstances)
- Obligations that arise frequently take precedence over infrequent ones
- Active violation is treated more severely than passive non-compliance

Express these as data types or priority orderings that the membrane can reference. The membrane is the post-generation control surface that processes the model's raw output before it reaches the operator. When the membrane encounters a conflict -- the model's output violates one principle to satisfy another -- your priority hierarchy determines which principle wins.

```idris
-- Example: Halachic priority ordering
data HalachicPriority
  = PikuachNefesh       -- saving life
  | BiblicalObligation  -- d'oraita
  | RabbinicEnactment   -- d'rabbanan
  | CustomaryPractice   -- minhag

-- The ordering must be total: every pair is comparable
priorityOrder : HalachicPriority -> HalachicPriority -> Ordering
```

In Idris2, you can prove that your priority ordering is total -- that every pair of obligations is comparable and the ordering is consistent. This is not an academic exercise. It means the membrane will never encounter an unresolvable conflict in your hierarchy. For communities that cannot rely on courts or regulators to resolve edge cases, this mathematical guarantee matters.

### Step 3: Define Your Tradition's Graph Categories

EDEN organizes knowledge using the ontology defined in `docs/CANONICAL_ONTOLOGY.md`. The core distinction is between behavior-domain memes (performative, actionable units) and knowledge-domain information (constative units with provenance). Your tradition module extends this by defining:

**What kinds of edges are meaningful in your tradition?** The base ontology provides `DERIVED_FROM`, `CO_OCCURS_WITH`, `INFLUENCES`, `REFERENCES`, and others. Your tradition may need additional edge types. Gematria equivalence (two words with the same numerical value) is a meaningful relationship in rabbinical hermeneutics that has no equivalent in the base ontology. Ubuntu's kinship and reciprocity obligations are relationship types that the base ontology does not capture.

**How does your tradition categorize knowledge?** Some traditions organize by source authority (Torah, Prophets, Writings in Judaism; Quran, Hadith, Ijma, Qiyas in Islamic jurisprudence). Others organize by domain of life (the Five Relationships in Confucianism, the Four Ashramas in Hindu tradition). Your categories determine how the graph structures knowledge for retrieval.

**What qualifies as "behavior" versus "information"?** The distinction between performative and constative is not universal. In some traditions, knowledge and obligation are inseparable -- to know the right thing and not do it is itself a moral category. Your module defines where the boundary falls.

### Step 4: Wire Into the Runtime

Once your pure analysis functions, priority hierarchies, and graph categories are defined, connect them to the runtime:

**Register analysis functions for document ingestion.** When documents in your tradition's language or domain are ingested, your analysis functions run on each chunk. Results become metadata on the created memes, and tradition-specific edges are created between related nodes.

In the Python implementation, this means instantiating your service in the runtime constructor (as `TanakhService` is instantiated in `eden/runtime.py`) and passing it to the ingestion pipeline.

In Idris2, import your module and call its pure functions during the ingestion phase in `Eden.Ingest`.

**Register priority hierarchies for membrane rules.** The membrane (`Eden.Membrane`) applies post-generation constraints. Your priority hierarchy extends the constraint set. When the model generates output that could satisfy one principle only by violating another, the membrane consults your ordering.

**Register graph categories for the ontology.** Add your tradition-specific edge types to the graph schema. Document them in your module and in `docs/GRAPH_SCHEMA.md`.

**Add an export sidecar for tradition-specific data.** The export system (`Eden.Export` in Idris2, `eden/observatory/exporters.py` in Python) produces the graph state as JSON. Your tradition module can add a sidecar file containing tradition-specific analysis, visualization parameters, or structured data that your community's tools consume. The Python Tanakh module exports a "surface bundle" with passage text, analysis results, and scene parameters for the observatory frontend.

### Step 5: Write Proofs (Idris2 Only)

If you are working in Idris2, the type system lets you prove properties about your tradition module that no amount of testing can guarantee.

**Totality.** With `%default total`, every function must handle all possible inputs and terminate. This means your analysis functions cannot crash, loop forever, or silently fail on unexpected input.

**Priority ordering is total.** Prove that every pair of obligations in your hierarchy is comparable. This guarantees the membrane will never encounter two conflicting obligations that your hierarchy cannot resolve.

```idris
-- Prove that every pair has a defined ordering
priorityTotal : (a, b : YourPriority) -> Either (a `LTE` b) (b `LTE` a)
```

**Analysis functions preserve invariants.** Prove that your analysis functions maintain the properties your tradition requires. For gematria, you might prove that normalization is idempotent (normalizing a normalized letter returns the same letter). For root extraction, you might prove that the result always has exactly three consonants.

The existing proof suite in `Eden.Proofs` provides 55 theorems across 18 sections as examples of what can be verified. Your tradition module's proofs extend this suite.

For communities deploying AI in healthcare, credit, education, or governance -- domains where errors have consequences -- these proofs are not decorative. They are the trust infrastructure. A proven priority ordering means a community can deploy the system knowing that their values will be consistently applied, not because they trust the developers, but because the mathematics does not permit otherwise.

## Worked Example: Skeleton of an Ubuntu Module

The following is hypothetical but concrete. It shows what a tradition module looks like before any runtime wiring -- just the pure analytical core.

```idris
||| Ubuntu tradition module: relational identity and communal ethics.
|||
||| Core insight: "Umuntu ngumuntu ngabantu" --
||| a person is a person through other persons.
||| Identity is constituted by relationships, not by individual properties.
module Eden.Ubuntu

import Data.List
import Data.String

%default total

------------------------------------------------------------------------
-- Relational entity types
------------------------------------------------------------------------

||| The kinds of relationships Ubuntu philosophy recognizes.
public export
data RelationType
  = Kinship          -- family and clan bonds
  | Reciprocity      -- mutual obligation between equals
  | ElderGuidance    -- wisdom flowing from elder to younger
  | CommunalBond     -- shared membership in a community
  | Hospitality      -- obligations to strangers and guests

||| A relationship between two entities with a typed bond.
public export
record Relation where
  constructor MkRelation
  subject   : String
  object    : String
  relType   : RelationType
  context   : String       -- communal context of the relationship

------------------------------------------------------------------------
-- Value priority hierarchy
------------------------------------------------------------------------

||| Ubuntu priority ordering: communal welfare takes precedence
||| over individual autonomy when they conflict.
||| This is the inverse of the Western liberal default.
public export
data UbuntuPriority
  = CommunalWelfare        -- the community's collective wellbeing
  | HarmonyPreservation    -- maintaining social cohesion
  | ElderWisdom            -- respect for accumulated experience
  | IndividualExpression   -- personal autonomy and self-actualization

||| Priority ordering. Every pair is comparable.
public export
priorityRank : UbuntuPriority -> Nat
priorityRank CommunalWelfare      = 4
priorityRank HarmonyPreservation  = 3
priorityRank ElderWisdom          = 2
priorityRank IndividualExpression = 1

public export
priorityOrder : UbuntuPriority -> UbuntuPriority -> Ordering
priorityOrder a b = compare (priorityRank a) (priorityRank b)

------------------------------------------------------------------------
-- Graph edge types
------------------------------------------------------------------------

||| Tradition-specific edge types for the EDEN graph.
||| These extend the base ontology's edge semantics.
public export
data UbuntuEdge
  = KinshipEdge        -- family/clan relationship
  | ObligationEdge     -- directional duty from one party to another
  | ReciprocityEdge    -- symmetric mutual obligation
  | CommunalEdge       -- shared community membership
  | HospitalityEdge    -- guest/host obligation

------------------------------------------------------------------------
-- Text analysis: relational entity identification
------------------------------------------------------------------------

||| Result of analyzing text for relational structure.
public export
record UbuntuAnalysis where
  constructor MkUbuntuAnalysis
  inputText      : String
  relations      : List Relation
  communalTerms  : List String    -- words indicating communal context
  individualTerms : List String   -- words indicating individual context
  communalRatio  : Double         -- proportion of communal vs individual framing

||| Identify relational entities in text.
||| This is the Ubuntu equivalent of Hebrew gematria:
||| a tradition-specific lens for extracting meaning from language.
|||
||| In a full implementation, this would use a lexicon of Bantu
||| relational terms, kinship vocabulary, and communal obligation
||| markers specific to the target language (Zulu, Xhosa, Sotho, etc.).
public export
analyzeRelations : String -> UbuntuAnalysis
analyzeRelations input =
  MkUbuntuAnalysis
    input
    []       -- placeholder: real implementation uses lexicon lookup
    []       -- placeholder: communal term extraction
    []       -- placeholder: individual term extraction
    0.0      -- placeholder: ratio computation
```

This skeleton is incomplete by design. A real Ubuntu module would require:

- A lexicon of relational terms in the target Bantu language(s)
- Linguistic analysis specific to the language family's noun class system (which encodes relational categories grammatically)
- Input from Ubuntu scholars and practitioners on what the priority hierarchy should contain and how edge cases resolve
- Community validation that the formalization captures the tradition faithfully

The skeleton shows the shape. Filling it in is the community's work, not the framework developer's.

## What This Enables

When a community builds their tradition module and loads it into Adam, the runtime does not just process their language. It organizes knowledge according to their tradition's categories, resolves conflicts according to their priority hierarchy, and makes decisions through their interpretive framework.

The model provides generation capability -- it produces text. The tradition module provides direction -- it determines how that text is analyzed, what it means within the tradition's framework, and which principles govern the output.

This separation is the architectural core of EDEN. The model is an inference surface. Identity -- values, priorities, interpretive methods, the accumulated weight of a community's feedback -- lives in the graph and in the tradition module. Swap the model, keep the identity. Swap the tradition module, keep the infrastructure.

The result is that a community in Nairobi running an Ubuntu module, a community in Isfahan running an Islamic jurisprudence module, and a community in Seoul running a Confucian ethics module all use the same runtime. The turn loop is the same. The membrane is the same. The graph is the same. The regard mechanism is the same. What differs is the analytical lens, the priority hierarchy, the graph categories, and the accumulated feedback -- which is to say, everything that makes a tradition a tradition.

No community needs permission from the framework developers to build their module. The pure-function constraint means the module is self-contained. The local-first architecture means it runs on their hardware. The measurement ledger means every decision is recorded, inspectable, and reversible. The Idris2 proofs -- if they choose to write them -- mean the guarantees are mathematical, not promissory.

This is what the missing value architecture looks like when it is built to be inhabited by any tradition, not just the one that happened to build it first.
