"""Generate 3 SDXL base 1.0 candidates per image into a candidates dir."""
import json, sys, os, time, torch
from diffusers import StableDiffusionXLPipeline
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
STYLE = ("product photography, single 3D-printed plastic part, plain light grey studio background, soft shadow, "
         "slightly visible print layer lines, matte finish, no text, no logo, no hands, ")
P = {
 "rv-window-latch": "small plastic RV window slide latch with a thumb tab, grey ASA plastic",
 "rv-cabinet-door-latch": "small push-button cabinet door catch for an RV cabinet, charcoal plastic",
 "whirlpool-kitchenaid-fridge-door-bin": "a refrigerator door shelf bin, clear-ish white plastic",
 "samsung-fridge-door-bin": "a slim refrigerator door bin with end caps, white plastic",
 "dewalt-tstak-latch-clip": "a small toolbox latch clip with a flexing tab, black plastic",
 "milwaukee-packout-drawer-latch": "a drawer latch lever for a stacking tool box, charcoal plastic",
 "bmw-e90-e46-cup-holder": "a car dashboard cup holder insert with spring arms, black plastic",
 "maytag-whirlpool-dryer-knob": "a round dryer control knob with a D-shaped shaft insert, white plastic",
 "bosch-dishwasher-tine-clip": "four small dishwasher rack tine clips arranged together, light grey plastic",
 "dyson-v11-trigger": "a stick vacuum trigger lever, plastic, isolated, teal plastic",
 "custom-replacement-part-from-photo": "a broken plastic bracket next to its freshly 3D-printed teal replacement bracket, side by side",
 "cat-rv-camper": "a small arrangement of 3 generic plastic parts for an RV camper: window latch, cabinet catch, hinge, grey and teal plastic",
 "cat-kitchen-appliance": "a small arrangement of 3 generic plastic appliance parts: fridge door bin, round knob, dishwasher clip, white and teal plastic",
 "cat-tools-toolboxes": "a small arrangement of 3 generic plastic toolbox parts: latch, clip, drawer lever, black and charcoal plastic",
 "cat-automotive": "a small arrangement of 3 generic plastic car interior parts: cup holder insert, trim clip, vent knob, black plastic",
 "article-fridge-door-bin-broken-options": "a refrigerator door bin with a cracked broken corner, white plastic, close view",
 "article-rv-window-latch-replacement-guide": "an RV window frame corner with a small plastic latch installed, aluminium frame",
 "article-dewalt-tstak-latch-keeps-breaking": "a black toolbox latch with a snapped broken tab, close up",
 "article-can-this-plastic-part-be-3d-printed": "assorted plastic parts on a wooden desk with a ruler, overhead view",
 "article-how-to-photograph-a-broken-part-for-a-quote": "overhead view of a broken plastic part on white paper next to a coin and a ruler",
}
HERO = "a 3D printer bed with several freshly printed teal and grey replacement parts, clean bright workshop, shallow depth of field, no text"
jobs = [(k, STYLE + v, 1216, 896) for k, v in P.items()]
jobs.append(("hero", HERO, 1600, 896))
only = sys.argv[2:] 
pipe = StableDiffusionXLPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("cuda")
meta = {}
t0 = time.time()
for k, prompt, w, h in jobs:
    if only and k not in only: continue
    for i, seed in enumerate([11, 222, 3333]):
        f = f"{OUT}/{k}__{i}.png"
        if os.path.exists(f): continue
        g = torch.Generator("cpu").manual_seed(seed)
        im = pipe(prompt, height=h, width=w, num_inference_steps=28, guidance_scale=6.5, negative_prompt="text, letters, logo, watermark, hands, fingers, people, blurry, deformed, multiple copies", generator=g).images[0]
        im.save(f); meta[f"{k}__{i}"] = dict(prompt=prompt, seed=seed, w=w, h=h)
    print(k, round(time.time()-t0), flush=True)
json.dump(meta, open(f"{OUT}/meta_{int(time.time())}.json", "w"), indent=1)
