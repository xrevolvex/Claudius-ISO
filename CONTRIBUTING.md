# Contributing to Claudius

Thanks for helping! Claudius aims to stay **light, fast and friendly**, so every change should keep RAM use low on a 2 GB VM while still making good use of bigger machines.

1. Fork the repo and create a branch.
2. Make your change (see [docs/BUILDING.md](docs/BUILDING.md) for where things live).
3. Push to your fork. GitHub Actions builds and boot-tests the ISO there, and you can check the screenshots in your fork's Releases.
4. Open a pull request with a short description and, for visual changes, a screenshot.

Guidelines:

- Prefer Debian packages over downloads from other sites.
- New background services need a good reason. Check `claudius ram` before and after.
- Shell scripts must be POSIX `sh` or `bash`, and pass `bash -n`.
- Artwork must be original and CC BY-SA 4.0 compatible.

Bugs and ideas: please open an issue.
