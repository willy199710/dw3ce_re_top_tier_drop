// version.dll proxy for DW3CE_RE: applies in-memory code patches, never touches the exe on disk.
// All real version.dll exports are forwarded to System32.
#include <windows.h>
#include <wchar.h>

#pragma comment(linker, "/export:GetFileVersionInfoA=C:\\Windows\\System32\\version.GetFileVersionInfoA,@1")
#pragma comment(linker, "/export:GetFileVersionInfoByHandle=C:\\Windows\\System32\\version.GetFileVersionInfoByHandle,@2")
#pragma comment(linker, "/export:GetFileVersionInfoExA=C:\\Windows\\System32\\version.GetFileVersionInfoExA,@3")
#pragma comment(linker, "/export:GetFileVersionInfoExW=C:\\Windows\\System32\\version.GetFileVersionInfoExW,@4")
#pragma comment(linker, "/export:GetFileVersionInfoSizeA=C:\\Windows\\System32\\version.GetFileVersionInfoSizeA,@5")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExA=C:\\Windows\\System32\\version.GetFileVersionInfoSizeExA,@6")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExW=C:\\Windows\\System32\\version.GetFileVersionInfoSizeExW,@7")
#pragma comment(linker, "/export:GetFileVersionInfoSizeW=C:\\Windows\\System32\\version.GetFileVersionInfoSizeW,@8")
#pragma comment(linker, "/export:GetFileVersionInfoW=C:\\Windows\\System32\\version.GetFileVersionInfoW,@9")
#pragma comment(linker, "/export:VerFindFileA=C:\\Windows\\System32\\version.VerFindFileA,@10")
#pragma comment(linker, "/export:VerFindFileW=C:\\Windows\\System32\\version.VerFindFileW,@11")
#pragma comment(linker, "/export:VerInstallFileA=C:\\Windows\\System32\\version.VerInstallFileA,@12")
#pragma comment(linker, "/export:VerInstallFileW=C:\\Windows\\System32\\version.VerInstallFileW,@13")
#pragma comment(linker, "/export:VerLanguageNameA=C:\\Windows\\System32\\version.VerLanguageNameA,@14")
#pragma comment(linker, "/export:VerLanguageNameW=C:\\Windows\\System32\\version.VerLanguageNameW,@15")
#pragma comment(linker, "/export:VerQueryValueA=C:\\Windows\\System32\\version.VerQueryValueA,@16")
#pragma comment(linker, "/export:VerQueryValueW=C:\\Windows\\System32\\version.VerQueryValueW,@17")

typedef struct {
    const char *key;          // ini key under [Patches]
    const char *desc;
    DWORD rva;                // expected RVA of sig[0] in game build 1.0.2.0
    BYTE sig[20];             // original bytes (must match before patching)
    int off;                  // patch offset inside sig
    int len;
    BYTE patch[8];
    BYTE *addr;               // resolved address; entries sharing a key are applied all-or-nothing
} Patch;

static Patch g_patches[] = {
    // GenerateWeapon: element table {FIRE,THUNDER,ZAN,WIND} -> all four set to the element chosen in the ini.
    // The patch bytes are filled in at runtime from [Patches] Element (see apply_element_setting).
    { "Element", "weapon element", 0x1516919,
      {0x00,0x00,0x00,0xbb,0x04,0x00,0x00,0x00,0xc7,0x45,0x67,0x04,0x08,0x10,0x20,0x48,0x8d,0x45,0x8b,0x48},
      11, 4, {0x10,0x10,0x10,0x10} },
    // skill value fn: rand within tier -> always ValueRand-1 (cmovl ecx,eax -> nop)
    { "MaxSkillRoll", "weapon/item skill value always top of tier", 0x1537669,
      {0xf3,0x0f,0x59,0xd0,0xf3,0x0f,0x2c,0xc2,0x3b,0xc1,0x0f,0x4c,0xc8,0xeb,0x02,0x33,0xc9,0x0f,0xaf,0x73},
      10, 3, {0x0f,0x1f,0x00} },
    // guard weapon skill value: rand within RandomSeed -> always max
    { "MaxGuardSkillRoll", "guard weapon skill value always max", 0x1516c51,
      {0xf3,0x0f,0x59,0xd0,0xf3,0x0f,0x2c,0xc2,0x3b,0xc1,0x0f,0x4c,0xc8,0xeb,0x02,0x8b,0xcf,0x80,0xfb,0x01},
      10, 3, {0x0f,0x1f,0x00} },
    // skill value fn: tier when no SkillItemRandRank entry matches -> 3 instead of 0.
    // Weapons only scan entries 0..3, items scan 0..4, so data [0,0,0,0,100] gives weapons tier 3, items tier 4.
    // xor r8d,r8d -> push 3; pop rsi   (esi = default tier)
    { "SkillTierFix", "weapon skill tier defaults to 3", 0x15375f7,
      {0x04,0x01,0x00,0x00,0x48,0x8b,0x48,0x18,0x45,0x33,0xc0,0x45,0x0f,0xb6,0xce,0x49,0x83,0xc1,0x04,0x33},
      8, 3, {0x6a,0x03,0x5e} },
    // ... and the match path takes the tier from rdx (same counter as r8d) since r8d is no longer zeroed:
    // mov esi,r8d -> mov esi,edx; nop
    { "SkillTierFix", "weapon skill tier match path", 0x153761a,
      {0x48,0x83,0xc1,0x04,0x49,0x3b,0xd1,0x7c,0xed,0xeb,0x03,0x41,0x8b,0xf0,0x48,0x8d,0x4c,0x24,0x50,0xe8},
      11, 3, {0x8b,0xf2,0x90} },
    // guard weapon skill tier default -> 3: (redundant) and eax,0x7fff; mov r14,rdi -> push 3; pop r14; nop4
    { "GuardTierFix", "guard weapon skill tier defaults to 3", 0x1516bab,
      {0x8b,0x4d,0x67,0xbe,0x63,0x00,0x00,0x00,0x25,0xff,0x7f,0x00,0x00,0x4c,0x8b,0xf7,0x66,0x0f,0x6e,0xc0},
      8, 8, {0x6a,0x03,0x41,0x5e,0x0f,0x1f,0x40,0x00} },
    // enemy drop (0x141377df0): items 0..15 (meat bun / arrows / ATK up / DEF up, sizes S..LL) are upgraded one
    // size when GetComboCount()/8 > current size. Remove the combo check so the upgrade always happens:
    // jle (skip upgrade) -> 2-byte nop
    { "ComboUpgradeAlways", "dropped item always upgraded one size, ignoring combo count", 0x1377ee6,
      {0x99,0x83,0xe2,0x07,0x03,0xc2,0xc1,0xf8,0x03,0x3b,0xc7,0x7e,0x0e,0xff,0xc3,0xeb,0x0a,0xbf,0xff,0x00},
      11, 2, {0x66,0x90} },
};
#define NPATCH (sizeof(g_patches)/sizeof(g_patches[0]))

