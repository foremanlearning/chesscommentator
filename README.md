# Chess Game Commentator

An automatic chess commentator that creates video analysis of chess games from PGN files, complete with move commentary, strategic analysis, and text-to-speech narration.

## Features

- Loads and parses PGN files
- Graphical representation of the chess board
- Move-by-move commentary
- Text-to-speech narration
- Engine analysis (when Stockfish is available)
- Video output with synchronized commentary

## Requirements

- Python 3.8+
- Stockfish chess engine (optional, for move analysis)
- Required Python packages (install via requirements.txt)

## Installation

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Download chess piece images and place them in a `pieces` folder:
   - Required images: K.png, Q.png, R.png, B.png, N.png, P.png (white pieces)
   - And: k.png, q.png, r.png, b.png, n.png, p.png (black pieces)
4. (Optional) Install Stockfish chess engine for move analysis

## Usage

1. Place your PGN file in the project directory
2. Update the `stockfish_path` in main.py if you have Stockfish installed
3. Run the script:
   ```bash
   python main.py
   ```
4. Find the output video in the `output` directory

## Configuration

You can modify various parameters in the `ChessCommentator` class:
- Board size and colors
- Frame rate and delay between moves
- Commentary style and detail level

## License

MIT License 