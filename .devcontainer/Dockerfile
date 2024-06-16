FROM mcr.microsoft.com/devcontainers/python:3.11

WORKDIR /

ENV CONDA_PREFIX=/azureml-envs/ai-development-env
ENV CONDA_DEFAULT_ENV=$CONDA_PREFIX
ENV PATH=$CONDA_PREFIX/bin:$PATH
ENV LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

# needed for build_mlindex
RUN apt update && apt install -y fuse

# Install Python SDK
COPY src/requirements.txt .
RUN pip install -r requirements.txt 
