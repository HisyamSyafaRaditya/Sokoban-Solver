import time
from collections import deque
import heapq

INFINITY = 999999

DIRECTIONS = {
    'R': (0, 1),
    'L': (0, -1),
    'D': (1, 0),
    'U': (-1, 0)
}

WALL = '1'
GOAL = '2'
EMPTY = '0'


class SokobanSolver:
    def __init__(self, board, player_pos, boxes_pos):
        self.board = board
        self.init_player_pos = player_pos
        self.init_boxes_pos = list(boxes_pos)

        self.height = len(board)
        self.width = len(board[0])

        self.goals_pos = [
            (r, c)
            for r in range(self.height)
            for c in range(self.width)
            if board[r][c] == GOAL
        ]

        self.dead_space = self._generate_dead_space_matrix()
        self.distance_map = self._precompute_goal_distances()

        self.fringe = []
        self.visited = set()

        self.solution = None
        self.expanded_nodes_count = 0
        self.visited_nodes_count = 0
        self.time_used = 0

    # ====================================================================
    # Dead Space Detection
    # ====================================================================

    def _generate_dead_space_matrix(self):
        ds = [[False] * self.width for _ in range(self.height)]

        for r in range(self.height):
            for c in range(self.width):
                if self.board[r][c] == WALL:
                    ds[r][c] = True
                    continue

                if self.board[r][c] == GOAL:
                    continue

                if self._is_corner(r, c):
                    ds[r][c] = True

        return ds

    def _is_corner(self, r, c):
        if not self._valid_inner(r, c):
            return False

        return (
            (self.board[r-1][c] == WALL and self.board[r][c-1] == WALL) or
            (self.board[r-1][c] == WALL and self.board[r][c+1] == WALL) or
            (self.board[r+1][c] == WALL and self.board[r][c-1] == WALL) or
            (self.board[r+1][c] == WALL and self.board[r][c+1] == WALL)
        )

    def _valid_inner(self, r, c):
        return 0 < r < self.height - 1 and 0 < c < self.width - 1

    # ====================================================================
    # BFS Distance to Each Goal
    # ====================================================================

    def _precompute_goal_distances(self):
        distmap = {}

        for goal in self.goals_pos:
            distmap[goal] = self._bfs_from_goal(goal)

        return distmap

    def _bfs_from_goal(self, start):
        visited = [[False] * self.width for _ in range(self.height)]
        dist = [[INFINITY] * self.width for _ in range(self.height)]
        q = deque()

        q.append(start)
        dist[start[0]][start[1]] = 0

        while q:
            r, c = q.popleft()
            if visited[r][c]:
                continue

            visited[r][c] = True

            for dr, dc in DIRECTIONS.values():
                nr, nc = r + dr, c + dc

                if not self._in_bounds(nr, nc):
                    continue
                if self.board[nr][nc] == WALL:
                    continue

                if dist[nr][nc] > dist[r][c] + 1:
                    dist[nr][nc] = dist[r][c] + 1
                    q.append((nr, nc))

        return dist

    # ====================================================================
    # Heuristic
    # ====================================================================

    def _heuristic(self, boxes):
        total = 0
        for bx, by in boxes:
            best = min(self.distance_map[g][bx][by] for g in self.goals_pos)
            total += best
        return total

    # ====================================================================
    # Core Search
    # ====================================================================

    def _in_bounds(self, r, c):
        return 0 <= r < self.height and 0 <= c < self.width

    def _is_position_in_bounds(self, r, c):
        return self._in_bounds(r, c)

    def _is_goal_state(self, boxes):
        return all(self.board[r][c] == GOAL for r, c in boxes)

    def _valid_move(self, r, c):
        if not self._in_bounds(r, c):
            return False
        return self.board[r][c] != WALL

    def _can_push(self, box_pos, dr, dc, boxes):
        nr, nc = box_pos[0] + dr, box_pos[1] + dc

        if not self._in_bounds(nr, nc):
            return False
        if self.board[nr][nc] == WALL:
            return False
        if (nr, nc) in boxes:
            return False
        if self.dead_space[nr][nc]:
            return False

        return True

    # Node structure stored in fringe:
    # (f_value, g_cost, player_pos, boxes(tuple), path_str)

    def solve(self):
        t0 = time.time()

        start_boxes = tuple(sorted(self.init_boxes_pos))
        h = self._heuristic(start_boxes)

        self._push_fringe(0, self.init_player_pos, start_boxes, "", h)

        while self.fringe:
            f, g, player, boxes, path = heapq.heappop(self.fringe)
            self.visited_nodes_count += 1

            state = (player, boxes)
            if state in self.visited:
                continue

            self.visited.add(state)

            if self._is_goal_state(boxes):
                self.solution = path
                self.time_used = time.time() - t0
                return path

            self._expand_node(g, player, boxes, path)

        self.time_used = time.time() - t0
        return None

    def _push_fringe(self, g, player, boxes, path, h):
        f = g + h
        node = (f, g, player, boxes, path)

        self.expanded_nodes_count += 1

        heapq.heappush(self.fringe, node)

    def _expand_node(self, g, player, boxes, path):
        px, py = player
        boxes_list = list(boxes)

        for move, (dr, dc) in DIRECTIONS.items():
            nr, nc = px + dr, py + dc

            if not self._valid_move(nr, nc):
                continue

            new_player = (nr, nc)
            new_boxes = list(boxes_list)

            if (nr, nc) in boxes_list:
                if not self._can_push((nr, nc), dr, dc, boxes_list):
                    continue

                idx = new_boxes.index((nr, nc))
                new_boxes[idx] = (nr + dr, nc + dc)

            new_boxes = tuple(sorted(new_boxes))

            if (new_player, new_boxes) in self.visited:
                continue

            h = self._heuristic(new_boxes)
            self._push_fringe(g + 1, new_player, new_boxes, path + move, h)
