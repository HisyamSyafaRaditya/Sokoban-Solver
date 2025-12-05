import time
import pygame
import os
from collections import deque

# Color constants
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
GREEN = (0, 128, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

# Game constants
TILE_SIZE = 50
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

# ============================================================================
# Dead Space Detection Methods
# ============================================================================

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

# ============================================================================
# Heuristic and Distance Calculation Methods
# ============================================================================
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

    # ========================================================================
    # Visualization Methods
    # ========================================================================

    def _load_assets(self, tile_size: int) -> dict:
        # Load game assets (images) from the images directory.
        assets = {}
        base_dir = os.path.join(os.path.dirname(__file__), 'images')
        
        def load_image(filename: str, size: tuple = None) -> pygame.Surface:
            # Load and scale an image.
            path = os.path.join(base_dir, filename)
            if not os.path.exists(path):
                return None
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.smoothscale(img, size) if size else img
            except Exception:
                return None
        
        # Load all game assets
        assets['wall'] = load_image('wall.png', (tile_size, tile_size))
        assets['ground'] = load_image('space.png', (tile_size, tile_size))
        assets['crate'] = load_image('box.png', (tile_size, tile_size))
        assets['box_on_target'] = load_image('box_on_target.png', (tile_size, tile_size))
        assets['endpoint'] = load_image('target.png', (tile_size, tile_size))
        assets['player'] = load_image('player.png', (tile_size - 10, tile_size - 10))
        
        return assets

    def _draw_board(self, screen: pygame.Surface, player_pos: tuple[int, int], 
                    boxes_pos: list[tuple[int, int]]) -> None:
        # Draw the game board with current state.
        screen.fill(BLACK)

        # Draw board tiles
        for row in range(self.height):
            for col in range(self.width):
                rect = pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                self._draw_tile(screen, rect, row, col)

        # Draw boxes
        self._draw_boxes(screen, boxes_pos)

        # Draw player
        self._draw_player(screen, player_pos)

        pygame.display.flip()

    def _draw_tile(self, screen: pygame.Surface, rect: pygame.Rect, row: int, col: int) -> None:
        # Draw a single board tile.
        cell_type = self.board[row][col]
        assets = getattr(self, 'assets', {})
        
        if cell_type == WALL:
            img = assets.get('wall')
            if img:
                screen.blit(img, rect)
            else:
                pygame.draw.rect(screen, BROWN, rect)
        elif cell_type == GOAL:
            img = assets.get('endpoint')
            if img:
                screen.blit(img, rect)
            else:
                pygame.draw.rect(screen, GRAY, rect)
        else:
            img = assets.get('ground')
            if img:
                screen.blit(img, rect)
            else:
                pygame.draw.rect(screen, WHITE, rect)

    def _draw_boxes(self, screen: pygame.Surface, boxes_pos: list[tuple[int, int]]) -> None:
        # Draw all boxes on the board.
        assets = getattr(self, 'assets', {})
        
        for box_pos in boxes_pos:
            box_rect = pygame.Rect(box_pos[1] * TILE_SIZE, box_pos[0] * TILE_SIZE, 
                                   TILE_SIZE, TILE_SIZE)
            on_target = self.board[box_pos[0]][box_pos[1]] == GOAL
            
            if on_target and assets.get('box_on_target'):
                screen.blit(assets['box_on_target'], box_rect)
            elif assets.get('crate'):
                screen.blit(assets['crate'], box_rect)
            else:
                color = GREEN if on_target else YELLOW
                pygame.draw.rect(screen, color, box_rect)

    def _draw_player(self, screen: pygame.Surface, player_pos: tuple[int, int]) -> None:
        # Draw the player on the board.
        player_rect = pygame.Rect(player_pos[1] * TILE_SIZE, player_pos[0] * TILE_SIZE, 
                                  TILE_SIZE, TILE_SIZE)
        assets = getattr(self, 'assets', {})
        
        if assets.get('player'):
            player_img = assets['player']
            dest = player_img.get_rect()
            dest.center = player_rect.center
            screen.blit(player_img, dest)
        else:
            pygame.draw.circle(screen, BLUE, player_rect.center, TILE_SIZE // 2 - 5)

    def _draw_ui_text(self, screen: pygame.Surface, level_num: int, total_levels: int, mode: str) -> None:
        # Draw UI text showing level info and controls.
        try:
            font = pygame.font.Font(None, 36)
            small_font = pygame.font.Font(None, 24)
        except:
            return
        
        # Level info
        level_text = font.render(f"Level {level_num}/{total_levels}", True, WHITE)
        screen.blit(level_text, (10, 10))
        
        # Mode indicator
        mode_color = GREEN if mode == "AUTO" else YELLOW
        mode_text = font.render(f"Mode: {mode}", True, mode_color)
        screen.blit(mode_text, (10, 50))
        
        # Controls hint
        if mode == "MANUAL":
            controls = small_font.render("WASD: Move | SPACE: Auto-Solve | R: Restart | ESC: Quit", True, GRAY)
            screen.blit(controls, (10, self.height * TILE_SIZE - 30))

    def _handle_manual_move(self, direction: str, player_pos: tuple[int, int], 
                           boxes_pos: list[tuple[int, int]]) -> tuple[tuple[int, int], list[tuple[int, int]], bool]:
        # Handle manual player movement and return new state.
        delta_row, delta_col = DIRECTIONS.get(direction, (0, 0))
        new_player_pos = (player_pos[0] + delta_row, player_pos[1] + delta_col)
        new_boxes_pos = list(boxes_pos)
        
        # Check if move is valid
        if not self._is_position_in_bounds(new_player_pos[0], new_player_pos[1]):
            return player_pos, boxes_pos, False
        if self.board[new_player_pos[0]][new_player_pos[1]] == WALL:
            return player_pos, boxes_pos, False
        
        # Check if pushing a box
        if new_player_pos in new_boxes_pos:
            new_box_pos = (new_player_pos[0] + delta_row, new_player_pos[1] + delta_col)
            
            # Validate box push
            if not self._is_position_in_bounds(new_box_pos[0], new_box_pos[1]):
                return player_pos, boxes_pos, False
            if self.board[new_box_pos[0]][new_box_pos[1]] == WALL:
                return player_pos, boxes_pos, False
            if new_box_pos in new_boxes_pos:
                return player_pos, boxes_pos, False
            
            # Move the box
            new_boxes_pos[new_boxes_pos.index(new_player_pos)] = new_box_pos
        
        return new_player_pos, new_boxes_pos, True

    def play_manual(self, level_num: int, total_levels: int) -> tuple[str, tuple, list]:
        # Main manual play mode - returns (result, current_pos, current_boxes).
        # result can be 'next', 'auto', or 'quit'
        if not pygame.get_init():
            pygame.init()

        # Create display and load assets
        screen = pygame.display.set_mode((self.width * TILE_SIZE, self.height * TILE_SIZE))
        pygame.display.set_caption(f'Sokoban - Level {level_num}/{total_levels}')
        
        try:
            self.assets = self._load_assets(TILE_SIZE)
        except Exception:
            self.assets = {}

        # Initialize game state
        current_pos = self.init_player_pos
        current_boxes = list(self.init_boxes_pos)
        clock = pygame.time.Clock()
        running = True
        result = 'quit'

        # Draw initial state
        self._draw_board(screen, current_pos, current_boxes)
        self._draw_ui_text(screen, level_num, total_levels, "MANUAL")
        pygame.display.flip()

        # Main game loop
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    result = 'quit'
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        result = 'quit'
                    
                    elif event.key == pygame.K_r:
                        # Restart level
                        current_pos = self.init_player_pos
                        current_boxes = list(self.init_boxes_pos)
                    
                    elif event.key == pygame.K_SPACE:
                        # Switch to auto-solve mode with current state
                        running = False
                        result = 'auto'
                    
                    # Handle WASD movement
                    elif event.key == pygame.K_w:
                        current_pos, current_boxes, _ = self._handle_manual_move('U', current_pos, current_boxes)
                    elif event.key == pygame.K_a:
                        current_pos, current_boxes, _ = self._handle_manual_move('L', current_pos, current_boxes)
                    elif event.key == pygame.K_s:
                        current_pos, current_boxes, _ = self._handle_manual_move('D', current_pos, current_boxes)
                    elif event.key == pygame.K_d:
                        current_pos, current_boxes, _ = self._handle_manual_move('R', current_pos, current_boxes)
                    
                    # Check win condition
                    if all(self.board[box[0]][box[1]] == GOAL for box in current_boxes):
                        # Draw winning state
                        self._draw_board(screen, current_pos, current_boxes)
                        self._draw_ui_text(screen, level_num, total_levels, "MANUAL")
                        
                        # Show win message
                        try:
                            font = pygame.font.Font(None, 72)
                            win_text = font.render("LEVEL COMPLETE!", True, GREEN)
                            text_rect = win_text.get_rect(center=(self.width * TILE_SIZE // 2, self.height * TILE_SIZE // 2))
                            screen.blit(win_text, text_rect)
                            pygame.display.flip()
                            pygame.time.wait(1500)
                        except:
                            pass
                        
                        running = False
                        result = 'next'
            
            # Redraw screen
            self._draw_board(screen, current_pos, current_boxes)
            self._draw_ui_text(screen, level_num, total_levels, "MANUAL")
            pygame.display.flip()
            clock.tick(30)

        return result, current_pos, current_boxes

    def visualize_pygame(self, solution_path: str, animation_speed: float = 0.5) -> None:
        # Visualize the solution using Pygame animation.
        if not solution_path:
            print("No solution to visualize.")
            return

        if not pygame.get_init():
            pygame.init()

        # Create display and load assets
        screen = pygame.display.set_mode((self.width * TILE_SIZE, self.height * TILE_SIZE))
        pygame.display.set_caption('Sokoban Solver Animation')
        
        try:
            self.assets = self._load_assets(TILE_SIZE)
        except Exception:
            self.assets = {}

        # Initialize animation state
        current_pos = self.init_player_pos
        current_boxes = list(self.init_boxes_pos)
        step_index = 0
        clock = pygame.time.Clock()
        running = True

        # Draw initial state
        self._draw_board(screen, current_pos, current_boxes)
        pygame.time.wait(int(animation_speed * 1000 * 2))

        # Animate solution
        while running and step_index < len(solution_path):
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

            if step_index < len(solution_path):
                # Execute next move
                move = solution_path[step_index]
                delta_row, delta_col = DIRECTIONS.get(move, (0, 0))

                next_pos = (current_pos[0] + delta_row, current_pos[1] + delta_col)
                next_boxes = current_boxes[:]

                # Handle box pushing
                if next_pos in next_boxes:
                    next_box_pos = (next_pos[0] + delta_row, next_pos[1] + delta_col)
                    next_boxes[next_boxes.index(next_pos)] = next_box_pos

                current_pos = next_pos
                current_boxes = next_boxes

                # Draw updated state
                self._draw_board(screen, current_pos, current_boxes)
                pygame.time.wait(int(animation_speed * 1000))
                step_index += 1
            else:
                self._draw_board(screen, current_pos, current_boxes)
                clock.tick(10)

        print("Animation complete. Window closed.")
        if pygame.get_init():
            pygame.quit()


# ============================================================================
# Level Loading Functions
# ============================================================================

def load_all_levels(config_file: str) -> list[tuple]:
    # Load all levels from a configuration file.
    with open(config_file, 'r') as f:
        content = f.read().strip()
    
    levels = []
    level_blocks = content.split('[LEVEL]')
    
    for block in level_blocks:
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines:
            continue
        
        # Parse board
        board = []
        i = 0
        while i < len(lines) and all(c in '012' for c in lines[i]):
            board.append(lines[i])
            i += 1
        
        # Parse player and box positions
        if i < len(lines):
            player_pos = tuple(map(int, lines[i].split(',')))
            boxes_pos = [tuple(map(int, pos.split(','))) for pos in lines[i + 1].split(';')]
            levels.append((board, player_pos, boxes_pos))
    
    return levels


def load_level_config(config_file: str):
    # Load the first level from a configuration file.
    levels = load_all_levels(config_file)
    return levels[0] if levels else ([], (0, 0), [])



# ============================================================================
# Main Program
# ============================================================================

if __name__ == '__main__':
    print("Loading levels...")
    levels = load_all_levels('level/level.txt')
    current_level = 0
    
    print("\n" + "=" * 50)
    print("SOKOBAN SOLVER")
    print("=" * 50)
    print("Controls:")
    print("  WASD  - Move player (Manual mode)")
    print("  SPACE - Switch to Auto-Solve mode")
    print("  R     - Restart current level")
    print("  ESC  - Quit game")
    print("=" * 50)
    
    while current_level < len(levels):
        board, player_pos, boxes_pos = levels[current_level]
        
        print(f"\n{'=' * 50}")
        print(f"Level {current_level + 1} / {len(levels)}")
        print(f"{'=' * 50}")
        
        solver = SokobanSolver(board, player_pos, boxes_pos)
        
        # Start with manual play mode
        print("Starting in MANUAL mode...")
        result, current_player_pos, current_boxes_pos = solver.play_manual(current_level + 1, len(levels))
        
        if result == 'next':
            # Level completed manually
            print("✓ Level completed manually!")
            current_level += 1
            
            if current_level < len(levels):
                print(f"\nProceeding to Level {current_level + 1}...")
            else:
                print("\n🎉 All levels completed! Congratulations!")
        
        elif result == 'auto':
            # User requested auto-solve from current state
            print("\nSwitching to AUTO-SOLVE mode...")
            print(f"Solving from current position...")
            
            # Create new solver with current state
            auto_solver = SokobanSolver(board, current_player_pos, current_boxes_pos)
            solution = auto_solver.solve()
            
            if solution:
                # Display solution statistics
                print(f"Solution found in {auto_solver.time_used:.3f}s")
                print(f"Step needed: {len(solution)} step(s)")
                print(f"Moves: {solution}")
                print(f"Expanded nodes: {auto_solver.expanded_nodes_count}")
                print(f"Visited nodes: {auto_solver.visited_nodes_count}")
                
                # Visualize solution from current state
                auto_solver.visualize_pygame(solution, animation_speed=0.3)
                current_level += 1
                
                if current_level < len(levels):
                    print(f"\nProceeding to Level {current_level + 1}...")
                else:
                    print("\n🎉 All levels completed!")
            else:
                print("No solution found from current position.")
                retry = input("Retry this level? (y/n): ").strip().lower()
                if retry != 'y':
                    break
        
        else:
            # User quit
            print("\nThanks for playing!")
            break
    
    # Cleanup
    if pygame.get_init():
        pygame.quit()