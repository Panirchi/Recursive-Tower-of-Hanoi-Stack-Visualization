import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass

TOWER_W, TOWER_H = 600, 460
STACK_W, STACK_H = 340, 460
PEG_X = {"A": 100, "B": 300, "C": 500}
BASE_Y = 380
PEG_TOP = 110
LIFT_Y = PEG_TOP - 28
DISK_H = 24
FRAME_MS = 16
MAX_DISKS = 7

BG, PANEL, ACTIVE = "#1e1e2e", "#2a2a3c", "#3b3b55"
FG, MUTED, GREEN = "#cdd6f4", "#8086a0", "#a6e3a1"
DISK_COLORS = ["#f38ba8", "#fab387", "#f9e2af", "#a6e3a1",
               "#89dceb", "#89b4fa", "#cba6f7"]
ROLE = {"src": ("source", "#fab387"),
        "dst": ("target", "#a6e3a1"),
        "aux": ("spare", "#89b4fa")}

MONO = ("Courier", 10, "bold")
SMALL = ("Helvetica", 9)

@dataclass
class Frame:
    n: int
    src: str
    dst: str
    aux: str
    phase: str = ""
    returning: bool = False

    @property
    def label(self):
        return f"hanoi(n={self.n}, src={self.src}, dst={self.dst}, aux={self.aux})"


def hanoi(n, src, dst, aux, stack):
    frame = Frame(n, src, dst, aux)
    # PUSH
    stack.append(frame)
    yield ("call", frame)

    if n == 1:
        frame.phase = f"base case: move disk 1  {src}→{dst}"
        yield ("move", 1, src, dst)
    else:
        frame.phase = f"1) move {n - 1} disk(s) {src}→{aux}  (recurse)"
        yield from hanoi(n - 1, src, aux, dst, stack)

        frame.phase = f"2) move disk {n}  {src}→{dst}"
        yield ("move", n, src, dst)

        frame.phase = f"3) move {n - 1} disk(s) {aux}→{dst}  (recurse)"
        yield from hanoi(n - 1, aux, dst, src, stack)

    frame.phase = "done, returning to caller"
    frame.returning = True
    yield ("return", frame)
    # POP
    stack.pop()

