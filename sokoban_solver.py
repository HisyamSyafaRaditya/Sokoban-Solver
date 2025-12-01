import time
import pygame
import os
from collections import deque

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BROWN = (139, 69, 19)
GRAY = (128, 128, 128)
GREEN = (0, 128, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)

TILE_SIZE = 50


class SokobanSolver:

    def __init__(self, board: list[str], player_pos: tuple, boxes_pos: list[tuple]):
        self.board = board
        self.init_player_pos = player_pos
        self.init_boxes_pos = boxes_pos
        self.goals_pos = [(r, c) for r in range(len(board))
                          for c in range(len(board[r])) if board[r][c] == '2']
        self.width = len(board[0]) if board else 0
        self.height = len(board)

        self.dead_space = self.generate_dead_space_matrix()
        self.minimum_distance_map = {}
        for goal_pos in self.goals_pos:
            self.minimum_distance_map[goal_pos] = self.minimum_distances(goal_pos)

        self.visited_states = {}
        self.fringe = []
        self.solution = None
        self.expanded_nodes_count = 0
        self.visited_nodes_count = 0
        self.time_used = 0

    def is_corner(self, r: int, c: int) -> bool:
        corners = [
            (self.board[r - 1][c] == '1' and self.board[r][c - 1] == '1'),
            (self.board[r - 1][c] == '1' and self.board[r][c + 1] == '1'),
            (self.board[r + 1][c] == '1' and self.board[r][c - 1] == '1'),
            (self.board[r + 1][c] == '1' and self.board[r][c + 1] == '1')
        ]
        return any(corners)

    def generate_dead_space_matrix(self) -> list[list[bool]]:
        dead_space = [[False for _ in range(self.width)] for _ in range(self.height)]

        for r in range(self.height):
            for c in range(self.width):
                if dead_space[r][c]:
                    continue
                if self.board[r][c] == '1':
                    dead_space[r][c] = True
                elif self.board[r][c] == '2':
                    dead_space[r][c] = False
                elif r > 0 and c > 0 and r < self.height - 1 and c < self.width - 1 and self.is_corner(r, c) and self.board[r][c] != '2':
                    dead_space[r][c] = True

        for r in range(self.height):
            for c in range(self.width):
                if self.board[r][c] == '1' or self.board[r][c] == '2':
                    continue
                elif dead_space[r][c]:
                    continue
                elif r > 0 and c > 0 and r < self.height - 1 and c < self.width - 1:
                    if self.board[r-1][c] == '1' or self.board[r+1][c] == '1':
                        left_c = c
                        while left_c > 0 and self.board[r][left_c-1] != '1' and (self.board[r-1][left_c] == '1' or self.board[r+1][left_c] == '1') and self.board[r][left_c] != '2':
                            left_c -= 1
                        if not self.is_corner(r, left_c) or not dead_space[r][left_c]:
                            continue

                        right_c = c
                        while right_c < self.width - 1 and self.board[r][right_c+1] != '1' and (self.board[r-1][right_c] == '1' or self.board[r+1][right_c] == '1') and self.board[r][right_c] != '2':
                            right_c += 1
                        if not self.is_corner(r, right_c) or not dead_space[r][right_c]:
                            continue

                        for cur_c in range(left_c, right_c + 1):
                            dead_space[r][cur_c] = True

                    if self.board[r][c-1] == '1' or self.board[r][c+1] == '1':
                        top_r = r
                        while top_r > 0 and self.board[top_r-1][c] != '1' and (self.board[top_r][c-1] == '1' or self.board[top_r][c+1] == '1') and self.board[top_r][c] != '2':
                            top_r -= 1
                        if not self.is_corner(top_r, c) or not dead_space[top_r][c]:
                            continue

                        bottom_r = r
                        while bottom_r < self.height - 1 and self.board[bottom_r+1][c] != '1' and (self.board[bottom_r][c-1] == '1' or self.board[bottom_r][c+1] == '1') and self.board[bottom_r][c] != '2':
                            bottom_r += 1
                        if not self.is_corner(bottom_r, c) or not dead_space[bottom_r][c]:
                            continue

                        for cur_r in range(top_r, bottom_r + 1):
                            dead_space[cur_r][c] = True

        return dead_space

    def minimum_distances(self, start_pos: tuple[int, int]) -> list[list[int]]:
        visited = [[False] * self.width for _ in range(self.height)]
        dist = [[999999] * self.width for _ in range(self.height)]
        dist[start_pos[0]][start_pos[1]] = 0
        queue = deque([(start_pos, 0)])
        
        while queue:
            pos, d = queue.popleft()
            if visited[pos[0]][pos[1]]:
                continue
            visited[pos[0]][pos[1]] = True
            dist[pos[0]][pos[1]] = d
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                new_pos = (pos[0] + dr, pos[1] + dc)
                if 0 <= new_pos[0] < self.height and 0 <= new_pos[1] < self.width:
                    if self.board[new_pos[0]][new_pos[1]] != '1':
                        queue.append((new_pos, d + 1))
        return dist

    def h(self, state: tuple[tuple[int, int], list[tuple[int, int]]]) -> int:
        return sum(min(self.minimum_distance_map[goal][box[0]][box[1]]
                       for goal in self.goals_pos)
                   for box in state[1])

    def is_goal(self, state: tuple[tuple[int, int], list[tuple[int, int]]]) -> bool:
        return all(self.board[box[0]][box[1]] == '2' for box in state[1])

    def insert_into_fringe(self, node: tuple) -> None:
        state = (node[0], tuple(sorted(node[1])))
        
        if state in self.visited_states:
            return
        
        self.expanded_nodes_count += 1
        f = node[2] + node[3]
        
        for i in range(len(self.fringe)):
            if self.fringe[i][2] + self.fringe[i][3] > f:
                self.fringe.insert(i, (node[0], state[1], node[2], node[3], node[4]))
                return
        self.fringe.append((node[0], state[1], node[2], node[3], node[4]))

    def solve(self) -> str:
        start_time = time.time()
        init_state = (self.init_player_pos, self.init_boxes_pos)
        self.insert_into_fringe((self.init_player_pos, self.init_boxes_pos, 0, self.h(init_state), ''))

        while self.fringe:
            node = self.fringe.pop(0)
            state = (node[0], node[1])
            self.visited_nodes_count += 1
            
            if self.is_goal(state):
                self.solution = node[4]
                self.time_used = time.time() - start_time
                return node[4]

            if state in self.visited_states:
                continue
            self.visited_states[state] = True

            for dr, dc, op in [(0, 1, 'R'), (0, -1, 'L'), (1, 0, 'D'), (-1, 0, 'U')]:
                new_player_pos = (node[0][0] + dr, node[0][1] + dc)
                new_boxes_pos = list(node[1])
                
                if not (0 <= new_player_pos[0] < self.height and 0 <= new_player_pos[1] < self.width):
                    continue
                if self.board[new_player_pos[0]][new_player_pos[1]] == '1':
                    continue
                
                if new_player_pos in new_boxes_pos:
                    new_box_pos = (new_player_pos[0] + dr, new_player_pos[1] + dc)
                    if not (0 <= new_box_pos[0] < self.height and 0 <= new_box_pos[1] < self.width):
                        continue
                    if self.board[new_box_pos[0]][new_box_pos[1]] == '1':
                        continue
                    if new_box_pos in new_boxes_pos:
                        continue
                    if self.dead_space[new_box_pos[0]][new_box_pos[1]]:
                        continue
                    
                    new_boxes_pos[new_boxes_pos.index(new_player_pos)] = new_box_pos
                
                new_state = (new_player_pos, new_boxes_pos)
                new_node = (new_player_pos, new_boxes_pos, node[2] + 1, self.h(new_state), node[4] + op)
                self.insert_into_fringe(new_node)

        self.solution = None
        self.time_used = time.time() - start_time
        return None

    def draw_board_pygame(self, screen, player_pos: tuple[int, int], boxes_pos: list[tuple[int, int]]) -> None:
        screen.fill(BLACK)

        for r in range(self.height):
            for c in range(self.width):
                rect = pygame.Rect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                cell_type = self.board[r][c]
                
                if cell_type == '1':
                    img = getattr(self, 'assets', {}).get('wall')
                    if img:
                        screen.blit(img, rect)
                    else:
                        pygame.draw.rect(screen, BROWN, rect)
                elif cell_type == '2':
                    img = getattr(self, 'assets', {}).get('endpoint')
                    if img:
                        screen.blit(img, rect)
                    else:
                        pygame.draw.rect(screen, GRAY, rect)
                else:
                    img = getattr(self, 'assets', {}).get('ground')
                    if img:
                        screen.blit(img, rect)
                    else:
                        pygame.draw.rect(screen, WHITE, rect)

        for box_pos in boxes_pos:
            box_rect = pygame.Rect(box_pos[1] * TILE_SIZE, box_pos[0] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            on_target = self.board[box_pos[0]][box_pos[1]] == '2'
            assets = getattr(self, 'assets', {})
            
            if on_target and assets.get('box_on_target'):
                screen.blit(assets['box_on_target'], box_rect)
            elif assets.get('crate'):
                screen.blit(assets['crate'], box_rect)
            else:
                pygame.draw.rect(screen, GREEN if on_target else YELLOW, box_rect)

        player_rect = pygame.Rect(player_pos[1] * TILE_SIZE, player_pos[0] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        assets = getattr(self, 'assets', {})
        if assets.get('player'):
            player_img = assets['player']
            dest = player_img.get_rect()
            dest.center = player_rect.center
            screen.blit(player_img, dest)
        else:
            pygame.draw.circle(screen, BLUE, player_rect.center, TILE_SIZE // 2 - 5)

        pygame.display.flip()

    def load_assets(self, tile_size: int) -> dict:
        assets = {}
        base_dir = os.path.join(os.path.dirname(__file__), 'images')
        
        def load_image(filename: str, size: tuple = None) -> pygame.Surface:
            path = os.path.join(base_dir, filename)
            if not os.path.exists(path):
                return None
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.smoothscale(img, size) if size else img
            except Exception:
                return None
        
        assets['wall'] = load_image('wall.png', (tile_size, tile_size))
        assets['ground'] = load_image('space.png', (tile_size, tile_size))
        assets['crate'] = load_image('box.png', (tile_size, tile_size))
        assets['box_on_target'] = load_image('box_on_target.png', (tile_size, tile_size))
        assets['endpoint'] = load_image('target.png', (tile_size, tile_size))
        assets['player'] = load_image('player.png', (tile_size - 10, tile_size - 10))
        return assets

    def visualize_pygame(self, solution_path: str, animation_speed: float = 0.5) -> None:
        if not solution_path:
            print("No solution to visualize.")
            return

        if not pygame.get_init():
            pygame.init()

        # Create display and load assets
        screen = pygame.display.set_mode((self.width * TILE_SIZE, self.height * TILE_SIZE))
        pygame.display.set_caption('Sokoban Solver Animation')
        
        try:
            self.assets = self.load_assets(TILE_SIZE)
        except Exception:
            self.assets = {}

        current_pos = self.init_player_pos
        current_boxes = list(self.init_boxes_pos)
        step_index = 0
        clock = pygame.time.Clock()
        running = True

        self.draw_board_pygame(screen, current_pos, current_boxes)
        pygame.time.wait(int(animation_speed * 1000 * 2))

        while running and step_index < len(solution_path):
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False

            if step_index < len(solution_path):
                op = solution_path[step_index]
                dr, dc = {'R': (0, 1), 'L': (0, -1), 'D': (1, 0), 'U': (-1, 0)}.get(op, (0, 0))

                next_pos = (current_pos[0] + dr, current_pos[1] + dc)
                next_boxes = current_boxes[:]

                if next_pos in next_boxes:
                    next_box_pos = (next_pos[0] + dr, next_pos[1] + dc)
                    next_boxes[next_boxes.index(next_pos)] = next_box_pos

                current_pos = next_pos
                current_boxes = next_boxes

                self.draw_board_pygame(screen, current_pos, current_boxes)
                pygame.time.wait(int(animation_speed * 1000))
                step_index += 1
            else:
                self.draw_board_pygame(screen, current_pos, current_boxes)
                clock.tick(10)

        print("Animation complete. Window closed.")
        if pygame.get_init():
            pygame.quit()


def load_all_levels(config_file: str) -> list[tuple]:
    with open(config_file, 'r') as f:
        content = f.read().strip()
    
    levels = []
    level_blocks = content.split('[LEVEL]')
    
    for block in level_blocks:
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines:
            continue
        
        board = []
        i = 0
        while i < len(lines) and all(c in '012' for c in lines[i]):
            board.append(lines[i])
            i += 1
        
        if i < len(lines):
            player_pos = tuple(map(int, lines[i].split(',')))
            boxes_pos = [tuple(map(int, pos.split(','))) for pos in lines[i + 1].split(';')]
            levels.append((board, player_pos, boxes_pos))
    
    return levels


def load_level_config(config_file: str):
    levels = load_all_levels(config_file)
    return levels[0] if levels else ([], (0, 0), [])


if __name__ == '__main__':
    levels = load_all_levels('level/level.txt')
    current_level = 0
    
    while current_level < len(levels):
        board, player_pos, boxes_pos = levels[current_level]
        print(f"\n{'='*50}")
        print(f"Level {current_level + 1} / {len(levels)}")
        print(f"{'='*50}")
        
        solver = SokobanSolver(board, player_pos, boxes_pos)
        solution = solver.solve()
        
        if solution:
            print(f"Solution found in {solver.time_used:.3f}s")
            print(f"Moves: {solution}")
            print(f"Expanded nodes: {solver.expanded_nodes_count}")
            print(f"Visited nodes: {solver.visited_nodes_count}")
            
            solver.visualize_pygame(solution, animation_speed=0.2)
            current_level += 1
            
            if current_level < len(levels):
                print(f"\nProceeding to Level {current_level + 1}...")
            else:
                print("\nAll levels completed!")
        else:
            print("No solution found for this level.")
            retry = input("Retry this level? (y/n): ").strip().lower()
            if retry != 'y':
                break