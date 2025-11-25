# Variants Tree Explorer

A tool for building and visualizing perfect game trees for variants using Fairy Stockfish engine.

## Overview

This project consists of two components:

1. **Google Colab Notebook** — Builds the game tree by analyzing positions with Fairy Stockfish
2. **HTML Viewer** — Interactive browser-based visualization of the generated tree

The explorer follows the principal variation while also tracking alternative moves, creating a tree structure that can be navigated and studied.

## Features

### Tree Generator (Colab)

- Supports multiple chess variants: chess, atomic, antichess, crazyhouse, 3check, racingkings, horde, tinyhouse, and custom variants
- Configurable search depth, threads, and hash size
- NNUE support for variants with trained networks
- Custom variant definitions via `variants.ini`
- Automatic save/resume — progress is stored on Google Drive
- Negamax backpropagation of evaluations through the tree

### Tree Viewer (HTML)

- Clean, responsive interface (desktop & mobile)
- Interactive chessboard with piece banks for crazyhouse/tinyhouse variants
- Move list sorted by evaluation with best/worst highlighting
- Navigation: step forward/back, jump to start/end
- Keyboard shortcuts (arrow keys, Home, End)
- Copy FEN or node ID to clipboard
- Hot reload — refresh the tree while exploring without losing position

## Getting Started

### 1. Generate the Tree

Open the Colab notebook and configure:

```python
VARIANT = "atomic"    # Chess variant to analyze
THREADS = 4           # CPU threads
HASHMB  = 4096        # Hash table size in MB
DEPTH   = 30          # Search depth per position
```

The notebook will:
- Build Fairy Stockfish (or use cached binary from Drive)
- Load any existing tree from `trees/{variant}/{variant}.epd`
- Continuously expand the tree following best moves
- Save progress to Google Drive

### 2. View the Tree

1. Download the generated `.epd` file from Google Drive
2. Open `perfect_tree_viewer.html` in a modern browser
3. Click **Load File** and select your `.epd` file
4. Navigate the tree by clicking moves or using controls

## File Format

The tree is stored in a simple EPD-like format:

```
node_id;fen;move1,move2,...;eval1,eval2,...;child1,child2,...;complete
```

| Field | Description |
|-------|-------------|
| `node_id` | Unique integer identifier |
| `fen` | Position (board + side to move) |
| `moves` | Comma-separated UCI moves |
| `evals` | Centipawn evaluations (29999 = mate in 1) |
| `child_ids` | Node IDs of child positions (-1 = unexpanded) |
| `complete` | 1 if all legal moves analyzed, 0 otherwise |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ← | Go back one move |
| → | Go forward (best move) |
| ↑ / Home | Jump to starting position |
| ↓ / End | Jump to end of principal variation |

## Requirements

### Colab Notebook
- Google account with Drive access
- ~30 minutes for initial Stockfish compilation (cached afterwards)

### HTML Viewer
- Modern browser with File System Access API (Chrome, Edge, Opera)
- For other browsers: basic file loading works, hot reload unavailable

## Directory Structure (Google Drive)

```
trees/
├── stockfish              # Compiled binary (shared)
├── variants.ini           # Custom variant definitions (optional)
└── {variant}/
    ├── {variant}.epd      # Tree data
    ├── {variant}.log      # Exploration log
    └── *.nnue             # NNUE weights (optional)
```

## Tips

- The tree grows at leaf nodes — terminal positions and unexpanded moves shown with ○
- Use the log file to track exploration progress and root evaluation over time
- For variants without NNUE, classical evaluation is used automatically

## License

MIT License

## Acknowledgments

- [Fairy Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) — the engine powering the analysis
