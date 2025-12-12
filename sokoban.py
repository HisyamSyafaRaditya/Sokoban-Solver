import pygame
import os
from solver import SokobanSolver, DIRECTIONS, WALL, GOAL

# Modern Color Palette
BLACK = (18, 18, 18)
WHITE = (240, 240, 240)
BROWN = (101, 67, 33)
GRAY = (40, 40, 40)
GREEN = (46, 204, 113)    # Emerald Green
YELLOW = (241, 196, 15)   # Sunflower Yellow
BLUE = (52, 152, 219)     # Peter River Blue
RED = (231, 76, 60)       # Alizarin Red
DARK_BLUE = (44, 62, 80)  # Midnight Blue
ACCENT = (155, 89, 182)   # Amethyst Purple

# UI Constants
BUTTON_COLOR = (52, 73, 94)
BUTTON_HOVER = (41, 128, 185)
TEXT_COLOR = (236, 240, 241)

# Game constants
TILE_SIZE = 50
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720


def draw_gradient_background(screen, top_color, bottom_color):
    """Draws a vertical gradient background."""
    height = screen.get_height()
    for i in range(height):
        # Linear interpolation
        alpha = i / height
        r = int(top_color[0] * (1 - alpha) + bottom_color[0] * alpha)
        g = int(top_color[1] * (1 - alpha) + bottom_color[1] * alpha)
        b = int(top_color[2] * (1 - alpha) + bottom_color[2] * alpha)
        pygame.draw.line(screen, (r, g, b), (0, i), (screen.get_width(), i))


