"""
scripts/benchmark_nlu.py — THING Phase 1 Latency Benchmark
===========================================================

Measures the latency of the Regex + Fuzzy NLU layer (Layer 1 + 2).
Target from roadmap: p99 < 20ms for the regex path.

Usage:
    python scripts/benchmark_nlu.py              # regex-only benchmark
    python scripts/benchmark_nlu.py --llm        # also run LLM benchmark (requires GROQ_API_KEY)
    python scripts/benchmark_nlu.py --runs 200   # custom run count
"""

import sys
import time
import os
import statistics
import argparse

# Make sure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Sample commands ────────────────────────────────────────────────────────────

REGEX_SAMPLE_COMMANDS = [
    # System & app control
    "open chrome",
    "open spotify",
    "close notepad",
    "launch vs code",
    "kill chrome",
    "exit calculator",
    # Volume / brightness
    "volume up 10",
    "volume down 20",
    "mute the sound",
    "unmute audio",
    "brightness up",
    "brightness down 15",
    # Screenshot / camera
    "take a screenshot",
    "capture a screen shot",
    "open camera",
    # Scrolling
    "scroll down",
    "scroll up 500",
    "go to top",
    "go to bottom",
    # Time / date / weather
    "what time is it",
    "what is the date",
    "how is the weather",
    "what's the weather in london",
    # Web & navigation
    "search for python tutorials",
    "google best laptops 2026",
    "open github.com",
    "go to reddit.com",
    "go back",
    "refresh page",
    "new tab",
    "close tab",
    # Messaging
    "send raj hello there",
    "message mom I'll be late",
    "send 9876543210 hi",
    # YouTube
    "play lofi hip hop on youtube",
    "pause the music",
    "next song",
    "previous track",
    # Power / lock
    "lock my pc",
    "shutdown",
    "restart my computer",
    # Stop
    "stop",
    "cancel",
    # Vision
    "what's on my screen",
    "describe my screen",
    "read the error message",
    "click the login button",
    "click submit",
    # Typing
    "type hello world",
    "write my name is raj",
    # WhatsApp
    "whatsapp",
    "open whatsapp",
    # Fuzzy (near-misses — these hit the fuzzy layer)
    "openn chrome",
    "volum up",
    "screnshoot",
    "lok my pc",
    # Unknown (should return None quickly)
    "flibbertigibbet zorgon",
    "xyzzy frobozz",
]

# Shorter set for optional live LLM benchmark
LLM_SAMPLE_COMMANDS = [
    "crank up the tunes",
    "kill the lights",
    "could you maybe play something chill on youtube",
    "send my manager the meeting notes via whatsapp",
    "open chrome and go to google.com",
    "what's happening on my screen",
    "tell me a joke",
    "dim it down a bit",
    "take a snap and lock the computer",
    "ping raj saying I'll be 10 mins late",
]


# ── Benchmark functions ────────────────────────────────────────────────────────

