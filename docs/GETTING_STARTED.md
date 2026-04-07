# Getting Started

This guide walks you through your first interaction with EDEN/Adam. By the end, you will have run the system, had a conversation, given feedback that changed persistent graph state, and exported the result. You will understand what happened at each step.

---

## Prerequisites

### For the Idris2 build (Paths 1 and 2)

- **Idris2 compiler** with the RefC backend. The project uses a custom fork, but any recent Idris2 with RefC support works. Set the `IDRIS2` environment variable if the compiler is not on your PATH.
- **GCC** (or any C compiler). The build script auto-detects MSYS2/MinGW, macOS, and Linux.
- **GMP** (GNU Multiple Precision Arithmetic Library). Usually available via your system package manager (`libgmp-dev` on Debian/Ubuntu, `gmp` on Homebrew, `mingw-w64-ucrt-x86_64-gmp` on MSYS2).
- **SQLite3** development headers (`libsqlite3-dev`, `sqlite3` on Homebrew, `mingw-w64-ucrt-x86_64-sqlite3` on MSYS2).

### For the Python build (Path 3)

- **Python 3.11+** and pip.
- A virtual environment is recommended.

### Optional

- **Claude CLI** (`claude`): Required for the Claude backend. Install from Anthropic and authenticate before use.
- **MLX** (Apple Silicon only): Required for the MLX local model backend in the Python version. Install with `pip install mlx-lm`.

---

## Path 1: Idris2 Quick Start (Mock Backend, No API Key)

This is the recommended first experience. The mock backend produces deterministic responses so you can see the full turn loop, graph mutations, and feedback cycle without needing any API key or network connection.

### Clone and build

```bash
git clone https://github.com/david-hoze/Adam.git
cd Adam/eden-idris

# Build: Idris2 type-check + RefC codegen + GCC link
./build.sh
```

The build script detects your platform, finds the Idris2 compiler, generates a C file via the RefC backend, and links it with GCC. The result is a native binary at `build/exec/eden.exe` (the `.exe` extension is used on all platforms).

If the build fails looking for Idris2, set the path explicitly:

```bash
IDRIS2=/path/to/idris2 ./build.sh
```

### Start the REPL

```bash
./build/exec/eden.exe --repl --backend mock
```

You will see:

```
=== EDEN/Adam Interactive REPL [mock] ===
    Type a message, then provide feedback.
    Commands: /quit /stats /memes /regard /hum /help

[you] >
```

The runtime has created an in-memory graph seeded with three behavior memes (Curiosity, Honesty, Clarity), opened a SQLite database at `data/eden.db` for persistence, and started a session.

### Have a conversation

Type a message:

```
[you] > Tell me about yourself.
```

Here is what happens behind the scenes:

1. **Retrieval**: The runtime scores every meme in the graph against your input. Scoring combines word-overlap similarity, regard (accumulated selection pressure), activation decay, and session bias. The highest-scoring memes form the **active set**.
2. **Assembly**: The active set, session history, and agent principles (loaded from `eden/agents/adam/seed_constitution.md`) are assembled into a prompt.
3. **Generation**: The mock backend produces a deterministic response. With a real backend, this is where the language model runs.
4. **Membrane**: The raw output is cleaned. Scaffold headings like "Answer:" or "Basis:" are stripped. Excessive newlines are collapsed. The membrane is a post-generation control surface, not a planner or filter on your input.
5. **Indexing**: Concepts are extracted from the response and added to the graph as new memes. Edges are created between related concepts.

Adam's response appears, followed by a feedback prompt:

```
[adam] I hear you. You said: "Tell me about yourself.". Let me reflect on that.

[feedback accept/reject/edit/skip] >
```

With the mock backend, responses are deterministic echoes. With a real backend (Claude), you will get substantive responses and see indexed concepts extracted from the response text.

### Give feedback

The system now asks for your verdict. Type `accept`:

```
[feedback accept/reject/edit/skip] > accept
[explanation] > Good foundation
  feedback recorded: Accept
```

This is not a thumbs-up. It is a structured event that changes persistent state:

