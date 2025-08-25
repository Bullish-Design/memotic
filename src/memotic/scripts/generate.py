import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
PROTO_GEN_DIR = SRC_DIR / "memotic" / "proto_gen"
MEMOS_REPO_URL = "https://github.com/usememos/memos.git"


def check_command(cmd: str):
    """Check if a command exists on the system PATH."""
    if not shutil.which(cmd):
        print(f"Error: '{cmd}' is not installed or not in your PATH.", file=sys.stderr)
        print("Please install it to continue.", file=sys.stderr)
        sys.exit(1)


def run_command(cmd_args: list[str], cwd: Path):
    """Run a command in a specified directory."""
    print(f"Running: {' '.join(cmd_args)}")
    process = subprocess.run(
        cmd_args, cwd=str(cwd), capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        print(f"Error executing command: {' '.join(cmd_args)}", file=sys.stderr)
        print(f"STDOUT:\n{process.stdout}", file=sys.stderr)
        print(f"STDERR:\n{process.stderr}", file=sys.stderr)
        sys.exit(1)
    return process.stdout


def main():
    """
    Main function to clone memos repo, generate proto files, and clean up.
    """
    check_command("git")
    check_command("buf")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        memos_repo_path = temp_path / "memos"

        # 1. Sparse clone the memos repository to get only the proto files
        print("Cloning 'usememos/memos' repository (sparse)...")
        run_command(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                MEMOS_REPO_URL,
            ],
            temp_path,
        )
        run_command(["git", "sparse-checkout", "set", "proto"], memos_repo_path)

        proto_source_dir = memos_repo_path / "proto"

        # 2. Prepare the generation directory
        if PROTO_GEN_DIR.exists():
            print(f"Removing existing generated code at {PROTO_GEN_DIR}...")
            shutil.rmtree(PROTO_GEN_DIR)
        PROTO_GEN_DIR.mkdir(parents=True)

        # 3. Create a buf.yaml in the proto source directory
        buf_yaml_content = """
version: v2
deps:
  - buf.build/googleapis/googleapis
"""
        with open(proto_source_dir / "buf.yaml", "w") as f:
            f.write(buf_yaml_content)

        # 4. Generate the Python code using buf
        print("Generating Python code from .proto files...")
        buf_gen_template = ROOT_DIR / "buf.gen.yaml"
        run_command(
            [
                "buf",
                "generate",
                f"--template={buf_gen_template}",
                f"--output={PROTO_GEN_DIR}",
            ],
            proto_source_dir,
        )

        # 5. Create __init__.py files to make packages importable
        for dirpath, _, _ in os.walk(PROTO_GEN_DIR):
            init_file = Path(dirpath) / "__init__.py"
            if not init_file.exists():
                print(f"Creating {init_file}")
                init_file.touch()

    print("\n✅ API client code generated successfully!")
    print(f"Generated code is located in: {PROTO_GEN_DIR}")


if __name__ == "__main__":
    main()
