"""One local image process; model downloads and setup are explicit operator tasks."""
import io
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

from PIL import Image
from dotenv import load_dotenv

from app.application.ai_provider import MissingProviderConfigurationError, ProviderRequestError, ProviderTimeoutError

ROOT = Path(__file__).resolve().parents[2] / ".data"
MODEL = "filipstrand/Z-Image-Turbo-mflux-4bit"
SKETCH_PROMPT_VERSION = "scene-sketch-direct-v3"
PARAMETERS = {"width": 768, "height": 432, "steps": 9, "seed": 42, "quantize": 4,
              "low_ram": True, "mlx_cache_limit_gb": 2, "timeout_seconds": 180,
              "model_revision": "b3a8f31115a11f2f9e2fa0bfbc8d78dcc3e6568b", "mflux_version": "0.23.0", "mlx_version": "0.32.4"}
MAX_BYTES = 8 * 1024 * 1024


def validate_png(data: bytes) -> bytes:
    if not data or len(data) > MAX_BYTES:
        raise ProviderRequestError("Sketch exceeds byte limit")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "PNG" or image.size != (768, 432) or getattr(image, "n_frames", 1) != 1:
                raise ValueError("Wrong sketch format or dimensions")
            image.verify()
        # Re-encode to remove metadata and ensure the pixels decode, not just the header.
        with Image.open(io.BytesIO(data)) as image:
            clean = io.BytesIO()
            image.convert("RGB").save(clean, format="PNG")
        return clean.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise ProviderRequestError("Invalid PNG sketch") from error


class SceneImageStore:
    def __init__(self, root: Path):
        self.root = root

    def path(self, project_id: str, asset_id: str) -> Path:
        # These components never come from a model URL or filesystem path.
        return self.root / str(UUID(project_id)) / (str(UUID(asset_id)) + ".png")

    def save(self, project_id: str, asset_id: str, data: bytes) -> None:
        path = self.path(project_id, asset_id)
        data = validate_png(data)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary.write(data)
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)

    def read(self, project_id: str, asset_id: str) -> bytes:
        path = self.path(project_id, asset_id)
        if path.is_symlink() or path.stat().st_size > MAX_BYTES:
            raise ProviderRequestError("Invalid stored image")
        return validate_png(path.read_bytes())


class MfluxSceneProvider:
    model = MODEL
    parameters = PARAMETERS

    def __init__(self, root: Path = ROOT):
        self.root = root

    def command(self, prompt_path: Path, output: Path) -> list[str]:
        snapshot = self.root / "image-models/hub/models--filipstrand--Z-Image-Turbo-mflux-4bit/snapshots" / PARAMETERS["model_revision"]
        return [str(self.root / "image-runtime/bin/python"), "-m", "mflux.models.z_image.cli.z_image_turbo_generate",
                "--model", str(snapshot), "--base-model", "z-image-turbo", "--quantize", "4", "--width", "768", "--height", "432",
                "--steps", "9", "--seed", "42", "--low-ram", "--mlx-cache-limit-gb", "2",
                "--prompt-file", str(prompt_path), "--output", str(output)]

    def generate(self, prompt: str) -> bytes:
        load_dotenv()
        python = self.root / "image-runtime/bin/python"
        cache = self.root / "image-models"
        snapshot = cache / "hub/models--filipstrand--Z-Image-Turbo-mflux-4bit/snapshots" / PARAMETERS["model_revision"]
        if os.getenv("SCENE_IMAGE_PROVIDER") != "mflux" or not python.is_file() or not snapshot.is_dir():
            raise MissingProviderConfigurationError("Local MFLUX runtime/model not configured")
        import fcntl  # This optional provider targets Apple Silicon, not the text provider's platform.
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "scene-image.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ProviderRequestError("Another local image is still running; no automatic retry") from error
            with tempfile.TemporaryDirectory(prefix="scene-image-", dir=self.root) as directory:
                directory = Path(directory)
                prompt_path = directory / "prompt.txt"
                output = directory / "preview.png"
                prompt_path.write_text(prompt, encoding="utf-8")
                command = self.command(prompt_path, output)
                env = {**os.environ, "HF_HOME": str(cache), "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                       "HF_HUB_DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1"}
                with (directory / "process.log").open("wb") as log:
                    process = subprocess.Popen(command, env=env, stdout=log, stderr=log, start_new_session=True)
                    try:
                        process.wait(timeout=PARAMETERS["timeout_seconds"])
                    except subprocess.TimeoutExpired as error:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        log.flush()
                        detail = (directory / "process.log").read_bytes()[-16000:].decode("utf-8", errors="replace")
                        raise ProviderTimeoutError("MFLUX exceeded 180 seconds\n" + detail) from error
                if process.returncode or not output.is_file() or output.stat().st_size > MAX_BYTES:
                    detail = (directory / "process.log").read_bytes()[-16000:].decode("utf-8", errors="replace")
                    raise ProviderRequestError("MFLUX failed to produce a valid sketch\n" + detail)
                return validate_png(output.read_bytes())


def sketch_prompt(scene, context, instructions: str) -> str:
    style = (
        "An unfinished HAND-DRAWN GRAPHITE PENCIL LINE DRAWING on plain white paper, not a photograph. "
        "Use visible thin, slightly irregular pencil contours, a few light hatch marks and large untouched white areas. "
        "Faces and surroundings are drawn with economical lines, without photographic skin/fabric textures, "
        "smooth photographic shading or solid black photographic shadows. One horizontal frame, one moment."
    )
    values = [scene.action, scene.characters, scene.location, scene.time]
    values.extend(scene.staging_choices[key] for key in (
        "blocking", "performance", "setting", "lighting", "color", "costume", "composition", "shot", "angle", "moment"
    ) if key in scene.staging_choices)
    values.extend([scene.goal, scene.purpose, scene.viewer_intent, context.idea])
    for decision in context.clarifications:
        if decision.answer.strip():
            values.extend([decision.question, decision.answer])
    # Put source limits after refinements, without discarding or rewriting either.
    values.extend([instructions, scene.keep_or_avoid, *context.constraints])
    sentences = [value if value.rstrip().endswith((".", "!", "?")) else value + "."
                 for value in values if value.strip()]
    limits = []
    if instructions.strip():
        limits.append("Scene constraints take priority over depiction refinements.")
    if scene.staging_choices.get("color", "").strip():
        limits.append("Render stated colors through graphite tonal differences, keeping the drawing monochrome.")
    limits.append("Do not invent an event or resolve an open ending. Only pencil strokes on white paper: "
                  "no photograph, text, labels, captions, speech bubbles or panel grid.")
    return "\n\n".join([style, " ".join(sentences), " ".join(limits)])
