from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT.parents[1]


def main() -> int:
    cfg = SITE_ROOT / "_config.yml"
    text = cfg.read_text(encoding="utf-8")
    if "  - Applicant" not in text and "- Applicant" not in text:
        raise SystemExit("Applicant is not excluded in _config.yml")

    leaked_paths = []
    built_applicant = SITE_ROOT / "_site" / "Applicant"
    if built_applicant.exists():
        leaked_paths.append(str(built_applicant.relative_to(SITE_ROOT)))

    # Detect direct references in generated collection pages.
    qr_dir = SITE_ROOT / "_quantum_radar"
    if qr_dir.exists():
        for md_file in qr_dir.glob("*.md"):
            body = md_file.read_text(encoding="utf-8", errors="ignore")
            if "/Applicant/" in body or "Applicant/" in body:
                leaked_paths.append(str(md_file.relative_to(SITE_ROOT)))

    if leaked_paths:
        raise SystemExit(f"Applicant exposure risk detected: {', '.join(leaked_paths)}")

    print("Applicant privacy checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
