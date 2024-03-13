import numpy as np
from PIL import Image
from marigold.marigold_pipeline import MarigoldPipeline
from flow_estimation import FlowEstimator

from diffusers.utils import load_image
import torch
import glob

from utils import warp_with_flow
import tqdm


pipe = MarigoldPipeline.from_pretrained(
    "Bingxin/Marigold",
    torch_dtype=torch.float16
)

pipe.to("cuda")

flow_estimator = FlowEstimator("gmflow/pretrained/gmflow_things-e9887eda.pth", "cuda")

frames_path = "input/cam09/images"
images = glob.glob(frames_path + "/*.png")
images.sort()
images = images[:100]
noise_ratio = 0.35

for i, image_path in tqdm.tqdm(enumerate(images), total=len(images)):
    cur_image = Image.open(image_path)
    prev_image = Image.open(images[i-1])
    flow = flow_estimator.estimate_flow(np.array(prev_image), np.array(cur_image))

    if i==0:
        pipeline_output = pipe(cur_image, input_depth=None, denoising_steps=10, ensemble_size=10)
        depth = pipeline_output.depth_np
        depth = (depth - np.min(depth)) / (np.max(depth) - np.min(depth))
        prev_depth = depth
        
    else:
        warped_depth = warp_with_flow(flow, prev_depth)
        pipeline_output = pipe(cur_image, input_depth=Image.fromarray(warped_depth*255), denoising_steps=4, 
                               ensemble_size=1, noise_ratio=noise_ratio, input_depth_mix = 0.4, show_progress_bar=False)
        
        prev_depth = pipeline_output.depth_np

    pipeline_output.depth_colored.save(f"video_out/output_{i}_colored.png")