/* Offline test of the shared favourites: one list for every Tropix on the MPC, kept in <data dir>/favorites.txt.
 * Needs no instruments (it only taps the faceplate).
 *
 *   cc -O2 -I../mpc-vst-plugins/wrapper -Isrc tools/fav_test.c -lm -lpthread -o /tmp/fav_test && /tmp/fav_test /tmp/favdir
 */
#include "../src/engine.c"

static const mpc_engine_t *E;
static void *S;
static int16_t buf[2 * 128];
static int fails;
#define CHECK(c, ...) do { int ok_ = (c); printf("%s ", ok_ ? "ok  " : "FAIL"); printf(__VA_ARGS__); printf("\n"); if (!ok_) fails++; } while (0)

static void set(const char *k, const char *v) { E->set_param(S, k, v); }
static float getf(const char *k) { char b[128]; E->get_param(S, k, b, sizeof b); return (float)atof(b); }
static void seti(const char *k, int v) { char b[16]; snprintf(b, sizeof b, "%d", v); set(k, b); }
static void run(double sec) { for (int n = (int)(sec * 44100 / 128); n > 0; n--) E->render(S, buf, 128); }
static void tap(const char *k) { set(k, "1"); run(0.2); usleep(300000); }   /* one tap on MPC's screen, then a moment (past TAP_S, a wall-clock window) */
static int file_has(const char *path, const char *line) {
    FILE *f = fopen(path, "r"); char b[200]; int hit = 0;
    while (f && fgets(b, sizeof b, f)) { b[strcspn(b, "\r\n")] = 0; if (!strcmp(b, line)) hit = 1; }
    if (f) fclose(f);
    return hit;
}
static int fav_bits(void) {
    int w = 0; char k[16];
    for (int i = 0; i < 10; i++) { snprintf(k, sizeof k, "fav_%d", i); w |= (int)getf(k); }
    return w;
}

int main(int argc, char **argv) {
    if (argc < 2) return 2;
    char path[1100];
    snprintf(path, sizeof path, "%s/../user/favorites.txt", argv[1]);
    remove(path);
    E = mpc_engine();
    S = E->create(argv[1]);
    int a = 5, b = 40;                               /* two presets, by index; names come from the preset table */
    const char *na = PRESET_NAME[a], *nb = PRESET_NAME[b];

    seti("preset", a); tap("fav_tap");
    seti("preset", b); tap("fav_tap");
    CHECK(getf("fav") == 1 && fav_bits() != 0, "FAV stars the preset and the project mirrors it");
    CHECK(file_has(path, na) && file_has(path, nb), "both are written to favorites.txt (%s, %s)", na, nb);

    void *S1 = S, *S2 = E->create(argv[1]);
    S = S2;
    seti("preset", a);
    CHECK(getf("fav") == 1, "a second Tropix sees the star at once");
    tap("fav_tap");
    CHECK(!file_has(path, na) && file_has(path, nb), "taking it off there updates the file");
    S = S1; run(0.01); seti("preset", a);
    CHECK(getf("fav") == 0, "and the first Tropix follows");
    E->destroy(S2);

    E->destroy(S1);
    g_fav_loaded = 0; memset(g_fav, 0, sizeof g_fav);  /* as if MPC had restarted: only the file is left */
    S = E->create(argv[1]);
    seti("preset", b);
    CHECK(getf("fav") == 1, "after a restart %s is still starred", nb);
    seti("preset", a);
    CHECK(getf("fav") == 0, "and %s is not", na);

    char key[16], val[16];                           /* a project saved while preset a was still starred */
    snprintf(key, sizeof key, "fav_%d", a / 13); snprintf(val, sizeof val, "%d", 1 << (a % 13));
    set(key, val); seti("preset", a);
    CHECK(getf("fav") == 0, "reopening a project saved with %s starred does not star it again", na);
    CHECK(((int)getf(key) >> (a % 13) & 1) == 0, "and the project's copy follows the list");
    seti("preset", b);
    CHECK(getf("fav") == 1, "and %s keeps its star", nb);

    E->destroy(S); remove(path);                     /* the first time, before there is a favorites.txt: */
    g_fav_loaded = 0; memset(g_fav, 0, sizeof g_fav);
    S = E->create(argv[1]);
    set(key, val); seti("preset", a);
    CHECK(getf("fav") == 1, "a project from before the shared list brings its star");
    tap("fav_tap");
    set(key, val); seti("preset", a);
    CHECK(getf("fav") == 0, "once a star is changed by hand, projects no longer add stars");
    CHECK(fav_bits() == 0 && !file_has(path, na) && !file_has(path, nb), "all stars off again");
    /* NEXT, with MPC's echo of the tap arriving late (after the faceplate redrew): one preset on, not two */
    seti("preset", 10); usleep(300000);
    int from = (int)getf("preset");
    set("next", "1"); run(0.18); usleep(180000); set("next", "0"); run(0.02);   /* audio runs as on a device */
    int to = (int)getf("preset");
    set("prev", "1"); run(0.18); usleep(180000); set("prev", "0"); run(0.02);
    int m[NPRESET], nm = list_members(S, m), want = -1;
    for (int k = 0; k < nm; k++) if (m[k] == from) want = m[(k + 1) % nm];
    CHECK(to == want && (int)getf("preset") == from, "a late echo of NEXT / PREV steps one preset, not two (%d -> %d (want %d) -> %d)",
          from, to, want, (int)getf("preset"));
    usleep(300000); set("next", "1"); run(0.02); int p1 = (int)getf("preset");
    usleep(300000); set("next", "0"); run(0.02); int p2 = (int)getf("preset");
    CHECK(p1 == to && p2 != p1 && p2 != from, "two taps a moment apart step twice (%d -> %d -> %d)", from, p1, p2);
    E->destroy(S);
    remove(path);
    printf(fails ? "%d FAILED\n" : "all passed\n", fails);
    return fails != 0;
}
