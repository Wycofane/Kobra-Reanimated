# Kobra-Reanimated

A community-maintained fork of [Kobra](https://github.com/VenomModding/Kobra) (the Greyhound/Wraith Archon asset extractor for Call of Duty games) — **revived for the 2026 Steam update of Black Ops II**.

Maintained by [Wycofane](https://github.com/Wycofane).

---

## Why this fork exists

On the current Steam build of **Black Ops II** (Zombies), Kobra / Greyhound fail with:

> *"This game is supported, but the current update is not. Or maybe you're running a mod. Please wait for an upcoming patch for support."*

**Root cause:** Kobra locates the BO2 asset pools inside the running game by scanning for two hardcoded byte signatures. The 2026 Steam update changed the compiled instruction sequence around the first signature (the sequence now uses `ebx` instead of `esi`, plus an added `push ebx`), so the old pattern no longer matches anywhere in the game module — and Kobra's fixed read offsets no longer line up with the pool immediates.

### The fix (in `src/WraithXCOD/WraithXCOD/GameBlackOps2.cpp`)

1. **Signature string**: `"56 51 FF D2 8B F0 83 C4 04 85 F6"` → `"53 51 FF D2 8B D8 83 C4 04 85 DB"`
2. **Read offset**: pool-sizes immediate is read at `DBAssetsScan + 0x3B` → **`+ 0x28`** in the updated build (the `push ebx` shifted the immediate by 19 bytes)
3. **Built-in offsets**: the current build was added to `ZombieModeOffsets` as a verified entry (`{ 0xC87798, 0xC873D8, 0x2B43380, 0 }`), with the legacy entry kept as fallback — so the fast path works even if the heuristic ever needs updating again

Every value was validated against the running game (asset pools live-check, `defaultvehicle` xmodel verification, pool sizes 5200 anims / 1400 models) before being committed.

### Using a patched binary without building?

If you downloaded the official Kobra.exe release and don't want to compile, `tools/patch_kobra.py` applies the same two byte-level changes to your local copy — with an SHA-256 safety gate that refuses any other build:

```powershell
python tools/patch_kobra.py              # patches .\Kobra.exe -> Kobra-patched.exe
python tools/patch_kobra.py --verify     # just report what the file is
```

It never modifies your original download. See [docs/PATCH_EVIDENCE.md](docs/PATCH_EVIDENCE.md) for the full technical documentation of how the fix was found and verified.

*The patched binary approach produces exactly the same result as building this fork from source.*

## Known issue

Repeated **Load Game** clicks while the game's asset pools are heavily loaded can take a few seconds and look frozen (Kobra rebuilds the whole asset list synchronously, with no progress indicator for loads; CPU sits low because it is mostly waiting on cross-process reads). Click Load **once** and wait. Proper progress UI and speedups are on the roadmap.

## Roadmap

- Progress dialog for Load Game (like the export flow already has)
- Batched pool reads (one big cross-process read per pool instead of thousands of small ones)
- Thread-safe asset-list swap (avoid GUI races on reload)

## Requirements

* Windows 10 x64 or above
* Microsoft Visual Studio 2017 Runtime ([x86](https://aka.ms/vs/16/release/vc_redist.x86.exe) and [x64](https://aka.ms/vs/16/release/vc_redist.x64.exe))
* Official copies of the games (only the latest copies from official distributors are tested)

## Links
* Upstream repository: [VenomModding/Kobra](https://github.com/VenomModding/Kobra)
* Greyhound Wiki (usage, settings, FAQs): [Wiki](https://scobalula.github.io/Greyhound/)
* Change Log: [CHANGELOG.md](CHANGELOG.md)

## License/Disclaimer

Kobra, like Greyhound, Wraith Archon and the WraithX Library, is licensed under the General Public License 3.0, you are free to use Kobra, both it and its source code, under the terms of the GPL. Kobra is distributed in the hope it will be useful to, but it comes WITHOUT ANY WARRANTY, without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE, see the [LICENSE](LICENSE) file for more information.

This repo is in no shape or form associated (apart from being a fork of course) with Scobalula, DTZxPorter or Activision and the developers. These tools are developed to allow users access to assets for use in other Call of Duty SDKs (such as the Black Ops III Mod Tools) and for use in 3D art such as YouTube thumbnails, etc. The assets extracted by these tools are property of their respective owners and what you do with the assets is your own responsbility.

## Credits/Contributors

* Wycofane - 2026 BO2 Steam update compatibility fix (this fork)
* JustVenom - Re-adding FX and GDT support and old Kobra maintainer
* hindercanrun - New Kobra maintainer
* Scobalula - Developer/Maintainer/Research (Greyhound)
* Blakintosh - MWR Material Support
* Eric Maynard - Help on BOCW from ModelGetter, ZM Hashes for BOCW Base
* DTZxPorter - Original Developer of the entire Wraith Project, Game Research
* ID-Daemon - Game Research

**If you use Kobra in any of your projects, it would be highly appreciated if you credit the people/parties listed in the Credits list.**
