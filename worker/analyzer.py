import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# High-impact viral keywords and phrases
VIRAL_KEYWORDS = {
    "secret": 15, "never": 14, "always": 12, "mistake": 16,
    "truth": 15, "hack": 14, "hacks": 14, "rule": 12, "rules": 12,
    "money": 13, "billionaire": 15, "millionaire": 14, "success": 12,
    "stop": 14, "warning": 16, "danger": 15, "strategy": 13,
    "insane": 14, "crazy": 14, "nobody": 13, "hidden": 14,
    "future": 12, "power": 12, "freedom": 12, "wealth": 14,
    "greatest": 13, "changed": 12, "scaling": 11, "rapidly": 11
}

class ViralMomentAnalyzer:
    def __init__(self, min_duration: float = 12.0, max_duration: float = 35.0):
        self.min_duration = min_duration
        self.max_duration = max_duration

    def analyze_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyzes transcribed segments and returns ranked candidate clips.
        Each candidate has:
        {
            "title": str,
            "start_time": float,
            "end_time": float,
            "duration": float,
            "score": float (0-100),
            "transcript_snippet": str
        }
        """
        if not segments:
            return []

        candidates = []
        n_segs = len(segments)

        # Sliding window over segment groups to form 12s-35s candidate clips
        for i in range(n_segs):
            window_text = []
            window_start = segments[i]["start"]
            
            for j in range(i, n_segs):
                window_end = segments[j]["end"]
                duration = window_end - window_start
                window_text.append(segments[j]["text"])
                
                if duration >= self.min_duration and duration <= self.max_duration:
                    full_text = " ".join(window_text)
                    score = self._score_candidate(full_text, duration)
                    title = self._generate_title(segments[i]["text"])
                    
                    candidates.append({
                        "title": title,
                        "start_time": round(window_start, 2),
                        "end_time": round(window_end, 2),
                        "duration": round(duration, 2),
                        "score": round(score, 1),
                        "transcript_snippet": full_text
                    })
                elif duration > self.max_duration:
                    break

        # Deduplicate overlapping clips (keep highest score)
        return self._deduplicate_candidates(candidates)

    def _score_candidate(self, text: str, duration: float) -> float:
        """
        Heuristic scoring function combining keyword impact, pacing, and sentence structure.
        """
        score = 50.0  # Base score
        words = re.findall(r"\b[A-Za-z0-9'-]+\b", text.lower())
        if not words:
            return 30.0

        # 1. Keyword impact
        keyword_hits = 0
        for w in words:
            if w in VIRAL_KEYWORDS:
                score += VIRAL_KEYWORDS[w]
                keyword_hits += 1

        # 2. Pacing score (optimal speaking rate: 2.2 to 3.0 words per second)
        wps = len(words) / max(duration, 1.0)
        if 2.0 <= wps <= 3.2:
            score += 15.0
        elif 1.5 <= wps < 2.0 or 3.2 < wps <= 4.0:
            score += 8.0

        # 3. Complete sentence ending bonus
        if text.strip().endswith((".", "!", "?")):
            score += 10.0

        # 4. Opening hook bonus
        first_few = " ".join(words[:5])
        if any(hook in first_few for hook in ["this is", "never", "how to", "why you", "the secret", "the truth"]):
            score += 15.0

        return min(100.0, score)

    def _generate_title(self, first_sentence: str) -> str:
        """
        Extracts a punchy title from the first sentence or hook.
        """
        cleaned = re.sub(r"[^\w\s-]", "", first_sentence).strip()
        words = cleaned.split()
        if len(words) <= 6:
            return cleaned.title()
        return " ".join(words[:6]).title() + "..."

    def _deduplicate_candidates(self, candidates: List[Dict[str, Any]], iou_threshold: float = 0.4) -> List[Dict[str, Any]]:
        """
        Filters overlapping clips using Non-Maximum Suppression (NMS) based on temporal IoU.
        """
        if not candidates:
            return []

        # Sort descending by score
        sorted_candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
        selected = []

        for cand in sorted_candidates:
            overlap = False
            for sel in selected:
                # Compute temporal intersection over union
                inter_start = max(cand["start_time"], sel["start_time"])
                inter_end = min(cand["end_time"], sel["end_time"])
                inter = max(0.0, inter_end - inter_start)
                
                union_start = min(cand["start_time"], sel["start_time"])
                union_end = max(cand["end_time"], sel["end_time"])
                union = max(1e-5, union_end - union_start)

                iou = inter / union
                if iou > iou_threshold:
                    overlap = True
                    break

            if not overlap:
                selected.append(cand)
                if len(selected) >= 5:  # Cap max clips per chunk
                    break

        # Re-sort chronologically
        return sorted(selected, key=lambda x: x["start_time"])
