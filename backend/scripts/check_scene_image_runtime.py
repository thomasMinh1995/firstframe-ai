"""Validate our exact CLI arguments with the installed MFLUX parser; never loads weights."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.infrastructure.scene_images import MfluxSceneProvider

with tempfile.TemporaryDirectory() as directory:
    prompt = Path(directory) / "prompt.txt"
    prompt.write_text("Synthetic parser check, no generation.")
    command = MfluxSceneProvider().command(prompt, Path(directory) / "unused.png")
    code = """
import json,sys
from mflux.models.z_image.cli.z_image_turbo_generate import build_parser, ZImageTurboCommand
sys.argv=['mflux-parser-check',*json.loads(sys.stdin.read())]
args=build_parser().parse_args()
ZImageTurboCommand.validate(args)
print(json.dumps({'parser_valid':True,'model_path':args.model_path,'base_model':args.base_model,
                  'width':args.width,'height':args.height,'seed':args.seed,'steps':args.steps,'quantize':args.quantize,
                  'weights_loaded':False}))
"""
    completed = subprocess.run([command[0], "-c", code], input=json.dumps(command[3:]),
                               text=True, capture_output=True, timeout=30)
    print(completed.stdout, end="")
    if completed.returncode:
        print(completed.stderr, file=sys.stderr)
    sys.exit(completed.returncode)
