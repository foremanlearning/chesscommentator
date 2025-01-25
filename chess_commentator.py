import chess
import chess.pgn
import pygame
import cv2
import numpy as np
import pyttsx3
from PIL import Image
import io
import os
from stockfish import Stockfish
import sys
import time
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
import requests
import shutil
from logger import Logger

class ChessCommentator:
    def __init__(self, stockfish_path=None):
        try:
            Logger.info("Initializing Chess Commentator...")
            
            # Initialize pygame
            if not pygame.get_init():
                Logger.debug("Initializing Pygame...")
                pygame.init()
            
            # Create a visible window for feedback
            self.SQUARE_SIZE = 80
            self.BOARD_SIZE = self.SQUARE_SIZE * 8
            self.WINDOW_WIDTH = self.BOARD_SIZE + 300  # Extra space for info panel
            self.WINDOW_HEIGHT = self.BOARD_SIZE + 100  # Extra space for status
            
            # Create the main window
            Logger.debug("Creating display window...")
            self.window = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
            pygame.display.set_caption("Chess Game Commentator")
            
            # Create surface for the chess board
            self.screen = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
            
            # Initialize board
            self.board = None
            
            # Colors
            self.WHITE = (240, 217, 181)  # Light brown for white squares
            self.BLACK = (181, 136, 99)   # Dark brown for black squares
            self.HIGHLIGHT = (255, 255, 0, 128)
            self.TEXT_COLOR = (220, 220, 220)  # Light gray text
            self.BG_COLOR = (49, 46, 43)  # Dark background
            self.TITLE_COLOR = (255, 255, 255)  # White for titles
            
            # Initialize font
            Logger.debug("Initializing fonts...")
            pygame.font.init()
            self.font = pygame.font.SysFont('Arial', 16)
            self.large_font = pygame.font.SysFont('Arial', 24)
            
            # Initialize TTS engine
            Logger.info("Initializing Text-to-Speech engine...")
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.9)
                Logger.success("TTS engine initialized successfully")
            except Exception as e:
                Logger.warning(f"TTS initialization failed: {e}")
                self.tts_engine = None
            
            # Initialize Stockfish if path is provided
            self.stockfish = None
            if stockfish_path:
                Logger.info(f"Initializing Stockfish engine from: {stockfish_path}")
                try:
                    self.stockfish = Stockfish(path=stockfish_path)
                    # Configure Stockfish for better analysis
                    self.stockfish.set_depth(20)  # Deeper analysis
                    self.stockfish.set_skill_level(20)  # Maximum skill level
                    self.stockfish.update_engine_parameters({
                        "Hash": 128,  # Memory in MB
                        "Threads": 4,  # Number of CPU threads
                        "MultiPV": 3,  # Show top 3 moves
                        "UCI_ShowWDL": True  # Show Win/Draw/Loss statistics
                    })
                    Logger.success("Stockfish engine initialized successfully")
                except Exception as e:
                    Logger.warning(f"Stockfish initialization failed: {e}")
            
            # Load chess pieces
            Logger.info("Loading chess pieces...")
            self.pieces = {}
            if not self.load_piece_images():
                raise Exception("Failed to load chess pieces")
            
            # Game state
            self.current_move = 0
            self.total_moves = 0
            self.status_message = "Ready to analyze game"
            self.audio_segments = []
            
            # Add arrow color
            self.ARROW_COLOR = (255, 0, 0)  # Red arrows
            self.ARROW_WIDTH = 3
            self.last_move_from = None
            self.last_move_to = None
            
            # Add state tracking
            self.state = {
                'center_control': None,  # 'white', 'black', or None
                'development': None,     # 'white', 'black', or None
                'king_safety': None,     # 'white', 'black', or None
                'last_move': None,
                'current_opening': None
            }
            
            # Add computer analysis arrow colors
            self.COMPUTER_ARROW_COLOR_WHITE = (128, 128, 128, 180)  # Semi-transparent gray for White
            self.COMPUTER_ARROW_COLOR_BLACK = (100, 100, 100, 180)  # Darker gray for Black
            self.computer_suggestions = {'white': None, 'black': None}
            
            # Add colors for evaluation indicators
            self.BLUNDER_COLOR = (255, 0, 0, 180)  # Red for blunders
            self.MISTAKE_COLOR = (255, 165, 0, 180)  # Orange for mistakes
            self.MISSED_WIN_COLOR = (148, 0, 211, 180)  # Purple for missed wins
            self.GOOD_MOVE_COLOR = (0, 255, 0, 180)  # Green for good moves
            self.CIRCLE_RADIUS = 35
            self.CIRCLE_WIDTH = 3

            # Store evaluation thresholds (in centipawns)
            self.BLUNDER_THRESHOLD = -200  # -2.00 pawns
            self.MISTAKE_THRESHOLD = -100  # -1.00 pawns
            self.MISSED_WIN_THRESHOLD = 300  # +3.00 pawns 
            self.MATE_SCORE = 10000  # Used for mate-in-X evaluations
            
            # Add piece values for material counting
            self.PIECE_VALUES = {
                chess.PAWN: 1,
                chess.KNIGHT: 3,
                chess.BISHOP: 3,
                chess.ROOK: 5,
                chess.QUEEN: 9,
                chess.KING: 0
            }
            
            # Track captured pieces
            self.captured_pieces = {
                'white': [],  # pieces captured by white
                'black': []   # pieces captured by black
            }
            
            # Track material balance history
            self.material_balance_history = []
            
            # Track notable moves and positions
            self.notable_moves = {
                'blunders': {'white': [], 'black': []},
                'mistakes': {'white': [], 'black': []},
                'good_moves': {'white': [], 'black': []},
                'missed_wins': {'white': [], 'black': []}
            }
            
            # Track player scores (0-100)
            self.player_scores = {'white': 100, 'black': 100}
            
            Logger.success("Chess Commentator initialized successfully")
            
        except Exception as e:
            Logger.error(f"Error initializing Chess Commentator: {e}")
            raise
            
    def load_piece_images(self):
        """Load chess piece images into pygame surfaces."""
        try:
            Logger.info("Loading piece images into pygame surfaces...")
            
            # Define piece mappings with clearer names
            pieces = {
                'K': 'king-w.png',
                'Q': 'queen-w.png',
                'R': 'rook-w.png',
                'B': 'bishop-w.png',
                'N': 'knight-w.png',
                'P': 'pawn-w.png',
                'k': 'king-b.png',
                'q': 'queen-b.png',
                'r': 'rook-b.png',
                'b': 'bishop-b.png',
                'n': 'knight-b.png',
                'p': 'pawn-b.png'
            }
            
            # Map piece characters to full names for commentary
            self.piece_names = {
                'K': 'King', 'Q': 'Queen', 'R': 'Rook',
                'B': 'Bishop', 'N': 'Knight', 'P': 'Pawn',
                'k': 'king', 'q': 'queen', 'r': 'rook',
                'b': 'bishop', 'n': 'knight', 'p': 'pawn'
            }
            
            for piece_char, png_file in pieces.items():
                png_path = f"pieces/{png_file}"
                try:
                    # Load PNG directly with pygame
                    surface = pygame.image.load(png_path)
                    # Scale to square size
                    surface = pygame.transform.smoothscale(surface, (self.SQUARE_SIZE, self.SQUARE_SIZE))
                    self.pieces[piece_char] = surface
                    Logger.debug(f"Successfully loaded {png_file}")
                except Exception as e:
                    Logger.error(f"Error loading {png_file}: {e}")
                    return False
            
            Logger.success("All piece images loaded successfully")
            return True
            
        except Exception as e:
            Logger.error(f"Error loading piece images: {e}")
            return False
            
    def show_error_message(self, message):
        Logger.error(f"Displaying error message: {message}")
        if pygame.get_init():
            self.window.fill(self.BG_COLOR)
            error_text = self.large_font.render(f"Error: {message}", True, (255, 0, 0))
            text_rect = error_text.get_rect(center=(self.WINDOW_WIDTH//2, self.WINDOW_HEIGHT//2))
            self.window.blit(error_text, text_rect)
            pygame.display.flip()
            
    def load_pgn(self, pgn_path):
        try:
            Logger.info(f"Loading PGN file: {pgn_path}")
            if not os.path.exists(pgn_path):
                Logger.error(f"PGN file not found: {pgn_path}")
                raise FileNotFoundError(f"PGN file not found: {pgn_path}")
                
            with open(pgn_path) as pgn_file:
                self.game = chess.pgn.read_game(pgn_file)
                if self.game is None:
                    Logger.error("No game found in PGN file")
                    raise ValueError("No game found in PGN file")
                    
                self.board = self.game.board()
                self.total_moves = sum(1 for _ in self.game.mainline_moves())
                Logger.success(f"Successfully loaded game with {self.total_moves} moves")
                return self.game
                
        except Exception as e:
            Logger.error(f"Error loading PGN file: {e}")
            self.show_error_message(f"Error loading PGN: {str(e)}")
            return None
            
    def draw_board(self):
        Logger.debug("Drawing chess board...")
        # Draw the board directly on the window, not the screen
        for row in range(8):
            for col in range(8):
                color = self.WHITE if (row + col) % 2 == 0 else self.BLACK
                pygame.draw.rect(self.window, color,
                               (col * self.SQUARE_SIZE, row * self.SQUARE_SIZE,
                                self.SQUARE_SIZE, self.SQUARE_SIZE))
                
                # Draw rank numbers (1-8) on the left side
                if col == 0:
                    rank_label = self.font.render(str(8 - row), True, 
                                                self.BLACK if (row % 2 == 0) else self.WHITE)
                    self.window.blit(rank_label, 
                                   (5, row * self.SQUARE_SIZE + 5))
                
                # Draw file letters (a-h) on the bottom
                if row == 7:
                    file_label = self.font.render(chr(97 + col), True,
                                                self.WHITE if (col % 2 == 0) else self.BLACK)
                    self.window.blit(file_label,
                                   (col * self.SQUARE_SIZE + self.SQUARE_SIZE - 20,
                                    row * self.SQUARE_SIZE + self.SQUARE_SIZE - 20))
                                
    def draw_arrow(self, start_square, end_square, color):
        """Draw an arrow from one square to another."""
        # Calculate center points of squares
        start_col, start_row = start_square % 8, 7 - (start_square // 8)
        end_col, end_row = end_square % 8, 7 - (end_square // 8)
        
        start_x = start_col * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
        start_y = start_row * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
        end_x = end_col * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
        end_y = end_row * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
        
        # Draw the arrow line
        pygame.draw.line(self.window, color, 
                        (start_x, start_y), (end_x, end_y), 
                        self.ARROW_WIDTH)
        
        # Calculate arrow head
        angle = np.arctan2(end_y - start_y, end_x - start_x)
        arrow_size = 20
        arrow_angle = np.pi / 6  # 30 degrees
        
        # Calculate arrow head points
        point1 = (end_x - arrow_size * np.cos(angle - arrow_angle),
                 end_y - arrow_size * np.sin(angle - arrow_angle))
        point2 = (end_x - arrow_size * np.cos(angle + arrow_angle),
                 end_y - arrow_size * np.sin(angle + arrow_angle))
        
        # Draw arrow head
        pygame.draw.polygon(self.window, color,
                          [(end_x, end_y), point1, point2])

    def draw_circle(self, square, color):
        """Draw a circle around a square to highlight it."""
        col = square % 8
        row = 7 - (square // 8)
        center_x = col * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
        center_y = row * self.SQUARE_SIZE + self.SQUARE_SIZE // 2
        pygame.draw.circle(self.window, color, (center_x, center_y), 
                         self.CIRCLE_RADIUS, self.CIRCLE_WIDTH)

    def draw_pieces(self, board):
        Logger.debug("Drawing chess pieces...")
        piece_map = board.piece_map()
        
        # Draw computer suggestion arrows first
        if self.stockfish and self.computer_suggestions:
            # Draw White's suggestion
            if self.computer_suggestions['white']:
                move = chess.Move.from_uci(self.computer_suggestions['white']['move'])
                score = self.computer_suggestions['white'].get('score')
                mate = self.computer_suggestions['white'].get('mate')
                
                # Convert mate score to centipawns for comparison
                if mate is not None:
                    score = self.MATE_SCORE if mate > 0 else -self.MATE_SCORE
                
                # Determine arrow color based on evaluation
                if score is not None:  # Only evaluate if we have a score
                    if score <= self.BLUNDER_THRESHOLD:
                        arrow_color = self.BLUNDER_COLOR
                        self.draw_circle(move.from_square, self.BLUNDER_COLOR)
                    elif score <= self.MISTAKE_THRESHOLD:
                        arrow_color = self.MISTAKE_COLOR
                        self.draw_circle(move.from_square, self.MISTAKE_COLOR)
                    elif score >= self.MISSED_WIN_THRESHOLD:
                        arrow_color = self.MISSED_WIN_COLOR
                        self.draw_circle(move.from_square, self.MISSED_WIN_COLOR)
                    else:
                        arrow_color = self.COMPUTER_ARROW_COLOR_WHITE
                else:
                    arrow_color = self.COMPUTER_ARROW_COLOR_WHITE
                
                if (move.from_square != self.last_move_from or 
                    move.to_square != self.last_move_to):
                    self.draw_arrow(move.from_square, move.to_square, arrow_color)
            
            # Draw Black's suggestion similarly
            if self.computer_suggestions['black']:
                move = chess.Move.from_uci(self.computer_suggestions['black']['move'])
                score = self.computer_suggestions['black'].get('score')
                mate = self.computer_suggestions['black'].get('mate')
                
                # Convert mate score to centipawns for comparison
                if mate is not None:
                    score = self.MATE_SCORE if mate > 0 else -self.MATE_SCORE
                
                # Determine arrow color based on evaluation
                if score is not None:  # Only evaluate if we have a score
                    if score <= self.BLUNDER_THRESHOLD:
                        arrow_color = self.BLUNDER_COLOR
                        self.draw_circle(move.from_square, self.BLUNDER_COLOR)
                    elif score <= self.MISTAKE_THRESHOLD:
                        arrow_color = self.MISTAKE_COLOR
                        self.draw_circle(move.from_square, self.MISTAKE_COLOR)
                    elif score >= self.MISSED_WIN_THRESHOLD:
                        arrow_color = self.MISSED_WIN_COLOR
                        self.draw_circle(move.from_square, self.MISSED_WIN_COLOR)
                    else:
                        arrow_color = self.COMPUTER_ARROW_COLOR_BLACK
                else:
                    arrow_color = self.COMPUTER_ARROW_COLOR_BLACK
                
                if (move.from_square != self.last_move_from or 
                    move.to_square != self.last_move_to):
                    self.draw_arrow(move.from_square, move.to_square, arrow_color)
        
        # Draw pieces
        for square, piece in piece_map.items():
            row = 7 - (square // 8)
            col = square % 8
            piece_char = str(piece)
            if piece_char in self.pieces:
                self.window.blit(self.pieces[piece_char],
                               (col * self.SQUARE_SIZE, row * self.SQUARE_SIZE))
            else:
                Logger.warning(f"Missing piece image for: {piece_char}")
        
        # Draw last move arrow on top
        if self.last_move_from is not None and self.last_move_to is not None:
            self.draw_arrow(self.last_move_from, self.last_move_to, self.ARROW_COLOR)

    def draw_info_panel(self, commentary):
        Logger.debug("Drawing info panel...")
        # Draw info panel background
        pygame.draw.rect(self.window, self.BG_COLOR,
                        (self.BOARD_SIZE, 0, 300, self.WINDOW_HEIGHT))
        
        # Draw move counter
        move_text = self.large_font.render(f"Move: {self.current_move}/{self.total_moves}",
                                         True, self.TITLE_COLOR)
        self.window.blit(move_text, (self.BOARD_SIZE + 10, 10))
        
        # Add legend for colored circles
        y = 50
        legend_title = self.font.render("Event Indicators:", True, self.TITLE_COLOR)
        self.window.blit(legend_title, (self.BOARD_SIZE + 10, y))
        y += 25
        
        # Blunder explanation
        blunder_text = self.font.render("⭕ Blunder (eval drops >2.00)", True, self.BLUNDER_COLOR)
        self.window.blit(blunder_text, (self.BOARD_SIZE + 10, y))
        y += 25
        
        # Mistake explanation
        mistake_text = self.font.render("⭕ Mistake (eval drops >1.00)", True, self.MISTAKE_COLOR)
        self.window.blit(mistake_text, (self.BOARD_SIZE + 10, y))
        y += 25
        
        # Missed win explanation
        missed_win_text = self.font.render("⭕ Missed Win (eval >3.00)", True, self.MISSED_WIN_COLOR)
        self.window.blit(missed_win_text, (self.BOARD_SIZE + 10, y))
        y += 25
        
        # Good move explanation
        good_move_text = self.font.render("⭕ Good Move", True, self.GOOD_MOVE_COLOR)
        self.window.blit(good_move_text, (self.BOARD_SIZE + 10, y))
        y += 35

        # Draw bullet point list of current state
        bullet_points = []
        
        # Add current opening if available and within first 15 moves
        move_count = len(self.board.move_stack) // 2  # Convert half-moves to full moves
        if self.state['current_opening'] and move_count <= 15:
            bullet_points.append(f"• Opening: {self.state['current_opening']}")
        
        # Add center control
        if self.state['center_control'] == 'white':
            bullet_points.append("• White controls the center")
        elif self.state['center_control'] == 'black':
            bullet_points.append("• Black controls the center")
        
        # Add development
        if self.state['development'] == 'white':
            bullet_points.append("• White has better development")
        elif self.state['development'] == 'black':
            bullet_points.append("• Black has better development")
        
        # Add king safety
        if self.state['king_safety'] == 'white':
            bullet_points.append("• White has better king safety")
        elif self.state['king_safety'] == 'black':
            bullet_points.append("• Black has better king safety")
        
        # Add computer suggestions with detailed reasoning
        if self.computer_suggestions['white']:
            move = self.computer_suggestions['white']['move']
            text = self.computer_suggestions['white']['text']
            bullet_points.append(f"• Recommended for White: {move} - {text}")
            
            # Add reasoning
            if 'reasoning' in self.computer_suggestions['white']:
                bullet_points.append(f"  ↳ Reasoning: {self.computer_suggestions['white']['reasoning']}")
            
            # Add consequences
            if 'consequences' in self.computer_suggestions['white']:
                for consequence in self.computer_suggestions['white']['consequences']:
                    bullet_points.append(f"  ↳ {consequence}")
            
            # Add alternative moves
            if 'alternatives' in self.computer_suggestions['white']:
                for alt in self.computer_suggestions['white']['alternatives']:
                    eval_text = f"Mate in {alt['mate']}" if alt['mate'] else f"{alt['score']/100:.1f}"
                    bullet_points.append(f"  ↳ Alternative: {alt['move']} ({eval_text})")
                    if 'reasoning' in alt:
                        bullet_points.append(f"    • {alt['reasoning']}")
                    if 'consequences' in alt:
                        for consequence in alt['consequences']:
                            bullet_points.append(f"    • {consequence}")
        
        if self.computer_suggestions['black']:
            move = self.computer_suggestions['black']['move']
            text = self.computer_suggestions['black']['text']
            bullet_points.append(f"• Recommended for Black: {move} - {text}")
            
            # Add reasoning
            if 'reasoning' in self.computer_suggestions['black']:
                bullet_points.append(f"  ↳ Reasoning: {self.computer_suggestions['black']['reasoning']}")
            
            # Add consequences
            if 'consequences' in self.computer_suggestions['black']:
                for consequence in self.computer_suggestions['black']['consequences']:
                    bullet_points.append(f"  ↳ {consequence}")
            
            # Add alternative moves
            if 'alternatives' in self.computer_suggestions['black']:
                for alt in self.computer_suggestions['black']['alternatives']:
                    eval_text = f"Mate in {alt['mate']}" if alt['mate'] else f"{alt['score']/100:.1f}"
                    bullet_points.append(f"  ↳ Alternative: {alt['move']} ({eval_text})")
                    if 'reasoning' in alt:
                        bullet_points.append(f"    • {alt['reasoning']}")
                    if 'consequences' in alt:
                        for consequence in alt['consequences']:
                            bullet_points.append(f"    • {consequence}")
        
        # Draw all bullet points
        for point in bullet_points:
            text = self.font.render(point, True, self.TEXT_COLOR)
            self.window.blit(text, (self.BOARD_SIZE + 10, y))
            y += 25
        
        # Draw commentary below bullet points
        if commentary:
            y += 10  # Add some space
            words = commentary.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                text = ' '.join(current_line)
                if self.font.size(text)[0] > 280:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            for line in lines:
                text = self.font.render(line, True, self.TEXT_COLOR)
                self.window.blit(text, (self.BOARD_SIZE + 10, y))
                y += 25
        
        # Draw separator line
        pygame.draw.line(self.window, self.TEXT_COLOR,
                        (self.BOARD_SIZE, 0),
                        (self.BOARD_SIZE, self.WINDOW_HEIGHT),
                        2)
        
        # Draw material balance bar
        balance = self.calculate_material_balance(self.board)
        self.draw_material_bar(balance)
        
        # Draw captured pieces
        self.draw_captured_pieces()
        
        # Update display
        pygame.display.flip()
                               
    def analyze_position(self, board):
        """Get computer recommendations for the current position."""
        if not self.stockfish:
            Logger.debug("Skipping position analysis - Stockfish not available")
            return None
            
        try:
            Logger.debug("Analyzing position...")
            
            # Set position in Stockfish
            fen = board.fen()
            self.stockfish.set_fen_position(fen)
            
            # Get suggestions for both sides
            suggestions = {'white': None, 'black': None}
            
            # Get current side's best moves
            current_analysis = self.stockfish.get_top_moves(3)  # Get top 3 moves
            if current_analysis:
                side_to_move = 'white' if board.turn == chess.WHITE else 'black'
                best_move = current_analysis[0]
                move_uci = best_move['Move']
                move = chess.Move.from_uci(move_uci)
                
                # Get evaluation
                eval_score = best_move.get('Centipawn')
                mate_in = best_move.get('Mate')
                
                # Format evaluation text
                if mate_in is not None:
                    eval_text = f"Mate in {mate_in}"
                else:
                    eval_text = f"{eval_score/100:.1f}" if eval_score is not None else "?"
                
                # Get move reasoning and consequences
                reasoning = self.get_move_reasoning(board, move)
                consequences = self.analyze_move_consequences(board, move)
                
                suggestions[side_to_move] = {
                    'move': move_uci,
                    'score': eval_score,
                    'mate': mate_in,
                    'text': f"Best move: {move_uci} ({eval_text})",
                    'reasoning': reasoning,
                    'consequences': consequences,
                    'alternatives': [
                        {
                            'move': m['Move'],
                            'score': m.get('Centipawn'),
                            'mate': m.get('Mate'),
                            'reasoning': self.get_move_reasoning(board, chess.Move.from_uci(m['Move'])),
                            'consequences': self.analyze_move_consequences(board, chess.Move.from_uci(m['Move']))
                        } for m in current_analysis[1:3]  # Get next 2 best moves
                    ]
                }
            
            Logger.debug(f"Analysis complete: {suggestions}")
            return suggestions
            
        except Exception as e:
            Logger.error(f"Error in position analysis: {e}")
            return None
        
    def get_opening_name(self, board):
        """Get the name of the opening based on the current position using Stockfish."""
        move_count = len(board.move_stack) // 2  # Convert half-moves to full moves
        if move_count > 15:  # Stop checking after move 15
            self.state['current_opening'] = None  # Clear opening name after move 15
            return None
            
        if not self.stockfish:
            return None
            
        try:
            # Set position in Stockfish
            fen = board.fen()
            self.stockfish.set_fen_position(fen)
            
            # Get book moves and evaluation
            book_moves = self.stockfish.get_top_moves(5)  # Get top 5 book moves
            if not book_moves:
                return None
                
            # Get current move sequence
            moves = [move.uci() for move in board.move_stack]
            moves_str = " ".join(moves)
            
            # Common openings and their move patterns
            openings = {
                # Main lines
                "e2e4 e7e5": {
                    "name": "Open Game",
                    "variations": {
                        "g1f3 b8c6 f1b5": "Ruy Lopez",
                        "g1f3 b8c6 f1c4": "Italian Game",
                        "g1f3 b8c6 d2d4": "Scotch Game",
                        "f2f4": "King's Gambit",
                        "d2d4 e5d4": "Center Game"
                    }
                },
                "e2e4 c7c5": {
                    "name": "Sicilian Defense",
                    "variations": {
                        "g1f3 d7d6": "Sicilian Najdorf",
                        "g1f3 b8c6": "Sicilian Open",
                        "b1c3": "Sicilian Closed",
                        "c2c3": "Sicilian Alapin"
                    }
                },
                "e2e4 e7e6": {
                    "name": "French Defense",
                    "variations": {
                        "d2d4 d7d5": "French Main Line",
                        "d2d4 d7d5 e4e5": "French Advance",
                        "d2d4 d7d5 e4d5": "French Exchange"
                    }
                },
                "d2d4 d7d5": {
                    "name": "Queen's Pawn Game",
                    "variations": {
                        "c2c4": "Queen's Gambit",
                        "c2c4 d5c4": "Queen's Gambit Accepted",
                        "c2c4 e7e6": "Queen's Gambit Declined",
                        "g1f3 g8f6 c2c4": "Queen's Gambit Orthodox"
                    }
                },
                "d2d4 g8f6": {
                    "name": "Indian Defense",
                    "variations": {
                        "c2c4 e7e6 g1f3": "Nimzo-Indian Defense",
                        "c2c4 g7g6": "King's Indian Defense",
                        "c2c4 e7e6 g1f3 b7b6": "Queen's Indian Defense"
                    }
                }
            }
            
            # Find matching opening
            opening_name = None
            variation_name = None
            
            for pattern, data in openings.items():
                if moves_str.startswith(pattern):
                    opening_name = data["name"]
                    # Check for variations
                    for var_pattern, var_name in data.get("variations", {}).items():
                        if moves_str.startswith(pattern + " " + var_pattern):
                            variation_name = var_name
                            break
                    break
            
            if variation_name:
                return variation_name
            return opening_name
            
        except Exception as e:
            Logger.error(f"Error getting opening name: {e}")
            return None

    def analyze_position_strength(self, board, move):
        """Analyze the strength of a position and move."""
        # Center control
        center_squares = {chess.E4, chess.E5, chess.D4, chess.D5}
        center_control = 0
        for square in center_squares:
            if board.is_attacked_by(chess.WHITE, square):
                center_control += 1
            if board.is_attacked_by(chess.BLACK, square):
                center_control -= 1
        
        # Development
        developed_pieces = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                # Count developed minor pieces
                if piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
                    if piece.color == chess.WHITE and square > chess.H2:
                        developed_pieces += 1
                    elif piece.color == chess.BLACK and square < chess.H7:
                        developed_pieces -= 1
        
        # King safety (based on castling rights instead of castled status)
        king_safety = 0
        if board.has_kingside_castling_rights(chess.WHITE) or board.has_queenside_castling_rights(chess.WHITE):
            king_safety += 1
        if board.has_kingside_castling_rights(chess.BLACK) or board.has_queenside_castling_rights(chess.BLACK):
            king_safety -= 1
        
        return center_control, developed_pieces, king_safety

    def suggest_next_moves(self, board):
        """Suggest legal moves based on the current position."""
        suggestions = []
        
        # Only suggest castling if it's actually legal this turn
        if board.turn == chess.WHITE:
            if chess.Move.from_uci('e1g1') in board.legal_moves:
                suggestions.append("Kingside castling is available")
            if chess.Move.from_uci('e1c1') in board.legal_moves:
                suggestions.append("Queenside castling is available")
        else:
            if chess.Move.from_uci('e8g8') in board.legal_moves:
                suggestions.append("Kingside castling is available")
            if chess.Move.from_uci('e8c8') in board.legal_moves:
                suggestions.append("Queenside castling is available")
        
        # Check for tactical opportunities
        for move in board.legal_moves:
            # Check for captures
            if board.is_capture(move):
                captured_piece = board.piece_at(move.to_square)
                if captured_piece:
                    attacker = board.piece_at(move.from_square)
                    if captured_piece.piece_type >= attacker.piece_type:
                        suggestions.append(f"Can capture {self.piece_names[str(captured_piece).lower()]} on {chess.square_name(move.to_square)}")
            
            # Check for checks
            board.push(move)
            if board.is_check():
                suggestions.append(f"Check available with {self.piece_names[str(board.piece_at(move.to_square))]} to {chess.square_name(move.to_square)}")
            board.pop()
            
            if len(suggestions) >= 2:  # Limit to 2 tactical suggestions
                break
        
        return suggestions

    def identify_checkmate_pattern(self, board, move):
        """Identify common checkmate patterns."""
        if not board.is_checkmate():
            return None
            
        # Get the pieces involved in the checkmate
        attacking_pieces = []
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == board.turn:
                if board.is_attacked_by(board.turn, square):
                    attacking_pieces.append(piece.piece_type)
        
        # Sort pieces for consistent pattern matching
        attacking_pieces.sort()
        
        # Define checkmate patterns
        patterns = {
            # Basic mates
            (chess.QUEEN,): "Queen Checkmate",
            (chess.ROOK,): "Rook Checkmate",
            (chess.ROOK, chess.ROOK): "Two-Rook Checkmate",
            (chess.BISHOP, chess.BISHOP): "Two-Bishop Checkmate",
            (chess.BISHOP, chess.KNIGHT): "Bishop and Knight Checkmate",
            
            # Special patterns
            "Fool's Mate": lambda: len(board.move_stack) <= 4 and 
                          str(move) in ['f2f4', 'g2g4'] and 
                          board.is_checkmate(),
            
            "Scholar's Mate": lambda: len(board.move_stack) <= 8 and 
                            any(str(m) in ['f1c4', 'd1h5', 'd1f3'] for m in board.move_stack) and 
                            board.is_checkmate(),
            
            "Back Rank Mate": lambda: board.piece_at(move.to_square).piece_type in [chess.QUEEN, chess.ROOK] and 
                             move.to_square in [chess.H1, chess.H8] and 
                             board.is_checkmate(),
            
            "Smothered Mate": lambda: board.piece_at(move.to_square).piece_type == chess.KNIGHT and 
                             board.is_checkmate() and 
                             all(board.piece_at(sq) for sq in board.attacks(move.to_square)),
            
            "Arabian Mate": lambda: board.piece_at(move.to_square).piece_type == chess.KNIGHT and 
                          board.is_checkmate() and 
                          any(board.piece_at(sq) and board.piece_at(sq).piece_type == chess.ROOK 
                              for sq in board.attacks(board.king(not board.turn)))
        }
        
        # Check special patterns first
        for pattern_name, check_pattern in patterns.items():
            if isinstance(check_pattern, type(lambda: None)):
                if check_pattern():
                    return pattern_name
        
        # Check basic piece combination patterns
        attacking_pieces = tuple(attacking_pieces)
        if attacking_pieces in patterns:
            return patterns[attacking_pieces]
        
        return "Checkmate"  # Default if no specific pattern is identified

    def generate_commentary(self, board, move, analysis):
        try:
            Logger.debug(f"Generating commentary for move: {move}")
            piece_moved = board.piece_at(move.from_square)
            is_capture = board.is_capture(move)
            
            # Before making the move
            self.update_captured_pieces(board, move)
            
            # Basic move description (always included in audio)
            piece_name = self.piece_names.get(str(piece_moved), "Piece")
            side_color = "White" if piece_moved.color == chess.WHITE else "Black"
            commentary = f"{side_color} {piece_name.lower()} moves from {chess.square_name(move.from_square)} "
            commentary += f"to {chess.square_name(move.to_square)}"
            
            # Store move squares for arrow drawing
            self.last_move_from = move.from_square
            self.last_move_to = move.to_square
            
            # Add capture details (always included in audio)
            if is_capture:
                captured_piece = board.piece_at(move.to_square)
                if captured_piece:
                    commentary += f" capturing the {self.piece_names[str(captured_piece).lower()]}"
            
            # Make the move to analyze the resulting position
            board.push(move)
            
            # Get opening name
            opening_name = self.get_opening_name(board)
            if opening_name != self.state['current_opening']:
                self.state['current_opening'] = opening_name
                if opening_name:
                    commentary += f". This is a {opening_name}"
            
            # Analyze position strength
            center_control, development, king_safety = self.analyze_position_strength(board, move)
            
            # Update state and add to commentary only if changed
            new_center = 'white' if center_control > 1 else 'black' if center_control < -1 else None
            if new_center != self.state['center_control']:
                self.state['center_control'] = new_center
                if new_center == 'white':
                    commentary += ". White now controls the center"
                elif new_center == 'black':
                    commentary += ". Black now controls the center"
            
            new_development = 'white' if development > 1 else 'black' if development < -1 else None
            if new_development != self.state['development']:
                self.state['development'] = new_development
                if new_development == 'white':
                    commentary += ". White now has better piece development"
                elif new_development == 'black':
                    commentary += ". Black now has better piece development"
            
            # Check for game end conditions (always included in audio)
            if board.is_checkmate():
                winner = "White" if not board.turn else "Black"
                checkmate_pattern = self.identify_checkmate_pattern(board, move)
                if checkmate_pattern:
                    commentary += f". Checkmate! {winner} wins with a {checkmate_pattern}!"
                else:
                    commentary += f". Checkmate! {winner} wins!"
            elif board.is_stalemate():
                commentary += ". The game is a draw by stalemate"
            elif board.is_insufficient_material():
                commentary += ". The game is a draw due to insufficient material"
            elif board.is_check():
                commentary += ", putting the king in check"
            elif self.current_move == self.total_moves:
                winner = "Black" if board.turn == chess.WHITE else "White"
                commentary += f". {winner} wins by resignation"
            
            # Add computer analysis (only shown on screen)
            if analysis:
                self.computer_suggestions = analysis
            
            # Undo the move for further analysis
            board.pop()
            
            return commentary
            
        except Exception as e:
            Logger.error(f"Error generating commentary: {e}")
            return "Move made."

    def get_move_reasoning(self, board, move):
        """Generate reasoning for why a move is good."""
        reasons = []
        
        # Check if move captures a piece
        if board.is_capture(move):
            captured_piece = board.piece_at(move.to_square)
            if captured_piece:
                reasons.append(f"captures {self.piece_names[str(captured_piece).lower()]}")
        
        # Check if move gives check
        board.push(move)
        if board.is_check():
            reasons.append("gives check")
        
        # Check if move controls center
        center_squares = {chess.E4, chess.E5, chess.D4, chess.D5}
        if move.to_square in center_squares:
            reasons.append("controls center")
        
        # Check if move develops a piece
        piece = board.piece_at(move.to_square)
        if piece and piece.piece_type in [chess.KNIGHT, chess.BISHOP]:
            if piece.color == chess.WHITE and move.to_square > chess.H2:
                reasons.append("develops piece")
            elif piece.color == chess.BLACK and move.to_square < chess.H7:
                reasons.append("develops piece")
        
        board.pop()
        
        return ", ".join(reasons) if reasons else "improves position"

    def analyze_move_consequences(self, board, move):
        """Analyze what a move achieves or prevents."""
        consequences = []
        
        # Make the move on a copy of the board
        board_copy = board.copy()
        board_copy.push(move)
        
        # Check for immediate tactical consequences
        if board_copy.is_check():
            consequences.append("Gives check")
        if board_copy.is_checkmate():
            consequences.append("Checkmate!")
        if board_copy.is_stalemate():
            consequences.append("Forces stalemate")
            
        # Check for piece safety
        piece_moved = board.piece_at(move.from_square)
        if piece_moved:
            # Is the piece protected after the move?
            if board_copy.is_attacked_by(piece_moved.color, move.to_square):
                consequences.append("Piece remains protected")
            # Is it under attack?
            if board_copy.is_attacked_by(not piece_moved.color, move.to_square):
                consequences.append("Piece will be under attack")
                
        # Check for control of key squares
        center_squares = {chess.E4, chess.E5, chess.D4, chess.D5}
        if move.to_square in center_squares:
            consequences.append("Controls central square")
            
        # Check for piece coordination
        attacks = board_copy.attacks(move.to_square)
        if len(list(attacks)) > 2:
            consequences.append("Improves piece coordination")
            
        # Check for pawn structure impact
        if piece_moved and piece_moved.piece_type == chess.PAWN:
            if move.to_square >= 56 or move.to_square <= 7:  # Promotion
                consequences.append("Leads to pawn promotion")
            elif not any(board_copy.piece_at(sq) and 
                       board_copy.piece_at(sq).piece_type == chess.PAWN and
                       board_copy.piece_at(sq).color == piece_moved.color
                       for sq in board_copy.attacks(move.to_square)):
                consequences.append("Creates isolated pawn")
                
        return consequences

    def create_video(self, pgn_path, output_path, min_delay_seconds=3):
        game = self.load_pgn(pgn_path)
        if not game:
            return False
            
        try:
            Logger.info("Starting video creation...")
            self.board = game.board()  # Store the board as class attribute
            fps = 30
            temp_video_path = "output/temp_video.mp4"
            
            # Create video writer for the full window size
            Logger.debug("Initializing video writer...")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video = cv2.VideoWriter(temp_video_path, fourcc, fps, 
                                  (self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
            
            self.current_move = 0
            self.audio_segments = []
            current_time = 0
            
            clock = pygame.time.Clock()
            running = True
            
            # Reset player scores and notable moves
            self.player_scores = {'white': 100, 'black': 100}
            self.notable_moves = {
                'blunders': {'white': [], 'black': []},
                'mistakes': {'white': [], 'black': []},
                'good_moves': {'white': [], 'black': []},
                'missed_wins': {'white': [], 'black': []}
            }
            
            Logger.info("Processing moves...")
            for move in game.mainline_moves():
                if not running:
                    Logger.warning("Video creation interrupted")
                    break
                    
                self.current_move += 1
                self.status_message = f"Processing move {self.current_move}/{self.total_moves}"
                Logger.info(f"Processing move {self.current_move}/{self.total_moves}: {move}")
                
                # Get computer recommendations BEFORE the move is made
                if self.stockfish:
                    Logger.debug("Getting computer recommendations...")
                    analysis = self.analyze_position(self.board)
                    self.computer_suggestions = analysis
                    
                    # Analyze move quality
                    if analysis:
                        side = 'white' if self.board.turn == chess.WHITE else 'black'
                        if side in analysis and 'score' in analysis[side]:
                            score = analysis[side]['score']
                            if score is not None:
                                # Store notable moves
                                if score <= self.BLUNDER_THRESHOLD:
                                    self.notable_moves['blunders'][side].append({
                                        'move': str(move),
                                        'evaluation': score/100
                                    })
                                    self.player_scores[side] = max(0, self.player_scores[side] - 20)
                                elif score <= self.MISTAKE_THRESHOLD:
                                    self.notable_moves['mistakes'][side].append({
                                        'move': str(move),
                                        'evaluation': score/100
                                    })
                                    self.player_scores[side] = max(0, self.player_scores[side] - 10)
                                elif score >= self.MISSED_WIN_THRESHOLD:
                                    self.notable_moves['missed_wins'][side].append({
                                        'move': str(move),
                                        'evaluation': score/100
                                    })
                                else:
                                    self.notable_moves['good_moves'][side].append({
                                        'move': str(move),
                                        'evaluation': score/100
                                    })
                                    self.player_scores[side] = min(100, self.player_scores[side] + 5)
                    
                    # Draw the current position with recommendations
                    self.window.fill(self.BG_COLOR)
                    self.draw_board()
                    self.draw_pieces(self.board)
                    self.draw_info_panel("Computer analyzing position...")
                    pygame.display.flip()
                    
                    # Add a short delay to show recommendations
                    frames_for_analysis = int(1 * fps)  # 1 second to show recommendations
                    window_string = pygame.image.tostring(self.window, 'RGB')
                    frame = np.frombuffer(window_string, dtype=np.uint8)
                    frame = frame.reshape((self.WINDOW_HEIGHT, self.WINDOW_WIDTH, 3))
                    for _ in range(frames_for_analysis):
                        video.write(frame)
                    current_time += 1
                
                # Handle pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        Logger.warning("User closed the window")
                        running = False
                        break
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            Logger.warning("User pressed ESC")
                            running = False
                            break
                
                # Generate commentary and save audio
                commentary = self.generate_commentary(self.board, move, self.computer_suggestions)
                audio_file = f"temp_audio_{self.current_move}.mp3"
                
                # Get audio duration
                audio_duration = min_delay_seconds  # Default minimum duration
                if self.tts_engine:
                    try:
                        Logger.debug(f"Generating audio for move {self.current_move}")
                        self.tts_engine.save_to_file(commentary, audio_file)
                        self.tts_engine.runAndWait()
                        # Get actual audio duration
                        temp_audio = AudioFileClip(audio_file)
                        audio_duration = max(min_delay_seconds, temp_audio.duration + 0.5)  # Add 0.5s buffer
                        temp_audio.close()
                        self.audio_segments.append((audio_file, current_time))
                    except Exception as e:
                        Logger.error(f"TTS error: {e}")
                
                # Make the move
                self.board.push(move)
                
                # Clear the window
                self.window.fill(self.BG_COLOR)
                
                # Draw board and pieces
                self.draw_board()
                self.draw_pieces(self.board)
                
                # Draw info panel
                self.draw_info_panel(commentary)
                
                # Update the display
                pygame.display.flip()
                
                # Convert pygame window to video frame
                window_string = pygame.image.tostring(self.window, 'RGB')
                frame = np.frombuffer(window_string, dtype=np.uint8)
                frame = frame.reshape((self.WINDOW_HEIGHT, self.WINDOW_WIDTH, 3))
                
                # Write frames based on audio duration
                frames_per_position = int(audio_duration * fps)
                Logger.debug(f"Writing {frames_per_position} frames for move {self.current_move} (duration: {audio_duration:.2f}s)")
                for _ in range(frames_per_position):
                    video.write(frame)
                
                current_time += audio_duration
                clock.tick(60)
                
            video.release()
            Logger.success("Base video creation completed")
            
            # Combine video with audio
            if self.audio_segments:
                Logger.info("Combining video with audio...")
                video_clip = VideoFileClip(temp_video_path)
                audio_clips = []
                
                for audio_file, start_time in self.audio_segments:
                    if os.path.exists(audio_file):
                        Logger.debug(f"Processing audio segment: {audio_file}")
                        try:
                            audio_clip = AudioFileClip(audio_file)
                            audio_clips.append(audio_clip.set_start(start_time))
                            os.remove(audio_file)
                        except Exception as e:
                            Logger.warning(f"Failed to process audio clip {audio_file}: {e}")
                
                if audio_clips:
                    try:
                        Logger.debug("Creating final video with audio...")
                        # Combine all audio clips
                        from moviepy.audio.AudioClip import CompositeAudioClip
                        final_audio = CompositeAudioClip(audio_clips)
                        # Set the audio to the video
                        final_video = video_clip.set_audio(final_audio)
                        # Write the final video
                        final_video.write_videofile(output_path, audio_codec='aac')
                        # Close all clips
                        final_audio.close()
                        for clip in audio_clips:
                            clip.close()
                    except Exception as e:
                        Logger.error(f"Error combining audio: {e}")
                        # If audio fails, just save the video without audio
                        Logger.warning("Saving video without audio due to error")
                        video_clip.write_videofile(output_path)
                
                video_clip.close()
            
            # Clean up temporary video
            if os.path.exists(temp_video_path):
                Logger.debug("Removing temporary video file")
                os.remove(temp_video_path)
            
            self.status_message = "Video creation completed"
            Logger.success(f"Video creation completed: {output_path}")
            return True
            
        except Exception as e:
            Logger.error(f"Error creating video: {e}")
            self.show_error_message(f"Error creating video: {str(e)}")
            return False
        
    def cleanup(self):
        try:
            Logger.info("Starting cleanup...")
            if self.tts_engine:
                Logger.debug("Stopping TTS engine")
                self.tts_engine.stop()
            if os.path.exists('temp_audio.mp3'):
                Logger.debug("Removing temporary audio file")
                os.remove('temp_audio.mp3')
            Logger.debug("Quitting pygame")
            pygame.quit()
            Logger.success("Cleanup completed")
        except Exception as e:
            Logger.error(f"Error during cleanup: {e}")

    def calculate_material_balance(self, board):
        """Calculate the material balance of the position."""
        balance = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = self.PIECE_VALUES[piece.piece_type]
                if piece.color == chess.WHITE:
                    balance += value
                else:
                    balance -= value
        return balance

    def draw_material_bar(self, balance):
        """Draw a bar graph showing the balance of power."""
        bar_width = 200
        bar_height = 20
        x = self.BOARD_SIZE + 50
        y = self.WINDOW_HEIGHT - 150
        
        # Draw background
        pygame.draw.rect(self.window, (50, 50, 50),
                        (x, y, bar_width, bar_height))
        
        # Calculate bar position and width
        max_advantage = 15  # maximum material advantage to show
        center_x = x + bar_width // 2
        advantage_width = min(abs(balance) / max_advantage * (bar_width // 2), bar_width // 2)
        
        if balance > 0:  # White advantage
            pygame.draw.rect(self.window, (220, 220, 220),
                           (center_x, y, advantage_width, bar_height))
        else:  # Black advantage
            pygame.draw.rect(self.window, (50, 50, 50),
                           (center_x - advantage_width, y, advantage_width, bar_height))
        
        # Draw center line
        pygame.draw.line(self.window, (128, 128, 128),
                        (center_x, y), (center_x, y + bar_height), 2)
        
        # Draw advantage text
        advantage_text = f"{abs(balance):+.1f} {'White' if balance > 0 else 'Black'}"
        text = self.font.render(advantage_text, True, self.TEXT_COLOR)
        self.window.blit(text, (x + bar_width + 10, y))

    def draw_captured_pieces(self):
        """Draw the captured pieces for each side."""
        x = self.BOARD_SIZE + 50
        y_white = self.WINDOW_HEIGHT - 100
        y_black = self.WINDOW_HEIGHT - 50
        
        # Draw headers
        white_text = self.font.render("White captures:", True, self.TEXT_COLOR)
        black_text = self.font.render("Black captures:", True, self.TEXT_COLOR)
        self.window.blit(white_text, (x, y_white - 20))
        self.window.blit(black_text, (x, y_black - 20))
        
        # Draw captured pieces
        spacing = 30
        for i, piece in enumerate(self.captured_pieces['white']):
            if str(piece) in self.pieces:
                piece_surface = pygame.transform.scale(self.pieces[str(piece)], (25, 25))
                self.window.blit(piece_surface, (x + i * spacing, y_white))
                
        for i, piece in enumerate(self.captured_pieces['black']):
            if str(piece) in self.pieces:
                piece_surface = pygame.transform.scale(self.pieces[str(piece)], (25, 25))
                self.window.blit(piece_surface, (x + i * spacing, y_black))

    def update_captured_pieces(self, board, move):
        """Update the list of captured pieces after a move."""
        if board.is_capture(move):
            captured_piece = board.piece_at(move.to_square)
            if captured_piece:
                if captured_piece.color == chess.WHITE:
                    self.captured_pieces['black'].append(captured_piece)
                else:
                    self.captured_pieces['white'].append(captured_piece) 