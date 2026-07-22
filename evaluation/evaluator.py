import numpy as np

def extract_coords(frame):
    """
    Extract Nx3 numpy array from a frame landmark object.
    Supports list of dicts [{'x':..., 'y':..., 'z':...}] or list of lists [[x, y, z], ...]
    """
    coords = []
    for lm in frame:
        if isinstance(lm, dict):
            coords.append([lm.get('x', 0.0), lm.get('y', 0.0), lm.get('z', 0.0)])
        elif isinstance(lm, (list, tuple)):
            c = list(lm)
            while len(c) < 3:
                c.append(0.0)
            coords.append(c[:3])
    return np.array(coords, dtype=np.float32)

def normalize_frame(coords):
    """
    Center coordinates at wrist (Landmark 0) and scale by distance from wrist to Middle Finger MCP (Landmark 9).
    """
    if len(coords) == 0:
        return coords
    
    # 0 is WRIST
    wrist = coords[0]
    centered = coords - wrist

    # Scale using distance between Wrist (0) and Middle MCP (9)
    if len(coords) > 9:
        scale = np.linalg.norm(centered[9])
    else:
        scale = np.linalg.norm(centered[-1])

    if scale < 1e-6:
        scale = 1.0

    normalized = centered / scale
    return normalized

def resample_sequence(sequence, target_len):
    """
    Resample sequence of landmark matrices (frames, 21, 3) to target_len.
    """
    current_len = len(sequence)
    if current_len == target_len:
        return sequence
    if current_len == 0:
        return np.zeros((target_len, 21, 3), dtype=np.float32)
    if current_len == 1:
        return np.repeat(sequence, target_len, axis=0)

    orig_indices = np.linspace(0, current_len - 1, num=current_len)
    target_indices = np.linspace(0, current_len - 1, num=target_len)

    resampled = np.zeros((target_len, 21, 3), dtype=np.float32)
    for i in range(21):
        for j in range(3):
            resampled[:, i, j] = np.interp(target_indices, orig_indices, sequence[:, i, j])

    return resampled

def analyze_finger_deviations(user_frame, ref_frame):
    """
    Compares normalized single frame landmarks to identify specific finger misalignment errors.
    Landmark indexes:
    - Thumb: 1..4 (Tip: 4)
    - Index: 5..8 (Tip: 8)
    - Middle: 9..12 (Tip: 12)
    - Ring: 13..16 (Tip: 16)
    - Pinky: 17..20 (Tip: 20)
    """
    finger_names = {
        'thumb': (4, 'palec'),
        'index': (8, 'ukazováček'),
        'middle': (12, 'prostředníček'),
        'ring': (16, 'prsteníček'),
        'pinky': (20, 'malíček')
    }

    issues = []
    for key, (tip_idx, cz_name) in finger_names.items():
        if tip_idx < len(user_frame) and tip_idx < len(ref_frame):
            user_dist = np.linalg.norm(user_frame[tip_idx])  # distance from wrist
            ref_dist = np.linalg.norm(ref_frame[tip_idx])
            
            diff = user_dist - ref_dist
            if abs(diff) > 0.35:
                if diff > 0:
                    issues.append(f"{cz_name.capitalize()} je příliš natažený (příliš daleko od dlaně).")
                else:
                    issues.append(f"{cz_name.capitalize()} je příliš pokrčený.")

    return issues

def evaluate_landmarks(user_raw_sequence, ref_raw_sequence, tolerance=0.4):
    """
    Main evaluation pipeline.
    Returns: dict with score (0-100), success (bool), issues (list of strings), and summary_metrics.
    """
    if not user_raw_sequence or not ref_raw_sequence:
        return {
            'score': 0.0,
            'success': False,
            'issues': ['Nebyly zachyceny žádné body z kamery (No hand landmarks detected).'],
            'mean_distance': 1.0
        }

    # Extract & normalize
    user_norm = np.array([normalize_frame(extract_coords(f)) for f in user_raw_sequence])
    ref_norm = np.array([normalize_frame(extract_coords(f)) for f in ref_raw_sequence])

    # Resample user to match reference frame count
    user_resampled = resample_sequence(user_norm, len(ref_norm))

    # Compute Euclidean distance per frame per landmark
    diffs = user_resampled - ref_norm  # shape: (N, 21, 3)
    distances = np.linalg.norm(diffs, axis=2)  # shape: (N, 21)
    
    mean_distance = float(np.mean(distances))

    # Calculate score 0..100
    # distance of 0 -> score 100
    # distance of tolerance -> score 60
    # distance >= 2*tolerance -> score 0
    score = max(0.0, min(100.0, (1.0 - (mean_distance / (2 * tolerance))) * 100.0))
    score = round(score, 1)

    success = score >= 65.0

    # Extract finger alignment issues from middle frame for detailed feedback
    mid_frame_idx = len(ref_norm) // 2
    issues = analyze_finger_deviations(user_resampled[mid_frame_idx], ref_norm[mid_frame_idx])

    if not issues and not success:
        issues.append("Celkový tvar ruky nebo pohyb neodpovídá vzoru.")

    return {
        'score': score,
        'success': success,
        'issues': issues,
        'mean_distance': round(mean_distance, 4)
    }
