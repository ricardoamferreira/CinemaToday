"use client";

import { useEffect, useState, FormEvent } from "react";

type TodayGameResponse = {
  game_date: string;
  movie_slug: string;
  total_clues: number;
  current_clue_index: number;
  current_clue_text: string;
  solved: boolean;
};

type GuessResponse = {
  correct: boolean;
  finished: boolean;
  next_clue_index: number;
  next_clue_text: string | null;
  reveal_title: string | null;
  reveal_poster_url: string | null;
  message: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export default function HomePage() {
  const [game, setGame] = useState<TodayGameResponse | null>(null);
  const [currentClueIndex, setCurrentClueIndex] = useState(0);
  const [currentClueText, setCurrentClueText] = useState<string | null>(null);

  const [guess, setGuess] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const [revealedTitle, setRevealedTitle] = useState<string | null>(null);

  // Load today's game on first render
  useEffect(() => {
    const fetchGame = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/today-game`);
        if (!res.ok) {
          throw new Error("Failed to fetch game");
        }
        const data: TodayGameResponse = await res.json();
        setGame(data);
        setCurrentClueIndex(data.current_clue_index);
        setCurrentClueText(data.current_clue_text);
      } catch (err) {
        console.error(err);
        setStatusMessage("Could not load today's game.");
      }
    };

    fetchGame();
  }, []);

  const handleSubmitGuess = async (event: FormEvent) => {
    event.preventDefault();

    if (!game || finished) return;

    try {
      const res = await fetch(`${API_BASE_URL}/guess`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          movie_slug: game.movie_slug,
          guess,
          current_clue_index: currentClueIndex,
        }),
      });

      if (!res.ok) {
        throw new Error("Guess request failed");
      }

      const data: GuessResponse = await res.json();
      setStatusMessage(data.message);

      if (data.correct || data.finished) {
        setFinished(true);
        setRevealedTitle(data.reveal_title);
        if (data.next_clue_text) {
          setCurrentClueText(data.next_clue_text);
        }
      } else {
        setCurrentClueIndex(data.next_clue_index);
        setCurrentClueText(data.next_clue_text);
      }
    } catch (err) {
      console.error(err);
      setStatusMessage("Something went wrong when submitting your guess.");
    } finally {
      setGuess("");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex min-h-screen w-full max-w-3xl flex-col items-center justify-start gap-8 py-16 px-6 bg-white dark:bg-black sm:items-start">
        <header className="w-full space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
            CinemaThisWeek 🎬
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Guess the mystery film currently playing in UK cinemas.
          </p>
        </header>

        {!game && (
          <p className="text-zinc-600 dark:text-zinc-400">
            Loading today&apos;s mystery film...
          </p>
        )}

        {game && (
          <section className="w-full space-y-4">
            <p className="text-xs text-zinc-500">
              Game date: {game.game_date}
            </p>

            <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 space-y-2">
              <p className="font-semibold text-zinc-900 dark:text-zinc-50">
                Clue {currentClueIndex + 1} of {game.total_clues}
              </p>
              <p className="text-zinc-800 dark:text-zinc-200">
                {currentClueText}
              </p>
            </div>

            {!finished && (
              <form onSubmit={handleSubmitGuess} className="space-y-3">
                <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  Your guess
                </label>
                <input
                  type="text"
                  value={guess}
                  onChange={(e) => setGuess(e.target.value)}
                  className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm outline-none focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-50"
                  placeholder="Type a film title..."
                  required
                />
                <button
                  type="submit"
                  className="w-full rounded-full bg-black py-2 text-sm font-semibold text-white shadow-sm hover:bg-zinc-900 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200"
                >
                  Submit guess
                </button>
              </form>
            )}

            {statusMessage && (
              <p className="text-sm text-center text-zinc-700 dark:text-zinc-300">
                {statusMessage}
              </p>
            )}

            {finished && revealedTitle && (
              <div className="mt-4 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 text-center space-y-1">
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  The film was:
                </p>
                <p className="text-xl font-bold text-zinc-900 dark:text-zinc-50">
                  {revealedTitle}
                </p>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
