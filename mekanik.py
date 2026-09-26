#!/usr/bin/env python3
"""train-cinema — buharli lokomotif yurutucu mekanigi (SAF MATEMATIK).

Konvansiyon: lokomotif +X yonunde, yan gorunum (x ileri, z yukari).
    Tekerlek merkezi  : (cx, cz=teker_r)
    Krank pimi        : (cx + rc*sin(t), cz + rc*cos(t))
    Krosbas (piston)  : silindir ekseninde (z = z_silindir), biyel boyu L:
        x_kros = x_pin + sqrt(L^2 - (z_pin - z_silindir)^2)
    Krank fazlari: sol taraf butun tahrik tekerlerinde ayni faz (coupled rod),
        sag taraf sol + 90 derece (quartering).

Fonksiyonel olma capisi: pistongerinme/ilerleme tam 2*rc olur (merkeziyetli
biyel yaklasimi 2. dereceye kadar hatasiz), kollar tekerlerle ayni hizda
doner, kayma yok.
"""

import math

TEKER_R = 0.8          # tahrik teker yaricapi
KLEVIN_R = 0.45        # on takim (pony) teker
KRANK_R = 0.35         # krank pimi yaricapi (istriyere)
BIYEL_L = 2.70         # ana biyel (main rod) uzunlugu
Z_SILINDIR = 0.62      # silindir/piston ekseni yuksekligi
TAHIRIK_X = (0.0, 2.1, 4.2)   # 3 tahrik teker x pozisyonlari
PONY_X = (-2.1,)       # on takim tekerleri
FAZ_SOL = 0.0
FAZ_SAG = math.pi / 2


def pin_pozisyonu(cx, cz, theta, krank_r=KRANK_R):
    return (cx + krank_r * math.sin(theta), cz + krank_r * math.cos(theta))


def krosbas_x(x_pin, z_pin, biyel_l=BIYEL_L, z_silindir=Z_SILINDIR):
    dz = z_pin - z_silindir
    kok = max(0.0, biyel_l ** 2 - dz ** 2)
    return x_pin + math.sqrt(kok)


def yurutucu(theta):
    """Tum mekanik durum. theta = sol taraf krank acisi (radyan).

    Donen: her teker icin aci, krank pinleri, yan itici (side rod) ucleri,
    krosbas, piston pin konumu. Sozluk doner (Blender tarafı bununla pozlar).
    """
    durum = {"theta": theta, "tekerler": {}, "krosbas": {}, "pinler": {}}
    for taraf, faz in (("sol", FAZ_SOL), ("sag", FAZ_SAG)):
        pins = []
        for i, cx in enumerate(TAHIRIK_X):
            aci = theta + faz
            pin = pin_pozisyonu(cx, TEKER_R, aci)
            pins.append(pin)
            durum["tekerler"][f"{taraf}{i}"] = aci
            durum["pinler"][f"{taraf}{i}"] = pin
        # yan itici: ayni fazdaki pinleri baglar — dogru duz cizgi
        durum.setdefault("yan_itici", {})[taraf] = pins
        # ana biyel: ortadaki tahrik tekeri
        x_pin, z_pin = pins[1]
        durum["krosbas"][taraf] = krosbas_x(x_pin, z_pin)
    return durum


if __name__ == "__main__":
    # hızlı bakı: bir turda piston yer değiştirme genligi = 2*krank_r olmali
    en_cok, en_az = -1e9, 1e9
    k = 0.0
    while k <= 2 * math.pi + 1e-9:
        d = yurutucu(k)
        x = d["krosbas"]["sol"]
        en_cok = max(en_cok, x)
        en_az = min(en_az, x)
        k += math.radians(5)
    print(f"piston kursu: {en_cok - en_az:.4f} m (beklenen {2 * KRANK_R:.4f})")
