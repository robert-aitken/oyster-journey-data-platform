FROM astrocrpublic.azurecr.io/runtime:3.2-5

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER astro