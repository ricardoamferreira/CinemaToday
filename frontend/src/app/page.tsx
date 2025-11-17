"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  FormEvent,
} from "react";

type TodayGameResponse = {
  game_date: string;
  movie_slug: string;
  total_clues: number;
  current_clue_index: number;
  current_clue_text: string;
  solved: boolean;
  poster_url: string | null;
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
  const [isLoadingGame, setIsLoadingGame] = useState(false);

  const [guess, setGuess] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [finished, setFinished] = useState(false);
  const [revealedTitle, setRevealedTitle] = useState<string | null>(null);
  const [posterUrl, setPosterUrl] = useState<string | null>(null);
  const [previousClues, setPreviousClues] = useState<string[]>([]);

  const fetchGame = useCallback(
    async (options?: { requireDifferent?: boolean; excludeSlug?: string | null }) => {
      const requireDifferent = options?.requireDifferent ?? false;
      const excludeSlug = options?.excludeSlug ?? null;

      setIsLoadingGame(true);
      if (!requireDifferent) {
        setStatusMessage(null);
      }

      try {
        let attempt = 0;
        const maxAttempts = requireDifferent ? 5 : 1;
        let nextGame: TodayGameResponse | null = null;

        while (attempt < maxAttempts) {
          const res = await fetch(`${API_BASE_URL}/today-game`);
          if (!res.ok) {
            throw new Error("Failed to fetch game");
          }
          const data: TodayGameResponse = await res.json();

          if (
            !requireDifferent ||
            !excludeSlug ||
            data.movie_slug !== excludeSlug
          ) {
            nextGame = data;
            break;
          }

          attempt += 1;
        }

        if (!nextGame) {
          setStatusMessage("Could not find a different movie right now. Try again.");
          return;
        }

        setGame(nextGame);
        setCurrentClueIndex(nextGame.current_clue_index);
        setCurrentClueText(nextGame.current_clue_text);
        setPosterUrl(nextGame.poster_url);
        setPreviousClues([]);
        setGuess("");
        setFinished(false);
        setRevealedTitle(null);
        if (requireDifferent) {
          setStatusMessage(null);
        }
      } catch (err) {
        console.error(err);
        setStatusMessage(
          requireDifferent
            ? "Could not load a new movie. Please try again."
            : "Could not load today's game.",
        );
      } finally {
        setIsLoadingGame(false);
      }
    },
    [],
  );

  // Load today's game on first render
  useEffect(() => {
    fetchGame();
  }, [fetchGame]);

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
        if (data.reveal_poster_url) {
          setPosterUrl(data.reveal_poster_url);
        }
        if (data.next_clue_text) {
          setCurrentClueText(data.next_clue_text);
        }
      } else {
        setPreviousClues((prev) =>
          currentClueText ? [...prev, currentClueText] : prev,
        );
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

  const isGuessInputEmpty = guess.trim().length === 0;

  const posterBlurAmount = useMemo(() => {
    if (!game || !posterUrl) return 0;
    if (finished) return 0;

    const maxBlur = 30;
    const minBlur = 12;
    const totalSteps = Math.max(game.total_clues - 1, 1);
    const progressRatio = Math.min(currentClueIndex / totalSteps, 1);
    const blurRange = maxBlur - minBlur;

    return Number((maxBlur - progressRatio * blurRange).toFixed(2));
  }, [game, posterUrl, currentClueIndex, finished]);

  const clueProgressPercent = useMemo(() => {
    if (!game) return 0;
    return Math.min(((currentClueIndex + 1) / game.total_clues) * 100, 100);
  }, [game, currentClueIndex]);

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-[#0f172a] via-[#312e81] to-[#be185d] font-sans text-zinc-50">
      <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-12 px-6 py-12 lg:flex-row lg:items-start lg:py-16">
        <div className="w-full space-y-5 lg:w-5/12">
          <p className="text-xs uppercase tracking-[0.3em] text-zinc-400">
            Visual teaser
          </p>

          <div className="relative aspect-[2/3] w-full overflow-hidden rounded-[32px] border border-white/10 bg-white/5 shadow-[0_30px_80px_rgba(0,0,0,0.35)]">
            {posterUrl ? (
              <img
                src={posterUrl}
                alt={
                  revealedTitle
                    ? `Poster for ${revealedTitle}`
                    : "Blurred poster for today's film"
                }
                className="h-full w-full object-cover"
                style={{
                  filter: `blur(${posterBlurAmount}px)`,
                  transform: finished ? "scale(1)" : "scale(1.04)",
                  transition: "filter 500ms ease, transform 500ms ease",
                }}
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-xs uppercase tracking-[0.3em] text-zinc-500">
                Poster loading…
              </div>
            )}

            {!finished && (
              <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent px-5 pb-5 pt-16">
                <p className="text-[11px] uppercase tracking-[0.3em] text-zinc-200/70">
                  Poster reveal in progress
                </p>
                <p className="text-sm text-zinc-100">Each clue sharpens it.</p>
              </div>
            )}
          </div>
          {game && previousClues.length > 0 && (
            <div className="space-y-3 rounded-3xl border border-white/10 bg-white/[0.02] p-6 shadow-[0_8px_30px_rgba(0,0,0,0.35)] backdrop-blur">
              <p className="text-xs uppercase tracking-[0.4em] text-fuchsia-200/80">
                Previous clues
              </p>
              <div className="space-y-3 max-h-56 overflow-y-auto pr-2">
                {previousClues.map((clue, index) => (
                  <div
                    key={`${index}-${clue.slice(0, 10)}`}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-zinc-200"
                  >
                    <p className="text-[10px] uppercase tracking-[0.4em] text-fuchsia-200/60">
                      Clue {index + 1}
                    </p>
                    <p className="mt-1 text-base leading-relaxed">{clue}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <section className="flex flex-1 flex-col gap-8">
          <header className="space-y-3">
            <p className="text-xs uppercase tracking-[0.4em] text-zinc-500">
              CinemaToday
            </p>
            <h1 className="text-4xl font-semibold leading-tight text-white">
              Guess this current UK Box Office Top 10 film
            </h1>
            <p className="text-sm text-zinc-400">
              Minimal clues, maximal suspense. Submit your guess after every hint or
              ride them out until you&apos;re certain.
            </p>
            {game && (
              <p className="text-xs text-zinc-500">
                Game date: {game.game_date}
              </p>
            )}
          </header>

          {!game && (
            <div className="rounded-3xl border border-white/10 bg-white/[0.03] p-6 text-sm text-zinc-400">
              Loading today&apos;s mystery film...
            </div>
          )}

          {game && (
            <>
              <div className="space-y-3 rounded-3xl border border-white/10 bg-white/[0.04] p-4 shadow-inner shadow-white/5 backdrop-blur">
                <p className="text-xs uppercase tracking-[0.4em] text-zinc-400">
                  Clue progress
                </p>
                <div className="h-1.5 w-full rounded-full bg-white/10">
                  <span
                    className="block h-full rounded-full bg-white"
                    style={{ width: `${clueProgressPercent}%` }}
                  />
                </div>
                <p className="text-sm text-zinc-300">
                  Clue {currentClueIndex + 1} <span className="text-zinc-600">/</span>{" "}
                  {game.total_clues}
                </p>
              </div>

              <div className="space-y-4 rounded-3xl border border-white/10 bg-white/[0.02] p-6 shadow-[0_15px_60px_rgba(0,0,0,0.35)] backdrop-blur">
                <p className="text-xs uppercase tracking-[0.4em] text-zinc-500">
                  Current clue
                </p>
                <p className="text-lg leading-relaxed text-white">
                  {currentClueText}
                </p>
              </div>

              {!finished && (
                <form
                  onSubmit={handleSubmitGuess}
                  className="space-y-4 rounded-3xl border border-white/10 bg-white/[0.03] p-6 shadow-[0_10px_40px_rgba(0,0,0,0.35)] backdrop-blur"
                >
                  <label className="text-xs uppercase tracking-[0.4em] text-zinc-500">
                    Your guess
                  </label>
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={guess}
                      onChange={(e) => setGuess(e.target.value)}
                      className="w-full rounded-2xl border border-white/15 bg-white/[0.02] px-4 py-3 text-base text-white outline-none transition focus:border-white/60 focus:bg-white/[0.04]"
                      placeholder="Type a film title..."
                    />
                    <button
                      type="submit"
                      className="w-full rounded-2xl bg-white/90 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-black transition hover:bg-white"
                    >
                      {isGuessInputEmpty ? "Skip clue" : "Submit guess"}
                    </button>
                  </div>
                </form>
              )}

              {statusMessage && (
                <p className="rounded-2xl border border-white/10 bg-white/[0.02] px-4 py-3 text-center text-sm text-zinc-300">
                  {statusMessage}
                </p>
              )}

              {finished && revealedTitle && (
                <div className="space-y-2 rounded-3xl border border-emerald-400/20 bg-emerald-400/10 p-6 text-center text-emerald-100">
                  <p className="text-xs uppercase tracking-[0.4em] text-emerald-200/80">
                    The film was
                  </p>
                  <p className="text-2xl font-semibold text-white">{revealedTitle}</p>
                </div>
              )}

              <button
                type="button"
                onClick={() =>
                  fetchGame({
                    requireDifferent: true,
                    excludeSlug: game?.movie_slug ?? null,
                  })
                }
                disabled={isLoadingGame}
                className="w-full rounded-2xl bg-white/95 py-4 text-xs font-semibold uppercase tracking-[0.25em] text-black transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoadingGame ? "Loading new movie…" : "New movie"}
              </button>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
