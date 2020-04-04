import curses
import time
import random
from collections import defaultdict
from itertools import tee

CONNECTED = {"N": 1, "S": 2, "E": 4, "W": 8}
DIRECTIONS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
ANTIPODES = {"N": "S", "S": "N", "W": "E", "E": "W"}
WALL = {12: '═', 3: '║', 10: '╗', 5: '╚', 9: '╝', 6: '╔', 7: '╠', 11: '╣',
        14: '╦', 13: '╩', 15: '╬', 0: " ", 4: "═", 8: "═", 1: "║", 2: "║"}
VISITED = 16

class Maze:
    def __init__(self, height, width, start=(0, 0)):
        self.height = height
        self.width = width
        self.stack = []
        self.cells = {(y, x): 0 for y in range(height) for x in range(width)}
        self.build(start)
    def eligible_neighbours(self, y, x):
        return [((y + i, x + j), d) for d, (i, j) in DIRECTIONS.items()
                if (y + i, x + j) in self.cells.keys()
                    and not self.cells[(y + i, x + j)] & VISITED]
    def connected_cells(self, y, x):
        cell_directions = [d for (d, v) in CONNECTED.items()
                           if v & self.cells[(y, x)]]
        return {(y + i, x + j): d for d, (i, j) in DIRECTIONS.items()
                if d in cell_directions}
    def build(self, start):
        current_cell = start
        while [c for c in self.cells.values() if not c & VISITED]:
            self.cells[current_cell] |= VISITED
            eligible_neighbours = self.eligible_neighbours(*current_cell)
            if not eligible_neighbours:
                next_cell = self.stack.pop()
            else:
                self.stack.append(current_cell)
                next_cell, direction = random.choice(eligible_neighbours)
                self.cells[current_cell] |= CONNECTED[direction]
                self.cells[next_cell] |= CONNECTED[ANTIPODES[direction]]
            current_cell = next_cell
    def track(self, start=(0, 0)):
        yield start
        current_cell = start
        self.stack = []
        for coord in self.cells.keys():
            self.cells[coord] &= ~VISITED
        while [c for c in self.cells.values() if not c & VISITED]:
            self.cells[current_cell] |= VISITED
            eligible_neighbours = [(c, d) for (c, d) in self.connected_cells(*current_cell).items()
                                   if not self.cells[c] & VISITED]
            if not eligible_neighbours:
                next_cell = self.stack.pop()
            else:
                self.stack.append(current_cell)
                next_cell, direction = random.choice(eligible_neighbours)
            yield next_cell
            current_cell = next_cell
    def __repr__(self):
        buffer = [[0 for _ in range(2 * self.width + 1)]
                  for _ in range(2 * self.height + 1)]
        for row in range(self.height):
            for col in range(self.width):
                if row:
                    buffer[2 * row][2 * col + 1] = (~self.cells[row, col]
                                                    & CONNECTED["N"]) << 3
                if col:
                    buffer[2 * row + 1][2 * col] = (~self.cells[row, col]
                                                    & CONNECTED["W"]) >> 3
                if row and col:
                    buffer[2 * row][2 * col] = (buffer[2 * row][2 * col - 1] | (buffer[2 * row][2 * col + 1] >> 1)
                                                    | buffer[2 * row - 1][2 * col] | (buffer[2 * row + 1][2 * col] << 1))
        for row in range(1, 2 * self.height):
            buffer[row][0] = CONNECTED["N"] | CONNECTED["S"] | (buffer[row][1] >> 1)
            buffer[row][2 * self.width] = (CONNECTED["N"] | CONNECTED["S"]
                                           | buffer[row][2 * self.width - 1])
        for col in range(1, 2 * self.width):
            buffer[0][col] = (CONNECTED["E"] | CONNECTED["W"]
                              | (buffer[1][col] << 1))
            buffer[2 * self.height][col] = (CONNECTED["E"] | CONNECTED["W"]
                                            | buffer[2 * self.height - 1][col])
        buffer[0][0] = CONNECTED["S"] | CONNECTED["E"]
        buffer[0][2 * self.width] = CONNECTED["S"] | CONNECTED["W"]
        buffer[2 * self.height][0] = CONNECTED["N"] | CONNECTED["E"]
        buffer[2 * self.height][2 * self.width] = CONNECTED["N"] | CONNECTED["W"]
        return "\n".join(["".join(WALL[cell] for cell in row) for row in buffer])