- A `FeedbackEntry` is recorded with your verdict and explanation.
- The `Accept` signal updates the reward EMA (exponential moving average) on every meme in the active set.
- The update **propagates to related memes** with 0.85x attenuation per hop. A meme two edges away from the accepted content receives 72% of the signal (0.85 * 0.85). Three hops: 61%.
- On future turns, retrieval scoring will rank these memes higher. Your feedback has created durable selection pressure in the graph.

### Ask another question

```
[you] > What matters most to you?
```

This time, retrieval is different. The regard scores updated by your feedback shift which memes enter the active set. The graph is shaping Adam's response based on what you reinforced.

### Inspect the graph

Use the built-in commands to see what happened:

```
[you] > /stats
  memes:    6
  edges:    5
  turns:    2
  feedback: 1
```

```
[you] > /regard
  --- Regard Breakdown ---
  Curiosity [behavior] total=0.86 rw=0.14 ev=0.00 act=1.0
  Honesty [behavior] total=0.90 rw=0.17 ev=0.00 act=1.0
  ...
  --- Ontology ---
  constative:   3
  performative: 3
  ...
```

The regard breakdown shows each component: reward (from feedback), evidence (from usage), activation (time decay), coherence (graph structure), and risk.

```
[you] > /hum
  --- Hum (v1) ---
  status: Active
  turns:  2
  motifs: 3
  ...
```

The hum is a bounded continuity artifact. It tracks recurring themes across turns and persists them to `data/hum/`. It is not input to generation and not a hidden inner voice. It is an inspectable record of what patterns have emerged.

### End the session

```
[you] > /quit

--- Session complete ---
  memes:    6
  edges:    5
  turns:    2
  feedback: 1
  graph saved to data/eden.db
Goodbye.
```

The graph is saved to SQLite. When you start a new session, it resumes from this state. Identity persists across sessions.

### Export the graph

```bash
./build/exec/eden.exe --export
```

This writes the full graph state as JSON to `data/export/`. The export contains every meme, edge, memode, feedback event, session record, and measurement entry. This is the identity substrate. It is yours to inspect, back up, or load into the observatory.

---

## Path 2: Idris2 with Claude

If you have the Claude CLI installed and authenticated, you can run Adam with a real language model:

```bash
./build/exec/eden.exe --tui --backend claude
```

This launches the TUI (terminal user interface), which is the primary interface for EDEN/Adam.

### TUI layout

The screen is divided into regions:

- **Action strip** (top left): Numbered actions like Review Last Reply, Export Artifacts, Start New Session. Navigation hints appear at the bottom of the strip.
- **Status panels** (top right): Three panels showing context (token budget), live turn status (backend, phase, reasoning mode), and the aperture/active set (which memes are currently scored highest).
- **Runtime status line**: A single line below the top panels showing the current runtime state.
- **Dialogue tape** (left column): The conversation history. Your messages appear with `[you T0]` tags, Adam's responses with `[adam T0]` tags. Responses word-wrap within the panel.
- **Memgraph bus** (right column, top): A scatter plot of memes. Behavior memes appear as `^`, knowledge memes as `o`. Position reflects reward (vertical) and risk (horizontal). The session anchor `@` sits at center.
- **Reasoning panel** (right column, bottom): Shows response material, reasoning signals, runtime condition, and membrane record for the current turn.
- **Composer** (bottom left): Type your message here and press Enter to send. After Adam responds, you have a brief window to press a feedback key: `a` (accept), `r` (reject), `e` (edit), or `s` (skip).
- **Footer**: Keyboard shortcuts. `Ctrl+Q` or `Esc` to quit.

The interaction cycle is the same as the REPL: type a message, read the response, give feedback. The TUI shows more of the runtime state at a glance.

---

## Path 3: Python Reference Implementation

The Python version is the full-featured reference implementation. It includes capabilities not yet ported to Idris2: the observatory web server with 20+ REST endpoints, the MLX local model backend, full TUI modals (help, session configuration, feedback dialogs, conversation atlas), paste handling, mouse support, and themes.

### Install and run

```bash
cd Adam
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Launch the TUI (default command)
python -m eden
```

Or with a specific backend:

```bash
python -m eden app --backend mock     # No API key needed
python -m eden app --backend claude   # Requires Claude CLI
python -m eden app --backend mlx      # Requires Apple Silicon + mlx-lm
```