static WCHAR g_dir[MAX_PATH];
static HANDLE g_log = INVALID_HANDLE_VALUE;

static void plog(const char *fmt, ...)
{
    char buf[512]; va_list ap; DWORD n;
    if (g_log == INVALID_HANDLE_VALUE) return;
    va_start(ap, fmt); n = (DWORD)wvsprintfA(buf, fmt, ap); va_end(ap);
    WriteFile(g_log, buf, n, &n, NULL); WriteFile(g_log, "\r\n", 2, &n, NULL);
}

static int matches(const BYTE *p, const BYTE *sig)
{
    for (int i = 0; i < 20; i++) if (p[i] != sig[i]) return 0;
    return 1;
}

static int is_patched(const Patch *pt, const BYTE *p)
{
    for (int i = 0; i < 20; i++) {
        BYTE want = (i >= pt->off && i < pt->off + pt->len) ? pt->patch[i - pt->off] : pt->sig[i];
        if (p[i] != want) return 0;
    }
    return 1;
}

// [Patches] Element: 0 = vanilla random, 1 = Fire, 2 = Lightning, 3 = Slash (ZAN), 4 = Wind (EWeaponAttrFlag values)
static const BYTE  kElemFlag[5] = { 0, 0x04, 0x08, 0x10, 0x20 };
static const char *kElemDesc[5] = { "", "weapon element always Fire", "weapon element always Lightning",
                                    "weapon element always Slash", "weapon element always Wind" };

// Fills in the Element patch bytes; returns 0 when the patch should be skipped.
static int apply_element_setting(const WCHAR *ini)
{
    int elem = (int)GetPrivateProfileIntW(L"Patches", L"Element", (UINT)-1, ini);
    if (elem == -1)   // older ini files only have ZanOnly=0/1
        elem = GetPrivateProfileIntW(L"Patches", L"ZanOnly", 1, ini) ? 3 : 0;
    if (elem == 0) { plog("[Element] 0 = vanilla random element"); return 0; }
    if (elem < 0 || elem > 4) { plog("[Element] invalid value %d (use 0-4), keeping vanilla", elem); return 0; }
    for (int i = 0; i < NPATCH; i++) {
        Patch *pt = &g_patches[i];
        if (lstrcmpA(pt->key, "Element")) continue;
        for (int k = 0; k < pt->len; k++) pt->patch[k] = kElemFlag[elem];
        pt->desc = kElemDesc[elem];
    }
    plog("[Element] = %d (%s)", elem, kElemDesc[elem]);
    return 1;
}

static void get_text(BYTE *base, BYTE **start, DWORD *size)
{
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(base + ((IMAGE_DOS_HEADER *)base)->e_lfanew);
    IMAGE_SECTION_HEADER *s = IMAGE_FIRST_SECTION(nt);
    *start = NULL; *size = 0;
    for (int i = 0; i < nt->FileHeader.NumberOfSections; i++, s++)
        if (!lstrcmpA((const char *)s->Name, ".text")) { *start = base + s->VirtualAddress; *size = s->Misc.VirtualSize; }
}