def path(maze, start, finish):
    heuristic = lambda node: abs(node[0] - finish[0]) + abs(node[1] - finish[1])
    nodes_to_explore = [start]
    explored_nodes = set()
    parent = {}
    global_score = defaultdict(lambda: float("inf"))
    global_score[start] = 0
    local_score = defaultdict(lambda: float("inf"))
    local_score[start] = heuristic(start)
    def retrace_path(current):
        total_path = [current]
        while current in parent.keys():
            current = parent[current]
            total_path.append(current)
        return reversed(total_path)
    while nodes_to_explore:
        nodes_to_explore.sort(key=lambda n: local_score[n])
        current = nodes_to_explore.pop()
        if current == finish:
            return retrace_path(current)
        explored_nodes.add(current)
        for neighbour in maze.connected_cells(*current).keys():
            tentative_global_score = global_score[current] + 1
            if tentative_global_score < global_score[neighbour]:
                parent[neighbour] = current
                global_score[neighbour] = tentative_global_score
                local_score[neighbour] = global_score[neighbour] + heuristic(neighbour)
                if neighbour not in explored_nodes:
                    nodes_to_explore.append(neighbour)

def draw_path(path, screen, delay=0, head=None, trail=None, skip_first=True):
    if not head:
        head=("█", curses.color_pair(1))
    if not trail:
        trail=("█", curses.color_pair(1))
    current_cell = next(path)
    old_cell = current_cell
    for idx, next_cell in enumerate(path):
        first = (not idx) and skip_first
        if screen.getch() == ord("q"):
            break
        screen.refresh()
        for last, cell in enumerate([(current_cell[0] + t * (next_cell[0] - current_cell[0]),
                            current_cell[1] + t * (next_cell[1] - current_cell[1])) for t in [0, 1/2]]):
            time.sleep(delay)
            if not first:
                screen.addstr(*coords(cell), *head)
            if last:
                if not first:
                    screen.addstr(*coords(current_cell), *trail)
                old_cell = cell
            elif not first:
                screen.addstr(*coords(old_cell), *trail)
            screen.refresh()
        current_cell = next_cell

def coords(node):
    return (int(2 * node[0]) + 1, int(2 * node[1]) + 1)

def construction_demo(maze, screen):
    head = ("*", curses.color_pair(2))
    trail = (".", curses.color_pair(1))
    draw_path(maze.track(), screen, delay=.1, head=head, trail=trail, skip_first=False)
    screen.nodelay(False)
    screen.getch()

def pathfinding_demo(maze, screen):
    start = []
    finish = []
    solution = None
    old_solution = None
    def reset(start_or_finish, cell, colour):
        nonlocal solution, old_solution
        if start_or_finish:
            screen.addstr(*coords(start_or_finish.pop()), " ")
        screen.addstr(*coords(cell), "█", colour)
        screen.refresh()
        if old_solution:
            draw_path(old_solution, screen, head=" ", trail=" ")
        start_or_finish.append(cell)
        if start and finish:
            solution, old_solution = tee(path(maze, start[0], finish[0]))
            draw_path(solution, screen)
    while True:
        key = screen.getch()
        if key == ord("q"):
            break
        elif key == curses.KEY_MOUSE:
            _, x, y, _, state = curses.getmouse()
            cell = (int(y / 2), int(x / 2))
            if state & curses.BUTTON3_PRESSED:
                reset(finish, cell, curses.color_pair(2))
            elif state & curses.BUTTON1_PRESSED:
                reset(start, cell, curses.color_pair(3))


def main(screen):
    curses.curs_set(False)
    curses.mousemask(curses.ALL_MOUSE_EVENTS)
    screen.nodelay(True)
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
    screen.clear()
    height, width = screen.getmaxyx()
    height, width = int((height - 2)/2), int((width - 2)/2)
    maze = Maze(height, width)
    screen.addstr(0, 0, str(maze))
    screen.refresh()
    # construction_demo(maze, screen)
    pathfinding_demo(maze, screen)


if __name__ == '__main__':
    curses.wrapper(main)
