import pytest

from focuslens.camera import (
    CameraFrame,
    CameraOpenError,
    CameraReadError,
    WebcamCamera,
    bgr_to_rgb,
)


class FakeFrame:
    shape = (480, 640, 3)


class FakeRgbFrame:
    shape = (480, 640, 3)


class FakeClock:
    def __init__(self, *values):
        self.values = list(values)
        self.last_value = values[-1] if values else 0.0

    def __call__(self):
        if self.values:
            self.last_value = self.values.pop(0)
        return self.last_value


class FakeCapture:
    def __init__(self, *, opened=True, reads=None):
        self.opened = opened
        self.reads = list(reads or [])
        self.released = False
        self.properties = []

    def isOpened(self):
        return self.opened

    def read(self):
        if self.reads:
            return self.reads.pop(0)
        return False, None

    def release(self):
        self.released = True

    def set(self, property_id, value):
        self.properties.append((property_id, value))
        return True


class FakeCv2:
    COLOR_BGR2RGB = "BGR2RGB"
    CAP_DSHOW = 700
    CAP_MSMF = 1400
    CAP_PROP_FOURCC = 6
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5

    def __init__(self, capture, rgb_frame=None):
        self.capture = capture
        self.rgb_frame = rgb_frame or FakeRgbFrame()
        self.video_capture_indexes = []
        self.cvt_color_calls = []

    def VideoCapture(self, camera_index, backend=None):
        if backend is None:
            self.video_capture_indexes.append(camera_index)
        else:
            self.video_capture_indexes.append((camera_index, backend))
        return self.capture

    def cvtColor(self, frame, code):
        self.cvt_color_calls.append((frame, code))
        return self.rgb_frame

    def VideoWriter_fourcc(self, *characters):
        return "".join(characters)


def test_webcam_camera_rejects_negative_camera_index():
    with pytest.raises(ValueError, match="camera_index must be non-negative"):
        WebcamCamera(camera_index=-1)


def test_webcam_camera_reads_bgr_rgb_and_timestamp():
    frame_bgr = FakeFrame()
    frame_rgb = FakeRgbFrame()
    capture = FakeCapture(reads=[(True, frame_bgr)])
    cv2 = FakeCv2(capture, rgb_frame=frame_rgb)
    camera = WebcamCamera(camera_index=2, cv2_module=cv2, clock=FakeClock(10.0, 10.125))

    result = camera.read()

    assert result == CameraFrame(bgr=frame_bgr, rgb=frame_rgb, timestamp_ms=125)
    assert cv2.video_capture_indexes == [2]
    assert cv2.cvt_color_calls == [(frame_bgr, "BGR2RGB")]


def test_webcam_camera_can_request_backend_and_capture_options():
    capture = FakeCapture(reads=[(True, FakeFrame())])
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(
        camera_index=1,
        backend="dshow",
        frame_width=1280,
        frame_height=720,
        fps=30,
        fourcc="mjpg",
        cv2_module=cv2,
        clock=FakeClock(1.0, 1.1),
    )

    camera.read()

    assert cv2.video_capture_indexes == [(1, 700)]
    assert capture.properties == [
        (6, "MJPG"),
        (3, 1280),
        (4, 720),
        (5, 30.0),
    ]


def test_webcam_camera_rejects_invalid_backend_options():
    with pytest.raises(ValueError, match="backend must be one of"):
        WebcamCamera(backend="missing")

    with pytest.raises(ValueError, match="frame_width must be"):
        WebcamCamera(frame_width=0)

    with pytest.raises(ValueError, match="fps must be"):
        WebcamCamera(fps=0)

    with pytest.raises(ValueError, match="fourcc must contain exactly"):
        WebcamCamera(fourcc="MJPEG")


def test_webcam_camera_keeps_timestamps_increasing_with_fast_reads():
    capture = FakeCapture(reads=[(True, FakeFrame()), (True, FakeFrame())])
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(cv2_module=cv2, clock=FakeClock(5.0, 5.0, 5.0))

    first = camera.read()
    second = camera.read()

    assert first.timestamp_ms == 0
    assert second.timestamp_ms == 1


def test_webcam_camera_frames_accepts_optional_limit():
    capture = FakeCapture(
        reads=[
            (True, FakeFrame()),
            (True, FakeFrame()),
            (True, FakeFrame()),
        ]
    )
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(cv2_module=cv2, clock=FakeClock(1.0, 1.125, 1.25))

    frames = list(camera.frames(limit=2))

    assert len(frames) == 2
    assert [frame.timestamp_ms for frame in frames] == [125, 250]
    assert len(capture.reads) == 1


def test_webcam_camera_frames_rejects_negative_limit():
    camera = WebcamCamera(cv2_module=FakeCv2(FakeCapture()))

    with pytest.raises(ValueError, match="limit must be non-negative"):
        list(camera.frames(limit=-1))


def test_webcam_camera_context_manager_releases_capture():
    capture = FakeCapture(reads=[(True, FakeFrame())])
    cv2 = FakeCv2(capture)

    with WebcamCamera(cv2_module=cv2, clock=FakeClock(1.0, 1.1)) as camera:
        assert camera.read().timestamp_ms == 100
        assert capture.released is False

    assert capture.released is True


def test_webcam_camera_close_is_safe_when_not_open():
    capture = FakeCapture()
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(cv2_module=cv2)

    camera.close()

    assert capture.released is False
    assert cv2.video_capture_indexes == []


def test_webcam_camera_open_is_idempotent():
    capture = FakeCapture()
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(cv2_module=cv2)

    camera.open()
    camera.open()

    assert cv2.video_capture_indexes == [0]


def test_webcam_camera_raises_when_camera_cannot_open():
    capture = FakeCapture(opened=False)
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(camera_index=4, cv2_module=cv2)

    with pytest.raises(CameraOpenError, match="Could not open webcam at index 4"):
        camera.open()

    assert capture.released is True


def test_webcam_camera_raises_when_frame_read_fails():
    capture = FakeCapture(reads=[(False, None)])
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(cv2_module=cv2)

    with pytest.raises(CameraReadError, match="Could not read frame from webcam"):
        camera.read()


def test_webcam_camera_rejects_invalid_frame_shape():
    class InvalidFrame:
        shape = (480, 640)

    capture = FakeCapture(reads=[(True, InvalidFrame())])
    cv2 = FakeCv2(capture)
    camera = WebcamCamera(cv2_module=cv2)

    with pytest.raises(ValueError, match="frame_bgr must be an image array"):
        camera.read()


def test_bgr_to_rgb_uses_opencv_color_conversion():
    frame_bgr = FakeFrame()
    frame_rgb = FakeRgbFrame()
    cv2 = FakeCv2(FakeCapture(), rgb_frame=frame_rgb)

    result = bgr_to_rgb(frame_bgr, cv2_module=cv2)

    assert result is frame_rgb
    assert cv2.cvt_color_calls == [(frame_bgr, "BGR2RGB")]
