import sys,json,torch
from diffusers import StableDiffusionXLPipeline
P="wide photo of a clean workshop bench with an enclosed desktop 3D printer, and in the foreground a row of freshly printed small teal and grey plastic replacement parts (latches, clips, knobs) lined up on the bench, soft daylight, shallow depth of field, tidy, no text"
pipe=StableDiffusionXLPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0",torch_dtype=torch.float16,variant="fp16").to("cuda")
meta={}
for s in [5,6,7,8,9,10]:
    im=pipe(P,height=896,width=1600,num_inference_steps=28,guidance_scale=6.5,negative_prompt="text, letters, logo, watermark, hands, fingers, people, blurry, deformed",generator=torch.Generator("cpu").manual_seed(s)).images[0]
    im.save(f"{sys.argv[1]}/hero_x{s}.png"); meta[s]=P
json.dump(meta,open(f"{sys.argv[1]}/meta_hero_extra.json","w"))
