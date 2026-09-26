#!/usr/bin/env python3
"""train-cinema — fonksiyonel buharlı lokomotif + tender (Blender icinde).

Mimari: her parca kok bos nesnesine parentli; YURUTUCU mekanik mekanik.py'den
gelir. poz(refs, theta) ile:
    - tahrik tekerleri doner (krank pimleri child: dogru yerde dolanir)
    - yan iticiler (side rods) pimleri takip eder
    - ana biyel ortadaki sag kranka bagli, krosbasta
    - krosbas + piston rod silindir icinde ileri geri gider
Yani makine GERCEKTEN calisir: her karede kinematik kapidan gecen pozlar.

Yerlesim (+X on): pony -2.1 | tahrikler 0 / 2.1 / 4.2 | bogaz kabi -3.3..-0.9
kazan -0.6..4.6 | duman kutusu 4.6..5.7 | baca 5.15 | tender -4.6..-10.2
"""

import math

import bpy
from mathutils import Vector

from mekanik import (KRANK_R, TEKER_R, TAHIRIK_X, Z_SILINDIR, yurutucu)

MAT = {}


def mat_yap(ad, renk, rough=0.5, metalik=0.0):
    if ad in MAT:
        return MAT[ad]
    m = bpy.data.materials.new(ad)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (renk[0], renk[1], renk[2], 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metalik
    MAT[ad] = m
    return m


def kutu(ad, merkez, boyut, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=merkez)
    o = bpy.context.active_object
    o.name = ad
    o.scale = boyut
    o.data.materials.append(mat)
    return o


def silindir(ad, merkez, r, derinlik, mat, eksen="Z"):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=derinlik,
                                        location=merkez, vertices=32)
    o = bpy.context.active_object
    o.name = ad
    if eksen == "X":
        o.rotation_euler = (0, math.pi / 2, 0)
    elif eksen == "Y":
        o.rotation_euler = (math.pi / 2, 0, 0)
    o.data.materials.append(mat)
    return o


def cubuk_objesi(ad, r, mat):
    """Iki nokta arasinda gerilebilir birim cubuk; scale.z = boy."""
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=1.0,
                                        location=(0, 0, 0), vertices=16)
    o = bpy.context.active_object
    o.name = ad
    o.data.materials.append(mat)
    return o


def cubuk_ger(o, p0, p1):
    d = Vector(p1) - Vector(p0)
    o.location = (Vector(p0) + Vector(p1)) / 2
    o.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    o.scale = (1, 1, max(1e-4, d.length))


def teker_kur(ad, cx, cz, r, kalinlik, y, mat_jant, mat_ici, krankli=False,
              krank_faz_lokal=0.0):
    """Tekerlek: bos nesne (donus merkezi) + jant + flans + ic disk + ispitler.
    krankli ise krank pimi child — kok donunce pin dogru orbitte dolanir."""
    kok = bpy.data.objects.new(ad, None)
    kok.location = (cx, y, cz)
    bpy.context.collection.objects.link(kok)

    jant = silindir(f"{ad}_jant", (0, 0, 0), r, kalinlik, mat_jant, eksen="Y")
    jant.parent = kok
    flans_y = -(kalinlik / 2 + 0.02) if y > 0 else (kalinlik / 2 + 0.02)
    jel = silindir(f"{ad}_flans", (0, flans_y, 0), r + 0.025, 0.04,
                   mat_yap("Celik", (0.35, 0.36, 0.38), rough=0.3, metalik=0.9),
                   eksen="Y")
    jel.parent = kok
    disk = silindir(f"{ad}_govde", (0, 0, 0), r * 0.78, kalinlik + 0.04,
                    mat_ici, eksen="Y")
    disk.parent = kok
    for i in range(10):
        aci = 2 * math.pi * i / 10
        b = kutu(f"{ad}_ispit{i}", (0, 0, 0), (0.06, kalinlik + 0.05, r * 0.92),
                 mat_ici)
        b.parent = kok
        b.rotation_euler = (aci, 0, 0)
    if krankli:
        px = KRANK_R * math.sin(krank_faz_lokal)
        pz = KRANK_R * math.cos(krank_faz_lokal)
        yon = 1 if y > 0 else -1
        pin = silindir(f"{ad}_pin", (px, yon * (kalinlik / 2 + 0.25), pz),
                       0.055, 0.5, MAT["Celik"], eksen="Y")
        pin.parent = kok
    return kok