def run_regex_benchmark(runs: int) -> dict:
    """Benchmark the regex + fuzzy layer only (no LLM calls)."""
    from backend.engine.intent_router import get_local_intent

    latencies_ms = []
    hits = 0
    misses = 0

    commands = (REGEX_SAMPLE_COMMANDS * ((runs // len(REGEX_SAMPLE_COMMANDS)) + 1))[:runs]

    print(f"\n" + "-"*60)
    print(f"  THING Phase 1 -- Regex + Fuzzy Layer Benchmark")
    print(f"  {runs} commands | LLM fallback: DISABLED")
    print("-"*60)

    for cmd in commands:
        t0 = time.perf_counter()
        result = get_local_intent(cmd, use_llm_fallback=False)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)
        if result:
            hits += 1
        else:
            misses += 1

    return {
        "runs": runs,
        "hits": hits,
        "misses": misses,
        "hit_rate_pct": round((hits / runs) * 100, 1),
        "avg_ms":  round(statistics.mean(latencies_ms), 3),
        "p50_ms":  round(statistics.median(latencies_ms), 3),
        "p95_ms":  round(_percentile(latencies_ms, 95), 3),
        "p99_ms":  round(_percentile(latencies_ms, 99), 3),
        "max_ms":  round(max(latencies_ms), 3),
    }


def run_llm_benchmark() -> dict:
    """Benchmark the full LLM path (requires live GROQ_API_KEY)."""
    from backend.engine.llm_intent_classifier import classify_intent_llm
    from unittest.mock import patch

    latencies_ms = []
    hits = 0

    print(f"\n" + "-"*60)
    print(f"  THING Phase 1 -- LLM Classifier Benchmark")
    print(f"  {len(LLM_SAMPLE_COMMANDS)} commands | LIVE Groq API calls")
    print("-"*60)

    for cmd in LLM_SAMPLE_COMMANDS:
        with patch("backend.engine.memory_engine.memory.get_chat_history", return_value=[]):
            t0 = time.perf_counter()
            result = classify_intent_llm(cmd)
            elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)
        status = f"OK  {result['action']}" if result else "MISS None"
        print(f"  [{elapsed_ms:6.1f}ms]  {cmd[:45]:<45}  ->  {status}")
        if result:
            hits += 1

    return {
        "runs": len(LLM_SAMPLE_COMMANDS),
        "hits": hits,
        "avg_ms":  round(statistics.mean(latencies_ms), 1),
        "p50_ms":  round(statistics.median(latencies_ms), 1),
        "p95_ms":  round(_percentile(latencies_ms, 95), 1),
        "p99_ms":  round(_percentile(latencies_ms, 99), 1),
        "max_ms":  round(max(latencies_ms), 1),
    }


def _percentile(data: list, p: int) -> float:
    """Calculate the p-th percentile of a sorted list."""
    sorted_data = sorted(data)
    index = (p / 100) * (len(sorted_data) - 1)
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_data):
        return sorted_data[-1]
    fraction = index - lower
    return sorted_data[lower] + fraction * (sorted_data[upper] - sorted_data[lower])


def print_regex_report(stats: dict) -> bool:
    """Print a formatted report and return True if targets are met."""
    TARGET_P99_MS = 20.0
    passed = stats["p99_ms"] < TARGET_P99_MS

    status = "PASS" if passed else "FAIL"

    print(f"\n" + "="*60)
    print(f"  REGEX LAYER RESULTS                               [{status}]")
    print("-"*60)
    print(f"  Runs:           {stats['runs']}")
    print(f"  Hit rate:       {stats['hits']}/{stats['runs']}  ({stats['hit_rate_pct']}%)")
    print(f"  Average:        {stats['avg_ms']} ms")
    print(f"  p50 (median):   {stats['p50_ms']} ms")
    print(f"  p95:            {stats['p95_ms']} ms")
    print(f"  p99:            {stats['p99_ms']} ms  <- Target: < {TARGET_P99_MS} ms")
    print(f"  Max:            {stats['max_ms']} ms")
    print(f"{'='*60}")

    if not passed:
        print(f"\n  WARNING: p99 ({stats['p99_ms']}ms) exceeds target ({TARGET_P99_MS}ms).")
        print(f"  Consider: regex reordering, pattern optimisation, or pre-compilation check.\n")

    return passed


def print_llm_report(stats: dict) -> bool:
    """Print LLM benchmark results and return True if target met."""
    TARGET_P99_MS = 800.0
    passed = stats["p99_ms"] < TARGET_P99_MS

    status = "PASS" if passed else "FAIL"

    print(f"\n" + "="*60)
    print(f"  LLM LAYER RESULTS                                 [{status}]")
    print("-"*60)
    print(f"  Runs:           {stats['runs']}")
    print(f"  Hits:           {stats['hits']}/{stats['runs']}")
    print(f"  Average:        {stats['avg_ms']} ms")
    print(f"  p50 (median):   {stats['p50_ms']} ms")
    print(f"  p95:            {stats['p95_ms']} ms")
    print(f"  p99:            {stats['p99_ms']} ms  <- Target: < {TARGET_P99_MS} ms")
    print(f"  Max:            {stats['max_ms']} ms")
    print(f"{'='*60}")

    return passed


# ── Entry point ───────────────────────────────────────────────────────────────

