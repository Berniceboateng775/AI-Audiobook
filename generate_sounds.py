"""
Generate ambient background sounds programmatically.
Creates atmospheric sounds using pydub generators — no downloads needed!

Run this once: python generate_sounds.py
"""

import os
import sys
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Auto-detect ffmpeg
if not shutil.which("ffmpeg"):
    ffmpeg_dir = os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Links")
    if os.path.exists(os.path.join(ffmpeg_dir, "ffmpeg.exe")):
        os.environ["PATH"] = ffmpeg_dir + ";" + os.environ.get("PATH", "")

from pydub import AudioSegment
from pydub.generators import Sine, WhiteNoise
import random

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "sounds")
os.makedirs(SOUNDS_DIR, exist_ok=True)

DURATION = 30000  # 30 seconds each (looped during playback)


def generate_soft_piano():
    """Gentle, warm ambient for romantic scenes."""
    print("  [piano] soft_piano.mp3 (romantic)...")
    notes = [(261.63, -18), (329.63, -20), (392.00, -22), (523.25, -24)]
    base = AudioSegment.silent(duration=DURATION)
    for freq, vol in notes:
        tone = Sine(freq).to_audio_segment(duration=4000) + vol
        tone = tone.fade_in(1500).fade_out(2000)
        full = AudioSegment.silent(duration=0)
        for _ in range(0, DURATION, 5000):
            full += AudioSegment.silent(duration=random.randint(0, 1000)) + tone
        base = base.overlay(full[:DURATION])
    warmth = WhiteNoise().to_audio_segment(duration=DURATION) - 38
    base = base.overlay(warmth.low_pass_filter(800))
    base.fade_in(2000).fade_out(2000).export(os.path.join(SOUNDS_DIR, "soft_piano.mp3"), format="mp3")


def generate_nature_ambient():
    """Gentle wind/atmosphere for calm scenes."""
    print("  [nature] nature_ambient.mp3 (calm)...")
    wind = WhiteNoise().to_audio_segment(duration=DURATION) - 22
    wind = wind.low_pass_filter(2000).high_pass_filter(200)
    deep = WhiteNoise().to_audio_segment(duration=DURATION) - 28
    deep = deep.low_pass_filter(500)
    result = wind.overlay(deep).fade_in(3000).fade_out(3000)
    result.export(os.path.join(SOUNDS_DIR, "nature_ambient.mp3"), format="mp3")


def generate_suspense_ambient():
    """Dark, tense atmosphere for suspense scenes."""
    print("  [suspense] suspense_ambient.mp3 (suspense)...")
    rumble = Sine(55).to_audio_segment(duration=DURATION) - 20
    rumble2 = Sine(82.41).to_audio_segment(duration=DURATION) - 24
    tension = Sine(116.54).to_audio_segment(duration=DURATION) - 28
    dark = WhiteNoise().to_audio_segment(duration=DURATION) - 30
    dark = dark.low_pass_filter(400)
    result = rumble.overlay(rumble2).overlay(tension).overlay(dark)
    result.fade_in(3000).fade_out(3000).export(os.path.join(SOUNDS_DIR, "suspense_ambient.mp3"), format="mp3")


def generate_tension_drums():
    """Heartbeat pulse for action scenes."""
    print("  [drums] tension_drums.mp3 (action)...")
    base = AudioSegment.silent(duration=DURATION)
    beat = (Sine(60).to_audio_segment(duration=150) - 12).fade_in(10).fade_out(80)
    pattern = AudioSegment.silent(duration=0)
    for _ in range(0, DURATION, 1200):
        pattern += beat + AudioSegment.silent(200) + beat + AudioSegment.silent(800)
    drone = Sine(73.42).to_audio_segment(duration=DURATION) - 22
    result = pattern[:DURATION].overlay(drone).fade_in(2000).fade_out(2000)
    result.export(os.path.join(SOUNDS_DIR, "tension_drums.mp3"), format="mp3")


