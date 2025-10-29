import json
import os
import re
from typing import List, Tuple, Dict


TimeInterval = Tuple[float, float]


def _time_to_seconds(ts: str) -> float:
    """Convert time string like HH:MM:SS.mmm to seconds (float)."""
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt_like_intervals(file_path: str) -> List[TimeInterval]:
    """Parse lines formatted as "HH:MM:SS.mmm --> HH:MM:SS.mmm" to intervals.

    Ignores any non-timestamp lines; returns merged, sorted non-overlapping intervals.
    """
    if not os.path.exists(file_path):
        return []

    pattern = re.compile(r"^(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})$")
    intervals: List[TimeInterval] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            m = pattern.match(line)
            if not m:
                continue
            start_s = _time_to_seconds(m.group(1))
            end_s = _time_to_seconds(m.group(2))
            if end_s > start_s:
                intervals.append((start_s, end_s))

    return merge_intervals(intervals)


def merge_intervals(intervals: List[TimeInterval]) -> List[TimeInterval]:
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: (x[0], x[1]))
    merged: List[TimeInterval] = []
    cur_start, cur_end = intervals[0]
    for s, e in intervals[1:]:
        if s <= cur_end + 1e-6:
            cur_end = max(cur_end, e)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = s, e
    merged.append((cur_start, cur_end))
    return merged


def total_duration(intervals: List[TimeInterval]) -> float:
    return sum(max(0.0, e - s) for s, e in intervals)


def overlap_duration(a: List[TimeInterval], b: List[TimeInterval]) -> float:
    """Compute total overlap duration between two interval sets (seconds)."""
    if not a or not b:
        return 0.0
    i, j = 0, 0
    overlap = 0.0
    while i < len(a) and j < len(b):
        s1, e1 = a[i]
        s2, e2 = b[j]
        inter_s = max(s1, s2)
        inter_e = min(e1, e2)
        if inter_e > inter_s:
            overlap += inter_e - inter_s
        if e1 < e2 - 1e-9:
            i += 1
        else:
            j += 1
    return overlap


def duration_metrics(test: List[TimeInterval], ref: List[TimeInterval]) -> Dict[str, float]:
    """Compute precision/recall/F1 based on durations (time-range matching)."""
    test_dur = total_duration(test)
    ref_dur = total_duration(ref)
    inter = overlap_duration(test, ref)
    precision = inter / test_dur if test_dur > 0 else 0.0
    recall = inter / ref_dur if ref_dur > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    iou = inter / (test_dur + ref_dur - inter) if (test_dur + ref_dur - inter) > 0 else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "overlap": inter,
        "test_dur": test_dur,
        "ref_dur": ref_dur,
        "iou": iou,
    }