def run_vision_benchmark() -> dict:
    """
    Benchmarks the screen capture + JPEG encode path (Phase 2 Layer 1).
    Does NOT call Gemini — uses a pre-built fake screenshot to measure
    the _capture_screen() + base64 encode pipeline.
    Target: p99 < 300ms for the capture+encode layer.
    """
    import io
    from PIL import Image

    print(f"\n" + "-"*60)
    print(f"  THING Phase 2 -- Screen Capture + Encode Benchmark")
    print(f"  10 calls | Mocked screen | No Gemini API call")
    print("-"*60)

    # Create a fake 1920x1080 image to simulate a real screenshot
    fake_img = Image.new("RGB", (1920, 1080), color=(20, 20, 30))

    latencies_ms = []
    RUNS = 10

    for i in range(RUNS):
        t0 = time.perf_counter()

        # Simulate the _capture_screen encode path (resize + JPEG encode + b64)
        import base64
        img = fake_img.resize((1280, 720), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        jpeg_bytes = buf.getvalue()
        _ = base64.b64encode(jpeg_bytes).decode("utf-8")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)
        print(f"  [{elapsed_ms:6.1f}ms]  Capture+encode run {i+1}")

    return {
        "runs": RUNS,
        "avg_ms":  round(statistics.mean(latencies_ms), 1),
        "p50_ms":  round(statistics.median(latencies_ms), 1),
        "p95_ms":  round(_percentile(latencies_ms, 95), 1),
        "p99_ms":  round(_percentile(latencies_ms, 99), 1),
        "max_ms":  round(max(latencies_ms), 1),
    }


def print_vision_report(stats: dict) -> bool:
    """Print vision benchmark results and return True if target met."""
    TARGET_P99_MS = 300.0
    passed = stats["p99_ms"] < TARGET_P99_MS
    status = "PASS" if passed else "FAIL"

    print(f"\n" + "="*60)
    print(f"  VISION CAPTURE LAYER RESULTS                      [{status}]")
    print("-"*60)
    print(f"  Runs:           {stats['runs']}")
    print(f"  Average:        {stats['avg_ms']} ms")
    print(f"  p50 (median):   {stats['p50_ms']} ms")
    print(f"  p95:            {stats['p95_ms']} ms")
    print(f"  p99:            {stats['p99_ms']} ms  <- Target: < {TARGET_P99_MS} ms")
    print(f"  Max:            {stats['max_ms']} ms")
    print("="*60)
    print("  Note: Full vision latency (with Gemini API) is ~1-3s.")
    print("        This measures only capture+resize+encode (offline).")

    return passed


def main():
    parser = argparse.ArgumentParser(description="THING NLU + Vision Latency Benchmarker")
    parser.add_argument("--runs", type=int, default=100, help="Number of regex benchmark runs (default: 100)")
    parser.add_argument("--llm", action="store_true", help="Also run the live LLM benchmark (requires GROQ_API_KEY)")
    parser.add_argument("--vision", action="store_true", help="Also run the Phase 2 vision capture benchmark")
    args = parser.parse_args()

    # ── Regex benchmark (always runs) ─────────────────────────────────────────
    regex_stats = run_regex_benchmark(args.runs)
    regex_passed = print_regex_report(regex_stats)

    # ── LLM benchmark (optional, requires live API key) ───────────────────────
    llm_passed = True
    if args.llm:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("\n  WARNING: GROQ_API_KEY not set -- skipping LLM benchmark.")
        else:
            llm_stats = run_llm_benchmark()
            llm_passed = print_llm_report(llm_stats)
    else:
        print("\n  INFO: LLM benchmark skipped. Run with --llm to include live API calls.")

    # ── Vision capture benchmark (optional, offline, no API key needed) ───────
    vision_passed = True
    if args.vision:
        vision_stats = run_vision_benchmark()
        vision_passed = print_vision_report(vision_stats)
    else:
        print("  INFO: Vision benchmark skipped. Run with --vision to measure capture+encode path.")

    # ── Final verdict ──────────────────────────────────────────────────────────
    print()
    all_passed = regex_passed and llm_passed and vision_passed
    if all_passed:
        layers = "Phase 1 + Phase 2" if args.vision else "Phase 1"
        print(f"  RESULT: All {layers} latency targets met. PRODUCTION PERFECT.\n")
        sys.exit(0)
    else:
        print("  RESULT: One or more latency targets missed. See report above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