class Button:
    def __init__(self, x, y, width, height, text, action_id, color=BUTTON_COLOR, hover_color=BUTTON_HOVER, text_color=TEXT_COLOR):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action_id = action_id
        self.base_color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = pygame.font.Font(None, 40) # Larger font
        self.small_font = pygame.font.Font(None, 28)
        self.shadow_offset = 4
        self.is_hovered = False

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        color = self.hover_color if self.is_hovered else self.base_color
        
        # Draw Shadow
        shadow_rect = self.rect.copy()
        shadow_rect.x += self.shadow_offset
        shadow_rect.y += self.shadow_offset
        pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=12) # Semi-transparent shadow

        # Draw Button Body
        # If hovered, slightly move button up/left to simulate press/lift or just standard highlight
        draw_rect = self.rect.copy()
        if self.is_hovered:
            draw_rect.x -= 2
            draw_rect.y -= 2
        
        pygame.draw.rect(screen, color, draw_rect, border_radius=12)
        pygame.draw.rect(screen, (255, 255, 255, 50), draw_rect, 2, border_radius=12) # Subtle border
        
        # Handle multiline text
        lines = self.text.split('\n')
        
        # Calculate total height with different fonts
        total_height = 0
        fonts = [self.font if i == 0 else self.small_font for i in range(len(lines))]
        for font in fonts:
            total_height += font.get_height()
            
        current_y = draw_rect.center[1] - total_height // 2
        
        for i, line in enumerate(lines):
            font = fonts[i]
            text_surf = font.render(line, True, self.text_color)
            text_rect = text_surf.get_rect(center=(draw_rect.center[0], current_y + font.get_height() // 2))
            screen.blit(text_surf, text_rect)
            current_y += font.get_height()

    def is_clicked(self, pos):
        # Check against the drawn position (which might be shifted if hovered)
        check_rect = self.rect.copy()
        if self.is_hovered:
            check_rect.x -= 2
            check_rect.y -= 2
        return check_rect.collidepoint(pos)


class SokobanGame:
    """
    Sokoban game with manual play mode and auto-solve visualization.
    """

    def __init__(self, solver: SokobanSolver = None, best_score: int = 0):
        self.solver = solver
        self.assets = {}
        self.buttons = []
        self.best_score = best_score


    def _init_ui(self):
        # Modern styled buttons for in-game
        self.buttons = [
            Button(50, 200, 200, 50, "Restart (R)", "restart", color=(52, 73, 94), hover_color=(41, 128, 185)),
            Button(50, 270, 200, 50, "Auto-Solve", "auto", color=(39, 174, 96), hover_color=(46, 204, 113)), # Green
            Button(50, 340, 200, 50, "Exit Level", "exit", color=(192, 57, 43), hover_color=(231, 76, 60))  # Red
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
        draw_gradient_background(screen, BLACK, DARK_BLUE)

        # Calculate offsets to center the board
        board_width = self.solver.width * TILE_SIZE
        board_height = self.solver.height * TILE_SIZE
        offset_x = (SCREEN_WIDTH - board_width) // 2
        offset_y = (SCREEN_HEIGHT - board_height) // 2

        # Draw decorative border around board
        border_rect = pygame.Rect(offset_x - 10, offset_y - 10, board_width + 20, board_height + 20)
        pygame.draw.rect(screen, (255, 255, 255, 30), border_rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, border_rect, 2, border_radius=5)

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

        # Draw sidebar info panel
        panel_rect = pygame.Rect(50, 50, 200, 120)
        pygame.draw.rect(screen, (0, 0, 0, 150), panel_rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, panel_rect, 1, border_radius=10)

        # Draw move counter
        font = pygame.font.Font(None, 48)
        text = font.render(f"Moves: {moves_count}", True, WHITE)
        screen.blit(text, (65, 70))
        
        # Draw Best Score
        # if self.best_score > 0:
        best_text_str = f"Best: {self.best_score}" if self.best_score > 0 else "Best: -"
        text_best = pygame.font.Font(None, 36).render(best_text_str, True, YELLOW)
        screen.blit(text_best, (65, 120))

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
                                elif button.action_id == 'exit':
                                    running = False
                                    result = 'quit'

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
                        # Show win message with modern overlay
                        try:
                            # Dim background
                            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                            overlay.fill((0, 0, 0, 180)) # Darker fade
                            screen.blit(overlay, (0, 0))
                            
                            # Draw panel
                            panel_w, panel_h = 600, 300
                            panel_x = (SCREEN_WIDTH - panel_w) // 2
                            panel_y = (SCREEN_HEIGHT - panel_h) // 2
                            panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
                            
                            pygame.draw.rect(screen, (34, 49, 63), panel_rect, border_radius=20)
                            pygame.draw.rect(screen, WHITE, panel_rect, 3, border_radius=20)
                            
                            # Calculate centers
                            center_x = SCREEN_WIDTH // 2
                            center_y = SCREEN_HEIGHT // 2

                            # Update best score
                            if level_path and (self.best_score == 0 or moves_count < self.best_score):
                                save_best_score(level_path, moves_count)
                                self.best_score = moves_count
                                # New Record Text
                                record_font = pygame.font.Font(None, 50)
                                record_text = record_font.render("NEW RECORD!", True, YELLOW)
                                record_rect = record_text.get_rect(center=(center_x, center_y))
                                screen.blit(record_text, record_rect)
                            
                            # Level Complete Text
                            font = pygame.font.Font(None, 80)
                            win_text = font.render("LEVEL COMPLETE", True, GREEN)
                            win_rect = win_text.get_rect(center=(center_x, center_y - 70))
                            screen.blit(win_text, win_rect)

                            # Continue Text
                            small_font = pygame.font.Font(None, 40)
                            cont_text = small_font.render("Press SPACE to Next Level", True, WHITE)
                            cont_rect = cont_text.get_rect(center=(center_x, center_y + 80))
                            screen.blit(cont_text, cont_rect)
                            
                            pygame.display.flip()
                            pygame.time.wait(2000)
                        except Exception as e:
                            print(f"Error in victory screen: {e}")
                        
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


def run_main_menu(levels: list[dict]) -> int:
    # Run the main menu loop. Returns the index of the selected level or -1 to quit.
    if not pygame.get_init():
        pygame.init()
        
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Sokoban Solver - Main Menu')
    clock = pygame.time.Clock()
    
    # Create buttons for each level
    level_buttons = []
    button_width = 200
    button_height = 120
    
    # Grid layout calculations
    cols = 4
    start_x = (SCREEN_WIDTH - (cols * button_width + (cols - 1) * 20)) // 2
    start_y = 200
    gap_x = 20
    gap_y = 20
    
    for i, level in enumerate(levels):
        row = i // cols
        col = i % cols
        x = start_x + col * (button_width + gap_x)
        y = start_y + row * (button_height + gap_y)
        
        # Custom button rendering for multiline text
        btn_text = f"LEVEL {i+1}"
        if level['best_score'] > 0:
            btn_text += f"\n\nBest:\n{level['best_score']} Moves"
        else:
            btn_text += f"\n\nBest:\n--"
            
        # Alternate colors for visual interest
        color = (41, 128, 185) if level['best_score'] > 0 else (52, 73, 94) # Blue if completed else Dark Blue
        
        level_buttons.append(Button(x, y, button_width, button_height, btn_text, i, color=color, hover_color=(52, 152, 219)))

    # Add Exit Game button
    exit_btn = Button(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 100, 200, 60, "Exit Game", -1, color=(192, 57, 43), hover_color=(231, 76, 60))
    level_buttons.append(exit_btn)

    running = True
    title_font = pygame.font.Font(None, 100)
    subtitle_font = pygame.font.Font(None, 40)
    
    while running:
        draw_gradient_background(screen, (44, 62, 80), (18, 18, 18)) # Dark Blue to Black
        
        # Draw Title with Shadow
        title_text = "SOKOBAN"
        title_surf = title_font.render(title_text, True, WHITE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 80))
        
        # Shadow
        shadow_surf = title_font.render(title_text, True, (0, 0, 0))
        shadow_rect = shadow_surf.get_rect(center=(SCREEN_WIDTH // 2 + 4, 84))
        screen.blit(shadow_surf, shadow_rect)
        screen.blit(title_surf, title_rect)
        
        # Subtitle
        sub_text = subtitle_font.render("Select a Level", True, (200, 200, 200))
        sub_rect = sub_text.get_rect(center=(SCREEN_WIDTH // 2, 140))
        screen.blit(sub_text, sub_rect)
        
        # Draw Buttons
        mouse_pos = pygame.mouse.get_pos()
        for btn in level_buttons:
            btn.draw(screen)
            
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return -1
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return -1
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for btn in level_buttons:
                        if btn.is_clicked(event.pos):
                            return btn.action_id
                            
        clock.tick(30)
        
    return -1


# ============================================================================
# Main Program
# ============================================================================

if __name__ == '__main__':
    print("Loading levels...")
    levels = load_all_levels('level')
    
    while True:
        # Reload levels to get fresh best scores if updated
        levels = load_all_levels('level')
        
        choice = run_main_menu(levels)
        
        if choice == -1:
            print("Exiting game...")
            break
            
        current_level = choice
        level_data = levels[current_level]
        board = level_data['board']
        player_pos = level_data['player']
        boxes_pos = level_data['boxes']
        best_score = level_data['best_score']
        level_path = level_data['file_path']
        
        print(f"\n{'=' * 50}")
        print(f"Playing Level {current_level + 1}...")
        print(f"{'=' * 50}")
        
        solver = SokobanSolver(board, player_pos, boxes_pos)
        game = SokobanGame(solver, best_score)
        
        # Start with manual play mode
        print("Starting in MANUAL mode...")
        result, current_player_pos, current_boxes_pos = game.play_manual(current_level + 1, len(levels), level_path)
        
        if result == 'next':
            print("Level completed! Returning to menu...")
            pygame.time.wait(1000)
            
        elif result == 'auto':
            # User requested auto-solve from current state
            print("\nSwitching to AUTO-SOLVE mode...")
            
            # Create new solver with current state
            auto_solver = SokobanSolver(board, current_player_pos, current_boxes_pos)
            solution = auto_solver.solve()
            
            if solution:
                # Display solution statistics
                print(f"Solution found in {auto_solver.time_used:.3f}s")
                print(f"Step needed: {len(solution)} step(s)")
                
                # Visualize solution from current state
                auto_game = SokobanGame(auto_solver)
                auto_game.visualize_solution(solution, animation_speed=0.3)
                print("Auto-solve complete. Returning to menu...")
            else:
                print("No solution found from current position.")
                pygame.time.wait(2000)
        
        # If result is 'quit', it just breaks the inner game loop and returns here,
        # which loops back to the main menu. Matches "ESC -> Menu" behavior.

    
    # Cleanup
    if pygame.get_init():
        pygame.quit()
