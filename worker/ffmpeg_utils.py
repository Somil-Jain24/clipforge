import os
import shutil
import subprocess
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

def get_ffmpeg_path() -> str:
    """
    Returns the path to a usable ffmpeg executable.
    Checks system PATH first; falls back to bundled imageio-ffmpeg binary.
    """
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.error(f"Failed to locate ffmpeg via imageio_ffmpeg: {e}")
        raise RuntimeError("No ffmpeg binary found on system or in python environment.")

def get_ffprobe_path() -> Optional[str]:
    """
    Returns the path to a usable ffprobe executable, or None if unavailable.
    """
    return shutil.which("ffprobe")

def run_ffmpeg_command(cmd: List[str], timeout_sec: int = 300) -> subprocess.CompletedProcess:
    """
    Executes an ffmpeg subprocess command with timeout and error checking.
    """
    logger.debug("Executing FFmpeg: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_sec
    )
    if result.returncode != 0:
        logger.error(f"FFmpeg error: {result.stderr}")
        raise RuntimeError(f"FFmpeg failed with exit code {result.returncode}: {result.stderr[-500:]}")
    return result

def generate_synthetic_test_video(output_path: str, duration_sec: int = 120) -> str:
    """
    Generates a synthetic 1920x1080 test video with audio using FFmpeg's testsrc & sine filter.
    Useful for automated testing without requiring external YouTube downloads.
    """
    ffmpeg_exe = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_sec}:size=1920x1080:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_sec}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path
    ]
    run_ffmpeg_command(cmd, timeout_sec=120)
    return output_path

def probe_video(video_path: str) -> Dict[str, Any]:
    """
    Extracts duration, resolution, audio presence from video file using FFmpeg.
    """
    ffmpeg_exe = get_ffmpeg_path()
    cmd = [
        ffmpeg_exe,
        "-i", video_path,
        "-hide_banner"
    ]
    # FFmpeg writes stream info to stderr
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = res.stderr
    
    has_audio = "Audio:" in output
    has_video = "Video:" in output
    
    # Extract duration: Duration: 00:02:00.00
    duration = 0.0
    for line in output.splitlines():
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            duration = float(h) * 3600 + float(m) * 60 + float(s)
            break
            
    return {
        "duration": duration,
        "has_audio": has_audio,
        "has_video": has_video,
        "path": video_path
    }

def split_video_into_chunks(
    video_path: str,
    chunk_duration_sec: int,
    output_dir: str
) -> List[Dict[str, Any]]:
    """
    Splits a video into sequential chunks of chunk_duration_sec seconds.
    Returns list of chunk descriptors: [{index, path, start_time, end_time}].
    """
    info = probe_video(video_path)
    total_duration = info["duration"]
    if total_duration <= 0:
        total_duration = chunk_duration_sec

    os.makedirs(output_dir, exist_ok=True)
    ffmpeg_exe = get_ffmpeg_path()
    chunks = []
    
    start_time = 0.0
    idx = 0
    while start_time < total_duration:
        end_time = min(start_time + chunk_duration_sec, total_duration)
        chunk_path = os.path.join(output_dir, f"chunk_{idx:03d}.mp4")
        
        # Extract chunk fast using stream copy where possible or fast encode
        cmd = [
            ffmpeg_exe,
            "-y",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", str(end_time - start_time),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            chunk_path
        ]
        run_ffmpeg_command(cmd, timeout_sec=120)
        chunks.append({
            "chunk_index": idx,
            "path": chunk_path,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time
        })
        start_time = end_time
        idx += 1

    return chunks

def render_vertical_clip(
    source_video_path: str,
    start_time: float,
    duration: float,
    output_path: str,
    title: Optional[str] = None,
    captions: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Synthesizes a 1080x1920 9:16 vertical short:
    - Blurred background: 1080x1920 scaled, cropped, blurred (boxblur=20:5)
    - Foreground: centered original aspect video (scale 1080:-1)
    - High-contrast styled title / hook
    - AAC audio preserved
    """
    ffmpeg_exe = get_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Complex filtergraph:
    # [0:v] split [bg_in][fg_in]
    # bg: scale to fill 1080x1920, boxblur=20:5, setsar=1
    # fg: scale to width 1080 keeping aspect ratio, setsar=1
    # overlay fg centered on bg
    
    # We will build the filter graph
    escaped_title = (title or "").replace("'", "").replace(":", "").replace("\\", "")
    
    filtergraph = (
        "[0:v]split=2[bg_raw][fg_raw];"
        "[bg_raw]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,setsar=1[bg];"
        "[fg_raw]scale=1080:-2:flags=lanczos,setsar=1[fg];"
        "[bg][fg]overlay=(W-w)/2:(H-h)/2[base]"
    )
    
    final_v = "base"
    if escaped_title:
        # Add drawtext filter for title/hook with high-contrast background box
        filtergraph += (
            f";[{final_v}]drawtext=text='{escaped_title}':fontsize=42:fontcolor=white:"
            f"box=1:boxcolor=black@0.65:boxborderw=12:x=(w-text_w)/2:y=240[v_out]"
        )
        final_v = "v_out"
    else:
        filtergraph += f";[{final_v}]copy[v_out]"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-ss", str(start_time),
        "-i", source_video_path,
        "-t", str(duration),
        "-filter_complex", filtergraph,
        "-map", f"[{final_v}]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]

    run_ffmpeg_command(cmd, timeout_sec=180)
    return output_path
