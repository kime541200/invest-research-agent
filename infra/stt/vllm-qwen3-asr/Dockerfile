ARG VLLM_IMAGE_TAG=latest
FROM vllm/vllm-openai:${VLLM_IMAGE_TAG}

ARG VLLM_AUDIO_PIP_SPEC=vllm[audio]
ARG HF_TRANSFORMERS_SPEC=

RUN uv pip install --system "${VLLM_AUDIO_PIP_SPEC}" && \
    if [ -n "${HF_TRANSFORMERS_SPEC}" ]; then uv pip install --system "${HF_TRANSFORMERS_SPEC}"; fi
