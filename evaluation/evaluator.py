import numpy as np


MESSAGES = {
    'cs': {
        'face_missing': 'Obličej nebyl spolehlivě zachycen; ponechte jej celý v záběru.',
        'smile': 'Pro tento znak přidejte přirozený úsměv.',
        'sad': 'Zvýrazněte smutný výraz mírným zvednutím vnitřní části obočí.',
        'eyes_closed': 'Při dokončení znaku jemně zavřete oči.',
        'no_hands': 'Nebyly zachyceny požadované body rukou.',
        'shape': 'Celkový tvar rukou nebo pohyb neodpovídá vzoru.',
        'almost': 'Tvar je již blízko. Zopakujte pohyb pomaleji a chvíli podržte konečnou polohu.',
    },
    'ru': {
        'face_missing': 'Лицо не удалось распознать. Держите его полностью в кадре.',
        'smile': 'Добавьте к этому жесту естественную улыбку.',
        'sad': 'Подчеркните грустное выражение, слегка подняв внутренние части бровей.',
        'eyes_closed': 'В конце жеста мягко закройте глаза.',
        'no_hands': 'Не удалось записать нужное количество рук.',
        'shape': 'Общая форма рук или движение пока не совпадают с образцом.',
        'almost': 'Форма уже близка. Повторите движение немного медленнее и задержитесь в конечном положении.',
    },
    'en': {
        'face_missing': 'Your face was not detected reliably; keep it fully visible.',
        'smile': 'Add a natural smile to this sign.',
        'sad': 'Emphasize the sad expression by slightly raising your inner brows.',
        'eyes_closed': 'Gently close your eyes as you finish the sign.',
        'no_hands': 'The required number of hands was not captured.',
        'shape': 'The overall hand shape or movement does not match the reference yet.',
        'almost': 'Your shape is close. Repeat the movement a little slower and hold the final position.',
    },
}

FINGER_NAMES = {
    'cs': ['palec', 'ukazováček', 'prostředníček', 'prsteníček', 'malíček'],
    'ru': ['большой палец', 'указательный палец', 'средний палец', 'безымянный палец', 'мизинец'],
    'en': ['thumb', 'index finger', 'middle finger', 'ring finger', 'pinky'],
}


def message(language, key):
    return MESSAGES.get(language, MESSAGES['en'])[key]


def evaluate_face_metrics(raw_sequence, reference, language='en'):
    """Evaluate compact, normalized non-manual markers produced in the browser."""
    expression = (reference or {}).get('expression')
    if not expression:
        return {'score': None, 'issues': []}
    frames = [frame for frame in (raw_sequence or []) if isinstance(frame, dict)]
    if not frames:
        return {
            'score': 0.0,
            'issues': [message(language, 'face_missing')],
        }

    def average(key):
        values = [float(frame[key]) for frame in frames if frame.get(key) is not None]
        return float(np.mean(values)) if values else 0.0

    if expression == 'smile':
        value, threshold = average('smile'), 0.12
        issue = message(language, 'smile')
    elif expression == 'sad':
        value, threshold = average('brow_raise'), 0.035
        issue = message(language, 'sad')
    elif expression == 'eyes_closed':
        # eye_open is normalized lid distance, so a smaller value is better.
        value, threshold = average('eye_open'), 0.018
        score = max(0.0, min(100.0, (threshold * 2.0 - value) / threshold * 100.0))
        return {'score': round(score, 1), 'issues': [] if score >= 60 else [message(language, 'eyes_closed')]}
    else:
        return {'score': 100.0, 'issues': []}

    score = max(0.0, min(100.0, value / threshold * 100.0))
    return {'score': round(score, 1), 'issues': [] if score >= 60 else [issue]}

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
        return np.zeros((target_len, 0, 3), dtype=np.float32)
    if current_len == 1:
        return np.repeat(sequence, target_len, axis=0)

    orig_indices = np.linspace(0, current_len - 1, num=current_len)
    target_indices = np.linspace(0, current_len - 1, num=target_len)

    point_count = sequence.shape[1]
    resampled = np.zeros((target_len, point_count, 3), dtype=np.float32)
    for i in range(point_count):
        for j in range(3):
            resampled[:, i, j] = np.interp(target_indices, orig_indices, sequence[:, i, j])

    return resampled

