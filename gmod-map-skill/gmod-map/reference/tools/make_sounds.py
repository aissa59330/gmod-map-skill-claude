"""Sons de la map (embarqués dans le .bsp par compile.ps1 via bspzip, aucun addon).

python tools/make_sounds.py
- voix de SENTINELLE (synthèse vocale Windows fr-FR + traitement « droïde » : ring-mod, grain, écho court)
- petite sirène en boucle (wav avec point de boucle « cue », que le moteur Source sait boucler)
Réécrit compile_game/pack_list.txt avec TOUT le contenu maison (panneaux + sons).
"""
import os
import struct
import subprocess
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "compile_game")
SND = os.path.join(GAME, "sound", "givre_noir")
os.makedirs(SND, exist_ok=True)
RATE = 44100

LINES = {
    "sentinelle_hack": "Alerte. Intrusion détectée dans le centre de données. Piratage en cours. "
                       "Verrouillage de la base. Déploiement des garnisons de droïdes.",
    "sentinelle_hack_fin": "Piratage terminé. Verrouillage compromis.",
    "sentinelle_fin": "Intégrité du noyau... zéro pour cent. Vous avez gagné... rien. Je suis... partout. Je... re... vien...",
}


def tts(text, path):
    ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$s.SelectVoice('Microsoft Hortense Desktop'); $s.Rate = -2; "
          "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(%d, "
          "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono); "
          "$s.SetOutputToWaveFile('%s', $f); $s.Speak('%s'); $s.Dispose()") % (RATE, path, text.replace("'", "''"))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def read(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def write(path, x, loop=False):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2").tobytes()
    fmt = struct.pack("<HHIIHH", 1, 1, RATE, RATE * 2, 2, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(pcm)) + pcm
    if loop:   # point de boucle au début : Source boucle le son jusqu'à StopSound
        cue = struct.pack("<I", 1) + struct.pack("<II4sIII", 1, 0, b"data", 0, 0, 0)
        chunks += b"cue " + struct.pack("<I", len(cue)) + cue
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


def droid(x):
    # voix d'IA LISIBLE : pas de modulation d'amplitude (rendait la phrase incompréhensible),
    # juste un timbre métallique léger (filtre en peigne 7 ms) et un écho de grande salle
    c = int(0.007 * RATE)
    y = x.copy()
    y[c:] += 0.35 * x[:-c]
    d = int(0.11 * RATE)                                          # écho (haut-parleurs de la base)
    e = np.zeros(len(y) + d * 2, np.float32)
    e[:len(y)] += y
    e[d:d + len(y)] += 0.22 * y
    e[2 * d:2 * d + len(y)] += 0.08 * y
    e = np.concatenate([np.zeros(int(0.15 * RATE), np.float32), e])   # petit blanc avant la phrase
    return 0.9 * e / max(1e-6, np.abs(e).max())


def siren(on=0.62, off=0.48):
    """Klaxon d'alerte militaire « BWAAH » : accord de dents de scie (330 + 415 Hz) légèrement saturé,
    qui chute un peu en fin de coup, puis silence. Boucle d'environ 1,1 s."""
    n_on, n_off = int(on * RATE), int(off * RATE)
    t = np.arange(n_on) / RATE
    drop = 1 - 0.06 * (t / on) ** 3
    y = np.zeros(n_on, np.float32)
    for f0, a in ((330, 1.0), (415, 0.8), (165, 0.5)):
        ph = 2 * np.pi * np.cumsum(f0 * drop) / RATE
        for k in range(1, 9):                                     # dent de scie à bande limitée
            y += a * np.sin(k * ph) / k
    y = np.tanh(1.8 * y / np.abs(y).max())                        # saturation (haut-parleur de la base)
    env = np.minimum(1, np.minimum(t / 0.02, (on - t) / 0.06))
    y = np.concatenate([y * env, np.zeros(n_off, np.float32)])
    return 0.55 * y / np.abs(y).max()


for name, text in LINES.items():
    raw = os.path.join(SND, name + "_brut.wav")
    tts(text, raw)
    write(os.path.join(SND, name + ".wav"), droid(read(raw)))
    os.remove(raw)
write(os.path.join(SND, "sirene_hack.wav"), siren(), loop=True)
# voix d'alerte enregistrée (ElevenLabs, fournie par l'organisateur) : mp3 lu tel quel par le moteur
import shutil
shutil.copy(os.path.join(ROOT, "assets", "sons", "sentinelle_alerte.mp3"), os.path.join(SND, "sentinelle_alerte.mp3"))

# liste bspzip : tout le contenu maison
with open(os.path.join(GAME, "pack_list.txt"), "w", encoding="ascii") as f:
    for sub in (os.path.join("materials", "givre_noir"), os.path.join("sound", "givre_noir"), os.path.join("models", "givre_noir"), os.path.join("models", "gnl")):
        d = os.path.join(GAME, sub)
        if not os.path.isdir(d):
            continue
        for dp, _, files in os.walk(d):                     # récursif (models/givre_noir/lod, ...)
            for fn in sorted(files):
                full = os.path.join(dp, fn)
                f.write(os.path.relpath(full, GAME).replace(os.sep, "/") + "\n" + full + "\n")
print("SONS", sorted(os.listdir(SND)))