def kur():
    """Lokomotifi kurar; poz icin referans sozlugu dondurur."""
    MAT.clear()
    siyah = mat_yap("GovdeSiyah", (0.012, 0.012, 0.014), rough=0.32)
    duman_k = mat_yap("DumanKutusu", (0.008, 0.008, 0.009), rough=0.55)
    kirmizi = mat_yap("TekerKirmizi", (0.13, 0.018, 0.012), rough=0.45)
    jant_celik = mat_yap("JantCelik", (0.09, 0.095, 0.10), rough=0.35, metalik=0.85)
    celik = mat_yap("Celik", (0.35, 0.36, 0.38), rough=0.3, metalik=0.9)
    pirinc = mat_yap("Pirinc", (0.72, 0.52, 0.16), rough=0.25, metalik=1.0)
    cam = mat_yap("Cam", (0.01, 0.015, 0.02), rough=0.08)
    komur = mat_yap("Komur", (0.006, 0.006, 0.007), rough=0.95)

    kok = bpy.data.objects.new("Lokomotif", None)
    bpy.context.collection.objects.link(kok)
    once = set(bpy.data.objects)
    refs = {"kok": kok, "tekerler": {}, "cubuklar": {}, "duman": []}

    # ---------------- cerceve + ust yapi
    kutu("Sasi", (0.9, 0, 1.00), (8.8, 1.7, 0.12),
         mat_yap("SasiKoyu", (0.03, 0.03, 0.033), rough=0.6))
    kutu("YurumeTahtasi", (0.9, 0, 1.14), (9.2, 2.5, 0.05), siyah)
    kazan = silindir("Kazan", (2.0, 0, 2.55), 0.95, 5.2, siyah, eksen="X")
    silindir("KazanBandi1", (0.7, 0, 2.55), 0.965, 0.06, pirinc, eksen="X")
    silindir("KazanBandi2", (3.0, 0, 2.55), 0.965, 0.06, pirinc, eksen="X")
    smoky = silindir("DumanKutusu", (5.15, 0, 2.55), 0.97, 1.15, duman_k, eksen="X")
    kapak = silindir("DumanKapagi", (5.74, 0, 2.55), 0.95, 0.06, duman_k, eksen="X")
    kilit = silindir("KapakKilidi", (5.80, 0, 2.55), 0.12, 0.08, celik, eksen="X")
    baca_alt = silindir("BacaAlt", (5.15, 0, 3.72), 0.20, 0.42, duman_k)
    baca_ust = silindir("BacaUst", (5.15, 0, 4.10), 0.30, 0.36, duman_k)
    kubbe = bpy.ops.mesh.primitive_uv_sphere_add(radius=0.42, segments=24,
                                                 ring_count=16, location=(1.6, 0, 3.42))
    kubbe = bpy.context.active_object
    kubbe.name = "Kubbe"
    kubbe.scale = (1.35, 1.0, 0.8)
    kubbe.data.materials.append(pirinc)
    emniyet = silindir("EmniyetVentili", (0.2, 0.18, 3.62), 0.09, 0.35, pirinc)
    isligi = silindir("Isligi", (-0.25, -0.25, 3.66), 0.055, 0.30, pirinc)

    # ---------------- kabin
    kutu("KabinGovde", (-2.1, 0, 2.45), (2.4, 2.3, 2.6), siyah)
    kutu("KabinCati", (-2.1, 0, 3.82), (2.6, 2.5, 0.12), siyah)
    kutu("KabinOnCam", (-0.92, 0, 3.0), (0.05, 1.7, 1.0), cam)
    kutu("KabinYanCam1", (-2.4, 1.16, 3.0), (1.2, 0.05, 0.9), cam)
    kutu("KabinYanCam2", (-2.4, -1.16, 3.0), (1.2, 0.05, 0.9), cam)

    # ---------------- tekerlekler (jant celik, ic disk kirmizi)
    for i, cx in enumerate(TAHIRIK_X):
        for taraf, ys in (("sol", 0.715), ("sag", -0.715)):
            faz = 0.0 if taraf == "sol" else math.pi / 2
            t = teker_kur(f"Tahrik{i}_{taraf}", cx, TEKER_R, TEKER_R, 0.12, ys,
                          jant_celik, kirmizi, krankli=True, krank_faz_lokal=faz)
            refs["tekerler"][f"{taraf}{i}"] = t
    for j, px in enumerate((-2.1,)):
        for taraf, ys in (("ponysol", 0.715), ("ponysag", -0.715)):
            t = teker_kur(f"Pony{j}_{taraf}", px, 0.45, 0.45, 0.10, ys,
                          jant_celik, kirmizi)
            refs["tekerler"][taraf] = t

    # ---------------- silindir bloklari + kollar
    for taraf, ys in (("sol", 1.05), ("sag", -1.05)):
        kutu(f"SilindirBlok_{taraf}", (-1.6, ys, 0.78), (1.0, 0.55, 0.62), siyah)
        # krosbas kilavuz barlari
        for dz in (0.10, -0.10):
            kutu(f"Kilavuz_{taraf}{dz}", (-0.35, ys, Z_SILINDIR + dz),
                 (1.7, 0.05, 0.05), celik)
        kros = kutu(f"Krosbas_{taraf}", (0.0, ys, Z_SILINDIR), (0.22, 0.2, 0.18), celik)
        piston = cubuk_objesi(f"PistonRod_{taraf}", 0.05, celik)
        ana_biyel = cubuk_objesi(f"AnaBiyel_{taraf}", 0.045, celik)
        yan_itici = kutu(f"YanItici_{taraf}", (0, 0, 0),
                         (TAHIRIK_X[2] - TAHIRIK_X[0] + 0.3, 0.09, 0.11), celik)
        refs["cubuklar"][taraf] = {"kros": kros, "piston": piston,
                                   "ana_biyel": ana_biyel, "yan_itici": yan_itici}

    # ---------------- tamponlar
    kirmizi_boya = mat_yap("KirmiziBoya", (0.30, 0.03, 0.02), rough=0.4)
    kutu("OnTamponBeam", (5.95, 0, 1.06), (0.12, 2.3, 0.30), kirmizi_boya)
    for ys in (0.72, -0.72):
        silindir(f"OnBuffer{ys}", (6.15, ys, 1.06), 0.10, 0.45, celik, eksen="X")
    kutu("ArkaTamponBeam", (-3.5, 0, 1.06), (0.12, 2.3, 0.30), kirmizi_boya)
    for ys in (0.72, -0.72):
        silindir(f"ArkaBuffer{ys}", (-3.7, ys, 1.06), 0.10, 0.40, celik, eksen="X")

    # ---------------- tender
    kutu("TenderSasi", (-7.4, 0, 1.02), (6.2, 2.2, 0.16), celik)
    kutu("TenderGovde", (-7.4, 0, 2.05), (5.9, 2.35, 1.7), siyah)
    kutu("TenderKenar", (-7.4, 0, 2.95), (5.9, 2.45, 0.14), siyah)
    for i, (mx, my) in enumerate(((0.55, 0.7), (-0.4, -0.35), (-1.2, 0.5),
                                  (0.1, -0.75), (1.0, -0.2), (-1.5, -0.6))):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, segments=16,
                                             ring_count=10,
                                             location=(-7.4 + mx, my, 3.0 + (i % 3) * 0.18))
        k = bpy.context.active_object
        k.name = f"Komur{i}"
        k.scale = (1.0, 0.9, 0.55)
        k.data.materials.append(komur)
    for wx in (-5.4, -6.9, -8.1, -9.6):
        for taraf, ys in (("sol", 0.715), ("sag", -0.715)):
            teker_kur(f"TenderT{wx}_{taraf}", wx, 0.5, 0.5, 0.10, ys,
                      jant_celik, kirmizi)

    # ara baglanti
    kutu("CekiTeli", (-4.0, 0, 0.95), (1.4, 0.3, 0.2), celik)

    # ---------------- duman havuzu (GIF icin) — hacimsel gorunum
    duman_m = bpy.data.materials.new("Duman")
    duman_m.use_nodes = True
    nt = duman_m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out_n = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = (0.72, 0.72, 0.74, 1)
    vol.inputs["Density"].default_value = 0.55
    vol.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(vol.outputs["Volume"], out_n.inputs["Volume"])
    for i in range(14):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, segments=24,
                                             ring_count=16, location=(0, 0, -50))
        p = bpy.context.active_object
        p.name = f"Duman{i}"
        bpy.ops.object.shade_smooth()
        p.data.materials.append(duman_m)
        refs["duman"].append(p)

    # koke baglama — yalniz SAHIPSIZ nesneler (teker cocuklari kendi bos
    # nesnelerinde kalmali, yoksa tekerler dagilir)
    for o in set(bpy.data.objects) - once:
        if o is not kok and o.parent is None:
            o.parent = kok
    return refs


