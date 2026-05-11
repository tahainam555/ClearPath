"""Depth estimation module using MiDaS-compatible model loading and inference utilities.

This module provides the DepthEstimator class for monocular depth estimation using
Intel's MiDaS small model (Ranftl et al., 2022). It handles model loading, preprocessing,
inference, and postprocessing of depth maps for real-time obstacle detection.
"""

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms


class DepthEstimator:
    """
    Loads and manages the MiDaS small depth estimation model.
    
    Handles preprocessing of raw video frames, inference with the pre-trained
    depth model, and postprocessing to produce both visualization and analysis-ready
    depth maps.
    
    Reference: Ranftl et al. (2022). "Towards Robust Monocular Depth Estimation:
    Mixing Datasets for Zero-shot Cross-dataset Transfer." IEEE TPAMI.
    """
    
    def __init__(self, device: str = "cpu"):
        """
        Initialize the DepthEstimator with MiDaS small model.
        
        Loads the pre-trained MiDaS small model and its preprocessing transform
        from Intel's torch hub repository.
        
        Args:
            device (str): Device to run the model on ('cpu' or 'cuda'). Defaults to 'cpu'.
        
        Raises:
            RuntimeError: If model or transform loading fails.
        """
        self.device = device
        
        try:
            # Load the MiDaS small model from Intel's torch hub
            # MiDaS_small is optimized for real-time inference with lower memory footprint
            print("[DepthEstimator] Loading MiDaS small model from torch.hub...")
            self.model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")
            self.model = self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode (disables dropout, batch norm statistics updates)
            print("[DepthEstimator] Model loaded successfully.")
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to load MiDaS model: {str(e)}. "
                "Ensure torch.hub can access the Intel MiDaS repository and "
                "that your internet connection is stable."
            )
        
        try:
            # Load the official MiDaS preprocessing transform pipeline
            # This ensures consistent input preprocessing as used during model training
            print("[DepthEstimator] Loading MiDaS transform pipeline...")
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self.transform = midas_transforms.small_transform
            print("[DepthEstimator] Transform pipeline loaded successfully.")
            
        except Exception as e:
            raise RuntimeError(
                f"Failed to load MiDaS transform: {str(e)}. "
                "Ensure torch.hub can access the Intel MiDaS repository and "
                "that your internet connection is stable."
            )
    
    def predict(self, frame: np.ndarray) -> tuple:
        """
        Estimate depth from a single frame and return visualization + raw data.
        
        Accepts a raw BGR frame (OpenCV format), preprocesses it according to MiDaS
        specifications, runs inference, and postprocesses the output to return both
        a colorized visualization (for display) and the raw normalized depth values
        (for zone analysis and obstacle detection).
        
        Args:
            frame (np.ndarray): Input frame as BGR numpy array (OpenCV format).
                                Expected shape: (height, width, 3) with dtype uint8.
        
        Returns:
            tuple: (colored_depth_map, normalized_depth_array)
                - colored_depth_map (np.ndarray): Depth map with INFERNO colormap applied.
                                                  Shape: (height, width, 3), dtype: uint8, BGR.
                - normalized_depth_array (np.ndarray): Raw normalized depth values.
                                                       Shape: (height, width), dtype: uint8,
                                                       values in range [0, 255].
        
        Raises:
            ValueError: If frame format is invalid (not 3D array or wrong number of channels).
            RuntimeError: If inference fails.
        """
        
        # Validate input frame format
        if not isinstance(frame, np.ndarray) or frame.ndim != 3:
            raise ValueError("Frame must be a 3D numpy array (height, width, 3).")
        
        if frame.shape[2] != 3:
            raise ValueError(f"Frame must have 3 channels (BGR), got {frame.shape[2]}.")
        
        # Store original frame dimensions for postprocessing resizing
        original_height, original_width = frame.shape[:2]
        
        # ============ PREPROCESSING STAGE ============
        
        # Convert BGR (OpenCV standard) to RGB (PyTorch/MiDaS standard)
        # MiDaS model was trained on RGB images; using BGR directly would produce
        # inverted color channel responses in intermediate features
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Apply the MiDaS preprocessing transformation pipeline
        # This standardized transform includes:
        #   1. Resizing to model input size (256x256 for MiDaS_small)
        #   2. Normalization using ImageNet statistics (mean/std)
        #   3. Conversion to PyTorch tensor (1, 3, H, W) format
        # Using the official transform ensures consistency with training conditions
        input_batch = self.transform(frame_rgb).to(self.device)
        
        # ============ INFERENCE STAGE ============
        
        # Run depth estimation with gradient computation disabled
        # torch.no_grad() context:
        #   - Disables autograd (no computational graph built)
        #   - Reduces memory usage significantly (~50% reduction typical)
        #   - Speeds up inference by avoiding gradient bookkeeping
        with torch.no_grad():
            depth_output = self.model(input_batch)
        
        # ============ POSTPROCESSING STAGE ============
        
        # Resize the depth map back to the original frame dimensions
        # The model outputs depth at 256x256; we need to scale back to original input size
        # Bilinear interpolation preserves smooth depth transitions better than nearest-neighbor
        depth_resized = F.interpolate(
            depth_output.unsqueeze(0),  # Add batch dimension if not present: (1, 1, H, W)
            size=(original_height, original_width),
            mode="bilinear",
            align_corners=False  # More stable for arbitrary input sizes
        )
        
        # Convert PyTorch tensor to numpy array
        # squeeze() removes singleton dimensions, .cpu() moves to CPU RAM if on GPU,
        # .numpy() creates numpy array view
        depth_np = depth_resized.squeeze().cpu().numpy()
        
        # Normalize depth values to 0-255 range for visualization and analysis
        # Min-max normalization: (x - min) / (max - min) * 255
        depth_min = depth_np.min()
        depth_max = depth_np.max()
        
        if depth_max > depth_min:
            # Standard normalization when there is variance in depth values
            normalized_depth = ((depth_np - depth_min) / (depth_max - depth_min) * 255).astype(np.uint8)
        else:
            # Edge case: all depth values are identical (flat plane or very close obstacles)
            # Create uniform gray map (middle of range)
            normalized_depth = np.full_like(depth_np, 127, dtype=np.uint8)
        
        # Apply INFERNO colormap for enhanced visualization
        # INFERNO palette provides:
        #   - Perceptually uniform color progression
        #   - Better distinction for visually impaired users (high contrast)
        #   - Dark colors for close objects (low depth values)
        #   - Bright colors for far objects (high depth values)
        colored_depth = cv2.applyColorMap(normalized_depth, cv2.COLORMAP_INFERNO)
        
        # ============ RETURN RESULTS ============
        
        # Return both representations:
        # 1. Colored map for web UI display
        # 2. Raw normalized array for zone analysis and obstacle detection algorithms
        return colored_depth, normalized_depth
