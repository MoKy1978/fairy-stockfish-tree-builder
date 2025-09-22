#!/usr/bin/env python3
import platform
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

VARIANT = 'chess'
ENGINE = 'stockfish.exe' if platform.system() == 'Windows' else 'stockfish'
THREADS = 4
HASH = 8192
MULTIPV = 6
DEPTH = 16

@dataclass
class Position:
    fen: str
    analysis: int = 0
    leaf_distance: int = 0
    evals: List[int] = field(default_factory=list)
    moves: List[str] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)

class Engine:
    def __init__(self):
        self.process = subprocess.Popen(
            [ENGINE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=0
        )
        self.send("uci")
        self.receive("uciok")
        if Path('variants.ini').exists():
            self.send("load variants.ini")
        self.send(f"setoption name UCI_Variant value {VARIANT}")
        NNUE = next(Path(VARIANT).glob('*.nnue'), None)
        if NNUE:
            self.send(f"setoption name EvalFile value {NNUE}")
            self.send("setoption name Use NNUE value true")
        else:
            self.send("setoption name Use NNUE value false")
        self.send(f"setoption name Threads value {THREADS}")
        self.send(f"setoption name Hash value {HASH}")
        self.send(f"setoption name MultiPV value {MULTIPV}")

    def send(self, command: str):
        if self.process.poll() is None:
            self.process.stdin.write(f"{command}\n")
            self.process.stdin.flush()

    def receive(self, terminator: str) -> List[str]:
        lines = []
        while True:
            line = self.process.stdout.readline().strip()
            if not line and self.process.poll() is not None:
                break
            lines.append(line)
            if terminator in line:
                break
        return lines

    def get_fen(self, command: str = "position startpos") -> str:
        self.send(command)
        self.send("d")
        lines = self.receive("Sfen:")
        for line in lines:
            if line.startswith("Fen:"):
                return line.split("Fen:", 1)[1].strip()
        return ""
    
    def multipv(self, fen: str) -> List[Tuple[str, int]]:
        self.send(f"position fen {fen}")
        self.send(f"go depth {DEPTH}")
        pv_data = {}
        for line in self.receive("bestmove"):
            if "multipv" not in line:
                continue
            parts = line.split()
            try:
                if int(parts[parts.index("depth") + 1]) != DEPTH:
                    continue
                multipv_num = int(parts[parts.index("multipv") + 1])
                if multipv_num > MULTIPV:
                    continue
                move = parts[parts.index("pv") + 1]
                adjusted_score = None
                if "score" in parts:
                    adjusted_score = int(parts[parts.index("score") + 2])
                    if parts[parts.index("score") + 1] == "mate":
                        if adjusted_score  > 0:
                            adjusted_score  = 30001 - 2 * adjusted_score
                        else:
                            adjusted_score  = -30000 - 2 * adjusted_score
                pv_data[multipv_num] = (move, adjusted_score)
            except (ValueError, IndexError):
                continue
        return [pv_data[alt] for alt in sorted(pv_data.keys())]
    
    def quit(self):
        if self.process.poll() is None:
            self.send("quit")
            self.process.terminate()
            self.process.wait()

class Tree:
    def __init__(self):
        Path(VARIANT).mkdir(exist_ok=True)
        self.engine = Engine()
        self.positions = []
        self.fen_to_index = {}
        self.analysis_counter = 0
        self.root_index = 0
        self.data_path = Path(f"{VARIANT}/{VARIANT}_{DEPTH}.txt")
        self.load_data()
    
    def load_data(self):
        if not self.data_path.exists():
            self.new_tree()
            return
        with open(self.data_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('%'):
                    continue
                parts = line.rstrip(';').split(';')
                token = parts[0].split('|')
                idx = int(token[0])
                analysis = int(token[1])
                leaf_distance = int(token[2])
                fen = parts[1]
                moves = []
                evals = []
                indices = []
                for alt in range(2, len(parts)):
                    alt_data = parts[alt].split('|')
                    moves.append(alt_data[1])
                    evals.append(int(alt_data[2]))
                    indices.append(int(alt_data[3]))
                pos = Position(fen, analysis, leaf_distance, evals, moves, indices)
                self.positions[idx] = pos
                self.fen_to_index[fen] = idx
                if analysis > self.analysis_counter:
                    self.analysis_counter = analysis

    def new_tree(self):
        root_fen = self.engine.get_fen()
        self.add_position(root_fen, Position(fen=root_fen))
        self.positions[0].evals = [0]
        self.root_index = 0

    def add_position(self, fen: str, position: Position = None) -> int:
        if fen in self.fen_to_index:
            return self.fen_to_index[fen]
        index = len(self.positions)
        self.fen_to_index[fen] = index
        self.positions.append(position or Position(fen=fen))
        return index
    
    def save_data(self):
        lines = []
        lines.append("% Tree Explorer: position_index|analysis_number|leaf_distance; fen_string; alternative_number|move_string|adjusted_score|child_index;")
        for idx, pos in enumerate(self.positions):
            parts = [f"{idx}|{pos.analysis}|{pos.leaf_distance}", pos.fen]
            for alt in range(len(pos.evals)):
                move = pos.moves[alt] if alt < len(pos.moves) else ''
                index = pos.indices[alt] if alt < len(pos.indices) else -1
                parts.append(f"{alt}|{move}|{pos.evals[alt]}|{index}")
            lines.append('; '.join(parts) + ';')
        with open(self.data_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')

    def analyze(self):
        path = []
        line = []
        leaf_index = 0
        leaf_pos = self.positions[leaf_index]
        while True:
            path.append(leaf_index)
            if not leaf_pos.moves:
                break
            line.append(leaf_pos.moves[0])
            leaf_index = leaf_pos.indices[0]
            leaf_pos = self.positions[leaf_index]
        leaf_fen = leaf_pos.fen
        analysis = self.engine.multipv(leaf_fen)
        self.analysis_counter += 1
        leaf_pos.analysis = self.analysis_counter
        leaf_pos.moves = ['']
        leaf_pos.indices = [-1]
        print(f"\n#{self.analysis_counter} {leaf_pos.evals[0]} {' '.join(line)}")
        for alt, (move, adjusted_score) in enumerate(analysis, 1):
            print(f"  {alt} {move} {adjusted_score}")
            child_fen = self.engine.get_fen(f"position fen {leaf_fen} moves {move}")
            child_index = self.add_position(child_fen)
            if not self.positions[child_index].evals:
                self.positions[child_index].evals = [-adjusted_score]
            leaf_pos.moves.append(move)
            leaf_pos.evals.append(adjusted_score)
            leaf_pos.indices.append(child_index)
        for index in reversed(path):
            self.minimax(index)
    
    def minimax(self, index: int):
        pos = self.positions[index]
        if len(pos.moves) <= 1:
            return
        champion = -30000
        for alt in range(1, len(pos.indices)):
            child = self.positions[pos.indices[alt]]
            challenger = -3 * child.evals[0] - DEPTH * child.leaf_distance
            if challenger > champion:
                champion = challenger
                pos.moves[0] = pos.moves[alt]
                pos.indices[0] = pos.indices[alt]
                pos.leaf_distance = child.leaf_distance + 1
        new_best = -self.positions[pos.indices[0]].evals[0]
        if new_best < 0:
            pos.evals[0] = new_best + 1
        else:
            pos.evals[0] = new_best - 1
    
    def explore(self):
        try:
            while True:
                self.analyze()
                if (self.analysis_counter & 255) == 0:
                    self.save_data()
                
        except KeyboardInterrupt:
            print("\nStopped by user")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.save_data()
            print(f"Final save: {self.analysis_counter} positions analyzed")
            if hasattr(self, 'engine'):
                self.engine.quit()

def main():
    global VARIANT, ENGINE, THREADS, HASH, MULTIPV, DEPTH

    parser = argparse.ArgumentParser(description='Tree Explorer')

    parser.add_argument('--variant', help=f'Variant (default: {VARIANT})')
    parser.add_argument('--engine', help=f'Engine path (default: {ENGINE})')
    parser.add_argument('--threads', type=int, help=f'Threads (default: {THREADS})')
    parser.add_argument('--hash', type=int, help=f'Hash MB (default: {HASH})')
    parser.add_argument('--multipv', type=int, help=f'MultiPV (default: {MULTIPV})')
    parser.add_argument('--depth', type=int, help=f'Depth (default: {DEPTH})')

    args = parser.parse_args()
    
    if args.variant: VARIANT = args.variant
    if args.engine: ENGINE = args.engine
    if args.threads: THREADS = args.threads
    if args.hash: HASH = args.hash
    if args.multipv: MULTIPV = args.multipv
    if args.depth: DEPTH = args.depth

    tree = Tree()
    tree.explore()

if __name__ == '__main__':
    main()
