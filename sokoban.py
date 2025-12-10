import pygame
import os
from solver import SokobanSolver, DIRECTIONS, WALL, GOAL

# Color constants
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
GREEN = (0, 128, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
SSS = (26, 26, 26)

# Game constants
TILE_SIZE = 50
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720


class Button:
    def __init__(self, x, y, width, height, text, action_id, color=GRAY, hover_color=WHITE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_id = action_id
        self.color = color
        self.hover_color = hover_color
        self.font = pygame.font.Font(None, 36)

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=10)
        
        text_surf = self.font.render(self.text, True, BLACK if color == WHITE else WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class SokobanGame:
    """
    Sokoban game with manual play mode and auto-solve visualization.
    """

    def __init__(self, solver: SokobanSolver, best_score: int = 0):
        self.solver = solver
        self.assets = {}
        self.buttons = []
        self.best_score = best_score

    def _init_ui(self):
        self.buttons = [
            Button(50, 200, 200, 50, "Restart (R)", "restart", color=(100, 100, 100), hover_color=(150, 150, 150)),
            Button(50, 270, 200, 50, "Auto-Solve", "auto", color=(0, 100, 200), hover_color=(50, 150, 250))
        ]

    def _load_assets(self, tile_size: int) -> dict:
        # Load game assets (images) from the images directory.
        assets = {}
        base_dir = os.path.join(os.path.dirname(__file__), 'assets')
        
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
        
        # Load player sprites for animation
        player1 = load_image('player1.png', (tile_size - 10, tile_size - 10))
        player2 = load_image('player2.png', (tile_size - 10, tile_size - 10))
        
        # Create player animation list
        assets['player_frames'] = [player1, player2] if player1 and player2 else [player1] if player1 else []
        
        return assets


    def _draw_board(self, screen: pygame.Surface, player_pos: tuple[int, int], 
                    boxes_pos: list[tuple[int, int]], moves_count: int = 0) -> None:
        # Draw the game board with current state.
        screen.fill(SSS)

        # Calculate offsets to center the board
        board_width = self.solver.width * TILE_SIZE
        board_height = self.solver.height * TILE_SIZE
        offset_x = (SCREEN_WIDTH - board_width) // 2
        offset_y = (SCREEN_HEIGHT - board_height) // 2

        # Draw board tiles
        for row in range(self.solver.height):
            for col in range(self.solver.width):
                rect = pygame.Rect(col * TILE_SIZE + offset_x, row * TILE_SIZE + offset_y, TILE_SIZE, TILE_SIZE)
                self._draw_tile(screen, rect, row, col)

        # Draw boxes
        self._draw_boxes(screen, boxes_pos, offset_x, offset_y)

        # Draw player
        self._draw_player(screen, player_pos, offset_x, offset_y)

        # Draw UI buttons
        for button in self.buttons:
            button.draw(screen)

        # Draw move counter
        font = pygame.font.Font(None, 48)
        text = font.render(f"Moves: {moves_count}", True, WHITE)
        screen.blit(text, (50, 100))
        
        # Draw Best Score
        if self.best_score > 0:
            best_text = f"Best: {self.best_score}"
            text_best = font.render(best_text, True, WHITE)
            screen.blit(text_best, (SCREEN_WIDTH - 250, 100))

        pygame.display.flip()

    def _draw_tile(self, screen: pygame.Surface, rect: pygame.Rect, row: int, col: int) -> None:
        # Draw a single board tile.
        cell_type = self.solver.board[row][col]
        
        if cell_type == WALL:
            img = self.assets.get('wall')
            if img:
                screen.blit(img, rect)
            else:
                pygame.draw.rect(screen, BROWN, rect)
        elif cell_type == GOAL:
            img = self.assets.get('endpoint')
            if img:
                screen.blit(img, rect)
            else:
                pygame.draw.rect(screen, GRAY, rect)
        else:
            img = self.assets.get('ground')
            if img:
                screen.blit(img, rect)
            else:
                pygame.draw.rect(screen, WHITE, rect)

    def _draw_boxes(self, screen: pygame.Surface, boxes_pos: list[tuple[int, int]], offset_x: int, offset_y: int) -> None:
        # Draw all boxes on the board.
        for box_pos in boxes_pos:
            box_rect = pygame.Rect(box_pos[1] * TILE_SIZE + offset_x, box_pos[0] * TILE_SIZE + offset_y, 
                                   TILE_SIZE, TILE_SIZE)
            on_target = self.solver.board[box_pos[0]][box_pos[1]] == GOAL
            
            if on_target and self.assets.get('box_on_target'):
                screen.blit(self.assets['box_on_target'], box_rect)
            elif self.assets.get('crate'):
                screen.blit(self.assets['crate'], box_rect)
            else:
                color = GREEN if on_target else YELLOW
                pygame.draw.rect(screen, color, box_rect)

    def _draw_player(self, screen: pygame.Surface, player_pos: tuple[int, int], offset_x: int, offset_y: int) -> None:
        # Draw the player on the board with animation.
        player_rect = pygame.Rect(player_pos[1] * TILE_SIZE + offset_x, player_pos[0] * TILE_SIZE + offset_y, 
                                  TILE_SIZE, TILE_SIZE)
        
        player_frames = self.assets.get('player_frames', [])
        if player_frames:
            # Animate player by alternating frames every 500ms
            frame_index = (pygame.time.get_ticks() // 500) % len(player_frames)
            player_img = player_frames[frame_index]
            
            if player_img:
                dest = player_img.get_rect()
                dest.center = player_rect.center
                screen.blit(player_img, dest)
            else:
                pygame.draw.circle(screen, BLUE, player_rect.center, TILE_SIZE // 2 - 5)
        else:
            pygame.draw.circle(screen, BLUE, player_rect.center, TILE_SIZE // 2 - 5)


    def _handle_manual_move(self, direction: str, player_pos: tuple[int, int], 
                           boxes_pos: list[tuple[int, int]]) -> tuple[tuple[int, int], list[tuple[int, int]], bool]:
        # Handle manual player movement and return new state.
        delta_row, delta_col = DIRECTIONS.get(direction, (0, 0))
        new_player_pos = (player_pos[0] + delta_row, player_pos[1] + delta_col)
        new_boxes_pos = list(boxes_pos)
        
        # Check if move is valid
        if not self.solver._is_position_in_bounds(new_player_pos[0], new_player_pos[1]):
            return player_pos, boxes_pos, False
        if self.solver.board[new_player_pos[0]][new_player_pos[1]] == WALL:
            return player_pos, boxes_pos, False
        
        # Check if pushing a box
        if new_player_pos in new_boxes_pos:
            new_box_pos = (new_player_pos[0] + delta_row, new_player_pos[1] + delta_col)
            
            # Validate box push
            if not self.solver._is_position_in_bounds(new_box_pos[0], new_box_pos[1]):
                return player_pos, boxes_pos, False
            if self.solver.board[new_box_pos[0]][new_box_pos[1]] == WALL:
                return player_pos, boxes_pos, False
            if new_box_pos in new_boxes_pos:
                return player_pos, boxes_pos, False
            
            # Move the box
            new_boxes_pos[new_boxes_pos.index(new_player_pos)] = new_box_pos
        
        return new_player_pos, new_boxes_pos, True

    def play_manual(self, level_num: int, total_levels: int, level_path: str = None) -> tuple[str, tuple, list]:
        if not pygame.get_init():
            pygame.init()

        # Create display and load assets
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f'Sokoban - Level {level_num}/{total_levels}')
        
        try:
            self.assets = self._load_assets(TILE_SIZE)
        except Exception:
            self.assets = {}

        # Initialize UI
        self._init_ui()

        # Initialize game state
        current_pos = self.solver.init_player_pos
        current_boxes = list(self.solver.init_boxes_pos)
        moves_count = 0
        clock = pygame.time.Clock()
        running = True
        result = 'quit'

        # Draw initial state
        self._draw_board(screen, current_pos, current_boxes, moves_count)
        pygame.display.flip()

        # Main game loop
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    result = 'quit'
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        for button in self.buttons:
                            if button.is_clicked(event.pos):
                                if button.action_id == 'restart':
                                    current_pos = self.solver.init_player_pos
                                    current_boxes = list(self.solver.init_boxes_pos)
                                    moves_count = 0
                                elif button.action_id == 'auto':
                                    running = False
                                    result = 'auto'

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        result = 'quit'
                    
                    elif event.key == pygame.K_r:
                        # Restart level
                        current_pos = self.solver.init_player_pos
                        current_boxes = list(self.solver.init_boxes_pos)
                        moves_count = 0
                    
                    elif event.key == pygame.K_SPACE:
                        # Switch to auto-solve mode with current state
                        running = False
                        result = 'auto'
                    
                    # Handle WASD movement
                    elif event.key == pygame.K_w:
                        current_pos, current_boxes, moved = self._handle_manual_move('U', current_pos, current_boxes)
                        if moved: moves_count += 1
                    elif event.key == pygame.K_a:
                        current_pos, current_boxes, moved = self._handle_manual_move('L', current_pos, current_boxes)
                        if moved: moves_count += 1
                    elif event.key == pygame.K_s:
                        current_pos, current_boxes, moved = self._handle_manual_move('D', current_pos, current_boxes)
                        if moved: moves_count += 1
                    elif event.key == pygame.K_d:
                        current_pos, current_boxes, moved = self._handle_manual_move('R', current_pos, current_boxes)
                        if moved: moves_count += 1
                    
                    # Check win condition
                    if all(self.solver.board[box[0]][box[1]] == GOAL for box in current_boxes):
                        # Draw winning state
                        self._draw_board(screen, current_pos, current_boxes, moves_count)
                        
                        # Show win message with background
                        try:
                            font = pygame.font.Font(None, 72)
                            win_text = font.render("LEVEL COMPLETE!", True, GREEN)
                            text_rect = win_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

                            # Update best score
                            if level_path and (self.best_score == 0 or moves_count < self.best_score):
                                save_best_score(level_path, moves_count)
                                print(f"New Best Score: {moves_count}!")
                                self.best_score = moves_count
                            
                            # Draw semi-transparent background box
                            padding = 20
                            bg_rect = pygame.Rect(
                                text_rect.x - padding,
                                text_rect.y - padding,
                                text_rect.width + padding * 2,
                                text_rect.height + padding * 2
                            )
                            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
                            pygame.draw.rect(bg_surface, (0, 0, 0, 200), bg_surface.get_rect(), border_radius=15)
                            pygame.draw.rect(bg_surface, GREEN, bg_surface.get_rect(), width=3, border_radius=15)
                            screen.blit(bg_surface, (bg_rect.x, bg_rect.y))
                            
                            # Draw text
                            screen.blit(win_text, text_rect)
                            pygame.display.flip()
                            pygame.time.wait(1500)
                        except:
                            pass
                        
                        running = False
                        result = 'next'
            
            # Redraw screen
            self._draw_board(screen, current_pos, current_boxes, moves_count)
            pygame.display.flip()
            clock.tick(30)

        return result, current_pos, current_boxes

    def visualize_solution(self, solution_path: str, animation_speed: float = 0.5) -> None:
        # Visualize the solution using Pygame animation.
        if not solution_path:
            print("No solution to visualize.")
            return

        if not pygame.get_init():
            pygame.init()

        # Create display and load assets
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Sokoban Solver Animation')
        
        try:
            self.assets = self._load_assets(TILE_SIZE)
        except Exception:
            self.assets = {}

        # Initialize animation state
        current_pos = self.solver.init_player_pos
        current_boxes = list(self.solver.init_boxes_pos)
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

def save_best_score(filepath: str, new_score: int):
    # Update the best score in the level file.
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        best_score_line_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('BEST_SCORE:'):
                best_score_line_idx = i
                break
                
        if best_score_line_idx != -1:
            lines[best_score_line_idx] = f"BEST_SCORE:{new_score}\n"
        else:
            if lines[-1].strip():
                lines.append('\n')
            lines.append(f"BEST_SCORE:{new_score}\n")
            
        with open(filepath, 'w') as f:
            f.writelines(lines)
    except Exception as e:
        print(f"Error saving best score: {e}")

def load_all_levels(level_dir: str) -> list[dict]:
    # Load all levels from individual level files in the directory.
    import re
    
    levels = []
    if not os.path.exists(level_dir):
        return levels

    # Find all level files matching pattern level<number>.txt
    files = []
    for filename in os.listdir(level_dir):
        match = re.match(r'level(\d+)\.txt', filename)
        if match:
            files.append((int(match.group(1)), filename))
    
    # Sort by level number
    files.sort()
    
    for _, filename in files:
        path = os.path.join(level_dir, filename)
        try:
            with open(path, 'r') as f:
                content = f.read().strip()
            
            if not content:
                continue

            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if not lines:
                continue
            
            # Parse board
            board = []
            i = 0
            # Read until we hit a comma (coordinate line)
            while i < len(lines) and ',' not in lines[i]:
                board.append(lines[i])
                i += 1
            
            # Parse player and box positions
            if i < len(lines):
                player_pos = tuple(map(int, lines[i].split(',')))
                if i + 1 < len(lines):
                    # Remove trailing dot if present
                    boxes_line = lines[i + 1].rstrip('.')
                    boxes_pos = [tuple(map(int, pos.split(','))) for pos in boxes_line.split(';')]
                    
                    # Parse BEST_SCORE
                    best_score = 0
                    for line in lines[i+2:]: # Look in remaining lines
                        if line.startswith('BEST_SCORE:'):
                            try:
                                best_score = int(line.split(':')[1].rstrip('.'))
                            except ValueError:
                                best_score = 0
                    
                    levels.append({
                        'board': board,
                        'player': player_pos,
                        'boxes': boxes_pos,
                        'best_score': best_score,
                        'file_path': path
                    })
                    
        except Exception as e:
            print(f"Error loading {filename}: {e}")
    
    return levels


# ============================================================================
# Main Program
# ============================================================================

if __name__ == '__main__':
    print("Loading levels...")
    levels = load_all_levels('level')
    current_level = 0
    
    print("\n" + "=" * 50)
    print("SOKOBAN SOLVER")
    print("=" * 50)
    print("Controls:")
    print("  WASD  - Move player (Manual mode)")
    print("  SPACE - Switch to Auto-Solve mode")
    print("  R     - Restart current level")
    print("  ESC   - Quit game")
    print("=" * 50)
    
    while current_level < len(levels):
        level_data = levels[current_level]
        board = level_data['board']
        player_pos = level_data['player']
        boxes_pos = level_data['boxes']
        best_score = level_data['best_score']
        level_path = level_data['file_path']
        
        print(f"\n{'=' * 50}")
        print(f"Level {current_level + 1} / {len(levels)}")
        print(f"{'=' * 50}")
        
        solver = SokobanSolver(board, player_pos, boxes_pos)
        game = SokobanGame(solver, best_score)
        
        # Start with manual play mode
        print("Starting in MANUAL mode...")
        result, current_player_pos, current_boxes_pos = game.play_manual(current_level + 1, len(levels), level_path)
        
        if result == 'next':
            # Level completed manually
            print("Level completed manually!")
            current_level += 1
            
            if current_level < len(levels):
                print(f"\nProceeding to Level {current_level + 1}...")
            else:
                print("\nAll levels completed! Congratulations!!!")
        
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
                auto_game = SokobanGame(auto_solver)
                auto_game.visualize_solution(solution, animation_speed=0.3)
                current_level += 1
                
                if current_level < len(levels):
                    print(f"\nProceeding to Level {current_level + 1}...")
                else:
                    print("\nAll levels completed!")
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
