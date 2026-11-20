import pytest
from worker.analyzer import ViralMomentAnalyzer

def test_viral_analyzer_scoring_and_duration():
    analyzer = ViralMomentAnalyzer(min_duration=12.0, max_duration=35.0)

    # Synthetic transcript segments
    segments = [
        {
            "start": 0.0,
            "end": 8.0,
            "text": "This is the greatest secret to scaling your online business rapidly."
        },
        {
            "start": 8.0,
            "end": 18.0,
            "text": "Never make this fatal mistake when investing your money into untested ideas."
        },
        {
            "start": 18.0,
            "end": 26.0,
            "text": "The hidden truth is that high leverage skills always win in the long run."
        },
        {
            "start": 26.0,
            "end": 45.0,
            "text": "Now let us move on to the second part of today's lecture where we discuss general topics."
        }
    ]

    candidates = analyzer.analyze_segments(segments)
    assert len(candidates) > 0

    for cand in candidates:
        # Must strictly adhere to duration constraints
        assert 12.0 <= cand["duration"] <= 35.0
        # Must have scored reasonably high due to viral keywords
        assert cand["score"] >= 60.0
        assert len(cand["title"]) > 0

def test_viral_analyzer_deduplication():
    analyzer = ViralMomentAnalyzer(min_duration=12.0, max_duration=35.0)
    
    # Overlapping candidates
    cands = [
        {"title": "Clip A", "start_time": 0.0, "end_time": 20.0, "duration": 20.0, "score": 90.0, "transcript_snippet": "A"},
        {"title": "Clip B", "start_time": 2.0, "end_time": 21.0, "duration": 19.0, "score": 75.0, "transcript_snippet": "B"}, # heavy overlap with A
        {"title": "Clip C", "start_time": 30.0, "end_time": 50.0, "duration": 20.0, "score": 85.0, "transcript_snippet": "C"}, # distinct
    ]

    deduped = analyzer._deduplicate_candidates(cands, iou_threshold=0.4)
    # Clip B should be eliminated by NMS because Clip A has higher score (90 vs 75)
    titles = [c["title"] for c in deduped]
    assert "Clip A" in titles
    assert "Clip C" in titles
    assert "Clip B" not in titles