def load_reference_intervals(all_ref_json: str, mp3_key: str) -> Dict[str, List[TimeInterval]]:
    """Load reference speaker intervals for a given mp3 key.

    Returns dict: speaker_id -> intervals
    """
    with open(all_ref_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if mp3_key not in data:
        raise KeyError(f"Reference not found for key: {mp3_key}")

    raw = data[mp3_key]
    ref: Dict[str, List[TimeInterval]] = {}
    for spk, ranges in raw.items():
        intervals: List[TimeInterval] = []
        for pair in ranges:
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            s, e = float(pair[0]), float(pair[1])
            if e > s:
                intervals.append((s, e))
        ref[spk] = merge_intervals(intervals)
    return ref


def pick_top_two_speakers(ref: Dict[str, List[TimeInterval]]) -> List[str]:
    speakers_sorted = sorted(ref.keys(), key=lambda k: total_duration(ref[k]), reverse=True)
    return speakers_sorted[:2]


def find_spk_files(base_audio_dir: str, mp3_key: str) -> Tuple[str, str]:
    """Search under base_audio_dir for a directory containing this mp3_key and spk0/1.txt."""
    target_dir = None
    for root, dirs, files in os.walk(base_audio_dir):
        if mp3_key in root and "spk0.txt" in files and "spk1.txt" in files:
            target_dir = root
            break
    if not target_dir:
        raise FileNotFoundError("Could not locate spk0.txt and spk1.txt under the audio folder for the given key.")
    return os.path.join(target_dir, "spk0.txt"), os.path.join(target_dir, "spk1.txt")


def evaluate_assignment(
    test0: List[TimeInterval],
    test1: List[TimeInterval],
    ref_a: List[TimeInterval],
    ref_b: List[TimeInterval],
) -> Dict[str, object]:
    # Assignment 1: spk0->A, spk1->B
    m0a = duration_metrics(test0, ref_a)
    m1b = duration_metrics(test1, ref_b)
    macro_f1_1 = (m0a["f1"] + m1b["f1"]) / 2.0
    total_overlap_1 = m0a["overlap"] + m1b["overlap"]

    # Assignment 2: spk0->B, spk1->A
    m0b = duration_metrics(test0, ref_b)
    m1a = duration_metrics(test1, ref_a)
    macro_f1_2 = (m0b["f1"] + m1a["f1"]) / 2.0
    total_overlap_2 = m0b["overlap"] + m1a["overlap"]

    if macro_f1_2 > macro_f1_1 or (abs(macro_f1_2 - macro_f1_1) < 1e-9 and total_overlap_2 > total_overlap_1):
        return {
            "mapping": {"spk0": "B", "spk1": "A"},
            "spk0": m0b,
            "spk1": m1a,
            "macro_f1": macro_f1_2,
            "total_overlap": total_overlap_2,
        }
    else:
        return {
            "mapping": {"spk0": "A", "spk1": "B"},
            "spk0": m0a,
            "spk1": m1b,
            "macro_f1": macro_f1_1,
            "total_overlap": total_overlap_1,
        }


def main():
    # Inputs
    base_dir = os.path.dirname(os.path.dirname(__file__))
    audio_dir = os.path.join(base_dir, "audio")
    all_reference_path = os.path.join(audio_dir, "all_reference.json")
    mp3_key = "merged_SSYX41011846-1757820917_1757820917000_1757821256000.mp3"

    # Load reference intervals
    ref_map = load_reference_intervals(all_reference_path, mp3_key)
    chosen_ref_speakers = pick_top_two_speakers(ref_map)
    if len(chosen_ref_speakers) < 2:
        raise RuntimeError("Reference must contain at least two speakers.")
    ref_a_id, ref_b_id = chosen_ref_speakers[0], chosen_ref_speakers[1]
    ref_a = ref_map[ref_a_id]
    ref_b = ref_map[ref_b_id]

    # Load test intervals from spk0.txt and spk1.txt
    spk0_path, spk1_path = find_spk_files(audio_dir, mp3_key.replace(".mp3", ""))
    test0 = parse_srt_like_intervals(spk0_path)
    test1 = parse_srt_like_intervals(spk1_path)

    # Evaluate best assignment
    result = evaluate_assignment(test0, test1, ref_a, ref_b)

    # Micro-averaged F1 over combined durations (optional summary)
    test_all = merge_intervals(test0 + test1)
    ref_all = merge_intervals(ref_a + ref_b)
    micro = duration_metrics(test_all, ref_all)

    # Report
    print("Target:", mp3_key)
    print("Reference speakers considered (by duration):", ref_a_id, ref_b_id)
    print("Best assignment (test->reference order A,B):", result["mapping"])

    def fmt(m: Dict[str, float]) -> str:
        return (
            f"P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
            f"IoU={m['iou']:.3f} Overlap={m['overlap']:.2f}s Test={m['test_dur']:.2f}s Ref={m['ref_dur']:.2f}s"
        )

    print("spk0:", fmt(result["spk0"]))
    print("spk1:", fmt(result["spk1"]))
    print(f"Macro-F1: {result['macro_f1']:.3f}")
    print("Micro:", fmt(micro))


if __name__ == "__main__":
    main()


