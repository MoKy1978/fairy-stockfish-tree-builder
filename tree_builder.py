#!/usr/bin/env python3
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict

ENGINE = 'stockfish'
VARIANT = 'chess'
DEPTH = 30
MULTIPV = 3
THREADS = 4
HASH = 8192
DIR = '.'
NNUE = None
TEMPOCP = 5

@dataclass
class Position:
    fen: str
    best_move: Optional[str] = None
    best_child_fen: Optional[str] = None
    eval_cp: Optional[int] = None
    mate_in: Optional[int] = None
    moves_to_children: List[str] = field(default_factory=list)
    children_fens: List[str] = field(default_factory=list)

class FairyStockfishEngine:
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
        if NNUE and Path(NNUE).exists():
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

    def get_fen(self, position_cmd: str = "position startpos") -> str:
        self.send(position_cmd)
        self.send("d")
        lines = self.receive("Sfen:")
        for line in lines:
            if line.startswith("Fen:"):
                return line.split("Fen:", 1)[1].strip()
    
    def multipv(self, fen: str) -> List[Tuple[str, Optional[int], Optional[int]]]:
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
                eval_cp = None
                mate_in = None
                if "score" in parts:
                    score_idx = parts.index("score")
                    if parts[score_idx + 1] == "cp":
                        eval_cp = int(parts[score_idx + 2])
                    elif parts[score_idx + 1] == "mate":
                        mate_in = int(parts[score_idx + 2])
                pv_data[multipv_num] = (move, eval_cp, mate_in)
            except (ValueError, IndexError):
                continue
        return [pv_data[i] for i in sorted(pv_data.keys())]
    
    def quit(self):
        if self.process.poll() is None:
            self.send("quit")
            self.process.terminate()
            self.process.wait()

