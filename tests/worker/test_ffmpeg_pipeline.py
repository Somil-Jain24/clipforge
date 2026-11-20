import os
import pytest
from worker.ffmpeg_utils import (
    generate_synthetic_test_video,
    probe_video,
    split_video_into_chunks,
    render_vertical_clip
)

def test_synthetic_video_generation_and_probe(tmp_path):
    video_path = str(tmp_path / "synthetic_2min.mp4")
    # Generate 120-second synthetic test video
    generate_synthetic_test_video(video_path, duration_sec=120)
    
    assert os.path.exists(video_path)
    info = probe_video(video_path)
    assert info["has_video"] is True
    assert info["has_audio"] is True
    assert 118.0 <= info["duration"] <= 122.0

def test_split_video_into_chunks(tmp_path):
    video_path = str(tmp_path / "synth_chunks.mp4")
    generate_synthetic_test_video(video_path, duration_sec=130)
    
    chunk_dir = str(tmp_path / "chunks")
    chunks = split_video_into_chunks(video_path, chunk_duration_sec=60, output_dir=chunk_dir)
    
    # 130s split into 60s chunks should produce 3 chunks: [0-60], [60-120], [120-130]
    assert len(chunks) == 3
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["start_time"] == 0.0
    assert chunks[0]["end_time"] == 60.0
    assert os.path.exists(chunks[0]["path"])

def test_render_vertical_clip_with_blurred_background(tmp_path):
    source_path = str(tmp_path / "source.mp4")
    generate_synthetic_test_video(source_path, duration_sec=20)

    output_clip = str(tmp_path / "clip_vertical_9_16.mp4")
    render_vertical_clip(
        source_video_path=source_path,
        start_time=2.0,
        duration=15.0,
        output_path=output_clip,
        title="Top 3 Secrets to Scaling Fast"
    )

    assert os.path.exists(output_clip)
    probe = probe_video(output_clip)
    assert probe["has_video"] is True
    assert probe["has_audio"] is True
    assert 14.0 <= probe["duration"] <= 16.0
    assert os.path.getsize(output_clip) > 10000
