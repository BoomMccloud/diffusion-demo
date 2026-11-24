# WindTunnel benchmark and demos

WindTunnel runs browser-agent tasks. The upstream checkout and its run outputs
stay local. This repository contains the changes for the recording workflow
and the local diffusion runners.

From the repository root, set up a fresh checkout with:

```sh
git clone https://github.com/nekuda-ai/WindTunnel.git bench/windtunnel
git -C bench/windtunnel checkout --detach 5ca8644e23826ebb30108e7bad240b61043bfe67
git -C bench/windtunnel apply "$PWD/experiments/windtunnel/local-runners.patch"
npm ci --prefix bench/windtunnel
```

If you already have a local checkout with these changes, use it directly.
The [WindTunnel README](code/windtunnel/README.md) documents the harness,
and the [upstream attribution](code/windtunnel/ATTRIBUTION.md) covers its
dependencies and fixtures.
