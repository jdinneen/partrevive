"""Round-3 SDXL candidates: python gen_round3.py <out_dir> <prompts.json> [names...]
prompts.json: {"<name>": "<part description>"}; article-* names get a scene style, others the product style."""
import json, os, sys, time, torch
from diffusers import StableDiffusionXLPipeline
OUT, PROMPTS = sys.argv[1], json.load(open(sys.argv[2])); os.makedirs(OUT, exist_ok=True)
only = sys.argv[3:]
STYLE = ("product photography, single 3D-printed plastic part, plain light grey studio background, soft shadow, "
         "slightly visible print layer lines, matte finish, no text, no logo, no hands, ")
SCENE = "realistic photograph, natural light, shallow depth of field, no text, no logo, no faces, "
NEG = "text, letters, logo, watermark, hands, fingers, people, blurry, deformed, multiple copies, box, drawer, room, interior, vehicle, giant, tray"
pipe = StableDiffusionXLPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16, variant="fp16", use_safetensors=True).to("cuda")
meta = {}; t0 = time.time()
for k, desc in PROMPTS.items():
    if only and k not in only: continue
    prompt = (SCENE if k.startswith("article-") else STYLE) + desc
    neg = NEG if not k.startswith("article-") else "text, letters, logo, watermark, faces, blurry, deformed, cartoon"
    for i, seed in enumerate([11, 222, 3333]):
        f = f"{OUT}/{k}__r3{i}.png"
        if os.path.exists(f): continue
        g = torch.Generator("cpu").manual_seed(seed)
        im = pipe(prompt, height=896, width=1216, num_inference_steps=28, guidance_scale=6.5, negative_prompt=neg, generator=g).images[0]
        im.save(f); meta[f"{k}__{i}"] = dict(prompt=prompt, seed=seed, w=1216, h=896)
    print(k, round(time.time() - t0), flush=True)
json.dump(meta, open(f"{OUT}/meta_{int(time.time())}.json", "w"), indent=1)
