# Technical documentation (PATCH_EVIDENCE)

This file documents **how the fix was found and why the two byte-level changes are
correct**, so the work is reproducible and auditable. It contains no game assets
and no dumps — only facts about Kobra.exe and the analysis method used.

## 1. Why Kobra rejected the updated game

Kobra's Black Ops 2 loader (`GameBlackOps2::LoadOffsets`, visible in the upstream
GPL-3.0 source of VenomModding/Kobra) tries two paths for BO2 Zombies:

1. hard-coded pool offsets per known game build (one entry: `{ 0xD41240, 0xD40E80, 0x2BF8880 }`),
2. a heuristic fallback scanning the running game for two byte signatures:

```cpp
auto DBAssetsScan   = GameInstance->Scan("56 51 FF D2 8B F0 83 C4 04 85 F6");
auto StringTableScan = GameInstance->Scan("33 C9 66 89 0C 10 83 C0 02 83 F8 20");
// ...
auto GameOffsets = DBGameInfo(Read<uint32_t>(DBAssetsScan - 0xB),
                              Read<uint32_t>(DBAssetsScan + 0x3B),
                              Read<uint32_t>(StringTableScan - 0x2E), 0);
```

A 2026 Steam update changed the compiler output around the first signature:
the same instruction sequence now uses `ebx` instead of `esi` and one extra
instruction, so the 11-byte signature no longer matches anywhere. Neither Kobra
nor Greyhound of that vintage find the pools → the "current update is not
supported" message.

## 2. Findings against the updated game

Reading the running game's process memory **read-only** (no injection, no code
execution in the game, no files modified):

- The updated equivalent of the old pattern is present exactly once in the game's
  main module at address `0x597663`:
  `53 51 FF D2 8B D8 83 C4 04 85 DB`
  (`push ebx; push ecx; call edx; mov ebx,eax; add esp,4; test ebx,ebx`).
- Because of the added `push ebx` and register swap, Kobra's fixed read offsets no
  longer line up with the two pool immediates:
  - old layout: pools-array immediate at `hit - 0xB`, sizes-array immediate at `hit + 0x3B`
  - new layout: pools-array immediate is still at `hit - 0xB`
    (→ `0x00C87798`, the per-pool pointer array), but the sizes immediate moved to
    `hit + 0x28` (→ `0x00C873D8`, the per-pool sizes array).

## 3. The two fixes (and why they don't change anything else)

1. Replace Kobra's `.rdata` pattern literal (fixed 32-character string, VA
   `0x1402136D0`) with the new byte sequence. Same length, same meaning.
2. Correct the one displacement byte of Kobra's read instruction (`LEA RDX,[R14+0x3B]`
   at VA `0x14005AE58`) to `+0x28`, restoring the old semantics under the new layout.

Validation performed against a full snapshot of the running game:

| Check | Result |
|---|---|
| New pattern unique in all mapped game regions | yes (1 hit) |
| `read32(hit - 0xB)` | `0x00C87798` — live pointer array of asset pools |
| `read32(hit + 0x28)` | `0x00C873D8` — live per-pool sizes array |
| xmodel pool entry (`pools[5] = 0x012FECA8`, name at `+4 = 0x100A5BB1`) | contains `defaultvehicle` — Kobra's own verify check passes |
| pool sizes | xanim 5200 (`0x1450`), xmodel 1400 (`0x578`) — plausible |
| second signature (`33 C9 66 ...`) | still present at `0x7E03A6`, untouched |
| patched output SHA-256 | `d42882bedf0fa4a6fe31e1fbc5d61837f8c3172d899d6e53c95e49ab1a1ba811` |

Kobra's own hard-coded-table verification (`FirstXModelName == "defaultvehicle"`)
is the same mechanism upstream uses, so the patched loader follows exactly the
intended data flow: pools → `GameOffsetInfos` → asset enumeration → `defaultvehicle`
checksum → sizes → asset list.

## 4. Method summary

- Static analysis of the unmodified Kobra.exe (Ghidra-based decompiler; x64 PE).
- Same function identified in a second, statically readable build of the game
  family (Plutonium-shipped `t6zm.exe`, `2aff340f…`) to confirm the instruction
  table layout (`mov ecx,[eax*4+Pools]` / `mov edx,[eax*4+Sizes]` around the call).
- Passive read-only memory access to the user's own running game process to
  recover the updated byte layout; all conclusions cross-checked against a
  process snapshot with exact region accounting.
- The project never runs, patches or ships game code. The patcher refuses any
  build other than the one documented here by SHA-256.
