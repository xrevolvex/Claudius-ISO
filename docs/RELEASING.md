# Releasing Claudius

**Every push to `main`** builds the ISO, boots it in QEMU and publishes a **pre-release** called
`v1.0-build.N` with the ISO, its checksum, the build log and boot-test screenshots. Only the five newest
pre-releases are kept.

**To publish an official release**, try the newest pre-release first. When you're happy, tag the commit:

```bash
git tag v1.0          # or v1.1, v2.0...
git push origin v1.0
```

or on GitHub: **Releases → Draft a new release → Choose a tag → type `v1.0` → Create new tag**, then publish.

The tag starts a fresh build, and the result becomes the release marked **Latest**. That's the one the
README's download link points to.

To change the version shown in Claudius itself (boot screen, About, terminal), edit `CLAUDIUS_VERSION`
and `CLAUDIUS_CODENAME` in `claudius.conf` first.
