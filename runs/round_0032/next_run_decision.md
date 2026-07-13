# Next E1-prime Run

## Immediate Commands

```powershell
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\01_select_memos_full.py"
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\00_verify_serializer.py"
```

The verifier must report 1,987/1,987 byte-exact serializer matches and visibility counts of 763 visible-supported and 133 serialization-loss. Any mismatch blocks API execution.

Then run A0-exact only:

```powershell
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\02_generate_memos_full.py" --conditions A0 --yes
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\03_judge_memos_full.py" --conditions A0
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\04_analyze_memos_full.py"
```

Review A0 before launching treatments. If replay non-correct rate is below 90%, stop and inspect prompt equality, model endpoint/version, and judge stability. The earlier 93% expectation is a target, not a guaranteed threshold.

## Treatment Phase After A0 Passes

Treatment calls should be limited to `visible_supported AND A0 non-correct`, not merely all A0 non-correct samples. The current `--skip-a0-correct` option does not enforce the visibility restriction, so this filter should be added or verified before A1-A5 execution.

The clean explicit-authorization question also still requires the neutral-marker N and unified-license U controls. Existing A4/A5 do not provide that exact paired comparison. Do not spend on all treatment arms until the intended claim and matrix are frozen.

## Resource Estimate

The offline gate uses zero API calls. A0 requires 1,987 generation calls plus 1,987 judge calls. Based on prior token usage, expected volume is approximately 3.43 million tokens. A maximum five-arm run on all 763 visible-supported samples would require 3,815 generation and 3,815 judge calls, approximately 6.59 million tokens before stable-wrong filtering.