### Additional Python commands

```bash
# Run a one-turn demo
python -m eden demo --backend mock

# Ingest a document into the graph
python -m eden ingest path/to/document.md

# Export graph artifacts
python -m eden export

# Launch the observatory web server
python -m eden observatory --open
```

### What Python has that Idris2 does not yet

- **Observatory**: A browser-based measurement workbench (React/TypeScript with Graphology/Sigma) served over HTTP. It provides read, comparison, and bounded mutation surfaces for the graph. The Idris2 build has `--export` for static JSON but no server.
- **MLX backend**: Local model inference on Apple Silicon, with streaming, token counting, and sampler configuration. The Idris2 build relies on the Claude CLI.
- **Full TUI**: Modal dialogs, session configuration, conversation atlas, review editing, paste handling, mouse support, accessibility modes. The Idris2 TUI is functional but simpler.
- **Schema migrations**: Versioned additive migrations for the SQLite database. The Idris2 build has SQLite persistence but no migration framework.
- **Embedding-based retrieval**: Semantic similarity beyond lexical matching. The Idris2 build uses Jaccard word-overlap.

---

## Understanding What Just Happened

Whether you used Path 1, 2, or 3, you just experienced the same architecture. Here is what each piece did.

### The turn loop

Your input entered a fixed pipeline: **retrieve** (score graph memes against your query) then **assemble** (build the prompt from the active set, history, and principles) then **generate** (run the model) then **membrane** (clean and constrain the output) then **feedback** (your verdict) then **graph update** (propagate the signal). This ordering is the v1 invariant. It is not configurable, and it is not negotiable. There is no hidden planner, no pre-generation governor, no recursive decomposition. The Idris2 build proves this ordering correct at compile time.

### The graph

Every turn created new memes -- persistent units of knowledge or behavior. Feedback created edges and updated regard scores. The graph is now different from when you started. It will be different again after your next session. This is the identity substrate: Adam's continuity comes from this graph, not from model weights. You can swap the underlying model and Adam retains the same values, the same accumulated selection pressure, the same history.

### The membrane

The raw model output was processed before you saw it. Scaffold headings ("Answer:", "Basis:") were stripped. Excessive whitespace was collapsed. The membrane is a post-generation control surface. It does not filter your input or plan Adam's reasoning. It sanitizes the output and enforces constraints defined by the operator. Every membrane action is recorded as a persistent trace.

### Regard

Your "accept" feedback did not just note satisfaction. It updated the reward EMA on every meme in the active set and propagated durable selection pressure across related graph nodes with 0.85x attenuation per hop. A meme three hops from the accepted content still received 61% of the signal. On future turns, retrieval will rank reinforced memes higher. Over time, this accumulation shapes what Adam considers relevant. Regard is not prompt-time salience. It is a persistent, graph-wide valuation signal that emerges from your feedback history.

### The export

The JSON file you created (or can create with `--export`) contains the complete graph state: every meme with its domain, regard scores, and usage count; every edge with its type and weight; every memode with its member list; every feedback event with its verdict, explanation, and timestamp; every session record; every turn. This is not a log. It is the full identity substrate, serialized. You can inspect it, diff it between sessions, load it into the observatory, or back it up. It is yours.

---

## Next Steps

- **[Architecture Overview](ARCHITECTURE_OVERVIEW.md)** -- The full technical map: design principles, core concepts, proof architecture, and how the pieces fit together.
- **[Why This Matters](WHY_THIS_MATTERS.md)** -- The philosophical and political context: the governance gap, the value vacuum, and what this project does about it.
- **[Tradition Embedding Guide](TRADITION_EMBEDDING_GUIDE.md)** -- How to build a tradition module for your own community, using the Tanakh/Hebrew module as a worked example.
- **[Turn Loop and Membrane Spec](TURN_LOOP_AND_MEMBRANE.md)** -- The normative specification for the turn loop invariant and membrane behavior.
- **[Regard Mechanism](REGARD_MECHANISM.md)** -- The math behind regard: activation decay, coherence, evidence, reward, risk, and how feedback propagates.
- **[Observatory Spec](OBSERVATORY_SPEC.md)** -- The browser-based measurement workbench (Python only, static JSON export from Idris2).
