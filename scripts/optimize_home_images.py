from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "optimized"
OUT.mkdir(parents=True, exist_ok=True)

SPECS = [
    ("assets/home-tiles/Monochrome Brutalist House Diorama.png", "creativity-jia.webp", (720, 720), (0.58, 0.48)),
    ("assets/home-tiles/Gritty Kolkata Signage Study.png", "culture-type-around-town.webp", (720, 480), (0.50, 0.50)),
    ("assets/home-tiles/Australian Flag Billowing in Blue Sky.png", "technology-australia-u16.webp", (720, 480), (0.50, 0.50)),
    ("assets/home-tiles/Warm Orange Storage Showroom.png", "brands-kallax.webp", (720, 480), (0.58, 0.50)),
    ("assets/home-tiles/What an Architectural Model Lets You See.png", "discovery-jia.webp", (1000, 500), (0.50, 0.50)),
    ("assets/home-tiles/Urban-Typography-in-Grayscale-and-Red.png", "discovery-type-around-town.webp", (640, 360), (0.50, 0.50)),
    ("assets/Celestial-Archipelag-Map.png", "discovery-look-between-islands.webp", (640, 480), (0.50, 0.50)),
    ("assets/home-tiles/Moonlit-Noir-Canal-Town.png", "discovery-mur-mur.webp", (640, 480), (0.50, 0.50)),
    ("assets/home-tiles/Cozy-fantasy-Longhouse-Shelves.png", "discovery-kallax.webp", (640, 480), (0.50, 0.50)),
]

for source_rel, output_name, size, centering in SPECS:
    source = ROOT / source_rel
    target = OUT / output_name

    with Image.open(source) as image:
        image = image.convert("RGB")
        image = ImageOps.fit(
            image,
            size,
            method=Image.Resampling.LANCZOS,
            centering=centering,
        )
        image.save(
            target,
            "WEBP",
            quality=55,
            method=6,
            optimize=True,
        )

    print(f"{source_rel} -> {target.relative_to(ROOT)} ({target.stat().st_size} bytes)")