def generate_dramatic_strings():
    """Sustained strings for dramatic/emotional scenes."""
    print("  [strings] dramatic_strings.mp3 (dramatic)...")
    notes = [(196.00, -18), (246.94, -20), (293.66, -20), (349.23, -22)]
    base = AudioSegment.silent(duration=DURATION)
    for freq, vol in notes:
        tone = Sine(freq).to_audio_segment(duration=DURATION) + vol
        vibrato = Sine(freq * 1.003).to_audio_segment(duration=DURATION) + (vol - 3)
        base = base.overlay(tone.overlay(vibrato))
    texture = WhiteNoise().to_audio_segment(duration=DURATION) - 35
    base = base.overlay(texture.low_pass_filter(1500).high_pass_filter(300))
    base.fade_in(3000).fade_out(3000).export(os.path.join(SOUNDS_DIR, "dramatic_strings.mp3"), format="mp3")


# ═══════════════════════════════════════════════════
# NEW CINEMATIC SOUNDS
# ═══════════════════════════════════════════════════

def generate_rain():
    """Steady rainfall ambient."""
    print("  [rain] rain.mp3 (rain)...")
    # Rain = filtered white noise with varying density
    rain = WhiteNoise().to_audio_segment(duration=DURATION) - 16
    rain = rain.low_pass_filter(6000).high_pass_filter(500)
    
    # Add patter texture (higher frequency splashes)
    patter = WhiteNoise().to_audio_segment(duration=DURATION) - 22
    patter = patter.high_pass_filter(3000).low_pass_filter(8000)
    
    # Low rumble of rain on roof
    rumble = WhiteNoise().to_audio_segment(duration=DURATION) - 28
    rumble = rumble.low_pass_filter(300)
    
    result = rain.overlay(patter).overlay(rumble)
    result.fade_in(3000).fade_out(3000).export(os.path.join(SOUNDS_DIR, "rain.mp3"), format="mp3")


def generate_thunder():
    """Thunder and lightning storm."""
    print("  [thunder] thunder_storm.mp3 (storm)...")
    # Base rain
    rain = WhiteNoise().to_audio_segment(duration=DURATION) - 18
    rain = rain.low_pass_filter(5000).high_pass_filter(400)
    
    result = rain
    
    # Add thunder claps at random intervals
    for _ in range(6):
        pos = random.randint(2000, DURATION - 4000)
        
        # Thunder = low frequency burst + rumble tail
        crack = Sine(40 + random.randint(0, 20)).to_audio_segment(duration=300) - 6
        crack = crack.fade_in(5).fade_out(100)
        
        rumble = Sine(30 + random.randint(0, 15)).to_audio_segment(duration=3000) - 10
        rumble = rumble.fade_in(50).fade_out(2500)
        
        # Add noise burst for crack
        noise_burst = WhiteNoise().to_audio_segment(duration=200) - 8
        noise_burst = noise_burst.low_pass_filter(1000).fade_in(5).fade_out(150)
        
        thunder = crack.overlay(noise_burst) + rumble
        
        # Overlay at random position
        pad_before = AudioSegment.silent(duration=pos)
        pad_after = AudioSegment.silent(duration=max(0, DURATION - pos - len(thunder)))
        thunder_track = pad_before + thunder + pad_after
        thunder_track = thunder_track[:DURATION]
        
        result = result.overlay(thunder_track)
    
    result.fade_in(2000).fade_out(3000).export(os.path.join(SOUNDS_DIR, "thunder_storm.mp3"), format="mp3")