def poz(refs, theta):
    """Yurutucuyu theta'ya kur: tekerler + kollar + pistonlar.
    Ry(theta): pin lokal (sin faz, cos faz)*rc -> dunya (sin(theta+faz), cos(theta+faz))*rc
    — mekanik.py ile birebir; +X yonunde dogru yuvarlanma yonu."""
    d = yurutucu(theta)
    for ad, aci in d["tekerler"].items():
        t = refs["tekerler"].get(ad)
        if t:
            t.rotation_euler = (0, aci, 0)
    for taraf, ys in (("sol", 1.02), ("sag", -1.02)):
        k = refs["cubuklar"][taraf]
        x_pin, z_pin = d["pinler"][f"{taraf}1"]
        # yan itici: pimler ayni fazda — cubugun merkezi pimlerin merkezi
        pinler = d["yan_itici"][taraf]
        mx = sum(p[0] for p in pinler) / len(pinler)
        mz = sum(p[1] for p in pinler) / len(pinler)
        k["yan_itici"].location = (mx, ys, mz)
        # krosbas + piston cubugu
        xk = d["krosbas"][taraf]
        k["kros"].location = (xk, ys * 0.99, Z_SILINDIR)
        cubuk_ger(k["piston"], (xk + 0.1, ys * 0.995, Z_SILINDIR),
                  (-1.3, ys, Z_SILINDIR))
        # ana biyel: krosbas -> orta tahrik pimi
        cubuk_ger(k["ana_biyel"], (xk, ys * 0.99, Z_SILINDIR),
                  (x_pin, ys * 0.86, z_pin))


def duman_pozu(refs, t, hiz=1.0):
    """Bacadan duman puflari: havuzdaki kureler periyodik yukselir buyur solar."""
    kaynak = (5.15, 0, 4.35)
    adet = len(refs["duman"])
    periyot = 0.55
    for i, p in enumerate(refs["duman"]):
        faz = ((t / periyot + i / adet) % 1.0)
        yas = faz * 2.4
        p.location = (kaynak[0] - 0.9 * yas * hiz + 0.3 * math.sin(yas * 2 + i),
                      kaynak[1] + 0.4 * math.sin(yas * 1.3 + i * 2),
                      kaynak[1] * 0 + kaynak[2] + 1.55 * yas)
        olcek = 0.25 + 1.35 * yas
        p.scale = (olcek, olcek, olcek * 0.8)
        m = p.data.materials[0]
        if m.use_nodes:
            for dugum in m.node_tree.nodes:
                if dugum.type == "VOLUME_PRINCIPLED":
                    dugum.inputs["Density"].default_value = \
                        0.85 * (1.0 - faz) ** 1.5
    for p in refs["duman"]:
        p.visible_shadow = False
