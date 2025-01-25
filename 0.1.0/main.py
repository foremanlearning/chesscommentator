from chess_commentator import ChessCommentator
from logger import Logger
import os
import sys
import time
import tkinter as tk
from tkinter import filedialog

def main():
    try:
        # Initialize tkinter for file dialog
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        # Initialize the commentator
        stockfish_path = None  # Set this to your Stockfish path if you have it installed
        
        Logger.info("Starting Chess Game Commentator")
        Logger.info("Initializing components...")
        
        commentator = ChessCommentator(stockfish_path)
        
        # Open file dialog for PGN selection
        Logger.info("Please select a PGN file...")
        pgn_file = filedialog.askopenfilename(
            title="Select PGN File",
            filetypes=[("PGN files", "*.pgn"), ("All files", "*.*")]
        )
        
        if not pgn_file:
            Logger.error("No file selected. Exiting...")
            return
            
        if not os.path.exists(pgn_file):
            Logger.error(f"PGN file not found: {pgn_file}")
            return
            
        # Create output directory if it doesn't exist
        if not os.path.exists("output"):
            Logger.debug("Creating output directory")
            os.makedirs("output", exist_ok=True)
        
        # Generate the video
        Logger.info("\nStarting video generation process")
        Logger.info("Controls:")
        Logger.info("- Press ESC to cancel")
        Logger.info("- Close the window to stop")
        Logger.info("- Wait for the process to complete")
        
        # Create output filename based on input filename
        output_filename = os.path.splitext(os.path.basename(pgn_file))[0] + ".mp4"
        output_path = os.path.join("output", output_filename)
        
        if commentator.create_video(pgn_file, output_path):
            Logger.success(f"\nVideo has been created successfully at: {output_path}")
        else:
            Logger.error("\nVideo generation failed or was cancelled.")
        
        # Cleanup
        Logger.info("Performing cleanup...")
        commentator.cleanup()
        
    except Exception as e:
        Logger.error(f"\nUnexpected error: {str(e)}")
        Logger.error("The program will exit.")
        return

if __name__ == "__main__":
    main()
    Logger.info("\nPress Enter to exit...")
    input() 