class HanoiApp:
    def __init__(self, root):
        self.root = root
        root.title("Tower of Hanoi: recursion & call stack")
        root.configure(bg=BG)
        root.resizable(False, False)

        top = tk.Frame(root, bg=BG)
        top.pack(padx=10, pady=(10, 4))
        self.tower_canvas = tk.Canvas(top, width=TOWER_W, height=TOWER_H,
                                      bg=BG, highlightthickness=0)
        self.tower_canvas.pack(side="left")
        self.stack_canvas = tk.Canvas(top, width=STACK_W, height=STACK_H,
                                      bg=BG, highlightthickness=1,
                                      highlightbackground=PANEL)
        self.stack_canvas.pack(side="left", padx=(10, 0))

        self.status = tk.StringVar()
        tk.Label(root, textvariable=self.status, bg=BG, fg=FG,
                 font=("Helvetica", 11), anchor="w", width=110
                 ).pack(padx=12, pady=2)

        bar = ttk.Frame(root)
        bar.pack(fill="x", padx=10, pady=(4, 10))

        ttk.Label(bar, text="Disks:").pack(side="left")
        self.n_var = tk.StringVar(value="3")
        ttk.Spinbox(bar, from_=1, to=MAX_DISKS, width=3, state="readonly",
                    textvariable=self.n_var, command=self.reset
                    ).pack(side="left", padx=(4, 14))

        ttk.Label(bar, text="Speed:").pack(side="left")
        self.speed_var = tk.DoubleVar(value=4)
        ttk.Scale(bar, from_=1, to=10, length=150, variable=self.speed_var
                  ).pack(side="left", padx=(4, 14))

        self.start_btn = ttk.Button(bar, text="▶ Start", command=self.toggle)
        self.start_btn.pack(side="left", padx=2)
        ttk.Button(bar, text="Step", command=self.step).pack(side="left", padx=2)
        ttk.Button(bar, text="Reset", command=self.reset).pack(side="left", padx=2)

        self.epoch = 0
        self.after_id = None
        self.reset()

    @property
    def n(self):
        return int(self.n_var.get())

    def speed(self):
        return float(self.speed_var.get())

    def seg_steps(self):
        return max(2, round(22 / self.speed()))

    def event_delay(self):
        return int(700 / self.speed())

    @staticmethod
    def disk_y(level):
        return BASE_Y - DISK_H * level - DISK_H / 2

    def cancel_pending(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def reset(self):
        self.cancel_pending()
        self.epoch += 1
        n = self.n
        self.pegs = {"A": list(range(n, 0, -1)), "B": [], "C": []}
        self.stack = []
        self.gen = hanoi(n, "A", "C", "B", self.stack)
        self.moving = None
        self.moves = 0
        self.max_depth = 0
        self.running = False
        self.busy = False
        self.finished = False
        self.start_btn.config(text="▶ Start")
        self.status.set(f"Goal: move all {n} disks from A to C. "
                        f"Press Start (or Step to go one event at a time).")
        self.draw_all()

    def toggle(self):
        if self.finished:
            self.reset()
        self.running = not self.running
        self.start_btn.config(text="⏸ Pause" if self.running else "▶ Start")
        if self.running:
            if not self.busy:
                self.advance()
        else:
            self.cancel_pending()

    def step(self):
        if not (self.running or self.busy or self.finished):
            self.advance()

    def advance(self):
        self.after_id = None
        if self.busy or self.finished:
            return
        try:
            ev = next(self.gen)
        except StopIteration:
            self.finish()
            return

        kind = ev[0]
        if kind == "call":
            f = ev[1]
            self.max_depth = max(self.max_depth, len(self.stack))
            self.status.set(f"CALL    {f.label}   → pushed, stack depth = {len(self.stack)}")
        elif kind == "return":
            f = ev[1]
            self.status.set(f"RETURN  {f.label}   → finished, popped off the stack")
        else:
            _, disk, s, t = ev
            self.moves += 1
            self.status.set(f"MOVE #{self.moves}: disk {disk} from {s} → {t}")

        self.draw_stack()
        if kind == "move":
            self.busy = True
            self.animate_move(disk, s, t)
        else:
            self.draw_towers()
            self.after_event()

    def after_event(self):
        self.busy = False
        self.draw_all()
        if self.running:
            self.after_id = self.root.after(self.event_delay(), self.advance)

    def finish(self):
        self.finished = True
        self.running = False
        self.busy = False
        self.start_btn.config(text="↻ Replay")
        self.status.set(f"Solved in {self.moves} moves (2^{self.n} − 1 = {2 ** self.n - 1}). "
                        f"Deepest the call stack got: {self.max_depth} frames.")
        self.draw_all()

    def animate_move(self, disk, src, dst):
        epoch = self.epoch
        self.pegs[src].pop()
        x0, y0 = PEG_X[src], self.disk_y(len(self.pegs[src]))
        x1, y1 = PEG_X[dst], self.disk_y(len(self.pegs[dst]))
        k = self.seg_steps()

        path = [(x0, y0 + (LIFT_Y - y0) * i / k) for i in range(1, k + 1)]
        path += [(x0 + (x1 - x0) * i / k, LIFT_Y) for i in range(1, k + 1)]
        path += [(x1, LIFT_Y + (y1 - LIFT_Y) * i / k) for i in range(1, k + 1)]

        def tick(i=0):
            if epoch != self.epoch:
                return
            if i < len(path):
                self.moving = (disk, *path[i])
                self.draw_towers()
                self.root.after(FRAME_MS, tick, i + 1)
            else:
                self.moving = None
                self.pegs[dst].append(disk)
                self.after_event()

        tick()

    def draw_all(self):
        self.draw_towers()
        self.draw_stack()

    def draw_disk(self, size, x, y):
        c = self.tower_canvas
        w = 30 + 18 * size
        c.create_rectangle(x - w / 2, y - DISK_H / 2 + 1, x + w / 2, y + DISK_H / 2 - 1,
                           fill=DISK_COLORS[size - 1], outline="#11111b", width=2)
        c.create_text(x, y, text=str(size), fill="#11111b",
                      font=("Helvetica", 11, "bold"))

    def draw_towers(self):
        c = self.tower_canvas
        c.delete("all")

        c.create_text(14, 14, anchor="w", fill=FG, font=("Helvetica", 11),
                      text=f"moves: {self.moves} / {2 ** self.n - 1}      "
                           f"stack depth: {len(self.stack)}")
        
        c.create_rectangle(20, BASE_Y, TOWER_W - 20, BASE_Y + 14, fill="#45475a", outline="")
        for x in PEG_X.values():
            c.create_rectangle(x - 5, PEG_TOP, x + 5, BASE_Y, fill="#6c7086", outline="")


        roles = {}
        if self.stack:
            top = self.stack[-1]
            roles = {top.src: "src", top.dst: "dst", top.aux: "aux"}
        for name, x in PEG_X.items():
            c.create_text(x, BASE_Y + 32, text=name, fill=FG, font=("Helvetica", 14, "bold"))
            if name in roles:
                text, col = ROLE[roles[name]]
                c.create_text(x, BASE_Y + 54, text=text, fill=col, font=("Helvetica", 10, "bold"))


        for name, disks in self.pegs.items():
            for level, size in enumerate(disks):
                self.draw_disk(size, PEG_X[name], self.disk_y(level))
        if self.moving:
            self.draw_disk(*self.moving)

    def draw_stack(self):
        c = self.stack_canvas
        c.delete("all")
        c.create_text(STACK_W / 2, 20, text="CALL STACK",
                      fill=FG, font=("Helvetica", 11, "bold"))
        c.create_line(16, STACK_H - 14, STACK_W - 16, STACK_H - 14, fill=MUTED, width=2)

        if not self.stack:
            c.create_text(STACK_W / 2, STACK_H / 2, text="(empty)", fill=MUTED,
                          font=("Helvetica", 12, "italic"))
            return

        box_h, gap = 50, 6
        for i, f in enumerate(self.stack):
            y1 = STACK_H - 22 - i * (box_h + gap)
            y0 = y1 - box_h
            is_top = i == len(self.stack) - 1
            color = DISK_COLORS[f.n - 1]

            c.create_rectangle(16, y0, STACK_W - 16, y1,
                               fill=ACTIVE if is_top else PANEL,
                               outline=color, width=3 if is_top else 1)
            c.create_rectangle(16, y0, 24, y1, fill=color, outline="")
            c.create_text(34, y0 + 16, anchor="w", text=f.label, fill=FG, font=MONO)
            c.create_text(34, y1 - 14, anchor="w", text=f.phase, font=SMALL,
                          fill=GREEN if f.returning else (FG if is_top else MUTED))
            if is_top:
                c.create_text(STACK_W - 22, y0 + 16, anchor="e", text="TOP",
                              fill=color, font=("Helvetica", 9, "bold"))


if __name__ == "__main__":
    root = tk.Tk()
    HanoiApp(root)
    root.mainloop()