def generate_wind_storm():
    """Howling wind storm."""
    print("  [wind] wind_storm.mp3 (storm wind)...")
    # Base wind
    wind = WhiteNoise().to_audio_segment(duration=DURATION) - 16
    wind = wind.low_pass_filter(1500).high_pass_filter(100)
    
    # Howling effect (low sine wave variations)
    howl1 = Sine(180).to_audio_segment(duration=DURATION) - 22
    howl2 = Sine(220).to_audio_segment(duration=DURATION) - 24
    howl3 = Sine(150).to_audio_segment(duration=DURATION) - 26
    
    # Gusts (bursts of louder noise)
    gusts = AudioSegment.silent(duration=DURATION)
    for _ in range(8):
        pos = random.randint(1000, DURATION - 3000)
        gust = WhiteNoise().to_audio_segment(duration=2000) - 14
        gust = gust.low_pass_filter(2000).fade_in(300).fade_out(1200)
        pad = AudioSegment.silent(duration=pos) + gust + AudioSegment.silent(duration=max(0, DURATION - pos - 2000))
        gusts = gusts.overlay(pad[:DURATION])
    
    result = wind.overlay(howl1).overlay(howl2).overlay(howl3).overlay(gusts)
    result.fade_in(2000).fade_out(3000).export(os.path.join(SOUNDS_DIR, "wind_storm.mp3"), format="mp3")


def generate_chaos():
    """Chaotic, intense atmosphere for battle/fight/chaos scenes."""
    print("  [chaos] chaos.mp3 (chaos/battle)...")
    # Intense layered noise
    base_noise = WhiteNoise().to_audio_segment(duration=DURATION) - 14
    base_noise = base_noise.low_pass_filter(3000).high_pass_filter(200)
    
    # Rapid heartbeat
    heartbeat = AudioSegment.silent(duration=0)
    beat = (Sine(50).to_audio_segment(duration=100) - 10).fade_in(5).fade_out(60)
    for _ in range(0, DURATION, 500):  # Fast heartbeat
        heartbeat += beat + AudioSegment.silent(400)
    heartbeat = heartbeat[:DURATION]
    
    # Impact hits at random times
    impacts = AudioSegment.silent(duration=DURATION)
    for _ in range(15):
        pos = random.randint(500, DURATION - 1000)
        hit = WhiteNoise().to_audio_segment(duration=100) - 6
        hit = hit.low_pass_filter(2000).fade_in(2).fade_out(80)
        pad = AudioSegment.silent(pos) + hit + AudioSegment.silent(max(0, DURATION - pos - 100))
        impacts = impacts.overlay(pad[:DURATION])
    
    # Dissonant tones
    dissonant = Sine(100).to_audio_segment(duration=DURATION) - 20
    dissonant2 = Sine(107).to_audio_segment(duration=DURATION) - 22  # Slightly off = tension
    
    result = base_noise.overlay(heartbeat).overlay(impacts).overlay(dissonant).overlay(dissonant2)
    result.fade_in(1000).fade_out(2000).export(os.path.join(SOUNDS_DIR, "chaos.mp3"), format="mp3")


def generate_heartbeat():
    """Slow, heavy heartbeat for intense emotional moments."""
    print("  [heart] heartbeat.mp3 (intense emotion)...")
    base = AudioSegment.silent(duration=DURATION)
    
    # Deep thump
    thump = Sine(40).to_audio_segment(duration=200) - 8
    thump = thump.fade_in(10).fade_out(120)
    
    # Lighter follow-up thump
    thump2 = Sine(50).to_audio_segment(duration=150) - 12
    thump2 = thump2.fade_in(10).fade_out(100)
    
    pattern = AudioSegment.silent(duration=0)
    for _ in range(0, DURATION, 1500):
        pattern += thump + AudioSegment.silent(250) + thump2 + AudioSegment.silent(1050)
    
    # Subtle pad underneath
    pad = Sine(65).to_audio_segment(duration=DURATION) - 28
    
    result = pattern[:DURATION].overlay(pad)
    result.fade_in(2000).fade_out(2000).export(os.path.join(SOUNDS_DIR, "heartbeat.mp3"), format="mp3")


