# Run the demo without Git

The demo can be delivered as one ZIP containing a `Wanda` folder. You do not need
Git, Node, a GPU or any application packages to run it. **Python 3.11 or newer is
still required.** This is a source bundle, not an installer or a completed V1.

## Open Wanda

1. Download the demo ZIP linked in the morning handoff or the pull request's
   successful **V0 tests** run, under **Artifacts → Wanda-demo.zip**. GitHub may
   require you to sign in. CI downloads expire after seven days.
2. Extract the ZIP fully. On Windows, choose **Extract All** before opening files.
3. Open the extracted `Wanda` folder. Mac: double-click **Start Wanda.command**.
   Windows: double-click **Start Wanda.bat**. On Linux, run `python3 -m wanda`
   from that folder.
4. Keep the launcher window open. Use **Stop Wanda** in the same folder when done.
5. Follow the [five-minute walkthrough](MORNING_HANDOFF.md). The default scripted
   demo and simulated home need no key. Live voice needs your private configuration
   and a separate consent step.

The bundle contains no keys, saved memories, recordings or household settings.
Those remain in Wanda's private data folder outside the extracted source. Existing
private configuration on this computer is reused; the bundle does not reset it.
If another Wanda copy is already running with the same private data folder, the
launcher reopens that instance. Stop it before testing a newer bundle.

The ZIP records executable permissions for Mac launchers. Operating-system
download/security prompts and each desktop's extraction behavior still require
hands-on verification; do not disable security controls to run it. If the launcher
reports missing Python, install it from [python.org](https://www.python.org/downloads/).

## Developer build and provenance

Run these commands from a Git checkout. The extracted demo intentionally omits
development tests and build tools.

```sh
python3 scripts/build_demo.py
python3 scripts/build_demo.py --ref HEAD --output dist/Wanda-demo.zip
```

Building requires Git and Python. Running the extracted app requires only Python.
The builder resolves one committed revision and reads its Git blobs, so it never
packages unsaved edits, untracked files, ignored runtime state or the Git database.
It includes runtime code, launchers, browser assets, documentation and configuration
templates; development tests and the paid voice harness are not included.

`Wanda/BUILD_INFO.json` identifies the source commit and lists file hashes and
permissions. ZIP ordering and timestamps are fixed, allowing repeated builds of
the same committed tree with this builder to be compared. The manifest supports
inspection; it is not a signature or a substitute for trusting the source.
Existing output files are refused rather than overwritten. Choose a new name.

CI builds the bundle only after the full Python/platform and browser jobs succeed.
It uploads the ZIP as a single file using GitHub's documented
[artifact upload option](https://github.com/actions/upload-artifact#upload-an-individual-file-unzipped),
preserving the permissions recorded inside our ZIP. No release is published and
no PR is merged. For pull requests, the manifest identifies GitHub’s tested
preview commit, which is not a merge into main. The checkpoint links its branch
head and records checksum/reproduction evidence.

Remove this packaging increment to return to checkout-based launch. Removing an
extracted source folder does not delete the separate private data folder. Do not
delete your private data as part of upgrading the demo.
