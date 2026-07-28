const MAX_SEQUENCE_MS = 6000;
const SAMPLE_INTERVAL_MS = 80;
const MIN_SEQUENCE_FRAMES = 6;
const TWO_HAND_SEQUENCE_FRAMES = 12;
const TWO_HAND_GRACE_MS = 450;
const HANDS_CDN = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240';
const FACE_CDN = 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619';

let hands = null;
let faceMesh = null;
let video = null;
let running = false;
let busy = false;
let animationId = 0;
let lastSampleAt = 0;
let latestHands = [];
let lastCompleteHands = [];
let lastCompleteHandsAt = 0;
let latestFace = null;
let handSequence = [];
let faceSequence = [];
let capturedSequence = [];
let capturedFaceSequence = [];
let faceEnabled = false;
let requiredHands = 1;
let frameNumber = 0;

function clonePoints(points) {
  return points?.map(({ x, y, z = 0 }) => ({ x, y, z })) || null;
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function faceMetrics(points) {
  if (!points || points.length < 468) return null;
  const faceHeight = Math.max(distance(points[10], points[152]), 0.001);
  const mouthWidth = Math.max(distance(points[61], points[291]), 0.001);
  const mouthCenterY = (points[13].y + points[14].y) / 2;
  const cornerY = (points[61].y + points[291].y) / 2;
  const leftEye = distance(points[159], points[145]) / faceHeight;
  const rightEye = distance(points[386], points[374]) / faceHeight;
  const leftBrow = (points[159].y - points[70].y) / faceHeight;
  const rightBrow = (points[386].y - points[300].y) / faceHeight;
  return {
    smile: (mouthCenterY - cornerY) / mouthWidth,
    mouth_open: distance(points[13], points[14]) / faceHeight,
    eye_open: (leftEye + rightEye) / 2,
    brow_raise: ((leftBrow + rightBrow) / 2) - 0.12,
  };
}

function trimSequence(sequence, now) {
  while (sequence.length && now - sequence[0].t > MAX_SEQUENCE_MS) sequence.shift();
}

function targetSequenceFrames() {
  return requiredHands === 2 ? TWO_HAND_SEQUENCE_FRAMES : MIN_SEQUENCE_FRAMES;
}

function sample(now) {
  if (now - lastSampleAt < SAMPLE_INTERVAL_MS) return;
  lastSampleAt = now;
  let visibleHands = latestHands.slice(0, requiredHands);
  // MediaPipe can briefly lose one hand when hands overlap during a real
  // two-handed sign. Reuse the most recent complete pair for less than half a
  // second so one flickering frame does not reset an otherwise valid capture.
  if (
    requiredHands === 2 &&
    visibleHands.length < 2 &&
    lastCompleteHands.length === 2 &&
    now - lastCompleteHandsAt <= TWO_HAND_GRACE_MS
  ) {
    visibleHands = lastCompleteHands;
  }
  if (visibleHands.length === requiredHands) {
    handSequence.push({
      t: now,
      points: visibleHands.flatMap(points => clonePoints(points)),
    });
  }
  if (faceEnabled && latestFace) faceSequence.push({ t: now, ...latestFace });
  trimSequence(handSequence, now);
  trimSequence(faceSequence, now);
  const targetFrames = targetSequenceFrames();
  if (handSequence.length >= targetFrames) {
    const firstCapture = capturedSequence.length < targetFrames;
    capturedSequence = handSequence.map(frame => clonePoints(frame.points));
    capturedFaceSequence = faceSequence.map(({ t, ...metrics }) => ({ ...metrics }));
    if (firstCapture) {
      window.dispatchEvent(new CustomEvent('handsign-captured', {
        detail: { frames: capturedSequence.length, hands: requiredHands },
      }));
    }
  }
}

async function init() {
  if (!hands && window.Hands) {
    hands = new window.Hands({
      locateFile: file => `${HANDS_CDN}/${file}`,
    });
    hands.setOptions({
      maxNumHands: 2,
      // The lite model keeps tracking responsive on laptops and phones.
      modelComplexity: 0,
      minDetectionConfidence: 0.35,
      minTrackingConfidence: 0.35,
    });
    hands.onResults(results => {
      latestHands = [...(results.multiHandLandmarks || [])]
        .sort((a, b) => a[0].x - b[0].x);
      if (latestHands.length >= 2) {
        lastCompleteHands = latestHands.slice(0, 2).map(clonePoints);
        lastCompleteHandsAt = performance.now();
      }
      window.dispatchEvent(new CustomEvent('handsign-tracking', {
        detail: {
          handCount: latestHands.length,
          requiredHands,
          captureReady: capturedSequence.length >= targetSequenceFrames(),
          faceDetected: Boolean(latestFace),
          sequenceLength: handSequence.length,
          targetFrames: targetSequenceFrames(),
        },
      }));
    });
  }
  if (!faceMesh && window.FaceMesh) {
    faceMesh = new window.FaceMesh({
      locateFile: file => `${FACE_CDN}/${file}`,
    });
    faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true,
      minDetectionConfidence: 0.55,
      minTrackingConfidence: 0.55,
    });
    faceMesh.onResults(results => {
      latestFace = faceMetrics(results.multiFaceLandmarks?.[0]);
    });
  }
}

