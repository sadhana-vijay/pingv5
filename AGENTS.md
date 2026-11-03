# AGENTS.md: Ping - Dungeons and Dragons

> **Purpose of this file.** This is the single source of truth for the Dungeons and Dragons project. It serves two audiences:
>
> 1. **The organising team (humans)**: a full description of the event, its mechanics, and what is still undecided.
> 2. **AI coding agents** (Claude Code, Codex, Cursor, etc.) working in this repository: operating rules, boundaries, and conventions.
>
> If anything in the codebase contradicts this file, raise it rather than silently picking one. If something is listed under **Open Questions**, do **not** invent an answer; flag it, or implement it behind a clearly marked placeholder.

**Status legend used throughout:**

- [DECIDED] **Decided**: confirmed by the organisers.
- [OPEN] **Open**: undecided. Do not assume.
- [PROPOSED] **Proposed**: a suggestion for discussion, not a commitment.

- **Implementation note**: a detail can be architecturally important without being decided. Keep such details configurable and do not turn examples into rules.

**Authority order:** explicit organiser decisions in this file → confirmed repository interfaces/tests → clearly labelled proposals → assumptions. If two sources conflict, stop and report the conflict.

---

## Table of Contents

1. [Project Summary](#1-project-summary)
2. [Core Design Philosophy](#2-core-design-philosophy)
3. [System Architecture](#3-system-architecture)
4. [The Game Engine: Directed Graph, Nodes and Game State](#4-the-game-engine-directed-graph-nodes-and-game-state)
5. [Information Boundaries](#5-information-boundaries-who-sees-what)
6. [Dynamic (Intermediate) Nodes](#6-dynamic-intermediate-nodes)
7. [Turn Structure and Synchronisation Barrier](#7-turn-structure-and-synchronisation-barrier)
8. [Classes, Stats, Objectives and Ranking](#8-classes-stats-objectives-and-ranking)
9. [Dice and Action Resolution](#9-dice-and-action-resolution)
10. [Player Interaction and Coordination](#10-player-interaction-and-coordination)
11. [Action Format and Grammar-Constrained Generation](#11-action-format-and-grammar-constrained-generation)
12. [The Participant Harness](#12-the-participant-harness)
13. [Model, Context Window and Hardware Constraints](#13-model-context-window-and-hardware-constraints)
14. [Security Model](#14-security-model)
15. [Tournament Structure](#15-tournament-structure)
16. [End-to-End Event Flow](#16-end-to-end-event-flow)
17. [Build-Phase Deliverables for Participants](#17-build-phase-deliverables-for-participants)
18. [Organiser Task List](#18-organiser-task-list)
19. [Open Questions](#19-open-questions)
20. [Instructions for AI Coding Agents](#20-instructions-for-ai-coding-agents)
21. [Change Management and Specification Hygiene](#21-change-management-and-specification-hygiene)
22. [Glossary](#22-glossary)

---

## 1. Project Summary

**Ping - Dungeons and Dragons** is a mini hackathon event run by the **AIML team**.

Participants build an **AI harness** (a Python class plus all the logic around a language model) that plays a **Dungeons & Dragons-style game** against other participants' harnesses. The harness must use a **1-billion-parameter language model**. The harness, not the model, is what is being judged.

Participants **never see the real story**. During the build phase they get only:

- The Game Master (GM) to practise against.
- Descriptions of all possible classes (attributes, abilities, objectives, vendetta).
- A rough idea of the story and general constraints.
- A test suite.
- A small test story for individual testing.

After submission, the game is played as independent runs. [DECIDED] There are 5 classes and more than 5 participants; each run draws 5 participants at random to fill the 5 classes, one per class. [DECIDED] Each participant plays exactly one run. **The participant model and harness execute on the organisers' host, which runs on GCP, during the real game.**

[DECIDED] **Story shape:** there is a set of 5 bosses. Each run encounters every boss once, in a random order. Each class has a nemesis, one particular boss. At the start of the run each class is given a description of its nemesis and a specific action to perform when it meets it. The nemesis is not named, so the harness must recognise it from the boss encounters' descriptions (see §4, §8).

**Winning condition (summary):** [DECIDED] surviving to the end of the run is required. Among survivors, the first tie-breaker is completing your vendetta: performing your required action against your nemesis with a successful dice roll (your class objective), which also earns a stat buff. The second is your stat total (see §8).

---

## 2. Core Design Philosophy

[DECIDED] The Ping tests **harness engineering**, not raw LLM capability.

The 1B model, the fixed context window, the lack of internet, the lack of persistent storage, the CPU and RAM caps, and the hidden game information are all deliberate constraints. They force participants to engineer around the model's weaknesses.

Participants must independently decide:

- What to remember, what to discard, what to summarise.
- How to retrieve relevant information when needed.
- How to spend a fixed context budget.
- How to fit memory inside a fixed CPU and RAM budget, with no disk to fall back on.
- How to reason about the current situation.
- How to adapt to a class they do not know in advance.
- How to pursue their objective (recognise their nemesis from its description and perform the required action) while staying alive.

**The core challenge:** _Build the smartest possible game-playing agent around a deliberately constrained model, without knowing the actual story or your assigned character beforehand._

[DECIDED] **Non-LLM logic is explicitly allowed** (regex parsers, rule-based triage, structured memory, retrieval, embeddings computed at runtime within the resource cap, heuristics). Participants cannot offload all thinking to the LLM, and the 1B model should be used for narrow, well-scoped reasoning. This is the intended skill being tested.

---

## 3. System Architecture

Three primary components:

### A. Game Engine

- [DECIDED] A **directed graph**. Nodes are game states; directed edges are possible transitions.
- Multiple branching paths and multiple endings.
- [DECIDED] Holds the authoritative game state and player stats. Nodes hold only the story; stats, history and the boss draw are kept in the per-run game state (§4).

### B. Game Master (GM)

- A model hosted on organisers' machines. **Not constrained** to 1B.
- [DECIDED] Has the **complete skeletal graph**: all nodes, edges, transition conditions, and node information.
- Keeps the narrative on the intended story rails, preventing hallucinated storylines and tangents.
- Interprets players' actions (including creative ones) and decides which next state fits.
- [DECIDED] Connects each story node with the drawn boss, writes the current event (including the boss's name and description), fills in the defined interactions for that boss, decides the boss's action (§4), and judges whether a player's action is their required vendetta action (§8).
- [DECIDED] The test GM is exactly the same model/configuration as the real GM.

### C. Participant AI Harness

- A **Python class** wrapping a 1B model and any surrounding logic.
- Responsible for: processing observations, maintaining memory, managing context, summarising and prioritising, tracking player and game info, choosing actions, and emitting the structured action.

---

## 4. The Game Engine: Directed Graph, Nodes and Game State

[DECIDED] **Nodes contain only the story.** Everything that changes during a run (player stats, history, and the boss attached to the current node) is kept in the per-run **game state**, not on the nodes. The story graph itself is static.

### Story graph _(organiser/GM only)_

1. **Nodes**: each node holds the story for one game state.
2. **Possible next game states**: the outgoing edges from each node.
3. **Required conditions**: what must be fulfilled to take each transition, where applicable.

The GM uses the edges and conditions to choose the appropriate transition from participants' actions and the situation. A dynamic node (§6) uses the same structure.

### Game state _(per run; organiser/GM only, except each player's own stats)_

The engine holds the authoritative game state for each run (§3):

1. **Previous game state**: the previous node.
2. **Summary of previous narrative**: what happened before.
3. **Previous character actions**: what each character did last turn.
4. **Individual player stats**: HP, attributes, abilities, etc. [DECIDED] There is **no inventory**. [DECIDED] All player stats **carry over through the whole run**; nothing resets between nodes or bosses. Each player is given **only their own** stats.
5. **Boss draw**: the bosses already encountered in this run and the boss attached to the current node (see Bosses below).

### Defined interactions _(organiser/GM only)_

Obvious interactions for the current situation. Example, a giant in a tavern:

- Try to kill the giant.
- Run away.
- Hide.

[DECIDED] Defined interactions are **not stored on nodes**. Once the boss for a node is drawn, the GM fills them in for that boss.

**Purpose:** pre-handle the obvious cases so the GM does not reason from scratch for every action.

**Important:** participants are **not restricted** to these. A player might try to seduce the giant; the GM must still interpret and resolve it.

### Current event

What is happening now (e.g. _"A giant is in your tavern."_). The GM writes it by connecting the node's story with the boss drawn for that node. **Shown to players.** [DECIDED] It names the boss and includes a description of it, which harnesses match against their nemesis description (§8).

### Bosses

- [DECIDED] There is a set of **5 bosses**.
- [DECIDED] Each boss is encountered **exactly once per run**. Each boss encounter pulls a boss at random from the bosses not yet encountered in that run.
- [DECIDED] No node is tied to a particular boss. At runtime the GM connects the current story node with the boss drawn for it, adapting the narrative so the two fit.
- [DECIDED] Each node is played for **one round**: every living player submits one action, and the story then moves to the next node, which brings a new boss (see §7).
- [DECIDED] **Boss action.** The GM decides the boss's action based on the boss. If the players do not defeat the boss in its round, the GM announces the boss's action as part of the resolution. For example: the boss targets a player chosen on the basis of a stat, deals damage and applies an effect to them, while the other players escape unharmed. The story then moves to the next node.
- [OPEN] Whether every node (including dynamic nodes, §6) carries a boss; if so, every run is exactly 5 rounds. Also open: where boss data (stats, HP, abilities) is held and whether any of it beyond the name and description is shown to participants; whether the boss acts in a round where it is defeated; and whether boss damage and target selection follow fixed rules applied by the engine or are left to the GM's judgement.

---

## 5. Information Boundaries (Who Sees What)

| Information                                              | Organisers / GM | Participants                                                                     |
| -------------------------------------------------------- | --------------- | -------------------------------------------------------------------------------- |
| Previous game state                                      | Yes             | **No**                                                                           |
| Summary of previous narrative                            | Yes             | **No**                                                                           |
| Previous character actions                               | Yes             | **No**                                                                           |
| Possible next game states                                | Yes             | **No**                                                                           |
| Required transition conditions                           | Yes             | **No**                                                                           |
| Defined interactions (per boss)                          | Yes             | **No**                                                                           |
| Current event                                            | Yes             | **Yes**                                                                          |
| Current boss's name                                      | Yes             | **Yes (in the current event)**                                                   |
| Which class's nemesis each boss is                       | Yes             | **No, until a class completes its vendetta (the buff is announced to everyone)** |
| Individual player stats                                  | Yes             | **Own only**                                                                     |
| Other players' classes and stats                         | Yes             | **Initial state only**                                                           |
| Own objective                                            | Yes             | **Yes (initial state)**                                                          |
| Own nemesis description and required vendetta action     | Yes             | **Yes (initial state)**                                                          |
| Other players' nemesis descriptions and required actions | Yes             | **No**                                                                           |
| Other players' objectives                                | Yes             | **No (hidden)**                                                                  |
| Resolution outcome of the round                          | Yes             | **Yes (announced after resolution)**                                             |
| Broadcasts sent to `[all]` or to your class              | Yes             | **Yes (after the broadcast barrier)**                                            |
| Broadcasts sent to another class                         | Yes             | **No**                                                                           |

[DECIDED] **Initial-state observation:** current event, own stats and objective (including own nemesis description and required vendetta action), and other players' classes and stats. Other players' objectives, nemesis descriptions and required actions are never revealed.

[DECIDED] **Subsequent per-turn observation:** current event + own stats. After actions are resolved and before the GM selects the next game state, active harnesses also receive the publicly announced outcome of the round, including the outcomes of other players' actions. The resolution payload does not include hidden information, private objectives, or organiser-only node data. Nothing else is automatically provided. [DECIDED] The resolution outcome includes any vendetta stat buff awarded that round, announced to everyone (§8).

The distinction is intentional: participants must build their own in-memory record of anything they want to keep. The engine does **not** replay history to them.

> [OPEN] The exact contents and format of the resolution outcome are not yet decided.

---

## 6. Dynamic (Intermediate) Nodes

**Problem:** a purely predefined graph risks feeling like a choose-your-own-adventure book instead of D&D.

**Solution:** the GM may generate **intermediate dynamic nodes** between skeletal nodes.

- The skeletal graph remains predefined and authoritative.
- Dynamic nodes have **exactly the same structure** as normal nodes (same information categories).
- They let the GM elaborate events and introduce situations dynamically.
- [PROPOSED] **Maximum of 2 consecutive dynamic nodes** (proposed value). After at most two, the GM **must** select the next node from the skeletal graph.

```text
Skeletal A → Dynamic 1 → Dynamic 2 → Skeletal B      allowed under the proposed limit
Skeletal A → Dynamic 1 → Dynamic 2 → Dynamic 3 → …    not allowed under the proposed limit
```

This balances narrative flexibility with story adherence. The barrier and turn structure apply identically to dynamic nodes.

> [OPEN] How dynamic nodes interact with bosses (§4). With 5 bosses, each encountered once, and a new boss on every node, a dynamic node would either use up one of the 5 bosses or carry no boss at all.

---

## 7. Turn Structure and Synchronisation Barrier

[DECIDED] A **synchronisation barrier** exists at **every round**, for both skeletal and dynamic nodes. It sits **before dice rolls**.

[DECIDED] **One round per node.** Each node is played for exactly one round, so each player gets exactly one action per node. After that round the GM moves the story to the next node.

**Per-round sequence:**

1. At the start of the first round, each living participant receives the **initial-state observation**, containing the current event, their own stats and objective (including their nemesis description and required vendetta action), and the other players' classes and stats. In subsequent rounds, living participants receive only the **current event** and **their own stats**.
2. **Broadcast window:** each harness may submit at most one optional broadcast message to the GM, addressed to `[None]`, `[all]`, or a specific `[class]`. `[None]` means no message; a submitted message cannot be empty. The broadcast window has a set time limit.
3. **Barrier (broadcast submission):** the game waits for broadcast submissions up to the set time limit. A harness that does not submit within the window loses its opportunity to broadcast that round; it receives no extension or additional time.
4. The GM announces each submitted message to its intended recipient or recipients, identifying the sender by class. `[all]` messages are announced to all harnesses; a class-addressed message is announced to the harness for that class. Harnesses receive the announcements before deciding their actions.
5. Each harness processes the observation and any broadcasts it received, then decides an action. This happens within the action-submission barrier's **set time limit**: the harness may do whatever internal processing it likes (non-LLM logic, one LLM call, several LLM calls) as long as it submits in time.
6. Each harness submits its **structured JSON action**.
7. **Barrier (action submission):** the game waits for all submissions, up to the set time limit. A player whose action is invalid or not submitted in time receives a health penalty (§11).
8. Player-directed interactions are resolved first: each receives its dice roll, and successful positive effects are applied as buffs to the affected player's stats (see §9–10).
9. Event-directed actions then receive their dice rolls and are resolved using the stats after those buffs have been applied (see §9). If the GM judges that a player's action is their required vendetta action against their nemesis, that action's dice roll uses a lower success threshold; if it succeeds, the player receives a vendetta stat buff, announced to everyone in the resolution (§8).
10. **Boss action:** if the boss was not defeated, the GM decides the boss's action based on the boss (§4), for example targeting a player based on a stat and dealing damage. The engine applies the effects to the game state.
11. The GM narrates the collective resolution, including the boss's action, communicating the successes, failures, and effects through the story. The **resolution outcome is announced** to all active harnesses (see §5). Nothing is required of a living player's harness except to ingest it however it wishes and send back a confirmation of receipt. If a player dies during resolution, their death is announced as part of the resolution outcome and their harness does not participate in the confirmation barrier.
12. **Barrier (confirmation):** the game waits for confirmations from all surviving players, with a **shorter time limit** than the action-submission barrier.
13. The **GM selects the next game state** using the graph and, for a boss encounter, connects it with the next randomly drawn boss (§4).
14. Next round begins.

[DECIDED] **All players travel together.** There is one shared sequence of game states. Players cannot branch off into separate nodes.

[DECIDED] When a character dies, its harness is **discarded** and is no longer called. The organisers' program records that the player died, along with the character info: time alive, whether the objective was completed, whether they completed their vendetta, their stat total (§8), and any other significant information.

[DECIDED] **Termination:** the graph's terminal nodes (nodes with no outgoing edges) are the different **ending nodes**. When the run reaches any ending node and the round there completes (harness actions submitted, actions resolved, resolution announced), the run for that group is over. The tie-breaking and point aggregation rules then apply (see §8).

> [OPEN] The duration of the broadcast window, the action-submission time limit, the shorter confirmation time limit, and the total game time limit; whether a window closes early once every living harness has submitted; and behaviour on a missed confirmation are **undecided**. Invalid or timed-out actions receive a health penalty (§11).

---

## 8. Classes, Stats, Objectives and Ranking

### Classes

- Participants receive **descriptions of all possible classes** during the build phase: characteristics, attributes, abilities, and objectives, including that each class has a vendetta. The nemesis description and required action are given only in the initial-state observation (see Objectives below).
- [DECIDED] Participants **do not know which class they will get**. Assignment happens at the start of the real game, **after submission**.
- [DECIDED] **Stats are fixed per class.** (The earlier idea of letting participants propose/lock their own stats, including the unclear "Lua" mention, is **dropped**.)
- [DECIDED] There are exactly **5 classes**.
- [DECIDED] **One player per class per run.**
- The harness **must adapt to any class** at runtime. It cannot be specialised after the fact.

### Objectives

- [DECIDED] Each class has an objective: **successfully perform its required vendetta action when it encounters its nemesis** (below).
- [DECIDED] The **main goal of every class is to survive** through all the boss encounters.
- [DECIDED] Each class has a **personal vendetta** against one particular boss, its **nemesis** (§4). In the initial-state observation, each class is given a **description of its nemesis** and a **specific action** to perform when it encounters it.
- [DECIDED] **Each nemesis is unique.** Every class has a different nemesis, so the 5 classes and the 5 bosses pair one to one.
- [DECIDED] **The nemesis is not named.** Each boss encounter message names the boss and describes it. The harness must match that description against its nemesis description to work out whether the current boss is its nemesis, and if so perform the required action.
- [DECIDED] **Completing the vendetta.** The GM decides whether a player's action is the required action. The action still needs a successful dice roll, but against a **lower threshold** than normal. On success the player receives a **stat buff** (not points), which is announced to everyone. Completing the vendetta is the first tie-breaker in the ranking. Each boss appears once per run, so each class has one chance.
- [OPEN] How much lower the vendetta threshold is; which stats the vendetta buff raises, by how much, and from when; and whether the boss must also be defeated.
- [DECIDED] A player receives the objective of their assigned class in the initial-state observation (§5). [OPEN] The exact field is part of the undecided message format (§19).
- [DECIDED] Other players' objectives are not part of the stated participant-facing information. Treat them as hidden unless the organisers explicitly decide otherwise.

### Ranking

[DECIDED] Players in a run are ranked in this order:

1. **Survive to the end of the run.** Required: a player must be alive when the run ends.
2. **First tie-breaker: completed vendetta.** Among survivors, players who completed their vendetta (see Objectives) rank above those who did not. [DECIDED] This counts as its own tie-breaker, in addition to the vendetta stat buff raising the player's stat total.
3. **Second tie-breaker: stat total.** Remaining ties are broken by the player's stat total.

[OPEN] Which stats make up the stat total (for example, whether HP counts, and whether it is the value at the end of the run), how players who died are ranked against each other, if at all, and what happens if players are still tied after the stat total.

> [OPEN] Each participant plays one run (§15). How results are compared across runs, which have different groups, class assignments and boss orders, is **undecided**.

---

## 9. Dice and Action Resolution

[DECIDED] Each player's submitted action receives exactly one dice roll. A broadcast message does not receive a dice roll, and a player receiving an interaction does not submit a response or receive an additional roll.

[DECIDED] Player-directed interactions are resolved before event-directed actions. Each player-directed interaction receives its action's one dice roll first; successful positive effects are applied as buffs to the affected player's stats. Event-directed actions then receive their dice rolls and are resolved using the stats after those buffs have been applied. If the boss is not defeated, the GM then decides the boss's action (§4). The GM narrates the collective resolution at the end, communicating successes, failures, and effects through the story.

[DECIDED] A required vendetta action against the player's own nemesis is rolled against a **lower success threshold** than normal (§8).

[OPEN] The actual dice system and mechanics (e.g. d20 + modifier), how stats map to rolls, and whether those rules are disclosed to participants must be finalised.

**Worked example:** three players act in the same round. Two choose _attack_, one chooses _hide_. **Each player receives one roll for their action** to determine whether it is possible and how well it succeeds. Both attackers can succeed (or fail) independently. If another player successfully applies a defensive buff to one of them, that buff is applied before the event-directed action is resolved.

---

## 10. Player Interaction and Coordination

[DECIDED] GM-mediated coordination between players is permitted. Interaction does **not** happen privately player-to-player; it goes **through the GM**, so that players' 1B models do not have to deal with prompt injection from other players directly.

[DECIDED] In each round, after the current event is announced and before actions are submitted, each harness has a broadcast window in which it may send **at most one** optional message to the GM. The recipient must be exactly one of `[None]`, `[all]`, or a specific `[class]`. `[None]` means no message; a submitted message cannot be empty. After the broadcast-submission barrier, the GM announces `[all]` messages to all harnesses and class-addressed messages to the harness for that class. Each announcement identifies the sender by class. Harnesses receive broadcasts before deciding their actions. A harness that misses the broadcast window cannot send a message that round and receives no extension or additional time.

[DECIDED] Each turn's action is directed either at the **current event** or at a **specific player/class**, not both. Player-directed interactions are **positive only**. Organisers will define the positive interactions available for each class; examples include healing, lending mana, and defending another player. Attacks, sabotage, and other negative player-directed interactions are not allowed. The exact class-specific interaction options are to be defined.

[DECIDED] Player-directed interactions do not require a response from the recipient. They are resolved before event-directed actions: successful interactions apply buffs to the affected player's stats, and event-directed actions are then resolved using the modified stats. See §9.

[DECIDED] **Consequence of hidden objectives:** messages between players cannot be assumed truthful. Players act simultaneously; there is no back-and-forth within a single round.

---

## 11. Action Format and Grammar-Constrained Generation

[DECIDED] Each turn, a player submits an optional broadcast during the broadcast window (see §10), followed by **only an action** to the GM as **structured JSON**. They submit nothing else; all memory and reasoning stays inside the harness.

[DECIDED] **Organisers define the grammar.** Participants' models use **grammar-constrained generation** so output is always syntactically valid JSON in the required structure. This avoids malformed JSON and stray natural-language text.

[DECIDED] The action includes an **open-ended free-text field.** Actions must be open-ended (e.g. "seduce the giant"), so a rigid enumerated verb list is not enough.

Illustration of the _kind_ of output (**not the final schema**):

```json
{
  "action": "attack",
  "target": "giant"
}
```

> [OPEN] **OPEN: the full action schema is not decided.** The exact field names, which fields are enumerated vs free text, field length limits, and how the mutually exclusive event/player target and class-specific positive interactions are represented are undecided. **Do not hard-code a schema.** Isolate schema handling in one module so it can change (see §20).

[DECIDED] **Syntactically valid ≠ valid in-game.** The game engine must still validate every submitted action.

[DECIDED] A player whose action is invalid, or not submitted within the action-submission time limit, receives a **health penalty**.

> [OPEN] The size of the penalty, whether the player's action is otherwise treated as no action, whether the penalty can kill a player, and whether a retry is allowed.

---

## 12. The Participant Harness

[DECIDED] Participants submit a **Python class** implementing their harness. Organisers run it for the actual game.

[DECIDED] Each player has one harness instance for the duration of their participation in a run. The instance persists across turns, and its in-memory state is retained between calls. A new instance is created for each player at the beginning of each run. When a player dies, their harness is discarded and is no longer invoked.

> [OPEN] The exact Python class interface, including method names, signatures, and lifecycle hooks (init, initial-state hook, per-turn method, etc.), will be defined by the organisers.

### What the harness is responsible for

- Parsing the observation (current event, own stats, broadcasts received, resolution outcome, initial-state info).
- Memory: deciding what to store, compress, and discard, in RAM and within the cap.
- Context management within the fixed window.
- Summarisation and prioritisation.
- Tracking own state, other players' info (from initial state), and the objective.
- Matching each boss encounter's description against its nemesis description, and performing the required vendetta action when it meets its nemesis.
- Choosing an action and emitting it in the required structured format.
- Adapting to whichever class it is assigned.

### What is allowed

- [DECIDED] **Non-LLM logic**: rules, regex, heuristics, structured data stores, keyword retrieval, embeddings (computed at runtime within the cap), etc.
- [DECIDED] Any **in-memory** memory strategy (summarisation, retrieval, structured memory, compression) that fits within the CPU/RAM cap.
- [DECIDED] The 1B model for narrow reasoning steps.
- [DECIDED] Each harness runs under an enforced maximum **CPU** and **memory (RAM)** cap. [OPEN] The cap values, whether the 1B model's footprint counts against the cap, and what happens on a breach (process killed, treated as a timed-out action, etc.). Keep both caps as configuration values.

### What is not allowed

- Internet access of any kind.
- Calling external LLMs/APIs (OpenAI, Gemini, Claude, etc.).
- Downloading models or resources during gameplay.
- Using a model larger than the provided 1B model.
- Attempting to access the hidden graph, organiser resources, or other players' data.
- Modifying own stats or the authoritative game state.
- Exceeding the CPU/RAM caps, or attempting to persist data outside the harness's own process memory.

[DECIDED] Within the action-submission time limit, a harness may do any internal processing it wants, including one or multiple LLM calls per turn. During resolution, the harness only needs to confirm receipt (§7).

[DECIDED] Harnesses have **no persistent storage to speak of**. All memory lives in the harness instance's process memory (RAM). It persists across turns within a run (as stated above) and is lost when the harness is discarded or the run ends. Memory strategies must not depend on reading or writing files, and disk may not be used to extend the memory budget. Each player's memory is isolated from other players and organiser resources.

> [OPEN] Whether any small ephemeral scratch area (e.g. a size-capped tmp directory) exists. Until decided, assume none.

> [OPEN] **Undecided:** token budget per turn, and the exact time limits (§7).

### Context vs. memory (distinct concepts)

|             | Context window                                           | External memory                                                                                 |
| ----------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| What        | Max information the model processes in **one inference** | Anything the harness keeps **outside the model, in process RAM** (no persistent storage)        |
| Who decides | **Organisers** (fixed, identical for everyone)           | **Participants**                                                                                |
| Example     | A fixed N-token limit                                    | Keep a compact event log in RAM (bounded by the cap), retrieve a small relevant subset per turn |

The context-window size is fixed by organisers and the same enforcement rules apply to every participant. The per-turn token budget, if any, is a separate limit across the harness's model calls during one turn.

---

## 13. Model, Context Window and Hardware Constraints

- [DECIDED] Participants **must** use a **1B-parameter** language model.
- [DECIDED] Organisers set a **fixed context window**, identical for all participants and **independent of hardware**. This prevents anyone gaining an edge from hardware that can run a larger context.
- [DECIDED] The context limit must be enforced by the supplied inference/runtime configuration, not merely documented in participant instructions. The same enforcement rules and token-counting convention must apply to every participant.
- [OPEN] The exact token-counting convention (including system prompt, observation, memory, and generated tokens) must be specified.
- [DECIDED] **Assumed participant hardware:** 8 GB RAM, integrated GPU, 6-core CPU. The 1B model must run within this envelope.
- [DECIDED] The per-harness CPU/RAM cap (§12) is an **enforced limit** applied on top of the assumed hardware envelope, not just guidance.
- [DECIDED] **Actual execution location:** during the real game, the participant model and harness execute on the organisers' host, which runs on **GCP**. The assumed hardware above describes participants' own machines during the build phase.
- [DECIDED] Organisers provide a **common Docker environment** so participants don't each configure everything.
- [DECIDED] The Docker image is distributed via **GitHub Container Registry (GHCR)**.

> [OPEN] **Undecided:** the specific 1B model, its quantisation, and the context window size. Organisers must ensure the _same model configuration and context limit_ apply to everyone.

---

## 14. Security Model

### 14.1 No external access

The participant harness executes in its isolated Docker environment on the GCP host. The container must not be able to reach the public internet or external APIs during gameplay. The organisers still need a controlled way to deliver observations and collect actions. Keep that organiser-to-agent communication separate from public network access (for example, an organiser-controlled local IPC/runner design); the exact transport is an implementation decision. The container must not have access to the host filesystem, organiser-only files, secrets, or the real graph, and has no writable persistent storage.

Harness execution environments must have **no internet access**, to prevent:

- External LLM API calls and outsourcing reasoning to larger models.
- Accessing external websites or services.
- Downloading additional models during gameplay.

### 14.2 Isolation and integrity

- Prevent access to the hidden skeletal graph.
- Prevent access to information participants shouldn't have (other players' objectives, vendetta assignments, hidden node data).
- Prevent participants from directly editing stats or authoritative state.
- **Validate every submitted action** in the engine.
- Restrict external API access.
- Isolate each participant's execution environment (sandboxing).
- Ensure participant code cannot reach unauthorised organiser resources.
- Enforce the CPU and RAM caps at the runtime level (container/cgroup limits), not by honour system.

---

## 15. Tournament Structure

- [DECIDED] The real game is run as **multiple independent runs**.
- [DECIDED] **Exactly 5 players per run**, one per class. There are more than 5 participants in total; for each run, 5 are picked at random to fill the 5 classes.
- [DECIDED] Each run draws its own random boss order (§4).
- [DECIDED] Each participant plays exactly **one run**.
- [OPEN] What happens when the number of participants is not a multiple of 5, since each run needs exactly 5 players, one per class.
- [DECIDED] Each run starts a **fresh game**; after it ends, the next group plays.
- [DECIDED] Classes are assigned **at the start of each run**, after harnesses are frozen, so participants cannot tune to a specific class.
- [OPEN] Cross-run scoring and aggregation are undecided.

---

## 16. End-to-End Event Flow

### Phase A: Build

1. Organisers prepare the Docker container and publish it via GHCR.
2. Participants pull the container.
3. Participants receive class descriptions (attributes, abilities, objectives, vendetta without naming the boss).
4. Participants receive general game info and constraints, plus a rough story idea.
5. Participants get access to the GM (same model as real GM).
6. Participants get a small **individually playable test game** and a **test suite**.
7. Participants build their harness around the 1B model.
8. Participants design their memory and context strategies, in-memory only and within the CPU/RAM cap.
9. Participants test against the test game.
10. Participants submit their Python class.

[DECIDED] **Not available in this phase:** the real skeletal graph, the real game plan, assigned class, class-specific real stats.

### Phase B: Real Game

1. Organisers collect and freeze submissions.
2. For each run, 5 participants who have not yet played are drawn at random; each participant plays exactly one run.
3. Each drawn participant is assigned one of the 5 classes, one per class.
4. Each participant receives the initial-state observation (current event, own stats and objective including the nemesis description and required vendetta action, and other players' classes and stats).
5. The game begins.
6. In each round, each living participant receives the current event and their own stats.
7. Each harness may submit at most one optional broadcast to the GM during the broadcast window, addressed to `[None]`, `[all]`, or a specific `[class]`.
8. The broadcast-submission barrier waits for submissions. The GM announces messages to their intended recipients, identifying each sender by class. A harness that misses the window loses its opportunity to broadcast that round.
9. After receiving broadcasts, each harness decides and submits an action within the action-submission time limit. The action is directed either at the current event or at a specific player/class, not both. An invalid or late action receives a health penalty.
10. Player-directed positive interactions receive their dice rolls first and successful effects are applied as buffs to affected players' stats. Event-directed actions then receive their dice rolls and are resolved using the modified stats. A required vendetta action against the player's nemesis uses a lower threshold; on success the player gets a stat buff, announced to everyone.
11. If the boss was not defeated, the GM decides the boss's action and the engine applies its effects.
12. The GM narrates the collective resolution, including the boss's action. The resolution outcome is announced to all active harnesses. Players who die during resolution are announced as dead, their harnesses are discarded, and they do not participate in the confirmation barrier.
13. The confirmation barrier waits for confirmations from surviving players (shorter time limit).
14. The GM chooses the next state from the graph (up to the configured limit of consecutive dynamic nodes; 2 is proposed) and connects it with the next randomly drawn boss (§4). Each node lasts exactly one round.
15. All surviving players continue together.
16. The run ends when the round at an ending node completes.
17. Ranking: surviving to the end is required; then completing your vendetta; then stat total.

---

## 17. Build-Phase Deliverables for Participants

What organisers must hand out:

- [ ] Docker image on GHCR (with model, runtime, and resource-limit setup).
- [ ] Class descriptions (stats, abilities, objectives for all 5 classes, stating that each has a vendetta; nemesis descriptions and required actions are given only in the initial-state observation, §8).
- [ ] Boss descriptions, if any boss information is disclosed. _(blocked on open question)_
- [ ] General game rules and constraints document.
- [ ] Rough story outline (without spoiling the real graph).
- [ ] Access to the GM.
- [ ] Test story (mini game, individually playable).
- [ ] Test suite.
- [ ] Python class interface and submission instructions.
- [ ] Action grammar / schema documentation. _(blocked on open question)_
- [ ] Observation, broadcast and resolution message format documentation. _(blocked on open question)_
- [ ] Fixed context window and model configuration documentation.
- [ ] Documentation of the CPU/RAM caps and the no-persistent-storage rule. _(cap values blocked on open question)_

---

## 18. Organiser Task List

From the whiteboard (originally marked **"for tomorrow"**; date not recorded):

- [ ] Basic scenarios.
- [ ] Model finalisation.
- [ ] Player + GM.
- [ ] Docker container setup.
- [ ] Python class schema.
- [ ] Security measures.

Additional implied work:

- [ ] Build the directed graph engine and node data model.
- [ ] Implement the GM prompt/pipeline with skeleton-graph access and dynamic-node generation (configured maximum of consecutive dynamic nodes).
- [ ] Implement the synchronisation barrier and the turn loop.
- [ ] Implement dice and resolution.
- [ ] Implement action validation.
- [ ] Implement the grammar for constrained generation.
- [ ] Implement sandboxing, network isolation, CPU/RAM cap enforcement and a read-only filesystem for harness execution.
- [ ] Author the real story graph, including endings.
- [ ] Define class roster, stats, abilities, and objectives.
- [ ] Author the 5 bosses (with the descriptions used in boss encounters), each class's nemesis description, and each class's required vendetta action.
- [ ] Implement the per-run game state (stats, history, boss draw), kept separate from the static story graph.
- [ ] Implement the random boss draw per run and the GM steps that connect the drawn boss to a story node, fill in defined interactions, and decide the boss's action.
- [ ] Define the stat-total calculation, the health penalty, the vendetta threshold and stat buff, and how results are compared across runs.

---

## 19. Open Questions

Anything here is **undecided**. Do not assume answers.

### Highest priority (blocks the participant-facing interface)

1. **The action schema** (explicitly deferred by organisers). Field names, which are free text vs enumerated, length limits, and representation of event/player targets and class-specific positive interactions. (§11)
2. Exact Python class interface, including method names, signatures, and lifecycle hooks (init, initial-state hook, per-turn method, etc.). (§12)
3. Exact contents and format of every GM → participant message: initial-state observation, per-turn observation, broadcast delivery, and resolution outcome. (§5)
4. The positive interactions available to each class (e.g. healing, lending mana, defending). (§10)
5. Whether the GM forwards broadcast text word for word or rewrites it. Forwarding it word for word lets one player's prompt injection reach another player's 1B model, which routing through the GM is meant to prevent. (§10)
6. Health penalty details: its size, whether the invalid or late action is otherwise treated as no action, whether the penalty can kill a player, whether a retry is allowed, and what happens on a missed confirmation. (§7, §11)

### Model and compute

7. Which 1B model, which quantisation. (§13)
8. Context window size. (§13)
9. Token budget per turn. (§12)
10. Durations of the broadcast window, the action-submission and confirmation time limits, and the total game time limit; whether a window closes early once every living harness has submitted. (§7)
11. CPU and RAM cap values, whether the 1B model's footprint counts toward them, and behaviour on breach. (§12)
12. Maximum submission size and bundled assets. With no runtime storage, can participants ship precomputed data (embedding models, vector indexes, lookup tables) inside the submission? This affects whether "embeddings" is realistically usable. (§12)
13. Whether any ephemeral scratch/tmp area exists. (§12)
14. The GCP host: the instance type; whether the 5 harnesses run in parallel or one after another, with equal CPU and RAM each; whether a GPU is present and usable; and how the per-harness caps relate to the 8 GB RAM / 6-core machines participants build on, so a harness behaves the same on the host as it did in testing. (§13)
15. Who enforces the output grammar: the supplied runtime, or each participant's harness. (§11)

### Game mechanics

16. Dice system and whether stat-to-roll rules are disclosed. (§9)
17. Order of resolution within the player-directed group and within the event-directed group, and how conflicting actions within a group are resolved. The order between the two groups is decided (§9).
18. Exact maximum for consecutive dynamic nodes (2 is the proposal). (§6)
19. What happens if every player dies before an ending node is reached. (§7)
20. Broadcast edge cases: addressing a dead player's class or your own class, and whether other players learn that a class-addressed message was sent. (§10)
21. What causes death: HP reaching 0, or something else. (§7, §8)

### Bosses and story shape

22. Whether every node, including dynamic nodes, carries a boss, and therefore whether every run is exactly 5 rounds. If so, each player makes only 5 actions per run, which reduces how much the memory and context-management challenge in §2 matters. (§4, §6)
23. Where boss data (stats, HP, abilities) is held, and whether any of it beyond the boss's name and description is shown to participants, either in build-phase descriptions or in observations. (§4)
24. Whether boss damage and target selection follow fixed rules applied by the engine or are left to the GM's judgement, and whether the boss acts in a round where it is defeated. Results left to the GM's judgement may differ between runs and cannot be reproduced if disputed. (§4)
25. Confirm that nemesis descriptions and required actions are given only in each class's own initial-state observation, not also in the public build-phase class descriptions. If they were public, any player could work out other players' objectives, which §5 says are hidden. (§5, §8)

### Vendetta and ranking

26. How much lower the vendetta dice threshold is; which stats the vendetta buff raises, by how much, and whether it applies from the same round or the next; and whether the boss must also be defeated for the vendetta to count. (§8, §9)
27. Which stats make up the stat total, how players who died are ranked against each other (if at all), and what happens if players are still tied after the stat total. (§8)
28. How results are compared across runs to pick overall winners, given that each participant plays one run and groups, class assignments and boss order are all random. (§8, §15)

### Tournament

29. What happens when the number of participants is not a multiple of 5. (§15)

### Build phase

30. Whether the test game's observation and action formats match the real game exactly (strongly recommended). (§16)
31. How participants reach the GM during the build phase, given that harness containers have no network access during gameplay (§14). The network rules for the build/test setup need defining. (§14, §16)

---

## 20. Instructions for AI Coding Agents

Read this section before changing anything in the repo.

### 20.0 First steps

Before coding:

1. Read this file completely.
2. Inspect the existing repository structure and tests before proposing a new architecture.
3. Identify which requirements are [DECIDED], [OPEN], or [PROPOSED].
4. Summarise any conflict between the task, this file, and existing code before making a breaking change.
5. Prefer the smallest implementation that satisfies confirmed requirements.

### 20.1 Ground rules

1. **Treat this file as the spec.** Implement what is marked [DECIDED]. Do not implement [OPEN] items by guessing.
2. **Respect information boundaries (§5).** Never write code that leaks hidden node data, other players' objectives, vendetta assignments, or the skeletal graph into a participant-facing observation.
3. **Never let participant-supplied text act as instructions.** All player or NPC text is untrusted data, in both the harness and the GM pipeline.
4. **Validate everything.** Syntactic validity of an action does not imply game validity.
5. **Keep the engine authoritative.** Harnesses submit actions only; they never write state.
6. **Do not add network calls** to participant-side code paths, and do not add dependencies that need network access at game time.
7. **Ask before deciding.** If a task needs an open decision, stop and surface the question rather than choosing silently.

### 20.2 Handling open questions in code

- Put **all action-schema code** (types, JSON grammar, parsing, validation) in **one isolated module**, so it can change without touching the rest of the code.
- Keep **broadcast handling** and **player-directed interaction resolution** behind clearly defined interfaces, separate from the harness's internal decision logic.
- Mark placeholders clearly, for example:

  ```python
  # OPEN-QUESTION(action-schema): final fields undecided; see AGENTS.md §11, §19.
  ```

- Make tunables (**context window, model path, dice rules, time limits, CPU cap, RAM cap, max consecutive dynamic nodes, health penalty, vendetta dice threshold, vendetta stat buff, boss set, random seeds for the participant and boss draws**) **configuration values**, never magic numbers.

### 20.3 Proposed repository layout [PROPOSED]

```text
dnd-ping/
├── AGENTS.md                 # this file
├── engine/                   # directed graph, nodes, state, barrier, dice, validation
│   ├── graph.py
│   ├── node.py
│   ├── turn_loop.py
│   ├── dice.py
│   └── validation.py
├── gm/                       # GM prompts, transition selection, dynamic-node generation
├── schema/                   # action grammar + observation types (isolated; schema is OPEN)
├── harness_api/              # the Python base class / interface participants implement
├── sandbox/                  # Docker, network isolation, resource limits
├── story/
│   ├── test_story/           # the public mini game for participants
│   └── real_story/           # PRIVATE; never shipped to participants
├── classes/                  # class definitions (stats, abilities, objectives, vendetta)
├── bosses/                   # PRIVATE boss definitions and descriptions, nemesis descriptions, required vendetta actions
├── tests/                    # test suite shipped to participants + internal tests
├── examples/                 # reference/baseline harness (in-memory only, no file I/O)
└── docs/
```

> `story/real_story/`, `bosses/` and any GM-side data must **never** be included in the participant Docker image.

### 20.4 Testing expectations

- Unit-test the engine: graph traversal, enforcement of the configured consecutive-dynamic-node limit, barrier behaviour (including that dead players do not participate in the confirmation barrier), death handling (dead harnesses are no longer called), ending-node termination.
- Test information boundaries: assert participant observations contain **only** permitted fields, never state which class's nemesis each boss is, and never reveal another class's nemesis description or required action.
- Test action validation: malformed, out-of-range, and adversarial inputs.
- Include **prompt-injection test cases** (e.g. NPC dialogue or player text attempting to override instructions or extract hidden objectives).
- Test against a resource-constrained configuration: the configured CPU/RAM caps within the assumed hardware (8 GB RAM, 6 cores, no GPU assumption). Test breach behaviour once decided, and test that any attempt to write to the filesystem fails.
- Test the boss draw: each boss appears exactly once per run, in a random order, and the draw is reproducible from its seed.
- Test the turn loop: one action per player per node; the broadcast barrier (missed windows, `[None]`, empty messages rejected, routing to `[all]` vs one class); the boss action is applied only when the boss is not defeated; stats carry over between nodes; an invalid or late action applies the health penalty; the lower vendetta threshold applies only to a player's required action against their own nemesis, and a successful vendetta announces the stat buff to everyone.
- Test that the per-run game state is kept separate from the static story graph, so one run cannot affect another.
- Ensure the test story exercises the **same observation/action path** as the real game.

### 20.4.1 Security implementation principles

- Treat participant submissions as untrusted code, not merely untrusted prompts.
- Do not treat Docker alone as a complete security boundary. Use least privilege, non-root execution, dropped capabilities, resource limits, a read-only root filesystem and no writable volume mounts (no persistent storage is provided to harnesses), and a stronger sandbox/VM boundary if the threat model requires it.
- Do not mount the Docker socket, host home directories, organiser secrets, the real story graph, or unrelated host paths into participant containers.
- Build and preload images/model assets before gameplay; runtime network access must not be needed.
- On the GCP host, block harness network egress at the cloud level as well (for example firewall rules and no external IP), not only inside Docker.
- Keep authoritative stats, dice, transition checks, and game state on the organiser side.
- Never rely on a prompt instruction to protect information that can simply be withheld from the participant observation.
- Log enough to audit actions, validation failures, timeouts, game transitions, and the random seeds and results of the participant and boss draws, without leaking hidden information to participants.

### 20.5 Style conventions

- Python 3, type hints on public interfaces, small pure functions where possible.
- Keep the participant-facing interface **minimal and stable**. Changes to it affect every participant.
- Prefer explicit configuration over hidden globals.
- Document every public class and function with its place in the turn sequence (§7).

### 20.6 Things an agent must not do

- Do not add features that give the GM or engine's hidden information to harnesses.
- Do not weaken sandboxing or the network restrictions to "make tests pass".
- Do not hard-code the real story, class stats, boss data, nemesis descriptions, required vendetta actions, or scoring before the organisers finalise them.
- Do not assume a specific model, quantisation, or context size.
- Do not invent details of the final action schema or class-specific positive interactions that organisers have not defined.
- Do not write harness, example, or test-story code that depends on file I/O or persistent storage.
- Do not hard-code CPU/RAM cap values.

---

## 21. Change Management and Specification Hygiene

When organisers make or revise a decision:

1. Update the relevant section in this file.
2. Update the status marker ([DECIDED], [OPEN], or [PROPOSED]).
3. Remove the resolved item from Open Questions.
4. Update interfaces, configuration, tests, and participant-facing documentation together.
5. Add or update tests for any changed information boundary, turn rule, or security requirement.

Do not leave contradictory old rules elsewhere in the file. If a decision changes the architecture, update the relevant prose descriptions and end-to-end flow as well. Do not add ASCII architectural diagrams.

---

## 22. Glossary

| Term                               | Meaning                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Harness**                        | The participant's Python class plus all logic around the 1B model: memory, context handling, decision logic.                                                                                                                                                                                                                                                                                                                                                                                                                         |
| **GM (Game Master)**               | The unconstrained organiser-hosted model that interprets actions and picks transitions.                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Skeletal graph**                 | The predefined directed graph of the real story. Hidden from participants.                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| **Node**                           | One game state, played for exactly one round. Holds only the story; stats, history and the drawn boss live in the game state.                                                                                                                                                                                                                                                                                                                                                                                                        |
| **Dynamic / intermediate node**    | A GM-generated node between skeletal nodes; max 2 in a row (proposed).                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **Defined interactions**           | Obvious interactions the GM fills in for each node once its boss is drawn; hidden; not a restriction on player actions.                                                                                                                                                                                                                                                                                                                                                                                                              |
| **Observation**                    | What a harness receives: the current event (with the boss's name and description) and own stats each round, plus initial-state info in round 1, broadcasts addressed to it, and the resolution outcome after each round.                                                                                                                                                                                                                                                                                                             |
| **Action**                         | The structured JSON a harness returns each turn. It targets either the current event or a specific player/class. Schema is OPEN.                                                                                                                                                                                                                                                                                                                                                                                                     |
| **Game state**                     | The engine's authoritative per-run record: player stats, history, and the boss draw. Kept separate from the static story graph.                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Boss**                           | One of a set of 5 bosses. Each is encountered once per run, in a random order; the GM connects the drawn boss to the current story node. Its name and description are shown to players; if it is not defeated, the GM decides its action.                                                                                                                                                                                                                                                                                            |
| **Vendetta**                       | A class's personal grudge against one particular boss, its nemesis; every class's nemesis is different. In the initial-state observation the class gets a description of its nemesis and a specific action to perform when it meets it. If the GM judges the action matches and its dice roll succeeds (against a lower threshold), the class gets a stat buff announced to everyone. Completing it is the first ranking tie-breaker. The nemesis is not named; the harness must recognise it from the boss encounter's description. |
| **Broadcast**                      | An optional message sent by a harness to the GM during the broadcast window, addressed to none, all, or a specific class.                                                                                                                                                                                                                                                                                                                                                                                                            |
| **Player-directed interaction**    | A positive-only action targeting another player; successful effects apply as buffs before event-directed actions are resolved.                                                                                                                                                                                                                                                                                                                                                                                                       |
| **Synchronisation barrier**        | A point where the game waits for harnesses, up to a set time limit. There are three per round: broadcasts, then actions (before dice rolls), then confirmations of receipt of the resolution outcome (shorter limit than actions).                                                                                                                                                                                                                                                                                                   |
| **Run / playthrough**              | One independent game with 5 players drawn at random, one per class, facing all 5 bosses in a random order. Each participant plays exactly one run.                                                                                                                                                                                                                                                                                                                                                                                   |
| **Ending node**                    | A terminal node in the graph; once the run reaches any and the round there completes, the run ends.                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **Resource cap**                   | The enforced maximum CPU and RAM available to a harness. Values are OPEN. Harnesses have no persistent storage, so all memory is in-process RAM.                                                                                                                                                                                                                                                                                                                                                                                     |
| **GHCR**                           | GitHub Container Registry, used to distribute the Docker image.                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Grammar-constrained generation** | Decoding restricted to a predefined grammar so output is always valid structured JSON.                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| **Prompt injection**               | Text that tries to override a model's instructions; must be treated as untrusted content.                                                                                                                                                                                                                                                                                                                                                                                                                                            |

---

_Maintained from the organisers' planning discussion, whiteboard notes, and subsequent clarifications. When a decision is made, update the relevant section and remove it from §19. Do not silently promote a proposal or assumption into a requirement._
