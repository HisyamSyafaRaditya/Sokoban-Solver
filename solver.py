import time
from collections import deque

# Constants
INFINITY = 999999

# Direction mappings
DIRECTIONS = {
    'R': (0, 1),   # Right
    'L': (0, -1),  # Left
    'D': (1, 0),   # Down
    'U': (-1, 0)   # Up
}

# Board cell types
WALL = '1'
GOAL = '2'
EMPTY = '0'


class SokobanSolver:
    """
    Sokoban puzzle solver using A* search algorithm with dead space detection.
    """

    def __init__(self, board: list[str], player_pos: tuple, boxes_pos: list[tuple]):
        # Initialize the Sokoban solver.
        self.board = board
        self.init_player_pos = player_pos
        self.init_boxes_pos = boxes_pos
        
        # Extract goal positions from board
        self.goals_pos = [
            (row, col) 
            for row in range(len(board))
            for col in range(len(board[row])) 
            if board[row][col] == GOAL
        ]
        
        # Board dimensions
        self.width = len(board[0]) if board else 0
        self.height = len(board)

        # Precompute dead spaces and distance maps
        self.dead_space = self._generate_dead_space_matrix()
        self.minimum_distance_map = self._precompute_distance_maps()

        # Search state
        self.visited_states = {}
        self.fringe = []
        
        # Solution and statistics
        self.solution = None
        self.expanded_nodes_count = 0
        self.visited_nodes_count = 0
        self.time_used = 0

    # ========================================================================
    # Dead Space Detection Methods
    # ========================================================================

    def _is_corner(self, row: int, col: int) -> bool:
        # Check if a position is a corner (two adjacent walls).
        corners = [
            (self.board[row - 1][col] == WALL and self.board[row][col - 1] == WALL),  # Top-left
            (self.board[row - 1][col] == WALL and self.board[row][col + 1] == WALL),  # Top-right
            (self.board[row + 1][col] == WALL and self.board[row][col - 1] == WALL),  # Bottom-left
            (self.board[row + 1][col] == WALL and self.board[row][col + 1] == WALL)   # Bottom-right
        ]
        return any(corners)

    def _generate_dead_space_matrix(self) -> list[list[bool]]:
        # Generate a matrix marking dead spaces where boxes cannot be pushed to goals.
        dead_space = [[False for _ in range(self.width)] for _ in range(self.height)]

        # Mark walls and corners as dead spaces
        self._mark_walls_and_corners(dead_space)
        
        # Mark horizontal and vertical dead zones
        self._mark_dead_zones(dead_space)

        return dead_space

    def _mark_walls_and_corners(self, dead_space: list[list[bool]]) -> None:
        # Mark walls and corners as dead spaces.
        for row in range(self.height):
            for col in range(self.width):
                if dead_space[row][col]:
                    continue
                    
                if self.board[row][col] == WALL:
                    dead_space[row][col] = True
                elif self.board[row][col] == GOAL:
                    dead_space[row][col] = False
                elif self._is_valid_position(row, col) and self._is_corner(row, col):
                    dead_space[row][col] = True

    def _mark_dead_zones(self, dead_space: list[list[bool]]) -> None:
        # Mark horizontal and vertical dead zones between corners.
        for row in range(self.height):
            for col in range(self.width):
                if not self._should_check_dead_zone(row, col, dead_space):
                    continue

                # Check horizontal dead zones
                if self.board[row - 1][col] == WALL or self.board[row + 1][col] == WALL:
                    self._mark_horizontal_dead_zone(row, col, dead_space)

                # Check vertical dead zones
                if self.board[row][col - 1] == WALL or self.board[row][col + 1] == WALL:
                    self._mark_vertical_dead_zone(row, col, dead_space)

    def _should_check_dead_zone(self, row: int, col: int, dead_space: list[list[bool]]) -> bool:
        # Check if a position should be evaluated for dead zones.
        if self.board[row][col] == WALL or self.board[row][col] == GOAL:
            return False
        if dead_space[row][col]:
            return False
        return self._is_valid_position(row, col)

    def _mark_horizontal_dead_zone(self, row: int, col: int, dead_space: list[list[bool]]) -> None:
        # Mark horizontal dead zone if conditions are met.
        # left 
        left_col = col
        while (left_col > 0 and 
               self.board[row][left_col - 1] != WALL and
               (self.board[row - 1][left_col] == WALL or self.board[row + 1][left_col] == WALL) and
               self.board[row][left_col] != GOAL):
            left_col -= 1

        if not self._is_corner(row, left_col) or not dead_space[row][left_col]:
            return

        # right 
        right_col = col
        while (right_col < self.width - 1 and 
               self.board[row][right_col + 1] != WALL and
               (self.board[row - 1][right_col] == WALL or self.board[row + 1][right_col] == WALL) and
               self.board[row][right_col] != GOAL):
            right_col += 1

        if not self._is_corner(row, right_col) or not dead_space[row][right_col]:
            return

        # Mark entire horizontal zone as dead
        for current_col in range(left_col, right_col + 1):
            dead_space[row][current_col] = True

    def _mark_vertical_dead_zone(self, row: int, col: int, dead_space: list[list[bool]]) -> None:
        # Mark vertical dead zone if conditions are met.
        # top 
        top_row = row
        while (top_row > 0 and 
               self.board[top_row - 1][col] != WALL and
               (self.board[top_row][col - 1] == WALL or self.board[top_row][col + 1] == WALL) and
               self.board[top_row][col] != GOAL):
            top_row -= 1

        if not self._is_corner(top_row, col) or not dead_space[top_row][col]:
            return

        # bottom 
        bottom_row = row
        while (bottom_row < self.height - 1 and 
               self.board[bottom_row + 1][col] != WALL and
               (self.board[bottom_row][col - 1] == WALL or self.board[bottom_row][col + 1] == WALL) and
               self.board[bottom_row][col] != GOAL):
            bottom_row += 1

        if not self._is_corner(bottom_row, col) or not dead_space[bottom_row][col]:
            return

        # Mark entire vertical zone as dead
        for current_row in range(top_row, bottom_row + 1):
            dead_space[current_row][col] = True

    def _is_valid_position(self, row: int, col: int) -> bool:
        # Check if position is within valid bounds (not on edges).
        return 0 < row < self.height - 1 and 0 < col < self.width - 1

    # ========================================================================
    # Heuristic and Distance Calculation Methods
    # ========================================================================
    
    def _precompute_distance_maps(self) -> dict:
        # Precompute minimum distances from each goal to all positions.
        distance_map = {}
        for goal_pos in self.goals_pos:
            distance_map[goal_pos] = self._compute_minimum_distances(goal_pos)
        return distance_map

    def _compute_minimum_distances(self, start_pos: tuple[int, int]) -> list[list[int]]:
        # Compute minimum distances from start position to all reachable positions using BFS.
        visited = [[False] * self.width for _ in range(self.height)]
        distances = [[INFINITY] * self.width for _ in range(self.height)]
        distances[start_pos[0]][start_pos[1]] = 0
        
        queue = deque([(start_pos, 0)])
        
        while queue:
            position, distance = queue.popleft()
            row, col = position
            
            if visited[row][col]:
                continue
                
            visited[row][col] = True
            distances[row][col] = distance
            
            # Explore all four directions
            for delta_row, delta_col in DIRECTIONS.values():
                new_row = row + delta_row
                new_col = col + delta_col
                
                if self._is_position_in_bounds(new_row, new_col):
                    if self.board[new_row][new_col] != WALL:
                        queue.append(((new_row, new_col), distance + 1))
                        
        return distances

    def _is_position_in_bounds(self, row: int, col: int) -> bool:
        # Check if position is within board bounds.
        return 0 <= row < self.height and 0 <= col < self.width

    def _calculate_heuristic(self, state: tuple[tuple[int, int], list[tuple[int, int]]]) -> int:
        # Calculate heuristic value for a state (sum of minimum distances from boxes to goals).
        _, boxes = state
        total_distance = 0
        
        for box in boxes:
            min_distance = min(
                self.minimum_distance_map[goal][box[0]][box[1]]
                for goal in self.goals_pos
            )
            total_distance += min_distance
            
        return total_distance

    # ========================================================================
    # Search Algorithm
    # ========================================================================

    def _is_goal_state(self, state: tuple[tuple[int, int], list[tuple[int, int]]]) -> bool:
        # Check if all boxes are on goal positions.
        _, boxes = state
        return all(self.board[box[0]][box[1]] == GOAL for box in boxes)

    def _insert_into_fringe(self, node: tuple) -> None:
        # Insert a node into the fringe (priority queue) sorted by f-value.
        player_pos, boxes_pos, g_cost, h_cost, path = node
        state = (player_pos, tuple(sorted(boxes_pos)))
        
        # Skip if already visited
        if state in self.visited_states:
            return
        
        self.expanded_nodes_count += 1
        f_value = g_cost + h_cost
        
        # Insert in sorted order by f-value
        for index in range(len(self.fringe)):
            fringe_f_value = self.fringe[index][2] + self.fringe[index][3]
            if fringe_f_value > f_value:
                self.fringe.insert(index, (player_pos, state[1], g_cost, h_cost, path))
                return
                
        self.fringe.append((player_pos, state[1], g_cost, h_cost, path))

    def solve(self) -> str:
        # Solve the Sokoban puzzle using A* search.
        start_time = time.time()
        
        # Initialize with starting state
        initial_state = (self.init_player_pos, self.init_boxes_pos)
        initial_heuristic = self._calculate_heuristic(initial_state)
        self._insert_into_fringe((self.init_player_pos, self.init_boxes_pos, 0, initial_heuristic, ''))

        while self.fringe:
            # Get node with lowest f-value
            node = self.fringe.pop(0)
            player_pos, boxes_pos, g_cost, h_cost, path = node
            state = (player_pos, boxes_pos)
            
            self.visited_nodes_count += 1
            
            # Check if goal state
            if self._is_goal_state(state):
                self.solution = path
                self.time_used = time.time() - start_time
                return path

            # Skip if already visited
            if state in self.visited_states:
                continue
            self.visited_states[state] = True

            # Explore all possible moves
            self._explore_moves(node)

        # No solution found
        self.solution = None
        self.time_used = time.time() - start_time
        return None

    def _explore_moves(self, node: tuple) -> None:
        # Explore all possible moves from current node.
        player_pos, boxes_pos, g_cost, h_cost, path = node
        
        for direction, (delta_row, delta_col) in DIRECTIONS.items():
            new_player_pos = (player_pos[0] + delta_row, player_pos[1] + delta_col)
            
            # Check if move is valid
            if not self._is_move_valid(new_player_pos):
                continue
            
            # Handle box pushing
            new_boxes_pos = list(boxes_pos)
            if new_player_pos in new_boxes_pos:
                if not self._try_push_box(new_player_pos, delta_row, delta_col, new_boxes_pos):
                    continue
            
            # Create new state and add to fringe
            new_state = (new_player_pos, new_boxes_pos)
            new_heuristic = self._calculate_heuristic(new_state)
            new_node = (new_player_pos, new_boxes_pos, g_cost + 1, new_heuristic, path + direction)
            self._insert_into_fringe(new_node)

    def _is_move_valid(self, position: tuple[int, int]) -> bool:
        # Check if a move to the given position is valid.
        row, col = position
        
        if not self._is_position_in_bounds(row, col):
            return False
        if self.board[row][col] == WALL:
            return False
            
        return True

    def _try_push_box(self, box_pos: tuple[int, int], delta_row: int, delta_col: int, 
                      boxes_list: list[tuple[int, int]]) -> bool:
        # Try to push a box in the given direction.
        new_box_pos = (box_pos[0] + delta_row, box_pos[1] + delta_col)
        
        # Check if new box position is valid
        if not self._is_position_in_bounds(new_box_pos[0], new_box_pos[1]):
            return False
        if self.board[new_box_pos[0]][new_box_pos[1]] == WALL:
            return False
        if new_box_pos in boxes_list:
            return False
        if self.dead_space[new_box_pos[0]][new_box_pos[1]]:
            return False
        
        # Update box position
        boxes_list[boxes_list.index(box_pos)] = new_box_pos
        return True