let skipLogCount = 0;
async function processFrame(now) {
  animationId = requestAnimationFrame(processFrame);
  if (!running || busy || !video || video.readyState < 2) {
    if (skipLogCount < 5 && running) {
      window.logDebug?.(`Skip frame. running:${running}, busy:${busy}, video:${!!video}, readyState:${video?.readyState}`);
      skipLogCount++;
    }
    return;
  }
  skipLogCount = 0;
  busy = true;
  try {
    frameNumber += 1;
    if (frameNumber === 1) window.logDebug?.('processFrame started, init() calling...');
    await init();
    if (frameNumber === 1) window.logDebug?.(`init() done, window.Hands = ${typeof window.Hands}, hands = ${!!hands}`);
    if (hands) await hands.send({ image: video });
    if (frameNumber === 1) window.logDebug?.('hands.send done.');
    if (faceEnabled && faceMesh && frameNumber % 2 === 0) {
      await faceMesh.send({ image: video });
    }
    sample(now);
  } catch (error) {
    console.info('On-device tracker frame skipped:', error);
    window.logDebug?.(`TRACKER EXCEPTION: ${error.message}`);
    window.dispatchEvent(new CustomEvent('tracker-error', { detail: error.message }));
  } finally {
    busy = false;
  }
}

window.HandSignLandmarkProvider = {
  async start(nextVideo, options = {}) {
    this.stop();
    video = nextVideo;
    faceEnabled = Boolean(options.face);
    requiredHands = options.hands === 2 ? 2 : 1;
    handSequence = [];
    faceSequence = [];
    capturedSequence = [];
    capturedFaceSequence = [];
    latestHands = [];
    lastCompleteHands = [];
    lastCompleteHandsAt = 0;
    latestFace = null;
    running = true;
    await init();
    animationId = requestAnimationFrame(processFrame);
  },
  stop() {
    running = false;
    if (animationId) cancelAnimationFrame(animationId);
    animationId = 0;
    video = null;
  },
  setFaceEnabled(enabled) {
    faceEnabled = Boolean(enabled);
  },
  reset() {
    handSequence = [];
    faceSequence = [];
    capturedSequence = [];
    capturedFaceSequence = [];
  },
  getFrame() {
    return latestHands.slice(0, requiredHands).flatMap(points => clonePoints(points));
  },
  getSequence() {
    return capturedSequence.length
      ? capturedSequence.map(clonePoints)
      : handSequence.map(frame => clonePoints(frame.points));
  },
  getFaceSequence() {
    return capturedFaceSequence.length
      ? capturedFaceSequence.map(metrics => ({ ...metrics }))
      : faceSequence.map(({ t, ...metrics }) => metrics);
  },
  isCaptured() {
    return capturedSequence.length >= targetSequenceFrames();
  },
};
