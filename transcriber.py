import warnings

# Suppress the massive torchcodec DLL initialization warnings
# These MUST stay at the very top of the file before any other imports!
warnings.filterwarnings("ignore", category=UserWarning, module=".*torchcodec.*")
warnings.filterwarnings("ignore", message=".*torchcodec is not installed correctly.*")

import whisperx
import torch
import os
import re

SEGMENT_BREAK = 0.8

def format_ts(seconds_float: float) -> str:
    """Format float seconds to HH:MM:SS.MS (Rule 31)"""
    hours = int(seconds_float // 3600)
    minutes = int((seconds_float % 3600) // 60)
    seconds = int(seconds_float % 60)
    milliseconds = int(round((seconds_float - int(seconds_float)) * 1000))
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

def validate_tags(text: str) -> bool:
    """Rule 27: Check for malformed tags. Return False if malformed."""
    open_tags = re.findall(r'<[^/][^>]*>', text)
    close_tags = re.findall(r'</[^>]+>', text)
    return len(open_tags) == len(close_tags)

def transcribe_audio(audio_path: str, lang: str = "en") -> list:
    """
    Transcribe the audio file using whisperX and apply specific tagging rules.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    batch_size = 16 
    compute_type = "float16" if device == "cuda" else "int8"
    
    # Rule 29: Use 'medium' or user's requested model
    print(f"Loading WhisperX model on {device}...")
    model = whisperx.load_model("medium", device, compute_type=compute_type)
    
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=batch_size, language=lang)
    
    # Align whisper output to get word-level precision
    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
    aligned_result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
    
    return apply_pipeline_rules(aligned_result["segments"])

def apply_pipeline_rules(segments):
    """
    Applies the custom text formatting, regex, and tagging rules (Rules 06, 27, 28, 30, 35).
    """
    final_segments = []
    
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            continue
            
        current_segment_words = []
        segment_start = words[0].get("start", seg["start"])
        segment_end = segment_start
        
        for i, w in enumerate(words):
            text = w.get("word", "").strip()
            w_start = w.get("start", segment_end)
            w_end = w.get("end", w_start)
            score = w.get("score", 0.0)
            
            # Rule 06 & 35: Segment Break detection
            if current_segment_words and (w_start - segment_end) >= SEGMENT_BREAK:
                # Flush segment
                flush_segment(final_segments, current_segment_words, segment_start, segment_end)
                # Start new segment
                current_segment_words = []
                segment_start = w_start
            
            # Rule 28 & 30: Empty tokens or low confidence -> Mumble Tag
            if text == "" or score < 0.40:
                text = "<MB></MB>"
                
            # Rule 27: Validate tags
            if not validate_tags(text):
                text = "<MB></MB>"
                
            current_segment_words.append(text)
            segment_end = w_end
            
        # Flush remaining
        if current_segment_words:
            flush_segment(final_segments, current_segment_words, segment_start, segment_end)
        
    return final_segments

def flush_segment(final_segments, current_segment_words, segment_start, segment_end):
    joined_text = " ".join(current_segment_words)
    final_segments.append({
        "start": format_ts(segment_start),
        "end": format_ts(segment_end),
        "text": joined_text,
        "raw_start": segment_start,
        "raw_end": segment_end
    })
