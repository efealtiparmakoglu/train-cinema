#!/usr/bin/env python3
"""train-cinema dogrulama kapilari (Blender'siz: python3 tests/verify.py)"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mekanik import (BIYEL_L, FAZ_SAG, FAZ_SOL, KRANK_R, TEKER_R, TAHIRIK_X,
                     Z_SILINDIR, pin_pozisyonu, yurutucu)


def main():
    ok_adet, fail_adet = 0, 0

    def kapil(ad, kosul, detay=""):
        nonlocal ok_adet, fail_adet
        if kosul:
            ok_adet += 1
            print(f"  [ok] {ad} {detay}")
        else:
            fail_adet += 1
            print(f"  [FAIL] {ad} {detay}")

    # 1) pistongerisi: slider-crank analitik — max-min tam 2*krank_r
    def kros(x_pin, z_pin):
        return x_pin + math.sqrt(max(0.0, BIYEL_L ** 2 - (z_pin - Z_SILINDIR) ** 2))

    xc, zc = TAHIRIK_X[1], TEKER_R
    f_maks = kros(xc + KRANK_R * math.sin(math.pi / 2),
                  zc + KRANK_R * math.cos(math.pi / 2))
    f_min = kros(xc + KRANK_R * math.sin(3 * math.pi / 2),
                 zc + KRANK_R * math.cos(3 * math.pi / 2))
    kurs = f_maks - f_min
    kapil("piston kursu = 2*krank_r (analitik)", abs(kurs - 2 * KRANK_R) < 1e-9,
          f"({kurs:.9f} ~ {2 * KRANK_R:.9f})")

    # 2) yan itici düzlüğü: aynı tarafın 3 pini daima aynı z'de (rod rigid)
    en_fark = 0.0
    k = 0.0
    while k <= 2 * math.pi:
        d = yurutucu(k)
        zs = [p[1] for p in d["yan_itici"]["sol"]]
        en_fark = max(en_fark, max(zs) - min(zs))
        k += math.radians(5)
    kapil("yan itici pimleri ayni hizada (sabit faz)", en_fark < 1e-9,
          f"(maks z farki {en_fark:.2e})")

    # 3) quartering: sag krank her aninnda sol + 90 derece
    tamam = True
    for k in (0.0, 0.7, 1.9, 3.1):
        d = yurutucu(k)
        p_sol = d["pinler"]["sol1"]
        p_sag = d["pinler"]["sag1"]
        # pin acilari: atan2 farki
        a1 = math.atan2(p_sol[0] - TAHIRIK_X[1], p_sol[1] - TEKER_R)
        a2 = math.atan2(p_sag[0] - TAHIRIK_X[1], p_sag[1] - TEKER_R)
        if abs(((a2 - a1 - FAZ_SAG + math.pi) % (2 * math.pi)) - math.pi) > 1e-9:
            tamam = False
    kapil("quartering 90 derece (sag = sol + 90)", tamam)

    # 4) biyel uzuncuğu sabit: krosbas-pin mesafesi her acida L
    en_sapma = 0.0
    k = 0.0
    while k <= 2 * math.pi:
        d = yurutucu(k)
        x_pin, z_pin = d["pinler"]["sag1"]
        xk = d["krosbas"]["sag"]
        L = math.hypot(xk - x_pin, Z_SILINDIR - z_pin)
        en_sapma = max(en_sapma, abs(L - BIYEL_L))
        k += math.radians(5)
    kapil("ana biyel boyu sabit", en_sapma < 1e-9, f"(maks sapma {en_sapma:.2e})")

    # 5) krank pimleri tam krank yaricapinda doner (orbit)
    en_sapma = 0.0
    for k in (0.0, 0.9, 2.2, 4.4):
        d = yurutucu(k)
        for ad, (px, pz) in d["pinler"].items():
            cx = TAHIRIK_X[int(ad[-1])]
            r = math.hypot(px - cx, pz - TEKER_R)
            en_sapma = max(en_sapma, abs(r - KRANK_R))
    kapil("krank pimi orbati = krank_r", en_sapma < 1e-9,
          f"(maks sapma {en_sapma:.2e})")

    # 6) determinizm
    kapil("determinizm", yurutucu(2.71) == yurutucu(2.71))

    print(f"\n{'TUM KAPILAR GECTI' if fail_adet == 0 else 'KAPILARDA FAIL VAR'}"
          f" ({ok_adet} ok, {fail_adet} fail)")
    sys.exit(0 if fail_adet == 0 else 1)


if __name__ == "__main__":
    main()
