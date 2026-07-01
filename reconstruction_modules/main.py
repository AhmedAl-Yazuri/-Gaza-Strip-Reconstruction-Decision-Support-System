# ======================================================
# main.py - Gaza Reconstruction DSS Main Orchestration Script
# ======================================================

import os
import sys
from datetime import datetime

from config import SYSTEM_VERSION
from pipeline_runner import run_reconstruction_pipeline
from project_selector import display_project_menu, get_user_project_selection


def main():
    """CLI entry point for Gaza Reconstruction DSS."""
    print("=" * 80)
    print("GAZA RECONSTRUCTION DECISION SUPPORT SYSTEM")
    print("=" * 80)
    print(f"Version: {SYSTEM_VERSION}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}/")
    print()

    display_project_menu()
    selected_projects = get_user_project_selection()
    if selected_projects is None:
        print("User exited the system.")
        return False

    print(f"Selected project types: {', '.join(selected_projects)}")
    print()

    result = run_reconstruction_pipeline(selected_projects, output_dir=output_dir)
    if not result["success"]:
        print(f"ERROR: Execution failed with error: {result['error']}")
        print(result.get("traceback", ""))
        return False

    print("EXECUTION COMPLETE")
    print("-" * 20)
    print(f"All outputs saved to: {result['output_dir']}")
    print("\nGenerated files:")
    for path in result["outputs"].values():
        print(f"   - {os.path.basename(path)}")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
