"""Background download queue that runs one job at a time."""
import re
import threading
import uuid

MAX_URL_LENGTH = 2048
MAX_FINISHED_JOBS = 30
AUDIO_QUALITIES = ("MP3", "M4A", "WAV")
FINISHED_STATUSES = ("done", "failed", "cancelled")
_URL_REGEX = re.compile(r"^https?://[^\s<>\"]+$", re.IGNORECASE)


def normalize_request(url, media_type="video", quality="best"):
    """Validates a download request, returning (url, media_type, quality) or raising ValueError."""
    url = str(url or "").strip()
    if len(url) > MAX_URL_LENGTH or not _URL_REGEX.match(url):
        raise ValueError("That is not a valid web link.")
    if media_type == "audio":
        quality = str(quality or "MP3").upper()
        if quality not in AUDIO_QUALITIES:
            raise ValueError("Unsupported audio format.")
    elif media_type == "video":
        quality = str(quality or "best").lower()
        if quality != "best" and not quality.isdigit():
            raise ValueError("Unsupported video quality.")
    else:
        raise ValueError("Unsupported media type.")
    return url, media_type, quality


class DownloadQueue:
    """Runs queued jobs on a daemon thread, holding gate for the length of each job.

    run_job takes a job dict and returns the download result dict.
    on_change takes the list of public job dicts after every state change.
    """

    def __init__(self, run_job, on_change=None, gate=None):
        self._run_job = run_job
        self._on_change = on_change
        self._gate = gate or threading.Lock()
        self._jobs = []
        self._wake = threading.Condition()
        threading.Thread(target=self._worker, daemon=True).start()

    def add(self, url, media_type="video", quality="best", title=None, options=None):
        """Queues a job. A matching job that is still pending is returned instead of a duplicate."""
        url, media_type, quality = normalize_request(url, media_type, quality)
        with self._wake:
            for job in self._jobs:
                if (job["status"] in ("queued", "downloading") and job["url"] == url
                        and job["media_type"] == media_type and job["quality"] == quality
                        and job["options"] == (options or {})):
                    return self._public(job)
            job = {
                "id": uuid.uuid4().hex,
                "url": url,
                "media_type": media_type,
                "quality": quality,
                "title": title or "",
                "status": "queued",
                "error": "",
                "options": options or {},
            }
            self._jobs.append(job)
            self._wake.notify_all()
            public = self._public(job)
        self._changed()
        return public

    def remove(self, job_id):
        """Removes a job unless it is downloading right now."""
        with self._wake:
            kept = [j for j in self._jobs if j["id"] != job_id or j["status"] == "downloading"]
            removed = len(kept) != len(self._jobs)
            self._jobs = kept
        if removed:
            self._changed()
        return removed

    def clear_finished(self):
        with self._wake:
            self._jobs = [j for j in self._jobs if j["status"] not in FINISHED_STATUSES]
        self._changed()

    def update(self, job_id, **fields):
        with self._wake:
            for job in self._jobs:
                if job["id"] == job_id:
                    job.update(fields)
                    break
            else:
                return
        self._changed()

    def snapshot(self):
        with self._wake:
            return [self._public(j) for j in self._jobs]

    @staticmethod
    def _public(job):
        return {k: v for k, v in job.items() if k != "options"}

    def _changed(self):
        if self._on_change:
            try:
                self._on_change(self.snapshot())
            except Exception:
                pass

    def _next_job(self):
        return next((j for j in self._jobs if j["status"] == "queued"), None)

    def _prune_finished(self):
        finished = [j for j in self._jobs if j["status"] in FINISHED_STATUSES]
        for job in finished[:max(0, len(finished) - MAX_FINISHED_JOBS)]:
            self._jobs.remove(job)

    def _worker(self):
        while True:
            with self._wake:
                while not self._next_job():
                    self._wake.wait()
            with self._gate:
                with self._wake:
                    job = self._next_job()
                    if not job:
                        continue
                    job["status"] = "downloading"
                self._changed()
                self._finish(job)

    def _finish(self, job):
        try:
            result = self._run_job(dict(job)) or {}
        except Exception as e:
            result = {"error": str(e)}
        fields = {}
        if result.get("cancelled"):
            fields["status"] = "cancelled"
        elif result.get("error"):
            fields.update(status="failed", error=str(result["error"]))
        else:
            fields["status"] = "done"
        if result.get("title"):
            fields["title"] = result["title"]
        with self._wake:
            job.update(fields)
            self._prune_finished()
        self._changed()
