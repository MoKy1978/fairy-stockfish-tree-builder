# Tree Explorer

**Tree Explorer** is a Python tool for automated chess (or chess-variant) game tree exploration using a UCI-compatible engine such as **Stockfish** or **Fairy-Stockfish**.
It incrementally analyzes positions, stores results in a persistent tree structure, and applies a lightweight minimax search to evaluate candidate moves.

---

## Features

* 🔍 Automated position analysis with UCI engines
* ♟️ Supports standard chess and arbitrary **variants** (via `UCI_Variant`)
* 🧠 MultiPV search for exploring multiple candidate moves
* 💾 Persistent storage of explored positions (`.txt` files per variant/depth)
* 📈 Incremental tree growth with minimax backpropagation
* ⏸ Safe interruption — results are auto-saved on exit

---

## Requirements

* Python **3.7+**
* A UCI-compatible chess engine, e.g.:

  * [Stockfish](https://stockfishchess.org/download/)
  * [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) (for variants)

---

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/tree-explorer.git
   cd tree-explorer
   ```

2. Ensure you have a working UCI engine (`stockfish` or `stockfish.exe`) in your PATH, or specify it via `--engine`.

3. (Optional) Place NNUE evaluation files (`.nnue`) in a folder named after the variant (e.g., `chess/`, `crazyhouse/`).

---

## Usage

Run Tree Explorer with default settings:

```bash
python3 tree_explorer.py
```

### Command-line arguments

| Option      | Default     | Description                                          |
| ----------- | ----------- | ---------------------------------------------------- |
| `--variant` | `chess`     | Variant name (used for UCI\_Variant and data folder) |
| `--engine`  | `stockfish` | Path to the UCI engine binary                        |
| `--threads` | `4`         | Number of engine threads                             |
| `--hash`    | `8192`      | Hash size in MB                                      |
| `--multipv` | `6`         | Number of principal variations to analyze            |
| `--depth`   | `16`        | Search depth for analysis                            |

Example:

```bash
python3 tree_explorer.py --variant crazyhouse --engine ./fairy-stockfish --threads 8 --hash 16384 --multipv 8 --depth 20
```

---

## Data Storage

* Results are stored in `<variant>/<variant>_<depth>.txt`.
* Format:

  ```
  % Tree Explorer: position_index|analysis_number|leaf_distance; fen_string; alternative_number|move_string|adjusted_score|child_index;
  ```
* Each analyzed position includes its FEN, best move, candidate moves, evaluations, and child references.

---

## Stopping & Resuming

* Press **Ctrl+C** to stop exploration safely.
* The program will:

  * Save all progress
  * Print the number of analyzed positions
  * Quit the engine gracefully
* On next run, it will **resume** from saved data.

---

## Example Workflow

1. Start from the default chess position.
2. The program picks a leaf node, analyzes candidate moves, and expands the tree.
3. For each new child position:

   * Adds FEN to the tree
   * Stores engine evaluation
   * Updates minimax values recursively
4. Progress is printed in the terminal and saved regularly.

---

## Roadmap / Ideas

* [ ] Add support for configurable evaluation functions beyond NNUE
* [ ] Export tree in PGN or JSON format
* [ ] Interactive exploration (GUI / web frontend)
* [ ] Parallel exploration

---

## License

This project is distributed under the MIT License.
See [LICENSE](LICENSE) for details.

---

## Acknowledgments

* [Stockfish](https://stockfishchess.org/) team for the base engine
* [Fairy-Stockfish](https://github.com/fairy-stockfish/Fairy-Stockfish) for chess variant support
* Inspiration from chess research and retrograde analysis projects
