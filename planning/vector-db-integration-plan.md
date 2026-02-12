# Vector Database Integration Plan for Obsidian Vault MCP

## The Problem

Your MCP server currently searches 2000+ notes with **substring matching** -- `note.contains_text(query)` in a linear O(n) scan. This means:

- Searching "team communication improvements" **won't find** a note titled "Standup Process Changes" or "Collaboration Feedback Loop"
- `gather_topic()` only finds notes containing the literal topic string + exact tag matches
- As the vault grows, search gets slower and less useful (more noise, same recall)

## What a Vector DB Adds

A vector database stores **semantic embeddings** -- numerical representations of meaning. Instead of "does this note contain the word X?", it asks "is the **meaning** of this note close to the **meaning** of the query?"

```
Current:  "authentication" → finds notes containing "authentication"
Semantic: "authentication" → finds notes about OAuth, JWT, login flows,
          session management, API keys, even if they never use the word
```

## Architecture: Option A (Recommended) -- Additive, Not Replacement

Add semantic search **alongside** existing keyword search. Zero changes to existing tool behavior. One new tool, one new module, fully optional.

```
User enables semantic search in config
         │
         ▼
┌─────────────────────┐
│   VaultIndex        │
│  ┌───────────────┐  │  ← Existing (unchanged)
│  │ Dict Index    │  │     O(1) title lookup, O(n) keyword search
│  │ {title: Note} │  │
│  └───────────────┘  │
│  ┌───────────────┐  │  ← New (optional)
│  │ SemanticIndex │  │     ChromaDB + embeddings
│  │ Vector Store  │  │     Cosine similarity search
│  └───────────────┘  │
└─────────────────────┘
         │
         ▼
  New MCP tool: obsidian_semantic_search
  Existing tools: unchanged
```

**Why not replace the existing search?** Keyword search is still better for exact matches ("find my note called API Redesign"), structured queries (filter by tag + date + PARA location), and it has zero startup cost. The two approaches are complementary.

## Embedding Model: Local vs API

### Local: fastembed + ONNX Runtime (Recommended)

| Aspect | Detail |
|--------|--------|
| **Model** | `BAAI/bge-small-en-v1.5` via fastembed |
| **Install size** | ~200MB total (fastembed + ONNX Runtime + model) |
| **Runtime memory** | ~230MB |
| **Speed** | ~30-50ms per chunk on CPU |
| **Privacy** | 100% local -- nothing leaves your machine |
| **API keys** | None needed |
| **First-time indexing** | ~2-3 min for 2000+ notes (one-time, then persisted) |
| **Quality** | Very good for retrieval tasks (top-tier on MTEB benchmarks for its size) |

**Why fastembed over sentence-transformers?** sentence-transformers pulls in PyTorch (~2.5GB). fastembed uses ONNX Runtime instead (~200MB total). Same quality, 10x smaller footprint. For a local MCP server, this matters.

### Remote: OpenAI text-embedding-3-small

| Aspect | Detail |
|--------|--------|
| **Model** | `text-embedding-3-small` (1536 dimensions) |
| **Install size** | ~5MB (`openai` SDK only) |
| **Runtime memory** | Minimal (no local model) |
| **Speed** | ~100-200ms per chunk (network round-trip) |
| **Privacy** | All note content sent to OpenAI's API |
| **API keys** | `OPENAI_API_KEY` required |
| **First-time indexing** | ~5-10 min for 2000+ notes (rate-limited, network-bound) |
| **Cost** | ~$0.02 per million tokens. 2000 notes ≈ 1-2M tokens ≈ $0.02-0.04 for full index |
| **Quality** | Excellent (best-in-class for the size) |

### Remote: Other Options

| Provider | Model | Cost/1M tokens | Notes |
|----------|-------|----------------|-------|
| **Anthropic** | No embedding API | N/A | Not available (as of early 2025) |
| **Cohere** | `embed-english-v3.0` | Free tier available | Good quality, generous free tier |
| **Voyage AI** | `voyage-3-lite` | $0.02/1M tokens | Optimized for retrieval |
| **Google** | `text-embedding-004` | $0.00025/1K chars | Very cheap |

### Recommendation

