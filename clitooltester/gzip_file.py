"""Temporary file that allows on the gzip compression of stdout."""

import gzip
import io
import os
import subprocess
import threading


class GzipStdoutReader:
    """Gzip compressed stdout (or stderr) reader for subprocess.run()."""

    def __init__(self, compressed_data):
        """Initializes a gzip compressed stdout (or stderr) reader.

        Args:
          compressed_data (bytes): gzip compressed stdout (or stderr).
        """
        self._compressed_data = compressed_data
        self._pipe_r, self._pipe_w = os.pipe()
        self._thread = None

    def __enter__(self):
        """Initializes a reader with with statement"""
        self._thread = threading.Thread(target=self._decompress_and_feed_worker)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finalizes a reader with with statement."""
        self._thread.join(timeout=5.0)
        os.close(self._pipe_r)

    def fileno(self):
        """Returns a file descriptor number."""
        return self._pipe_r

    def _decompress_and_feed_worker(self):
        """Starts a background thread that decompresses stdout (or stderr)."""
        compressed_stream = io.BytesIO(self._compressed_data)

        try:
            with os.fdopen(self._pipe_w, "wb") as pipe_out:
                with gzip.GzipFile(fileobj=compressed_stream, mode="rb") as zipper:
                    while True:
                        chunk = zipper.read(4096)
                        if not chunk:
                            break

                        try:
                            pipe_out.write(chunk)
                            pipe_out.flush()
                        except BrokenPipeError:
                            break

        except BrokenPipeError:
            pass


class GzipStdoutWriter:
    """Gzip compressed stdout (or stderr) writer for subprocess.run()."""

    def __init__(self, mode="wb", suffix=".gz"):
        """Initializes a gzip compressed stdout (or stderr) writer.

        Args:
          mode (Optional[str]): file access mode.
          suffix (Optional[str]): file name suffix (extension).
        """
        self._buffer = io.BytesIO()
        self._mode = mode
        self._pipe_r, self._pipe_w = os.pipe()
        self._suffix = suffix
        self._thread = None

    def __enter__(self):
        """Initializes a writer with with statement."""
        self._thread = threading.Thread(target=self._compress_worker)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finalizes a writer with with statement."""
        os.close(self._pipe_w)
        self._thread.join(timeout=5.0)

    def fileno(self):
        """Returns a file descriptor number."""
        return self._pipe_w

    def _compress_worker(self):
        """Starts a background thread that compresses stdout (or stderr)."""
        with os.fdopen(self._pipe_r, "rb") as pipe_in:
            with gzip.GzipFile(fileobj=self._buffer, mode=self._mode) as zipper:
                while True:
                    chunk = pipe_in.read(4096)
                    if not chunk:
                        break

                    zipper.write(chunk)

    def getvalue(self):
        """Retrieves the gzip compressed data.

        Returns:
          bytes: gzip compressed stdout (or stderr).
        """
        return self._buffer.getvalue()
