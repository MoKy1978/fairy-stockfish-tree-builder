# Tree Explorer

**Tree Explorer** is a Python tool for automated chess (and chess-variant) game tree exploration using UCI-compatible engines. It incrementally analyzes positions, stores results in a persistent tree structure, and applies minimax search with length-based adjustments to find optimal lines.

## Features

* Automated deep position analysis with UCI engines
* Support for standard chess and variants (via UCI_Variant)
* MultiPV search for exploring multiple candidate moves
* Evaluation with distance-to-leaf weighted minimax
* Persistent storage with auto-save every 5 minutes
* Safe interruption with progress preservation
* Interactive web-based visualization of explored trees

## Requirements

* Python 3.7+
* UCI-compatible chess engine:
  * [Stockfish](https://stockfishchess.org/download/) for standard chess
  * [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) for variants

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/tree-explorer.git
   cd tree-explorer
   ```

2. Download and install a UCI engine:
   ```bash
   # For standard chess
   wget https://github.com/official-stockfish/Stockfish/releases/latest
   # Or for variants
   wget https://github.com/fairy-stockfish/Fairy-Stockfish/releases/latest
   ```

3. (Optional) Place NNUE evaluation files in variant folders:
   ```
   chess/*.nnue
   crazyhouse/*.nnue
   ```

## Project Structure

```
trees/
├── tree_explorer.py    # Main exploration engine
├── tree_viewer.html    # Interactive web visualization
├── README.md          
├── variants.ini        # Optional variant definitions
└── [variant]/          # Auto-created data directories
    ├── *.nnue         # Optional NNUE files
    └── [variant]_[depth].txt  # Position database
```

## Usage

### Basic Usage

Start exploration with default settings:
```bash
python3 tree_explorer.py
```

### Command-line Arguments

| Option      | Default     | Description                                          |
| ----------- | ----------- | ---------------------------------------------------- |
| `--variant` | `chess`     | Variant name (UCI_Variant and data folder)          |
| `--engine`  | `stockfish` | Path to UCI engine binary                           |
| `--threads` | `4`         | Number of engine threads                            |
| `--hash`    | `8192`      | Hash table size in MB                               |
| `--multipv` | `6`         | Number of principal variations to analyze           |
| `--depth`   | `24`        | Search depth for analysis                           |

### Custom Example

Tic-tac-toe with increased resources:
```bash
python3 tree_explorer.py --variant tictactoe --engine /usr/local/bin/stockfish-17 --threads 16 --hash 16384 --multipv 10 --depth 28
```

## How It Works

The explorer uses a sophisticated evaluation algorithm:

1. **Leaf Selection**: Follows the best line to reach a leaf position
2. **MultiPV Analysis**: Analyzes top N moves at specified depth
3. **Tree Expansion**: Adds new positions as children
4. **Minimax Propagation**: Updates scores recursively with:
   - Length adjustments to prefer shorter wins
   - Penalty for longer paths to mate
   - Formula: `score + length * log2(|score + 1|) * sign`
5. **Auto-save**: Progress saved every 5 minutes and on exit

### Output Example

```
e2e4 e7e5 g1f3 b8c6 f1b5
-15

e2e4 e7e5 g1f3 b8c6 f1b5 a7a6
-8

Saved 1247 positions
```

## Data Format

Results stored in `[variant]/[variant]_[depth].txt`:
```
% idx|move|score|best|length; fen; children;
0|None|0|1|5; rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1; 1,2,3,4,5;
1|e2e4|-15|8|4; rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1; 8,9,10;
```

Fields:
- `idx`: Position index
- `move`: Move from parent
- `score`: Evaluation (centipawns, negative favors Black)
- `best`: Index of best child
- `length`: Distance to the best line leaf
- `fen`: Position in FEN notation
- `children`: Comma-separated child indices

## Visualization

Open `tree_viewer.html` in a web browser to explore the tree interactively:

- **Navigation**: Click moves or use arrow keys
- **Keyboard shortcuts**: 
  - `←/→` - Back/Forward through moves
  - `Home/End` - Jump to start/end of line
- **Features**:
  - Dynamic board display
  - Move evaluations and scores
  - Best move highlighting
  - Load different analysis files
  - Support for variants and non-standard boards

## Stopping & Resuming

- **Ctrl+C** to stop safely - progress is automatically saved
- Program resumes from saved data on next run
- Manual saves occur every 5 minutes during exploration

## Troubleshooting

**Engine not found**
```bash
# Specify full path
python3 tree_explorer.py --engine /usr/local/bin/stockfish
```

**Variant not supported**
```bash
# Use Fairy-Stockfish for variants
python3 tree_explorer.py --variant xiangqi --engine ./fairy-stockfish
```

**Out of memory**
```bash
# Reduce hash size or MultiPV count
python3 tree_explorer.py --hash 4096 --multipv 3
```

**Windows compatibility**
```bash
# Engine auto-detects .exe extension
python tree_explorer.py --engine stockfish.exe
```

## Advanced Configuration

### Variants Configuration
Create `variants.ini` for custom variant definitions:
```ini
[yourvariant]
startFen = ...
pieceTypes = ...
```

### NNUE Networks
Place `.nnue` files in variant directories:
```
chess/nn-[hash].nnue
crazyhouse/crazyhouse-[hash].nnue
```

## Contributing

Contributions welcome! Areas of interest:
- Additional evaluation functions
- Parallel exploration support  
- Opening book integration
- Endgame tablebase support

## Roadmap

- [x] Core tree exploration engine
- [x] Web-based visualization
- [x] Auto-save and resume
- [ ] Real-time analysis display in viewer
- [ ] Export to PGN/analysis formats
- [ ] Position comparison tools
- [ ] Cloud storage integration
- [ ] Multi-engine comparison
- [ ] Distributed computation support

## License

MIT License - see LICENSE file for details.

## Acknowledgments

* [Stockfish](https://stockfishchess.org/) team for the UCI engine
* [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) for variant support
* Chess programming community for algorithmic insights

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
