import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import chess
import chess.pgn
import pygame
import numpy as np
from PIL import Image as PILImage
import io

class GameReport:
    def __init__(self, commentator):
        self.commentator = commentator
        self.styles = getSampleStyleSheet()
        self.doc = None
        self.story = []
        
        # Create custom styles
        self.styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        ))
        self.styles.add(ParagraphStyle(
            name='MoveHeader',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=12
        ))
        
    def capture_position(self):
        """Capture the current board position as an image."""
        # Convert pygame surface to PIL Image
        string_image = pygame.image.tostring(self.commentator.window, 'RGB')
        pil_image = PILImage.frombytes('RGB', 
                                      (self.commentator.WINDOW_WIDTH, 
                                       self.commentator.WINDOW_HEIGHT), 
                                      string_image)
        
        # Save to bytes buffer
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
        
    def add_move_analysis(self, move_number, position_image, move, analysis):
        """Add analysis of a single move to the report."""
        # Move header
        self.story.append(Paragraph(f"Move {move_number}: {move}", self.styles['MoveHeader']))
        
        # Add position image
        img = Image(position_image, width=6*inch, height=4*inch)
        self.story.append(img)
        self.story.append(Spacer(1, 12))
        
        # Add computer analysis
        if analysis:
            # Best move analysis
            if 'text' in analysis:
                self.story.append(Paragraph(f"Computer Analysis:", self.styles['Heading3']))
                self.story.append(Paragraph(analysis['text'], self.styles['Normal']))
            
            # Reasoning
            if 'reasoning' in analysis:
                self.story.append(Paragraph(f"Reasoning:", self.styles['Heading3']))
                self.story.append(Paragraph(analysis['reasoning'], self.styles['Normal']))
            
            # Consequences
            if 'consequences' in analysis:
                self.story.append(Paragraph(f"Expected Consequences:", self.styles['Heading3']))
                for consequence in analysis['consequences']:
                    self.story.append(Paragraph(f"• {consequence}", self.styles['Normal']))
            
            # Alternative moves
            if 'alternatives' in analysis:
                self.story.append(Paragraph(f"Alternative Moves:", self.styles['Heading3']))
                for alt in analysis['alternatives']:
                    move_text = f"• {alt['move']}"
                    if 'score' in alt:
                        move_text += f" (Evaluation: {alt['score']/100:.2f})"
                    self.story.append(Paragraph(move_text, self.styles['Normal']))
                    if 'reasoning' in alt:
                        self.story.append(Paragraph(f"  - {alt['reasoning']}", self.styles['Normal']))
        
        self.story.append(Spacer(1, 20))
        
    def add_notable_moves_section(self):
        """Add a section listing all notable moves."""
        self.story.append(Paragraph("Notable Moves", self.styles['CustomHeading1']))
        
        # Create tables for each category
        categories = [
            ('Blunders', self.commentator.notable_moves['blunders']),
            ('Mistakes', self.commentator.notable_moves['mistakes']),
            ('Good Moves', self.commentator.notable_moves['good_moves']),
            ('Missed Wins', self.commentator.notable_moves['missed_wins'])
        ]
        
        for title, moves in categories:
            self.story.append(Paragraph(title, self.styles['Heading2']))
            if moves['white'] or moves['black']:
                data = [['Side', 'Move', 'Evaluation']]
                for side in ['white', 'black']:
                    for move_info in moves[side]:
                        data.append([
                            side.capitalize(),
                            move_info['move'],
                            move_info['evaluation']
                        ])
                
                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                self.story.append(table)
            else:
                self.story.append(Paragraph("None", self.styles['Normal']))
            
            self.story.append(Spacer(1, 20))
            
    def add_player_scores(self):
        """Add a section showing player scores and statistics."""
        self.story.append(Paragraph("Player Performance", self.styles['CustomHeading1']))
        
        # Create a table for scores
        data = [
            ['Player', 'Score', 'Notable Statistics'],
            ['White', f"{self.commentator.player_scores['white']}/100", self.get_player_stats('white')],
            ['Black', f"{self.commentator.player_scores['black']}/100", self.get_player_stats('black')]
        ]
        
        table = Table(data, colWidths=[1.5*inch, inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        self.story.append(table)
        self.story.append(Spacer(1, 20))
        
    def get_player_stats(self, side):
        """Generate statistics for a player."""
        stats = []
        moves = self.commentator.notable_moves
        
        # Count notable moves
        blunders = len(moves['blunders'][side])
        mistakes = len(moves['mistakes'][side])
        good_moves = len(moves['good_moves'][side])
        missed_wins = len(moves['missed_wins'][side])
        
        if blunders > 0:
            stats.append(f"{blunders} blunder{'s' if blunders > 1 else ''}")
        if mistakes > 0:
            stats.append(f"{mistakes} mistake{'s' if mistakes > 1 else ''}")
        if good_moves > 0:
            stats.append(f"{good_moves} good move{'s' if good_moves > 1 else ''}")
        if missed_wins > 0:
            stats.append(f"{missed_wins} missed win{'s' if missed_wins > 1 else ''}")
            
        return ", ".join(stats) if stats else "No notable statistics"
        
    def generate_report(self, output_path):
        """Generate the complete game report."""
        self.doc = SimpleDocTemplate(output_path, pagesize=letter)
        self.story = []
        
        # Title
        self.story.append(Paragraph("Chess Game Analysis Report", self.styles['Title']))
        self.story.append(Spacer(1, 30))
        
        # Game information
        if self.commentator.game.headers:
            headers = self.commentator.game.headers
            info = [
                f"White: {headers.get('White', 'Unknown')}",
                f"Black: {headers.get('Black', 'Unknown')}",
                f"Date: {headers.get('Date', 'Unknown')}",
                f"Event: {headers.get('Event', 'Unknown')}",
                f"Result: {headers.get('Result', 'Unknown')}"
            ]
            for line in info:
                self.story.append(Paragraph(line, self.styles['Normal']))
            self.story.append(Spacer(1, 20))
        
        # Opening information
        if self.commentator.state['current_opening']:
            self.story.append(Paragraph("Opening", self.styles['Heading2']))
            self.story.append(Paragraph(
                self.commentator.state['current_opening'],
                self.styles['Normal']
            ))
            self.story.append(Spacer(1, 20))
        
        # Move-by-move analysis
        self.story.append(Paragraph("Move-by-Move Analysis", self.styles['CustomHeading1']))
        
        # Notable moves section
        self.add_notable_moves_section()
        
        # Player scores and statistics
        self.add_player_scores()
        
        # Build the PDF
        self.doc.build(self.story) 