static BYTE *resolve(Patch *pt, BYTE *base, BYTE *text, DWORD tsize)
{
    BYTE *p = base + pt->rva;
    // only touch the expected address if it lies inside .text (a different build could be smaller)
    if (p >= text && p + 20 <= text + tsize && (matches(p, pt->sig) || is_patched(pt, p))) return p;
    BYTE *hit = NULL;   // fallback: unique signature scan
    for (DWORD i = 0; i + 20 <= tsize; i++)
        if (matches(text + i, pt->sig)) { if (hit) return NULL; hit = text + i; }
    return hit;
}

static DWORD WINAPI patch_thread(LPVOID unused)
{
    WCHAR path[MAX_PATH];
    BYTE *base = (BYTE *)GetModuleHandleW(NULL), *text; DWORD tsize;
    (void)unused;

    lstrcpyW(path, g_dir); lstrcatW(path, L"dw3ce_re_top_tier_drop.log");
    g_log = CreateFileW(path, GENERIC_WRITE, FILE_SHARE_READ, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    lstrcpyW(path, g_dir); lstrcatW(path, L"dw3ce_re_top_tier_drop.ini");
    if (GetFileAttributesW(path) == INVALID_FILE_ATTRIBUTES) {   // installs from before the rename
        WCHAR old_ini[MAX_PATH];
        lstrcpyW(old_ini, g_dir); lstrcatW(old_ini, L"dw3ce_patch.ini");
        if (GetFileAttributesW(old_ini) != INVALID_FILE_ATTRIBUTES) {
            lstrcpyW(path, old_ini);
            plog("using old ini name dw3ce_patch.ini (please rename to dw3ce_re_top_tier_drop.ini)");
        } else plog("no ini found, using defaults");
    }

    {
        WCHAR exe[MAX_PATH], *name;
        GetModuleFileNameW(NULL, exe, MAX_PATH);
        name = wcsrchr(exe, L'\\'); name = name ? name + 1 : exe;
        if (lstrcmpiW(name, L"DW3CE_RE-Win64-Shipping.exe")) { plog("not the game exe, doing nothing"); return 0; }
    }
    get_text(base, &text, &tsize);
    plog("base=%p text=%p size=%lx", base, text, tsize);
    if (!apply_element_setting(path))
        for (int i = 0; i < NPATCH; i++) if (!lstrcmpA(g_patches[i].key, "Element")) g_patches[i].addr = (BYTE *)1;

    for (int tries = 0; tries < 600; tries++) {          // wait up to 60s in case code is unpacked late
        int pending = 0;
        for (int i = 0; i < NPATCH; i++) {
            Patch *pt = &g_patches[i];
            WCHAR wkey[64];
            BYTE *found[NPATCH];
            int ok = 1;
            if (pt->addr) continue;
            MultiByteToWideChar(CP_ACP, 0, pt->key, -1, wkey, 64);
            // Element is configured by value (handled in apply_element_setting), the rest are 0/1 toggles
            if (lstrcmpA(pt->key, "Element") && !GetPrivateProfileIntW(L"Patches", wkey, 1, path)) {
                plog("[%s] disabled in ini", pt->key);
                for (int j = i; j < NPATCH; j++) if (!lstrcmpA(g_patches[j].key, pt->key)) g_patches[j].addr = (BYTE *)1;
                continue;
            }
            // resolve every entry of this key first; apply none unless all are found
            for (int j = i; j < NPATCH; j++)
                if (!lstrcmpA(g_patches[j].key, pt->key) && !(found[j] = resolve(&g_patches[j], base, text, tsize))) ok = 0;
            if (!ok) { pending++; continue; }
            for (int j = i; j < NPATCH; j++) {
                Patch *q = &g_patches[j]; BYTE *p = found[j]; DWORD old;
                if (lstrcmpA(q->key, pt->key)) continue;
                if (!is_patched(q, p)) {
                    VirtualProtect(p + q->off, q->len, PAGE_EXECUTE_READWRITE, &old);
                    for (int k = 0; k < q->len; k++) p[q->off + k] = q->patch[k];
                    VirtualProtect(p + q->off, q->len, old, &old);
                    FlushInstructionCache(GetCurrentProcess(), p + q->off, q->len);
                }
                q->addr = p;
                plog("[%s] applied at rva %lx (%s)", q->key, (DWORD)(p - base), q->desc);
            }
        }
        if (!pending) { plog("done"); return 0; }
        Sleep(100);
    }
    for (int i = 0; i < NPATCH; i++)
        if (!g_patches[i].addr) plog("[%s] signature NOT found - skipped (game updated?)", g_patches[i].key);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        WCHAR *slash;
        DisableThreadLibraryCalls(inst);
        GetModuleFileNameW(inst, g_dir, MAX_PATH);
        slash = wcsrchr(g_dir, L'\\'); if (slash) slash[1] = 0;
        CloseHandle(CreateThread(NULL, 0, patch_thread, NULL, 0, NULL));
    }
    return TRUE;
}
