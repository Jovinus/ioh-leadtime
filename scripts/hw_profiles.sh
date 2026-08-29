#!/usr/bin/env bash
# Per-machine hardware profiles for IOH training.
#
# Maps a machine to the train.py overrides that differ by hardware:
# AMP dtype (Turing wants fp16, Ampere/MPS want bf16) and batch size
# (24 GB CUDA can run BS=128; MPS must stay <=96 for the INT_MAX
# attention-tensor limit).
#
# Usage — source it, then it exports HW_OVERRIDES:
#
#   source scripts/hw_profiles.sh            # autodetect from the runtime
#   source scripts/hw_profiles.sh rtx3090    # force a profile
#   EXTRA_OVERRIDES="$HW_OVERRIDES" bash scripts/run_gap_sweep.sh
#
# Profiles (lr left at the config default 1.2e-3 @ BS=128; if you raise
# batch_size, scale lr linearly via EXTRA_OVERRIDES):
#   rtx6000  Quadro RTX 6000  Turing cc7.5  24 GB  fp16  BS=128
#   a5000    RTX A5000        Ampere cc8.6  24 GB  bf16  BS=128
#   rtx3090  RTX 3090         Ampere cc8.6  24 GB  bf16  BS=128
#   m3ultra  Apple M3 Ultra   MPS                  bf16  BS=96

_hw_profile="${1:-}"

if [ -z "${_hw_profile}" ]; then
    # Runtime detection only. Pass a profile name as $1 to force one.
    if python -c "import torch,sys; sys.exit(0 if torch.backends.mps.is_available() else 1)" 2>/dev/null; then
        _hw_profile="m3ultra"
    else
        _hw_profile="rtx3090"
    fi
fi

case "${_hw_profile}" in
    rtx6000)
        HW_OVERRIDES="train.amp_dtype=float16 train.batch_size=128 train.num_workers=8"
        ;;
    a5000|rtx3090)
        HW_OVERRIDES="train.amp_dtype=bfloat16 train.batch_size=128 train.num_workers=8"
        ;;
    m3ultra)
        HW_OVERRIDES="train.amp_dtype=bfloat16 train.batch_size=96 train.num_workers=4"
        ;;
    *)
        echo "hw_profiles.sh: unknown profile '${_hw_profile}'" >&2
        echo "  valid: rtx6000 a5000 rtx3090 m3ultra" >&2
        return 1 2>/dev/null || exit 1
        ;;
esac

export HW_OVERRIDES
echo "hw_profiles.sh: profile=${_hw_profile}  HW_OVERRIDES='${HW_OVERRIDES}'"
