"""Generate 3 SDXL base 1.0 candidates per image into a candidates dir."""
import json, sys, os, time, torch
from diffusers import StableDiffusionXLPipeline
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
STYLE = ("product photography, single 3D-printed plastic part, plain light grey studio background, soft shadow, "
         "slightly visible print layer lines, matte finish, no text, no logo, no hands, ")
P = {
 "rv-window-latch": "small slide latch with a thumb tab for a camper window, a short flat plastic bar with a rounded thumb grip and two screw holes, grey ASA plastic",
 "rv-cabinet-door-latch": "tiny round push-button catch for a cabinet door, a small cylindrical plastic push button with a flange, charcoal plastic, macro",
 "bmw-e90-e46-cup-holder": "a round cup holder insert for a car, ring-shaped black plastic with two curved spring arms, top three-quarter view",
 "bosch-dishwasher-tine-clip": "four tiny plastic clips, small U-shaped snap clips lined up in a row, light grey plastic, macro",
 "dewalt-tstak-latch-clip": "a small black plastic latch clip, a flat tab with a flexing hook end and a pivot hole, macro, on a tiny scale",
 "milwaukee-packout-drawer-latch": "a small plastic lever latch, a short curved lever handle with a hinge pin boss, charcoal plastic, macro, centered",
 "dyson-v11-trigger": "a small plastic trigger lever, a curved finger trigger with a pivot hole, teal plastic, macro, centered",
 "maytag-whirlpool-dryer-knob": "a round appliance knob with a fluted grip edge and a pointer line, white plastic, top three-quarter view",
 "article-fridge-door-bin-broken-options": "a white plastic refrigerator door shelf bin with a cracked broken corner, a visible crack and missing chip, close view",
 "article-rv-window-latch-replacement-guide": "a camper window aluminium frame corner with a small grey plastic latch on the sash, close view, daylight",
 "article-dewalt-tstak-latch-keeps-breaking": "a black plastic toolbox latch with a snapped off broken tab, jagged break, on a workbench",
 "article-how-to-photograph-a-broken-part-for-a-quote": "overhead flat lay of a small broken plastic clip on white paper next to a coin and a ruler",
}
HERO = "close view of a 3D printer build plate with several freshly printed small teal and grey plastic replacement parts sitting on it, clean bright workshop background, shallow depth of field, no text"
jobs = [(k, STYLE + v, 1216, 896) for k, v in P.items()]
jobs.append(("hero", HERO, 1600, 896))
only = sys.argv[2:] 
pipe = StableDiffusionXLPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("cuda")
meta = {}
t0 = time.time()
for k, prompt, w, h in jobs:
    if only and k not in only: continue
    for i, seed in enumerate([11, 222, 3333, 4444]):
        f = f"{OUT}/{k}__r2{i}.png"
        if os.path.exists(f): continue
        g = torch.Generator("cpu").manual_seed(seed)
        im = pipe(prompt, height=h, width=w, num_inference_steps=28, guidance_scale=6.5, negative_prompt="text, letters, logo, watermark, hands, fingers, people, blurry, deformed, multiple copies, box, drawer, room, interior, vehicle, giant, tray", generator=g).images[0]
        im.save(f); meta[f"{k}__{i}"] = dict(prompt=prompt, seed=seed, w=w, h=h)
    print(k, round(time.time()-t0), flush=True)
json.dump(meta, open(f"{OUT}/meta_{int(time.time())}.json", "w"), indent=1)
