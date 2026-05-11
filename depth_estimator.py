"""
Depth estimator module using MiDaS (small) on CPU.

Provides DepthEstimator class that loads the MiDaS_small model via torch.hub
and exposes an `estimate(frame)` method that accepts an OpenCV BGR frame (numpy
array) and returns (depth_gray, vis_bgr) where depth_gray is 0-255 single-channel
numpy array and vis_bgr is a colored visualization using COLORMAP_INFERNO.

Model weights are downloaded automatically on first run via torch.hub.
"""
import torch
import numpy as np
import cv2


class DepthEstimator:
    """Load MiDaS_small on CPU and run inference on frames.

    This class is designed to be lightweight and run on CPU-only systems.
    """

    def __init__(self):
        # Force CPU device everywhere
        self.device = torch.device('cpu')

        # Load MiDaS small model and transforms via torch.hub
        # The hub module will download weights on first use.
        model_type = 'MiDaS_small'
        self.midas = torch.hub.load('intel-isl/MiDaS', model_type)
        self.midas.to(self.device)
        self.midas.eval()

        # Load transforms that match the selected model
        midas_transforms = torch.hub.load('intel-isl/MiDaS', 'transforms')
        # small_transform is appropriate for MiDaS_small
        self.transform = midas_transforms.small_transform

    def estimate(self, bgr_frame: np.ndarray):
        """Estimate depth for an OpenCV BGR frame.

        Args:
            bgr_frame: HxWx3 uint8 BGR image from cv2

        Returns:
            depth_gray: HxW uint8 numpy array normalized to 0-255
            vis_bgr: HxWx3 uint8 BGR colored visualization
        """
        # Convert BGR to RGB for MiDaS transforms
        img_rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

        # The transform expects a PIL-like/numpy image (H,W,3 RGB)
        input_batch = self.transform(img_rgb).unsqueeze(0)
        input_batch = input_batch.to(self.device)

        with torch.no_grad():
            prediction = self.midas(input_batch)
            # prediction shape: 1x1xHxW (model-specific). Resize to input size.
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=img_rgb.shape[:2],
                mode='bicubic',
                align_corners=False,
            ).squeeze()

        depth = prediction.cpu().numpy()

        # Normalize to 0-255 (stretch to full dynamic range)
        d_min, d_max = depth.min(), depth.max()
        if d_max - d_min > 1e-6:
            norm = (depth - d_min) / (d_max - d_min)
        else:
            norm = np.zeros_like(depth)

        depth_gray = (norm * 255.0).astype('uint8')

        # Colored visualization using OpenCV colormap (INFERNO)
        vis_bgr = cv2.applyColorMap(depth_gray, cv2.COLORMAP_INFERNO)

        return depth_gray, vis_bgr
