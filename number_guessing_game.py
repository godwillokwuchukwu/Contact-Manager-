#!/usr/bin/env python3
"""
Number Guessing Game
=====================
Interactive game demonstrating dictionaries for state management.

Features:
- Random number generation with selectable difficulty levels
- Intelligent hint system (direction + hot/warm/cold proximity)
- Guess history tracking
- Score calculated from attempts used + a speed bonus
- High-score tracking persisted to JSON
- Replay option
"""

from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Improvement: difficulty levels
# ---------------------------------------------------------------------------
DIFFICULTY_LEVELS: Dict[str, Dict[str, int]] = {
    "easy": {"min": 1, "max": 50, "max_attempts": 10},
    "medium": {"min": 1, "max": 100, "max_attempts": 10},
    "hard": {"min": 1, "max": 200, "max_attempts": 8},
}


class GuessingGame:
    """Manages a single round of the number guessing game."""

    def __init__(self, difficulty: str = "medium", _target_override: Optional[int] = None):
        if difficulty not in DIFFICULTY_LEVELS:
            raise ValueError(
                f"Unknown difficulty {difficulty!r}. Choose from {list(DIFFICULTY_LEVELS)}."
            )
        self.difficulty = difficulty
        config = DIFFICULTY_LEVELS[difficulty]
        self.min_num = config["min"]
        self.max_num = config["max"]
        self.max_attempts = config["max_attempts"]
        # _target_override exists purely so tests can pin the answer instead
        # of relying on randomness.
        self._target_override = _target_override
        self.reset_game()

    def reset_game(self) -> None:
        """Reset game state for a new round."""
        self.target_number = self._target_override or random.randint(self.min_num, self.max_num)
        self.guesses: List[int] = []
        self.game_won = False
        self.attempts_used = 0
        self.start_time = time.time()
        self.time_taken: Optional[float] = None

    def get_hint(self, guess: int) -> Dict[str, str]:
        """Generate a hint based on direction and proximity to the target."""
        difference = abs(guess - self.target_number)

        if guess == self.target_number:
            return {"type": "correct", "message": " Correct! You guessed it!"}

        direction = "high" if guess > self.target_number else "low"

        if difference <= 5:
            proximity_msg = " HOT! You're very close!"
        elif difference <= 10:
            proximity_msg = "  Warm! Getting closer!"
        else:
            proximity_msg = "  Cold! Keep trying!"

        return {
            "type": "hint",
            "direction": direction,
            "message": f"Too {direction}! {proximity_msg}",
        }

    def make_guess(self, guess: int) -> Dict:
        """Process a player's guess and return the outcome."""
        if self.attempts_used >= self.max_attempts or self.game_won:
            raise RuntimeError("Game is already over; call reset_game() to play again.")

        self.attempts_used += 1
        self.guesses.append(guess)

        hint = self.get_hint(guess)

        if hint["type"] == "correct":
            self.game_won = True
            self.time_taken = round(time.time() - self.start_time, 1)
        elif self.attempts_used >= self.max_attempts:
            self.time_taken = round(time.time() - self.start_time, 1)

        return {
            "guess": guess,
            "attempt": self.attempts_used,
            "remaining": self.max_attempts - self.attempts_used,
            "hint": hint,
            "game_over": self.game_won or self.attempts_used >= self.max_attempts,
        }

    def calculate_score(self) -> int:
        """
        Score = attempt-based base score + a speed bonus.
        Base: 100 points, minus 10 per attempt beyond the first.
        Speed bonus: up to 20 extra points for solving quickly.
        """
        if not self.game_won:
            return 0

        base = max(0, 100 - (self.attempts_used - 1) * 10)

        elapsed = self.time_taken or 0
        if elapsed <= 15:
            speed_bonus = 20
        elif elapsed <= 30:
            speed_bonus = 10
        elif elapsed <= 60:
            speed_bonus = 5
        else:
            speed_bonus = 0

        return base + speed_bonus

    def is_game_over(self) -> bool:
        """True once the player has won or exhausted all attempts."""
        return self.game_won or self.attempts_used >= self.max_attempts

    def get_game_summary(self) -> Dict:
        """Full game summary for display or logging."""
        return {
            "difficulty": self.difficulty,
            "target": self.target_number if self.game_won else "???",
            "guesses": self.guesses,
            "attempts_used": self.attempts_used,
            "max_attempts": self.max_attempts,
            "won": self.game_won,
            "time_taken": self.time_taken,
            "score": self.calculate_score(),
            "game_over": self.is_game_over(),
            "guess_range": {
                "min": min(self.guesses) if self.guesses else 0,
                "max": max(self.guesses) if self.guesses else 0,
            },
        }