def generate_night_crickets():
    """Night ambience with crickets for quiet/intimate scenes."""
    print("  [night] night_crickets.mp3 (night/intimate)...")
    # Base quiet atmosphere
    night_air = WhiteNoise().to_audio_segment(duration=DURATION) - 32
    night_air = night_air.low_pass_filter(1000)
    
    # Cricket chirps (high frequency short bursts)
    crickets = AudioSegment.silent(duration=DURATION)
    chirp = Sine(4000).to_audio_segment(duration=80) - 22
    chirp = chirp.fade_in(5).fade_out(30)
    
    for _ in range(40):
        pos = random.randint(500, DURATION - 500)
        # Crickets chirp in bursts of 2-4
        burst = AudioSegment.silent(duration=0)
        for _ in range(random.randint(2, 4)):
            burst += chirp + AudioSegment.silent(random.randint(60, 120))
        pad = AudioSegment.silent(pos) + burst + AudioSegment.silent(max(0, DURATION - pos - len(burst)))
        crickets = crickets.overlay(pad[:DURATION])
    
    result = night_air.overlay(crickets)
    result.fade_in(3000).fade_out(3000).export(os.path.join(SOUNDS_DIR, "night_crickets.mp3"), format="mp3")


def generate_crowd_murmur():
    """Crowd/party ambient noise."""
    print("  [crowd] crowd_murmur.mp3 (crowd/party)...")
    # Multiple layers of filtered noise at different frequencies = crowd effect
    layer1 = WhiteNoise().to_audio_segment(duration=DURATION) - 18
    layer1 = layer1.low_pass_filter(2000).high_pass_filter(200)
    
    layer2 = WhiteNoise().to_audio_segment(duration=DURATION) - 20
    layer2 = layer2.low_pass_filter(1500).high_pass_filter(300)
    
    # Add some low hum (room tone)
    hum = Sine(120).to_audio_segment(duration=DURATION) - 28
    
    result = layer1.overlay(layer2).overlay(hum)
    result.fade_in(3000).fade_out(3000).export(os.path.join(SOUNDS_DIR, "crowd_murmur.mp3"), format="mp3")


def generate_eerie():
    """Eerie/horror ambient for dark/creepy scenes."""
    print("  [eerie] eerie.mp3 (horror/dark)...")
    # Dissonant low drones
    drone1 = Sine(65).to_audio_segment(duration=DURATION) - 18
    drone2 = Sine(69).to_audio_segment(duration=DURATION) - 20  # Slightly off-key = creepy
    drone3 = Sine(98).to_audio_segment(duration=DURATION) - 24
    
    # Ghostly wind
    wind = WhiteNoise().to_audio_segment(duration=DURATION) - 26
    wind = wind.low_pass_filter(800).high_pass_filter(100)
    
    # Occasional high-pitched whine
    whine = Sine(1200).to_audio_segment(duration=DURATION) - 34
    
    result = drone1.overlay(drone2).overlay(drone3).overlay(wind).overlay(whine)
    result.fade_in(4000).fade_out(4000).export(os.path.join(SOUNDS_DIR, "eerie.mp3"), format="mp3")


if __name__ == "__main__":
    print("\n[*] Generating cinematic background sounds...\n")
    
    # Original 5
    generate_soft_piano()
    generate_nature_ambient()
    generate_suspense_ambient()
    generate_tension_drums()
    generate_dramatic_strings()
    
    # New cinematic sounds
    generate_rain()
    generate_thunder()
    generate_wind_storm()
    generate_chaos()
    generate_heartbeat()
    generate_night_crickets()
    generate_crowd_murmur()
    generate_eerie()
    
    print(f"\nDone! All sounds saved to: {SOUNDS_DIR}")
    print("\nFiles:")
    for f in sorted(os.listdir(SOUNDS_DIR)):
        size = os.path.getsize(os.path.join(SOUNDS_DIR, f))
        print(f"  {f} ({size // 1024} KB)")
