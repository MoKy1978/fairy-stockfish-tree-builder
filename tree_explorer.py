#!/usr/bin/env python3
import platform
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Optional

VARIANT = 'chess'
ENGINE = 'stockfish.exe' if platform.system() == 'Windows' else 'stockfish'
THREADS = 4
HASH = 8192
MULTIPV = 6
DEPTH = 24

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
    
    def quit(self):
        if self.process.poll() is None:
            self.send("quit")
            self.process.terminate()
            self.process.wait()

class Tree:
    def __init__(self):
        Path(VARIANT).mkdir(exist_ok=True)
        self.engine = Engine()
        self.fen = []
        self.move = []
        self.score = []
        self.best = []
        self.children = []
        self.length = []
        self.fen_to_index = {}
        self.last_saved = time.time()
        self.data_path = Path(f"{VARIANT}/{VARIANT}_{DEPTH}.txt")
        self.load_data()
        
    def load_data(self):
        if not self.data_path.exists():
            root_fen = self.engine.get_fen()
            self.fen.append(root_fen)
            self.move.append(None)
            self.score.append(0)
            self.best.append(None)
            self.children.append([])
            self.length.append(0)
            self.fen_to_index[root_fen] = 0
            return
            
        with open(self.data_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('%'):
                    continue
                parts = line.rstrip(';').split(';')
                if len(parts) < 2:
                    continue
                header = parts[0].strip().split('|')
                idx = int(header[0])
                move = header[1] if header[1] != 'None' else None
                score_val = int(header[2])
                best_idx = int(header[3]) if header[3] != 'None' else None
                length_val = int(header[4])
                fen_str = parts[1].strip()
                children_list = []
                if len(parts) > 2 and parts[2].strip():
                    children_list = [int(x) for x in parts[2].strip().split(',')]
                self.fen.append(fen_str)
                self.move.append(move)
                self.score.append(score_val)
                self.best.append(best_idx)
                self.children.append(children_list)
                self.length.append(length_val)
                self.fen_to_index[fen_str] = idx

    def save_data(self):
        lines = []
        lines.append("% idx|move|score|best|length; fen; children;")
        for idx in range(len(self.fen)):
            move = self.move[idx] if self.move[idx] else 'None'
            header = f"{idx}|{move}|{self.score[idx]}|{self.best[idx]}|{self.length[idx]}"
            children_str = ','.join(map(str, self.children[idx])) if self.children[idx] else ''
            lines.append(f"{header}; {self.fen[idx]}; {children_str};")
        with open(self.data_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        self.last_saved = time.time()
        print(f"Saved {len(self.fen)} positions")

    def analyze(self):
        leaf = 0
        path = [0]
        variation = []
        while self.best[leaf] is not None:
            leaf = self.best[leaf]
            path.append(leaf)
            variation.append(self.move[leaf])
        print(*variation)
        self.engine.send(f"position fen {self.fen[leaf]}")
        self.engine.send(f"go depth {DEPTH}")
        lines = self.engine.receive("bestmove")
        for line in reversed(lines):
            if not line.startswith("info") or "multipv" not in line:
                continue
            parts = line.split()
            if int(parts[parts.index("depth") + 1]) != DEPTH:
                continue
            alt = int(parts[parts.index("multipv") + 1])
            move = parts[parts.index("pv") + 1]
            score = int(parts[parts.index("score") + 2])
            if parts[parts.index("score") + 1] == "mate":
                if score > 0:
                    score = 30001 - 2 * score
                else:
                    score = -30000 - 2 * score
            child_fen = self.engine.get_fen(f"position fen {self.fen[leaf]} moves {move}")
            if child_fen in self.fen_to_index:
                child_idx = self.fen_to_index[child_fen]
            else:
                child_idx = len(self.fen)
                self.fen_to_index[child_fen] = child_idx
                self.fen.append(child_fen)
                self.move.append(move)
                self.score.append(-score)
                self.best.append(None)
                self.children.append([])
                self.length.append(0)
            self.children[leaf].append(child_idx)
            if alt == 1:
                break
        for idx in reversed(path):
            champion = -30000
            for alt in self.children[idx]:
                score = self.score[alt]
                length = self.length[alt]
                challenger = -score + length * abs(score + 1).bit_length() * (1 if score < 0 else -1)
                if challenger > champion:
                    champion = challenger
                    self.best[idx] = alt
                    self.length[idx] = length + 1
                    if score < 0:
                        self.score[idx] = -score - 1
                    else:
                        self.score[idx] = -score + 1
        print(self.score[leaf])
        print()

    def explore(self):
        try:
            while True:
                self.analyze()
                if time.time() - self.last_saved > 300:
                    self.save_data()
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.save_data()
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
