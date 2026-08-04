"""FFMpegWriter class for encoding video from numpy RGB/RGBA frames."""

import subprocess

import numpy as np

# Bytes-per-pixel for the supported raw input pixel formats.
INPUT_PIX_FMT_CHANNELS = {"rgb24": 3, "rgba": 4}


class FFMpegWriter:
    """Writer for encoding video files using ffmpeg from numpy RGB/RGBA frames."""

    def __init__(
        self,
        filename: str,
        width: int,
        height: int,
        framerate: float = 30.0,
        vcodec: str = "libx264",
        preset: str | None = "slow",
        crf: int | None = 18,
        pix_fmt_output: str = "yuv420p",
        pix_fmt_input: str = "rgb24",
        video_filter: str | None = None,
        vcodec_profile: str | None = None,
        extra_output_args: list[str] | None = None,
    ):
        """
        Initialize FFMpegWriter.

        Args:
            filename: Output video filename (e.g., 'output.mp4')
            width: Video width in pixels
            height: Video height in pixels
            framerate: Frame rate in fps (default: 30.0)
            vcodec: Video codec (default: 'libx264')
            preset: Encoding preset, or None for codecs without one (default: 'slow')
            crf: Constant Rate Factor, lower is higher quality, or None for codecs
                without one (default: 18)
            pix_fmt_output: Output pixel format (default: 'yuv420p')
            pix_fmt_input: Raw input pixel format, 'rgb24' or 'rgba' (default: 'rgb24')
            video_filter: Optional ffmpeg -vf filter graph applied before encoding
            vcodec_profile: Optional codec profile (-profile:v), e.g. '4444' for prores_ks
            extra_output_args: Optional additional codec-specific output arguments,
                e.g. ['-deadline', 'realtime'] for libvpx-vp9
        """
        if pix_fmt_input not in INPUT_PIX_FMT_CHANNELS:
            raise ValueError(
                f"Unsupported pix_fmt_input '{pix_fmt_input}', expected one of {sorted(INPUT_PIX_FMT_CHANNELS)}"
            )
        self.filename = filename
        self.width = width
        self.height = height
        self.framerate = framerate
        self.channels = INPUT_PIX_FMT_CHANNELS[pix_fmt_input]
        self.process = None
        self._closed = False

        # Build ffmpeg command
        # Input: raw RGB/RGBA frames from stdin
        # -f rawvideo: raw video format
        # -pix_fmt: input pixel format (rgb24 = 3 bytes/pixel, rgba = 4 bytes/pixel)
        # -s WIDTHxHEIGHT: video size
        # -r FRAMERATE: frame rate
        # -i -: read from stdin
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-f",
            "rawvideo",
            "-pix_fmt",
            pix_fmt_input,
            "-s",
            f"{width}x{height}",
            "-r",
            str(framerate),
            "-i",
            "-",  # Read from stdin
        ]
        # Output encoding options
        if video_filter is not None:
            cmd += ["-vf", video_filter]
        cmd += ["-vcodec", vcodec]
        if vcodec_profile is not None:
            cmd += ["-profile:v", vcodec_profile]
        if preset is not None:
            cmd += ["-preset", preset]
        if crf is not None:
            cmd += ["-crf", str(crf)]
        if extra_output_args is not None:
            cmd += extra_output_args
        cmd += ["-pix_fmt", pix_fmt_output, filename]

        print("Starting ffmpeg process:", " ".join(cmd))
        # Start ffmpeg process
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                # stdout=subprocess.PIPE,
                # stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered for real-time streaming
            )
        except FileNotFoundError:
            raise RuntimeError("ffmpeg not found. Please install ffmpeg to use FFMpegWriter.")
        except Exception as e:
            raise RuntimeError(f"Failed to start ffmpeg process: {e}")

    def write_frame(self, frame: np.ndarray):
        """
        Write a single RGB/RGBA frame to the video.

        Args:
            frame: numpy array of shape (height, width, channels) with uint8 data,
                where channels matches the pix_fmt_input (3 for rgb24, 4 for rgba)

        Raises:
            RuntimeError: If writer is closed or frame dimensions don't match
            ValueError: If frame format is invalid
        """
        if self._closed:
            raise RuntimeError("FFMpegWriter is closed. Cannot write more frames.")

        if self.process is None:
            raise RuntimeError("FFMpeg process not initialized.")

        # Validate frame shape
        if frame.shape != (self.height, self.width, self.channels):
            raise ValueError(
                f"Frame shape {frame.shape} does not match expected ({self.height}, {self.width}, {self.channels})"
            )

        # Ensure frame is uint8
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        # Ensure frame is contiguous in memory (C-order)
        if not frame.flags["C_CONTIGUOUS"]:
            frame = np.ascontiguousarray(frame)

        # Write frame to stdin
        try:
            self.process.stdin.write(frame.tobytes())
            self.process.stdin.flush()
        except BrokenPipeError:
            # Process may have terminated due to error
            stderr_output = self.process.stderr.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"FFMpeg process terminated unexpectedly. Error: {stderr_output}")
        except Exception as e:
            raise RuntimeError(f"Error writing frame to ffmpeg: {e}")

    def close(self):
        """Close the writer and finalize the video file."""
        if self._closed:
            return

        if self.process is None:
            self._closed = True
            return

        try:
            # Close stdin to signal end of input
            if self.process.stdin:
                self.process.stdin.close()

            # Wait for process to finish and get return code
            return_code = self.process.wait()

            if return_code != 0:
                # Read stderr for error messages
                stderr_output = self.process.stderr.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"FFMpeg process exited with code {return_code}. Error output: {stderr_output}")
        except Exception as e:
            raise RuntimeError(f"Error closing FFMpegWriter: {e}")
        finally:
            self._closed = True
            self.process = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures close is called."""
        self.close()
        return False
