# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS builder

ENV PATH="/opt/venv/bin:${PATH}" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    VIRTUAL_ENV=/opt/venv

WORKDIR /src/packages/control-plane

COPY --from=ghcr.io/astral-sh/uv:0.9.29 /uv /usr/local/bin/uv
COPY packages/control-plane/pyproject.toml ./
COPY packages/control-plane/loop_control_plane ./loop_control_plane

RUN uv venv "${VIRTUAL_ENV}" \
    && uv pip install --python "${VIRTUAL_ENV}/bin/python" . \
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
EXPOSE 8080
ENTRYPOINT ["/opt/venv/bin/python"]
# `--workers 4` parallelises the cp-api across CPU cores. cp-api requests
# are lighter than dp-runtime turns (~1-5ms of in-memory work), so each
# worker sustains hundreds of RPS; combined with replicaCount=3 in the
# 5000-RPS perf gate this lands well under the 100ms p95 budget.
CMD ["-m", "uvicorn", "loop_control_plane.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
