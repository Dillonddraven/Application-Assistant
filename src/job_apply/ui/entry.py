"""Console entry point: `job-apply-ui` launches the Streamlit app.

Equivalent to `streamlit run src/job_apply/ui/streamlit_app.py`."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    try:
        from streamlit.web import cli as stcli   # type: ignore
    except ModuleNotFoundError:
        print(
            "streamlit not installed. Run `pip install -e .[ui]` first.",
            file=sys.stderr,
        )
        return 1
    app_path = Path(__file__).parent / "streamlit_app.py"
    sys.argv = ["streamlit", "run", str(app_path), "--server.headless=true"]
    return stcli.main()


if __name__ == "__main__":
    sys.exit(main())