**Default to local (fastembed)** but make the embedding provider configurable. The architecture should support swapping in an API-based provider via config, which is useful for:
- Users who already pay for OpenAI and want the best quality
- Future expansion: if this project becomes a general-purpose tool, API embeddings let users with smaller machines offload the compute
- CI/testing: API embeddings don't need the ONNX model cached

```python
# Config examples:

# Local (default)
embedding_provider: "local"
embedding_model: "BAAI/bge-small-en-v1.5"

# OpenAI
embedding_provider: "openai"
embedding_model: "text-embedding-3-small"
# Requires OPENAI_API_KEY env var
```

## Vector Store: ChromaDB

**Why ChromaDB:**
- SQLite-backed persistence (single directory, survives restarts)
- Built-in embedding function support (works with fastembed directly)
- Metadata filtering (filter by PARA location, tags, date ranges)
- Lightweight (~50MB)
- Active development, well-documented
- Handles deduplication via upsert

**Persistence location:** `{vault_path}/.obsidian/plugins/mcp-vectors/` -- keeps the vector data with the vault, excluded from Obsidian's own processing.

## Chunking Strategy

Obsidian notes have natural structure. The chunking strategy is **heading-based**:

```
Note: "API Redesign" (1 - Projects/PBSWI/)
│
├── Chunk 0: Full note if < 512 tokens
│   OR
├── Chunk 1: "## Overview" section
├── Chunk 2: "## Requirements" section
├── Chunk 3: "### Authentication Flow" subsection
├── Chunk 4: "## Open Questions" section
│
Each chunk prefixed with: "Title: API Redesign | Section: Requirements"
Each chunk carries metadata: {note_path, note_title, section, para_location, tags, content_hash}
```

- Notes under ~512 tokens: single chunk (most daily notes, quick captures)
- Long sections over ~1000 tokens: split at paragraph boundaries
- Prefix gives the embedding model context about what document/section this belongs to

## Implementation: File-by-File Changes

### New File: `obsidian_vault_mcp/embeddings.py` (~350 lines)

```python
class NoteChunker:
    """Split notes into embeddable chunks by heading structure."""
    def chunk_note(self, note: Note) -> List[Tuple[str, dict]]

class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""
    def embed(self, texts: List[str]) -> List[List[float]]

class LocalEmbeddingProvider(EmbeddingProvider):
    """fastembed/ONNX-based local embeddings."""

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API-based embeddings."""

class SemanticIndex:
    """Vector search index using ChromaDB."""
    def index_note(self, note: Note) -> int
    def remove_note(self, note_path: str)
    def search(self, query, n_results, para_location, tags) -> List[dict]
    def build_full_index(self, notes_by_path) -> Tuple[int, int]
    def needs_reindex(self, notes_by_path) -> bool
    def get_stats(self) -> dict
```

### Modified: `obsidian_vault_mcp/config.py` (+20 lines)

New fields in `VaultConfig`:

```python
enable_semantic_search: bool = False
embedding_provider: str = "local"          # "local" or "openai"
embedding_model: str = "BAAI/bge-small-en-v1.5"
chroma_persist_dir: Optional[str] = None   # Default: vault/.obsidian/plugins/mcp-vectors/
semantic_search_results: int = 20
chunk_max_tokens: int = 512
```

Environment variable: `OBSIDIAN_VAULT_SEMANTIC_SEARCH=true`

### Modified: `obsidian_vault_mcp/vault.py` (+40 lines, ~15 lines changed)

- Add `semantic_index: Optional[SemanticIndex]` to `VaultIndex`
- Add `_init_semantic_index()` method
- Add `upsert_note()` method that updates both dict index and vector index
- Replace 4 manual index-update sites with `upsert_note()` calls
- Update `refresh()` to rebuild semantic index too

### Modified: `obsidian_vault_mcp/server.py` (+70 lines)

- New `SemanticSearchParams` Pydantic model
- Register `obsidian_semantic_search` tool in `list_tools()`
- Handler in `call_tool()` -- query semantic index, format results with similarity scores

### Modified: `setup.py` (+5 lines)

```python
extras_require={
    "semantic": ["chromadb>=0.4.0", "fastembed>=0.2.0"],
    "semantic-openai": ["chromadb>=0.4.0", "openai>=1.0.0"],
}
```