def analyze_finger_deviations(user_frame, ref_frame, language='en'):
    """
    Compares normalized single frame landmarks to identify specific finger misalignment errors.
    Landmark indexes:
    - Thumb: 1..4 (Tip: 4)
    - Index: 5..8 (Tip: 8)
    - Middle: 9..12 (Tip: 12)
    - Ring: 13..16 (Tip: 16)
    - Pinky: 17..20 (Tip: 20)
    """
    issues = []
    names = FINGER_NAMES.get(language, FINGER_NAMES['en'])
    tips = [4, 8, 12, 16, 20]
    hand_count = min(len(user_frame), len(ref_frame)) // 21
    for hand_index in range(hand_count):
        wrist_index = hand_index * 21
        for name, local_tip in zip(names, tips):
            tip_index = wrist_index + local_tip
            user_dist = np.linalg.norm(user_frame[tip_index] - user_frame[wrist_index])
            ref_dist = np.linalg.norm(ref_frame[tip_index] - ref_frame[wrist_index])
            diff = user_dist - ref_dist
            if abs(diff) <= 0.52:
                continue
            hand_label = ''
            if hand_count == 2:
                labels = {
                    'ru': ('Левая рука', 'Правая рука'),
                    'cs': ('Levá ruka', 'Pravá ruka'),
                    'en': ('Left hand', 'Right hand'),
                }.get(language, ('Left hand', 'Right hand'))
                hand_label = f"{labels[hand_index]}: "
            if language == 'ru':
                detail = f"Немного согните {name}." if diff > 0 else f"Чуть сильнее разогните {name}."
            elif language == 'cs':
                detail = f"Trochu pokrčte {name}." if diff > 0 else f"O něco více narovnejte {name}."
            else:
                detail = f"Curl your {name} slightly." if diff > 0 else f"Straighten your {name} a little more."
            issues.append(f"{hand_label}{detail}")

    return issues[:2]

def evaluate_landmarks(
    user_raw_sequence,
    ref_raw_sequence,
    tolerance=0.8,
    face_metrics=None,
    reference_face_metrics=None,
    language='en',
):
    """
    Main evaluation pipeline.
    Returns: dict with score (0-100), success (bool), issues (list of strings), and summary_metrics.
    """
    if not user_raw_sequence or not ref_raw_sequence:
        return {
            'score': 0.0,
            'success': False,
            'issues': [message(language, 'no_hands')],
            'mean_distance': 1.0
        }

    # Extract & normalize
    user_frames = [extract_coords(frame) for frame in user_raw_sequence]
    ref_frames = [extract_coords(frame) for frame in ref_raw_sequence]
    expected_points = len(ref_frames[0]) if ref_frames else 0
    user_frames = [frame for frame in user_frames if len(frame) == expected_points]
    ref_frames = [frame for frame in ref_frames if len(frame) == expected_points]
    if expected_points not in (21, 42) or not user_frames or not ref_frames:
        return {
            'score': 0.0,
            'success': False,
            'issues': [message(language, 'no_hands')],
            'mean_distance': 1.0,
            'face_score': None,
        }
    user_norm = np.array([normalize_frame(frame) for frame in user_frames])
    ref_norm = np.array([normalize_frame(frame) for frame in ref_frames])

    # Resample user to match reference frame count
    user_resampled = resample_sequence(user_norm, len(ref_norm))

    # Accept either dominant hand by comparing the original and x-mirrored pose.
    mirrored_user = user_resampled.copy()
    mirrored_user[:, :, 0] *= -1
    if expected_points == 42:
        mirrored_user = np.concatenate(
            [mirrored_user[:, 21:42, :], mirrored_user[:, 0:21, :]],
            axis=1,
        )
    direct_distances = np.linalg.norm(user_resampled - ref_norm, axis=2)
    mirrored_distances = np.linalg.norm(mirrored_user - ref_norm, axis=2)
    if np.mean(mirrored_distances) < np.mean(direct_distances):
        user_resampled = mirrored_user
        distances = mirrored_distances
    else:
        distances = direct_distances
    
    mean_distance = float(np.mean(distances))

    # Calculate score 0..100
    # distance of 0 -> score 100
    # References are approximate, so allow normal variation in hand anatomy,
    # camera angle and execution speed.
    score = max(0.0, min(100.0, (1.0 - (mean_distance / (2 * tolerance))) * 100.0))
    score = round(score, 1)

    # Extract finger alignment issues from middle frame for detailed feedback
    mid_frame_idx = len(ref_norm) // 2
    issues = analyze_finger_deviations(
        user_resampled[mid_frame_idx],
        ref_norm[mid_frame_idx],
        language=language,
    )

    face_result = evaluate_face_metrics(face_metrics, reference_face_metrics, language=language)
    if face_result['score'] is not None:
        score = round((score * 0.8) + (face_result['score'] * 0.2), 1)
        issues.extend(face_result['issues'])

    success = score >= 60.0
    if not issues and 45.0 <= score < 60.0:
        issues.append(message(language, 'almost'))
    if not issues and not success:
        issues.append(message(language, 'shape'))

    return {
        'score': score,
        'success': success,
        'issues': issues,
        'mean_distance': round(mean_distance, 4),
        'face_score': face_result['score'],
    }
