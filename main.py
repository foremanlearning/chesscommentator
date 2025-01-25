from chess_commentator import ChessCommentator
from game_report import GameReport
from logger import Logger
import os
import sys
import time
import tkinter as tk
from tkinter import filedialog
import shutil

def main():
    try:
        # Hide the main tkinter window
        root = tk.Tk()
        root.withdraw()
        
        # Get Stockfish path
        stockfish_path = os.path.join(os.path.dirname(__file__), "0.1.0", "stockfish", "stockfish-windows-x86-64-avx2.exe")
        if not os.path.exists(stockfish_path):
            Logger.warning(f"Stockfish not found at: {stockfish_path}")
            # Try to find Stockfish in system PATH
            stockfish_path = shutil.which('stockfish')
            if stockfish_path:
                Logger.info(f"Found Stockfish in PATH: {stockfish_path}")
        
        # Initialize commentator
        commentator = ChessCommentator(stockfish_path)
        
        # Create output directory if it doesn't exist
        os.makedirs("output", exist_ok=True)
        
        # Open file dialog for PGN selection
        pgn_file = filedialog.askopenfilename(
            title="Select PGN file",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
        )
        
        if not pgn_file:
            Logger.error("No PGN file selected")
            sys.exit(1)
        
        # Generate output filenames based on input PGN
        base_name = os.path.splitext(os.path.basename(pgn_file))[0]
        video_output = os.path.join("output", f"{base_name}.mp4")
        report_output = os.path.join("output", f"{base_name}_analysis.pdf")
        
        # Create game report instance
        report = GameReport(commentator)
        
        # Create video and capture positions for report
        if commentator.create_video(pgn_file, video_output):
            Logger.success(f"\nVideo has been created successfully at: {video_output}")
            
            # Generate PDF report
            try:
                report.generate_report(report_output)
                Logger.success(f"Analysis report has been created at: {report_output}")
            except Exception as e:
                Logger.error(f"Error generating analysis report: {e}")
        
        # Cleanup
        Logger.info("\nPerforming cleanup...")
        commentator.cleanup()
        
    except Exception as e:
        Logger.error(f"\nUnexpected error: {str(e)}")
        Logger.error("The program will exit.")
        return

if __name__ == "__main__":
    main()
    Logger.info("\nPress Enter to exit...")
    input() 