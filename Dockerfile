FROM nvcr.io/nvidia/pytorch:25.01-py3

RUN mkdir -p ~/miniconda3 && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh && \
    bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 && \
    rm ~/miniconda3/miniconda.sh
ENV PATH="~/miniconda3/bin:$PATH"
RUN conda init bash

COPY environment.yaml /tmp/environment.yaml
RUN conda env create -f /tmp/environment.yaml
RUN echo "conda activate seg-tool" >> ~/.bashrc

RUN apt update
RUN apt install -y libgl1 libdbus-1-3 libegl1 libfontconfig1 libxcb-cursor0 libxkbcommon0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0