class TreeBuilder:
    def __init__(self):
        self.engine = FairyStockfishEngine()
        self.positions: Dict[str, Position] = {}
        self.analyzed_count = 0
        self.root_fen = None
        self.work_dir = Path(DIR)
        self.log_path = self.work_dir / f"{VARIANT}_{DEPTH}.log"
        self.json_path = self.work_dir / f"{VARIANT}_{DEPTH}.json"
        self.log = open(self.log_path, 'a')
        self.load_data()

    def load_data(self):
        if self.json_path.exists():
            try:
                with open(self.json_path, 'r') as f:
                    data = json.load(f)
                    self.root_fen = data['root_fen']
                    self.analyzed_count = data['analyzed_count']
                    for fen, pos_dict in data['positions'].items():
                        pos_dict['fen'] = fen
                        self.positions[fen] = Position(**pos_dict)
            except:
                self.new_tree()
        else:
            self.new_tree()

    def new_tree(self):
        self.root_fen = self.engine.get_fen()
        self.positions[self.root_fen] = Position(fen=self.root_fen)

    def analyze(self):
        path = []
        moves = []
        current_fen = self.root_fen
        path.append(current_fen)
        pos = self.positions[current_fen]
        while pos.best_child_fen:
            moves.append(pos.best_move)
            current_fen = pos.best_child_fen
            path.append(current_fen)
            pos = self.positions[current_fen]
        leaf = current_fen
        analysis = self.engine.multipv(leaf)
        msg = f"\nAnalysis #{self.analyzed_count + 1}"
        msg += f"\ncp {pos.eval_cp}"
        msg += f"\npv {' '.join(moves)}"
        print(msg)
        self.log.write(msg + "\n")
        for i, (move, eval_cp, mate_in) in enumerate(analysis, 1):
            if mate_in is None:
                msg = f"alt{i} {move} cp {eval_cp}"
            else:
                msg = f"alt{i} {move} mate {mate_in}"
            print(msg)
            self.log.write(msg + "\n")
        self.log.flush()
        best_move, best_cp, best_mate = analysis[0]
        pos.best_move = best_move
        if best_mate is None:
            pos.eval_cp = best_cp
            pos.mate_in = None
        else:
            pos.eval_cp = None
            pos.mate_in = best_mate
        for move, eval_cp, mate_in in analysis:
            child_fen = self.engine.get_fen(f"position fen {leaf} moves {move}")
            pos.children_fens.append(child_fen)
            pos.moves_to_children.append(move)
            if child_fen not in self.positions:
                if mate_in is None:
                    child_cp = -eval_cp
                    child_mate = None
                else:
                    child_cp = None
                    if mate_in > 0:
                        child_mate = -mate_in + 1
                    else:
                        child_mate = -mate_in
                self.positions[child_fen] = Position(
                    fen=child_fen,
                    eval_cp=child_cp,
                    mate_in=child_mate
                )
        for fen in reversed(path):
            self.minimax(fen)

    def minimax(self, fen: str):
        pos = self.positions[fen]
        best_index = 0
        best_child_fen = pos.children_fens[0]
        best_child = self.positions[best_child_fen]
        pos.best_move = pos.moves_to_children[0]
        pos.best_child_fen = best_child_fen
        for child_idx, child_fen in enumerate(pos.children_fens[1:], 1):
            child = self.positions[child_fen]
            ce, be = child.eval_cp, best_child.eval_cp
            cm, bm = child.mate_in, best_child.mate_in
            better = (
                (cm is not None and bm is not None and ((cm * bm > 0 and cm > bm) or (cm <= 0 < bm))) or
                (cm is not None and bm is None and cm < 0) or
                (cm is None and bm is not None and bm > 0) or
                (cm is None and bm is None and ce < be)
            )
            if better:
                best_child = child
                pos.best_move = pos.moves_to_children[child_idx]
                pos.best_child_fen = child_fen
        
        if best_child.mate_in is None:
            if best_child.eval_cp is not None:
                if best_child.eval_cp > 0:
                    pos.eval_cp = -best_child.eval_cp + TEMPOCP
                elif best_child.eval_cp < 0:
                    pos.eval_cp = -best_child.eval_cp - TEMPOCP
                else:
                    pos.eval_cp = 0
            pos.mate_in = None
        else:
            if best_child.mate_in > 0:
                pos.mate_in = -best_child.mate_in
            else:
                pos.mate_in = -best_child.mate_in + 1
            pos.eval_cp = None

    def export(self):
        with open(self.json_path, 'w') as f:
            positions_dict = {
                fen: {k: v for k, v in asdict(pos).items() if k != 'fen'}
                for fen, pos in self.positions.items()
            }
            json.dump({
                'root_fen': self.root_fen,
                'analyzed_count': self.analyzed_count,
                'positions': positions_dict
            }, f, indent=2)

    def build(self):
        try:
            while True:
                self.analyze()
                self.analyzed_count += 1
                self.export()
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            self.export()
            if hasattr(self, 'log') and self.log:
                self.log.close()
            if hasattr(self, 'engine') and self.engine:
                self.engine.quit()

def main():
    global ENGINE, VARIANT, DEPTH, MULTIPV, THREADS, HASH, DIR, NNUE, TEMPOCP
    
    parser = argparse.ArgumentParser(description='Variants tree  bulider powered by Fairy-Stockfish engine')

    parser.add_argument('--engine', default='stockfish', help='Path to engine executable (default: stockfish)')
    parser.add_argument('--variant', default='chess', help='Variant (default: chess)')
    parser.add_argument('--nnue', default=None, help='Path to NNUE evaluation file')
    parser.add_argument('--depth', type=int, default=30, help='Search depth (default: 30)')
    parser.add_argument('--multipv', type=int, default=3, help='Number of alternatives (default: 3)')
    parser.add_argument('--threads', type=int, default=4, help='Number of threads (default: 4)')
    parser.add_argument('--hash', type=int, default=8192, help='Hash table size (default: 8192)')
    parser.add_argument('--dir', default='.', help='Working directory (default: current directory)')
    parser.add_argument('--tempocp', type=int, default=5, help='Tempo degradation (default: 5)')
    args = parser.parse_args()

    if Path(args.engine).exists():
        ENGINE = args.engine
    else:
        print(f"Error: Engine not found at {args.engine}")
        sys.exit(1)
    VARIANT = args.variant
    NNUE = args.nnue
    DEPTH = args.depth
    MULTIPV = args.multipv
    THREADS = args.threads
    HASH = args.hash
    DIR = args.dir
    TEMPOCP = args.tempocp

    builder = TreeBuilder()
    builder.build()

if __name__ == '__main__':
    main()
