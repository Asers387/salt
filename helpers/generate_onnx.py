# Copyright (c) Meta Platforms, Inc. and affiliates.

# This source code is licensed under the Apache-2.0 license found in the LICENSE file in the root directory of segment_anything repository and source tree.
# Adapted from onnx_model_example.ipynb in the segment_anything repository.
# Please see the original notebook for more details and other examples and additional usage.
import argparse
import os
import shutil
import warnings

import torch
from onnxruntime.quantization import QuantType
from onnxruntime.quantization.quantize import quantize_dynamic
from PIL import Image
from segment_anything import SamPredictor, sam_model_registry
from segment_anything.utils.onnx import SamOnnxModel

warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)


def save_onnx_model(
    checkpoint, model_type, onnx_model_path, orig_im_size, opset_version, quantize=True
):
    sam = sam_model_registry[model_type](checkpoint=checkpoint)

    onnx_model = SamOnnxModel(sam, return_single_mask=True)

    dynamic_axes = {
        "point_coords": {1: "num_points"},
        "point_labels": {1: "num_points"},
    }

    embed_dim = sam.prompt_encoder.embed_dim
    embed_size = sam.prompt_encoder.image_embedding_size
    mask_input_size = [4 * x for x in embed_size]
    dummy_inputs = {
        "image_embeddings": torch.randn(1, embed_dim, *embed_size, dtype=torch.float),
        "point_coords": torch.randint(
            low=0, high=1024, size=(1, 5, 2), dtype=torch.float
        ),
        "point_labels": torch.randint(low=0, high=4, size=(1, 5), dtype=torch.float),
        "mask_input": torch.randn(1, 1, *mask_input_size, dtype=torch.float),
        "has_mask_input": torch.tensor([1], dtype=torch.float),
        "orig_im_size": torch.tensor(orig_im_size, dtype=torch.float),
    }
    output_names = ["masks", "iou_predictions", "low_res_masks"]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=torch.jit.TracerWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        with open(onnx_model_path, "wb") as f:
            torch.onnx.export(
                onnx_model,
                tuple(dummy_inputs.values()),
                f,
                export_params=True,
                verbose=False,
                opset_version=opset_version,
                do_constant_folding=True,
                input_names=list(dummy_inputs.keys()),
                output_names=output_names,
                dynamic_axes=dynamic_axes,
            )

    if quantize:
        temp_model_path = os.path.join(os.path.split(onnx_model_path)[0], "temp.onnx")
        shutil.copy(onnx_model_path, temp_model_path)
        quantize_dynamic(
            model_input=temp_model_path,
            model_output=onnx_model_path,
            optimize_model=True,
            per_channel=False,
            reduce_range=False,
            weight_type=QuantType.QUInt8,
        )
        os.remove(temp_model_path)


def main(
    checkpoint_path, model_type, onnx_models_path, dataset_path, opset_version, quantize
):
    if not os.path.exists(onnx_models_path):
        os.makedirs(onnx_models_path)

    images_path = os.path.join(dataset_path, "images")

    im_sizes = set()
    for image_path in os.listdir(images_path):
        if (
            image_path.endswith(".jpg")
            or image_path.endswith(".JPG")
            or image_path.endswith(".png")
        ):
            im_path = os.path.join(images_path, image_path)
            im_sizes.add(Image.open(im_path).size[::-1])

    for orig_im_size in im_sizes:
        onnx_model_path = os.path.join(
            onnx_models_path, f"sam_onnx.{orig_im_size[0]}_{orig_im_size[1]}.onnx"
        )
        save_onnx_model(
            checkpoint_path,
            model_type,
            onnx_model_path,
            orig_im_size,
            opset_version,
            quantize,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-path", type=str, default="./sam_vit_h_4b8939.pth")
    parser.add_argument("--model_type", type=str, default="default")
    parser.add_argument("--onnx-models-path", type=str, default="./models")
    parser.add_argument("--dataset-path", type=str, default="./dataset")
    parser.add_argument("--opset-version", type=int, default=15)
    parser.add_argument("--quantize", action="store_true")
    args = parser.parse_args()

    checkpoint_path = args.checkpoint_path
    model_type = args.model_type
    onnx_models_path = args.onnx_models_path
    dataset_path = args.dataset_path
    opset_version = args.opset_version
    quantize = args.quantize

    main(
        checkpoint_path,
        model_type,
        onnx_models_path,
        dataset_path,
        opset_version,
        quantize,
    )