# ---------------------------------------------------------------------------
# Improvement: high score tracking (persisted to JSON)
# ---------------------------------------------------------------------------
class HighScoreTracker:
    """Tracks and persists high scores keyed by player name and difficulty."""

    def __init__(self, path: str | Path = "high_scores.json"):
        self.path = Path(path)
        self.scores: List[Dict] = []
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self.scores = json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError):
                self.scores = []
        else:
            self.scores = []

    def save(self) -> None:
        self.path.write_text(json.dumps(self.scores, indent=2))

    def add_score(self, player: str, score: int, difficulty: str, attempts: int) -> None:
        self.scores.append({
            "player": player,
            "score": score,
            "difficulty": difficulty,
            "attempts": attempts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.save()

    def top_scores(self, difficulty: Optional[str] = None, top_n: int = 5) -> List[Dict]:
        pool = self.scores if difficulty is None else [
            s for s in self.scores if s["difficulty"] == difficulty
        ]
        return sorted(pool, key=lambda s: s["score"], reverse=True)[:top_n]


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------
def validate_guess(user_input: str, min_num: int, max_num: int) -> int:
    """Validate and convert user input to an in-range integer."""
    guess = int(user_input)  # raises ValueError on non-numeric input
    if not (min_num <= guess <= max_num):
        raise ValueError(f"Number must be between {min_num} and {max_num}")
    return guess


def choose_difficulty() -> str:
    print("\nChoose a difficulty:")
    for name, cfg in DIFFICULTY_LEVELS.items():
        print(f"  {name}: {cfg['min']}-{cfg['max']}, {cfg['max_attempts']} attempts")
    choice = input("Difficulty [medium]: ").strip().lower() or "medium"
    if choice not in DIFFICULTY_LEVELS:
        print(f"Unrecognized difficulty {choice!r}, defaulting to 'medium'.")
        choice = "medium"
    return choice


def play_game(high_scores: HighScoreTracker) -> None:
    """Run one interactive round, then offer a replay."""
    print("\n" + "=" * 60)
    print("   🎮 NUMBER GUESSING GAME")
    print("=" * 60)

    difficulty = choose_difficulty()
    game = GuessingGame(difficulty=difficulty)

    print(f"\n   I'm thinking of a number between {game.min_num} and {game.max_num}.")
    print(f"   You have {game.max_attempts} attempts to guess it.")
    print("   I'll give you hints: Hot , Warm , or Cold ")
    print("=" * 60 + "\n")

    while not game.get_game_summary()["game_over"]:
        try:
            user_input = input(
                f"Attempt {game.attempts_used + 1}/{game.max_attempts}: "
                f"Enter your guess ({game.min_num}-{game.max_num}): "
            )
            guess = validate_guess(user_input, game.min_num, game.max_num)
        except ValueError as e:
            print(f" Invalid input: {e}")
            continue

        result = game.make_guess(guess)
        print(f"\n   {result['hint']['message']}")

        if result["hint"]["type"] == "correct":
            print(f"\n    Congratulations! You guessed it in {result['attempt']} attempts "
                  f"({game.time_taken}s)!")
            print(f"    Your score: {game.calculate_score()}/120")
            break

        if result["remaining"] > 0:
            print(f"    {result['remaining']} attempts remaining.\n")

    summary = game.get_game_summary()

    print("\n" + "=" * 60)
    print("    GAME SUMMARY")
    print("=" * 60)
    print(f"   Difficulty:    {summary['difficulty']}")
    print(f"   Target number: {summary['target']}")
    print(f"   Your guesses:  {summary['guesses']}")
    print(f"   Attempts used: {summary['attempts_used']}/{summary['max_attempts']}")
    if summary["guesses"]:
        print(f"   Guess range:   {summary['guess_range']['min']} - {summary['guess_range']['max']}")
    print(f"   Final score:   {summary['score']}/120")
    print("=" * 60 + "\n")

    if summary["won"]:
        player = input("Enter your name for the high-score board: ").strip() or "Anonymous"
        high_scores.add_score(player, summary["score"], difficulty, summary["attempts_used"])

        print("\n Top scores:")
        for entry in high_scores.top_scores(difficulty=difficulty, top_n=5):
            print(f"   {entry['player']}: {entry['score']} ({entry['attempts']} attempts)")

    play_again = input("\nPlay again? (yes/no): ").strip().lower()
    if play_again in ("yes", "y"):
        play_game(high_scores)
    else:
        print("\n Thanks for playing! Goodbye!\n")


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------
def run_self_tests() -> None:
    # Hint correctness: direction + proximity
    game = GuessingGame(difficulty="medium", _target_override=50)
    assert game.get_hint(80)["direction"] == "high"
    assert "HOT" in game.get_hint(53)["message"]
    assert "Warm" in game.get_hint(58)["message"]
    assert "Cold" in game.get_hint(80)["message"]
    assert game.get_hint(50)["type"] == "correct"

    # make_guess tracks attempts, history, and game_over flag
    game = GuessingGame(difficulty="medium", _target_override=65)
    r1 = game.make_guess(50)
    assert r1["attempt"] == 1 and r1["game_over"] is False
    r2 = game.make_guess(75)
    r3 = game.make_guess(68)
    r4 = game.make_guess(65)
    assert r4["hint"]["type"] == "correct"
    assert r4["game_over"] is True
    assert game.guesses == [50, 75, 68, 65]
    assert game.game_won is True

    # Score: 4 attempts -> base 70, plus speed bonus depending on elapsed time
    game.time_taken = 5  # force a fast time for deterministic scoring
    assert game.calculate_score() == 70 + 20

    # Losing: exhaust all attempts without winning -> score 0
    game = GuessingGame(difficulty="easy", _target_override=1, )
    game.target_number = 999  # unreachable within range, forces a loss
    for _ in range(game.max_attempts):
        result = game.make_guess(25)
    assert result["game_over"] is True
    assert game.game_won is False
    assert game.calculate_score() == 0

    # Invalid guess beyond exhausted attempts raises
    try:
        game.make_guess(25)
        assert False, "expected RuntimeError after game over"
    except RuntimeError:
        pass

    # Difficulty levels are wired correctly
    hard = GuessingGame(difficulty="hard", _target_override=100)
    assert hard.min_num == 1 and hard.max_num == 200 and hard.max_attempts == 8

    try:
        GuessingGame(difficulty="impossible")
        assert False, "expected ValueError for unknown difficulty"
    except ValueError:
        pass

    # validate_guess: numeric range checks
    assert validate_guess("42", 1, 100) == 42
    for bad in ("abc", "0", "101"):
        try:
            validate_guess(bad, 1, 100)
            assert False, f"expected ValueError for {bad!r}"
        except ValueError:
            pass

    # High score tracker: add + persist + top_n + difficulty filter
    tmp_path = Path("_high_scores_selftest.json")
    tmp_path.unlink(missing_ok=True)
    tracker = HighScoreTracker(tmp_path)
    tracker.add_score("Alice", 90, "medium", 3)
    tracker.add_score("Bob", 70, "medium", 5)
    tracker.add_score("Carol", 100, "easy", 2)

    top_medium = tracker.top_scores(difficulty="medium", top_n=5)
    assert top_medium[0]["player"] == "Alice"
    assert len(top_medium) == 2

    reloaded = HighScoreTracker(tmp_path)
    assert len(reloaded.scores) == 3
    tmp_path.unlink(missing_ok=True)

    print("All self-tests passed.")


def main() -> None:
    import sys

    if "--test" in sys.argv:
        run_self_tests()
        return

    high_scores = HighScoreTracker()
    try:
        play_game(high_scores)
    except KeyboardInterrupt:
        print("\n\n  Game interrupted. Goodbye!\n")


if __name__ == "__main__":
    main()