Users install with `pip install -e ".[semantic]"` for local or `pip install -e ".[semantic-openai]"` for API-based.

## New MCP Tool: `obsidian_semantic_search`

```
Name: obsidian_semantic_search
Description: Search notes by meaning using AI embeddings. Finds conceptually
             related notes even without exact keyword matches.

Parameters:
  query: str           - Natural language query
  para_location: str?  - Filter by PARA location
  limit: int = 10      - Max results
  include_content: bool = False - Include full note content

Returns:
  Ranked results with:
  - note title, path, PARA location, tags
  - similarity score (0-100%)
  - matching snippet (the chunk that was most similar)
  - section heading (where in the note the match was found)
```

Example interaction:
```
Claude: obsidian_semantic_search(query="improving team onboarding process")

Results (similarity > 70%):
1. "New Hire Checklist" (projects) [92%]
   Section: ## First Week
   > Day 1 setup includes laptop provisioning, account creation...

2. "Q4 Retrospective" (areas) [84%]
   Section: ## What Could Be Better
   > Several team members mentioned the ramp-up period was too long...

3. "Engineering Culture Doc" (resources) [78%]
   Section: ## Growing the Team
   > We invest heavily in mentorship pairs for new engineers...
```

None of these would be found by keyword search for "onboarding process."

## Performance Expectations (2000+ note vault)

| Operation | Time | When |
|-----------|------|------|
| First-time indexing | ~2-3 min | Once (persisted to disk) |
| Subsequent startup | ~200ms | ChromaDB opens existing collection |
| Semantic search query | ~60ms | Per query (embed + lookup) |
| Note create/update | ~50ms | Per note (re-embed chunks) |
| Full re-index | ~2-3 min | Only if manually triggered |
| Disk space (vectors) | ~50-100MB | For 2000+ notes |

## Implementation Phases

### Phase 1: Core Infrastructure
1. Config fields in `config.py`
2. `embeddings.py` with `NoteChunker`, `SemanticIndex`, provider abstraction
3. `upsert_note()` helper in `VaultIndex`
4. Wire `_init_semantic_index()` into startup
5. Optional dependencies in `setup.py`

### Phase 2: MCP Tool
6. `SemanticSearchParams` model
7. Register + implement `obsidian_semantic_search` tool
8. Result formatting with scores and snippets

### Phase 3: Write Sync
9. Replace manual index updates with `upsert_note()` (4 sites in vault.py)
10. Ensure `update_daily_note()` re-indexes after write
11. `refresh()` rebuilds semantic index

### Phase 4: Polish
12. Tests for chunking and search
13. Documentation updates
14. Startup logging (index stats, timing)

### Future Enhancements (not in initial scope)
- **Incremental sync**: Compare file mtimes vs stored content hashes, only re-embed changed notes
- **`obsidian_find_similar`**: Given a note, find N most similar notes
- **Hybrid ranking in `gather_topic`**: Merge keyword + semantic results with weighted scoring
- **Background indexing**: Re-embed changed notes in a background thread

## Is This Overkill?

**For your vault (2000+ notes): No.** This is the sweet spot where semantic search becomes clearly valuable:

- Keyword search through 2000 notes returns either too many results (common words) or zero results (wrong synonym)
- You can't remember exact terminology across years of notes
- Cross-project discovery becomes possible ("what do I know about X across all projects?")
- The `gather_topic` tool goes from "find notes with this word" to "find notes about this concept"

**When it WOULD be overkill:**
- Vaults under ~100 notes (you remember what's there)
- Pure task-tracking vaults (structured data, not prose)
- Heavily tagged vaults where tag-based filtering already gives good recall

## Dependency Impact

| Component | Install Size | vs Current |
|-----------|-------------|------------|
| Current server | ~5MB | Baseline |
| + chromadb | ~50MB | +50MB |
| + fastembed + ONNX | ~150MB | +150MB |
| + Model download (first run) | ~130MB | One-time |
| **Total** | **~335MB** | |

For comparison, `sentence-transformers` + PyTorch would be **~2.5GB**. The fastembed approach is ~7x lighter.

The key design decision: **all of this is optional**. `enable_semantic_search: false` (the default) means zero new dependencies, zero behavior changes, zero startup cost.
