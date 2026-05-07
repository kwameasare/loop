# syntax=docker/dockerfile:1.7
# S140: dp-runtime distroless image. Mirrors packages/control-plane/Dockerfile;
# kept in sync deliberately so a single review covers both planes.

FROM python:3.12-slim-bookworm AS builder

ENV PATH="/opt/venv/bin:${PATH}" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    VIRTUAL_ENV=/opt/venv

WORKDIR /src

COPY --from=ghcr.io/astral-sh/uv:0.9.29 /uv /usr/local/bin/uv
COPY packages/channels/core/pyproject.toml ./packages/channels/core/
COPY packages/channels/core/loop_channels_core ./packages/channels/core/loop_channels_core
COPY packages/sdk-py/pyproject.toml ./packages/sdk-py/
COPY packages/sdk-py/loop ./packages/sdk-py/loop
COPY packages/gateway/pyproject.toml ./packages/gateway/
COPY packages/gateway/loop_gateway ./packages/gateway/loop_gateway
COPY packages/memory/pyproject.toml ./packages/memory/
COPY packages/memory/loop_memory ./packages/memory/loop_memory
COPY packages/control-plane/pyproject.toml ./packages/control-plane/
COPY packages/control-plane/loop_control_plane ./packages/control-plane/loop_control_plane
COPY packages/runtime/pyproject.toml ./packages/runtime/
COPY packages/runtime/loop_runtime ./packages/runtime/loop_runtime
COPY packages/data-plane/pyproject.toml ./packages/data-plane/
COPY packages/data-plane/loop_data_plane ./packages/data-plane/loop_data_plane

RUN uv venv "${VIRTUAL_ENV}" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" \
        ./packages/channels/core ./packages/sdk-py ./packages/gateway ./packages/memory ./packages/control-plane \
        ./packages/runtime ./packages/data-plane \
    && mkdir -p /python-libs \
    && for lib in \
        libbz2.so.1.0 \
        libcom_err.so.2 \
        libcrypt.so.1 \
        libcrypto.so.3 \
        libdb-5.3.so \
        libffi.so.8 \
        libgdbm.so.6 \
        libgssapi_krb5.so.2 \
        libk5crypto.so.3 \
        libkeyutils.so.1 \
        libkrb5.so.3 \
        libkrb5support.so.0 \
        liblzma.so.5 \
        libncursesw.so.6 \
        libnsl.so.2 \
        libpanelw.so.6 \
        libreadline.so.8 \
        libsqlite3.so.0 \
        libssl.so.3 \
        libtinfo.so.6 \
        libtirpc.so.3 \
        libuuid.so.1 \
        libz.so.1; \
        do cp -L /lib/*-linux-gnu/"${lib}" /python-libs/"${lib}"; done \
    && find "${VIRTUAL_ENV}" -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /usr/local/lib/python3.12 -type d \( -name test -o -name tests \) -prune -exec rm -rf {} + \
    && rm -rf /root/.cache /usr/local/lib/python3.12/ensurepip \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip* \
    && rm -rf /usr/local/lib/python3.12/site-packages/setuptools*

FROM gcr.io/distroless/cc-debian12:nonroot AS runtime

ENV PATH="/opt/venv/bin:/usr/local/bin:${PATH}" \
    LD_LIBRARY_PATH=/usr/local/lib/python-libs \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY --from=builder /python-libs /usr/local/lib/python-libs
COPY --from=builder /opt/venv /opt/venv

USER nonroot:nonroot
EXPOSE 8081
ENTRYPOINT ["/opt/venv/bin/python"]
CMD ["-m", "loop_data_plane.run_uvicorn"]
