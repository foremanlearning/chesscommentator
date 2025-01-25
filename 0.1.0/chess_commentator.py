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

    def draw_pieces(self, board):
        Logger.debug("Drawing chess pieces...")
        piece_map = board.piece_map()
        for square, piece in piece_map.items():
            row = 7 - (square // 8)
            col = square % 8
            piece_char = str(piece)
            if piece_char in self.pieces:
                self.window.blit(self.pieces[piece_char],
                               (col * self.SQUARE_SIZE, row * self.SQUARE_SIZE))
            else:
                Logger.warning(f"Missing piece image for: {piece_char}")
        
        # Draw last move arrow
        if self.last_move_from is not None and self.last_move_to is not None:
            self.draw_arrow(self.last_move_from, self.last_move_to, self.ARROW_COLOR)
        
        # Draw computer suggestion arrows for both sides
        if self.stockfish:
            # Draw White's suggestion
            if self.computer_suggestions['white']:
                move = chess.Move.from_uci(self.computer_suggestions['white']['move'])
                self.draw_arrow(move.from_square, move.to_square, self.COMPUTER_ARROW_COLOR_WHITE)
            
            # Draw Black's suggestion
            if self.computer_suggestions['black']:
                move = chess.Move.from_uci(self.computer_suggestions['black']['move'])
                self.draw_arrow(move.from_square, move.to_square, self.COMPUTER_ARROW_COLOR_BLACK)

    def draw_info_panel(self, commentary):
        Logger.debug("Drawing info panel...")
        # Draw info panel background
        pygame.draw.rect(self.window, self.BG_COLOR,
                        (self.BOARD_SIZE, 0, 300, self.WINDOW_HEIGHT))
        
        # Draw move counter
        move_text = self.large_font.render(f"Move: {self.current_move}/{self.total_moves}",
                                         True, self.TITLE_COLOR)
        self.window.blit(move_text, (self.BOARD_SIZE + 10, 10))
        
        # Draw bullet point list of current state
        y = 50
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
        
        # Add computer suggestions if available
        if self.computer_suggestions['white']:
            bullet_points.append(f"• White's best move: {self.computer_suggestions['white']['text']}")
        if self.computer_suggestions['black']:
            bullet_points.append(f"• Black's best move: {self.computer_suggestions['black']['text']}")
        
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
                               
    def analyze_position(self, board):
        if not self.stockfish:
            Logger.debug("Skipping position analysis - Stockfish not available")
            return None
            
        try:
            Logger.debug("Analyzing position...")
            self.stockfish.set_position([move.uci() for move in board.move_stack])
            
            # Get suggestions for both sides
            suggestions = {'white': None, 'black': None}
            
            # Analyze current position for the side to move
            current_analysis = self.stockfish.get_top_moves(1)
            if current_analysis:
                side_to_move = 'white' if board.turn == chess.WHITE else 'black'
                move = current_analysis[0]['Move']
                suggestions[side_to_move] = {
                    'move': move,
                    'score': current_analysis[0]['Centipawn'],
                    'text': f"{move} ({current_analysis[0]['Centipawn']/100:.1f}): "
                           f"{self.get_move_reasoning(board, chess.Move.from_uci(move))}"
                }
            
            # Make a null move to analyze from opponent's perspective
            board.push(chess.Move.null())
            self.stockfish.set_position([move.uci() for move in board.move_stack])
            opponent_analysis = self.stockfish.get_top_moves(1)
            if opponent_analysis:
                side_to_move = 'black' if board.turn == chess.WHITE else 'white'
                move = opponent_analysis[0]['Move']
                suggestions[side_to_move] = {
                    'move': move,
                    'score': opponent_analysis[0]['Centipawn'],
                    'text': f"{move} ({opponent_analysis[0]['Centipawn']/100:.1f}): "
                           f"{self.get_move_reasoning(board, chess.Move.from_uci(move))}"
                }
            board.pop()
            
            return suggestions
            
        except Exception as e:
            Logger.error(f"Error in position analysis: {e}")
            return None
        
    def get_opening_name(self, board):
        """Get the name of the opening based on the current position."""
        move_count = len(board.move_stack) // 2  # Convert half-moves to full moves
        if move_count > 15:  # Stop checking after move 15
            self.state['current_opening'] = None  # Clear opening name after move 15
            return None
            
        # Get the moves in UCI format
        moves = " ".join(move.uci() for move in board.move_stack)
        
        # Common openings and their move patterns for both White and Black
        openings = {
            # White openings
            "e2e4": {
                "name": "King's Pawn Opening",
                "responses": {
                    "e7e5": "Open Game",
                    "c7c5": "Sicilian Defense",
                    "e7e6": "French Defense",
                    "c7c6": "Caro-Kann Defense",
                    "d7d6": "Pirc Defense",
                    "g7g6": "Modern Defense",
                    "d7d5": "Scandinavian Defense"
                }
            },
            "d2d4": {
                "name": "Queen's Pawn Opening",
                "responses": {
                    "d7d5": "Queen's Pawn Game",
                    "g8f6": "Indian Defense",
                    "f7f5": "Dutch Defense",
                    "e7e6": "French Defense",
                    "d7d6 g7g6": "King's Indian Defense"
                }
            },
            "c2c4": {
                "name": "English Opening",
                "responses": {
                    "e7e5": "Reversed Sicilian",
                    "c7c5": "Symmetrical English",
                    "g8f6": "English Indian"
                }
            },
            "g1f3": {
                "name": "Réti Opening",
                "responses": {
                    "d7d5": "Réti Gambit",
                    "g8f6": "Double Réti"
                }
            }
        }
        
        # Find matching opening
        opening_name = None
        for first_move, data in openings.items():
            if moves.startswith(first_move):
                opening_name = data["name"]
                # Check for specific responses
                for response, response_name in data["responses"].items():
                    if moves.startswith(f"{first_move} {response}"):
                        opening_name = response_name
                        break
                break
        
        return opening_name

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
            
            # Basic move description (always included in audio)
            piece_name = self.piece_names.get(str(piece_moved), "Piece")
            commentary = f"{piece_name} moves from {chess.square_name(move.from_square)} "
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
            
            Logger.info("Processing moves...")
            for move in game.mainline_moves():
                if not running:
                    Logger.warning("Video creation interrupted")
                    break
                    
                self.current_move += 1
                self.status_message = f"Processing move {self.current_move}/{self.total_moves}"
                Logger.info(f"Processing move {self.current_move}/{self.total_moves}: {move}")
                
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
                commentary = self.generate_commentary(self.board, move, self.analyze_position(self.board))
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