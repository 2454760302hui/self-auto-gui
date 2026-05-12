"""HarmonyOS installed bundle listing via hdc."""

import re
import subprocess

from AutoGLM_GUI.hdc.connection import build_hdc_command


def list_installed_packages(device_id: str | None = None) -> dict:
    """Query HarmonyOS device for installed bundles via hdc.

    Uses ``hdc shell bm dump -a`` to list all bundles, then classifies them
    as system or third-party based on known system prefixes.

    Returns:
        dict with keys 'system' and 'third_party', each a sorted list of package names.
    """
    hdc_prefix = build_hdc_command(device_id)

    result = subprocess.run(
        hdc_prefix + ["shell", "bm", "dump", "-a"],
        capture_output=True, text=True,
    )

    # Parse lines like "com.example.app" from bm dump output
    all_packages = sorted(set(
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and re.match(r'^[a-z]', line.strip())
    ))

    system_prefixes = (
        "com.huawei.", "com.hihonor.", "com.android.", "android.",
        "com.harmony.", "com.ohos.",
    )
    system = sorted(p for p in all_packages if p.startswith(system_prefixes))
    third_party = sorted(p for p in all_packages if not p.startswith(system_prefixes))

    return {"system": system, "third_party": third_party}
