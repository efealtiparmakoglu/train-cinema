#!/usr/bin/env python3
# Blender icinde: blender --background --python tren_render.py -- --scene scenes/studyo.json [--gif 36]
"""train-cinema — stüdyo render: karanlık fon + 3 nokta stüdyo ışığı,
dönen tekerlekler/pistonlar + bacadan duman (GIF modda)."""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys

import bpy
from mathutils import Vector

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)

import tren  # noqa: E402


def temiz():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def kamera_kur(konum, hedef, lens=50):
    cam = bpy.data.cameras.new("Cam")
    cam.lens = lens
    co = bpy.data.objects.new("kamera", cam)
    bpy.context.collection.objects.link(co)
    co.location = konum
    yon = Vector(hedef) - Vector(konum)
    co.rotation_euler = yon.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = co
    return co


def stüdyo_ışıkları(cfg):
    lc = cfg.get("isik", {})
    ana = bpy.data.lights.new("Ana", "AREA")
    ana.energy = lc.get("ana", 2500)
    ana.size = 6.0
    ao = bpy.data.objects.new("Ana", ana)
    bpy.context.collection.objects.link(ao)
    ao.location = lc.get("ana_konum", (-8, -9, 7))
    ao.rotation_euler = (Vector((1.5, 0, 1.4)) - Vector(ao.location)
                         ).to_track_quat("-Z", "Y").to_euler()

    dolgu = bpy.data.lights.new("Dolgu", "AREA")
    dolgu.energy = lc.get("dolgu", 900)
    dolgu.size = 8.0
    do = bpy.data.objects.new("Dolgu", dolgu)
    bpy.context.collection.objects.link(do)
    do.location = lc.get("dolgu_konum", (10, -6, 4))
    do.rotation_euler = (Vector((1, 0, 1.5)) - Vector(do.location)
                         ).to_track_quat("-Z", "Y").to_euler()

    rim = bpy.data.lights.new("Rim", "AREA")
    rim.energy = lc.get("rim", 3200)
    rim.size = 4.0
    ri = bpy.data.objects.new("Rim", rim)
    bpy.context.collection.objects.link(ri)
    ri.location = lc.get("rim_konum", (4, 12, 6))
    ri.rotation_euler = (Vector((1.5, 0, 2)) - Vector(ri.location)
                         ).to_track_quat("-Z", "Y").to_euler()

    # alt takim (yurutucu mekanik) icin alcak dolgu
    mil = bpy.data.lights.new("Mekanik", "AREA")
    mil.energy = lc.get("mekanik", 1100)
    mil.size = 5.0
    mo = bpy.data.objects.new("Mekanik", mil)
    bpy.context.collection.objects.link(mo)
    mo.location = lc.get("mekanik_konum", (2, -8, 0.8))
    mo.rotation_euler = (Vector((1, 0, 0.9)) - Vector(mo.location)
                         ).to_track_quat("-Z", "Y").to_euler()


def sahne_kur(cfg):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
        sc.cycles.device = "GPU"
    except Exception as e:
        print("  [uyari] GPU:", e)
    sc.cycles.samples = cfg["render"].get("samples", 128)
    sc.cycles.use_denoising = True
    sc.render.resolution_x = cfg["render"].get("width", 1600)
    sc.render.resolution_y = cfg["render"].get("height", 900)
    sc.view_settings.view_transform = "Filmic"
    sc.view_settings.exposure = cfg["render"].get("exposure", 0.0)
    look = cfg["render"].get("look")
    if look:
        try:
            sc.view_settings.look = look
        except Exception:
            pass

    dunya = bpy.data.worlds.new("Studio")
    sc.world = dunya
    dunya.use_nodes = True
    nt = dunya.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    renk = cfg.get("fon", {"color": [0.012, 0.013, 0.016]})
    bg.inputs["Color"].default_value = (*renk["color"], 1)
    bg.inputs["Strength"].default_value = renk.get("strength", 1.0)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return sc


def zemin_kur(cfg):
    z = cfg.get("zemin", {})
    m = bpy.data.materials.new("Zemin")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    renk = z.get("color", (0.02, 0.02, 0.023))
    b.inputs["Base Color"].default_value = (*renk, 1)
    b.inputs["Roughness"].default_value = z.get("roughness", 0.35)
    b.inputs["Metallic"].default_value = z.get("metalik", 0.2)
    bpy.ops.mesh.primitive_plane_add(size=z.get("boyut", 80),
                                     location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = "Zemin"
    o.data.materials.append(m)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--gif", type=int, default=0)
    ap.add_argument("--fps", type=int, default=12)
    a = ap.parse_args(args)

    cfg = json.load(open(a.scene, encoding="utf-8"))
    if os.environ.get("HIZLI") == "1":
        cfg["render"] = {**cfg.get("render", {}), "width": 800, "height": 450,
                         "samples": 32}
        cfg["output"] = "/tmp/onizleme_tren_" + os.path.basename(a.scene).replace(".json", ".png")
        print("  [HIZLI] onizleme ->", cfg["output"])

    temiz()
    sc = sahne_kur(cfg)
    zemin_kur(cfg)
    stüdyo_ışıkları(cfg)

    refs = tren.kur()
    tren.poz(refs, cfg.get("theta", 0.0))

    cam_cfg = cfg["camera"]
    cam_obj = kamera_kur(cam_cfg["position"], cam_cfg["look_at"],
                         cam_cfg.get("lens", 50))
    print(f"  [kamera] {cam_cfg['position']} -> {cam_cfg['look_at']}")

    if a.gif:
        cfg["render"] = {**cfg.get("render", {}), "width": 1280, "height": 720,
                         "samples": 48}
        out = os.path.splitext(cfg["output"])[0] + ".gif"
    else:
        out = cfg["output"]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    if not a.gif:
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"== BİTTİ -> {out}")
        return

    tmp = out + ".frames"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    omega = cam_cfg.get("omega", 5.2)  # rad/s teker acisal hiz
    for f in range(a.gif):
        t = f / a.fps
        tren.poz(refs, omega * t)
        tren.duman_pozu(refs, t)
        sc.render.filepath = f"{tmp}/f{f:05d}.png"
        bpy.ops.render.render(write_still=True)
        print(f"  kare {f + 1}/{a.gif} theta={omega * t:.2f}")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{tmp}/f%05d.png",
                    "-vf", "palettegen=max_colors=256:stats_mode=diff",
                    f"{tmp}/pal.png"], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps),
                    "-i", f"{tmp}/f%05d.png", "-i", f"{tmp}/pal.png",
                    "-lavfi", "paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                    "-loop", "0", out], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"== BİTTİ -> {out}")


if __name__ == "__main__":
    main()
