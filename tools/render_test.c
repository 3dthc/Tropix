/* Offline engine test: plays every preset through the real engine and writes what it hears.
 *   cc -O2 -I<mpc-vst-plugins>/wrapper -Isrc tools/render_test.c -lm -lpthread -o render_test
 *   ./render_test engine <out dir> [first preset] [last preset]
 * For each preset: a phrase that suits its type (chords and a melody, a bass line, or the kit's hits), written to
 * <out>/<nnn>.wav (44.1 kHz stereo). Prints each preset's peak and loudness, and the worst render time per
 * 128-frame block. Exit status 1 on silence, clipping or a sound that did not load. */
#include "../src/engine.c"

static void put_le(FILE *f, uint32_t v, int n) { for (int i = 0; i < n; i++) fputc((v >> (8 * i)) & 255, f); }

static void write_wav(const char *path, const int16_t *a, size_t frames) {
    FILE *f = fopen(path, "wb");
    if (!f) return;
    fwrite("RIFF", 1, 4, f); put_le(f, 36 + frames * 4, 4); fwrite("WAVEfmt ", 1, 8, f);
    put_le(f, 16, 4); put_le(f, 1, 2); put_le(f, 2, 2); put_le(f, 44100, 4); put_le(f, 44100 * 4, 4);
    put_le(f, 4, 2); put_le(f, 16, 2); fwrite("data", 1, 4, f); put_le(f, frames * 4, 4);
    fwrite(a, 4, frames, f);
    fclose(f);
}

typedef struct { int at, st, d1, d2; } sev_t;   /* at: block index */
static double block_us(struct timespec a, struct timespec b) { return (b.tv_sec - a.tv_sec) * 1e6 + (b.tv_nsec - a.tv_nsec) / 1e3; }

#define BPS 344                      /* blocks per second (128 frames) */
static int add(sev_t *sc, int n, double t0, double t1, int key, int vel) {
    sc[n++] = (sev_t){ (int)(t0 * BPS), 0x90, key, vel };
    sc[n++] = (sev_t){ (int)(t1 * BPS), 0x80, key, 0 };
    return n;
}

int main(int argc, char **argv) {
    if (argc < 3) return 2;
    const mpc_engine_t *E = mpc_engine();
    void *s = E->create(argv[1]);
    inst_t *S = s;
    int bad = 0, first = argc > 3 ? atoi(argv[3]) : 0, last = argc > 4 ? atoi(argv[4]) : NPRESET - 1;
    const int B = 128;
    E->set_param(s, "lfo_bpm", "100");
    double worst_all = 0;
    for (int pr = first; pr <= last && pr < NPRESET; pr++) {
        char v[16];
        snprintf(v, sizeof v, "%d", pr);
        E->set_param(s, "preset", v);
        int16_t tmp[256];
        for (int w = 0; w < 4000 && need_loading(S); w++) { E->render(s, tmp, B); usleep(2000); }
        if (need_loading(S)) { printf("FAIL %03d %-22s did not load\n", pr + 1, PRESET_NAME[pr]); bad = 1; continue; }
        sev_t sc[256]; int n = 0;
        int ty = PRESET_TYPE[pr];
        double T = 6.0;
        if (ty == 6) {                                   /* percussion: a groove over the kit's keys */
            int keys[8] = { 36, 38, 46, 47, 40, 53, 58, 60 };
            for (int k = 0; k < 24; k++) n = add(sc, n, 0.15 * k, 0.15 * k + 0.1, keys[k % 8] + (k % 5 == 4 ? 12 : 0), 70 + (k * 37) % 57);
            if (PRESET_VAL[pr][0] >= 0) n = add(sc, n, 3.8, 4.0, 72, 110);
        } else if (ty == 5) {                            /* bass: a line */
            int keys[8] = { 36, 36, 43, 41, 36, 48, 46, 43 };
            for (int k = 0; k < 8; k++) n = add(sc, n, 0.3 * k, 0.3 * k + 0.22, keys[k], 100);
            n = add(sc, n, 2.6, 3.6, 33, 120);
        } else {                                         /* chords, then a melody */
            int ch[2][3] = { { 60, 64, 67 }, { 57, 62, 65 } };
            for (int c = 0; c < 2; c++) for (int j = 0; j < 3; j++) n = add(sc, n, 1.0 * c, 1.0 * c + 0.85, ch[c][j], 95);
            int mel[6] = { 72, 74, 76, 79, 76, 74 };
            for (int k = 0; k < 6; k++) n = add(sc, n, 2.1 + 0.3 * k, 2.1 + 0.3 * k + 0.32, mel[k], 80 + 7 * k);
            n = add(sc, n, 4.0, 5.0, 72, 100);
        }
        int nb = (int)(T * BPS);
        int16_t *a = calloc((size_t)nb * B * 2, sizeof(int16_t));
        double worst = 0, sum = 0; int peak = 0;
        for (int b = 0; b < nb; b++) {
            for (int k = 0; k < n; k++) if (sc[k].at == b) { uint8_t m[3] = { (uint8_t)sc[k].st, (uint8_t)sc[k].d1, (uint8_t)sc[k].d2 }; E->midi(s, m, 3); }
            struct timespec t0, t1;
            clock_gettime(CLOCK_MONOTONIC, &t0);
            E->render(s, a + (size_t)b * B * 2, B);
            clock_gettime(CLOCK_MONOTONIC, &t1);
            double us = block_us(t0, t1);
            if (us > worst) worst = us;
        }
        for (size_t i = 0; i < (size_t)nb * B * 2; i++) { int x = abs(a[i]); if (x > peak) peak = x; sum += (double)a[i] * a[i]; }
        double rms_db = 10 * log10(sum / ((double)nb * B * 2) / (32768.0 * 32768.0) + 1e-12);
        double pk_db = 20 * log10(peak / 32768.0 + 1e-12);
        char path[1200];
        snprintf(path, sizeof path, "%s/%03d.wav", argv[2], pr + 1);
        write_wav(path, a, (size_t)nb * B);
        free(a);
        const char *flag = peak < 300 ? "SILENT" : peak > 31000 ? "HOT" : "";
        if (peak < 300) bad = 1;
        printf("%03d %-22s peak %6.1f dB  rms %6.1f dB  worst block %5.0f us %s\n", pr + 1, PRESET_NAME[pr], pk_db, rms_db, worst, flag);
        if (worst > worst_all) worst_all = worst;
        unsigned char m[3] = { 0xB0, 120, 0 };
        E->midi(s, m, 3);
        for (int b = 0; b < 40; b++) E->render(s, tmp, B);
    }
    printf("worst block overall: %.0f us (of 2902)\n", worst_all);
    E->destroy(s);
    return bad;
}
