"""AeroCadastre Autonomous Experiment Orchestrator.

Sequentially executes:
1. Controlled improvement experiments
2. Comparative metrics aggregation
3. Final evaluation on untouched test set
4. End-to-end inference and GeoJSON polygon generation
"""

import sys
import subprocess
from pathlib import Path
import json

from ml.building_detection.experiment_tracker import generate_experiment_comparison
from ml.building_detection.evaluator import evaluate_checkpoint_on_test
from infer_buildings import run_inference


def main():
    root = Path("D:/SIH26012_AeroCadastre")
    configs = [
        root / "experiments/building_detection/configs/EXP_BUILDING_UNET_002.yaml",
        root / "experiments/building_detection/configs/EXP_BUILDING_UNET_003.yaml",
        root / "experiments/building_detection/configs/EXP_BUILDING_RESUNET_001.yaml",
    ]

    for cfg in configs:
        exp_id = cfg.stem
        print(f"\n=======================================================")
        print(f"Launching Experiment: {exp_id}")
        print(f"=======================================================")
        cmd = [sys.executable, str(root / "train.py"), "--config", str(cfg)]
        ret = subprocess.run(cmd, cwd=str(root))
        if ret.returncode != 0:
            print(f"ERROR: Experiment {exp_id} failed with exit code {ret.returncode}")
        else:
            print(f"SUCCESS: Experiment {exp_id} completed.")

    # Generate comparison
    print("\nGenerating Experiment Comparison...")
    comp_res = generate_experiment_comparison(
        experiments_dir=root / "experiments/building_detection",
        output_dir=root / "experiments/building_detection/reports",
    )
    print(f"Comparison report generated with {len(comp_res['records'])} experiments.")

    # Find champion model
    records = comp_res["records"]
    if records:
        best_exp = records[0]
        best_id = best_exp["experiment_id"]
        print(f"\nChampion Model: {best_id} (Val IoU: {best_exp['val_iou']*100:.2f}%)")

        best_ckpt = root / f"experiments/building_detection/{best_id}/checkpoints/best_model.pt"
        manifest_p = root / "data/real/inria/patches/exported_patch_manifest.json"
        out_eval = root / "experiments/building_detection/reports/test_evaluation"

        print(f"\nEvaluating champion {best_id} on UNTOUCHED test set...")
        test_metrics = evaluate_checkpoint_on_test(
            checkpoint_path=best_ckpt,
            patch_manifest_path=manifest_p,
            output_dir=out_eval,
        )
        print(f"Test IoU: {test_metrics['iou']*100:.2f}%, Test Dice: {test_metrics['dice']*100:.2f}%, Boundary F1: {test_metrics.get('boundary_f1', 0.0)*100:.2f}%")

        # Run End-to-End Inference & GIS Polygon Generation on full tile
        print(f"\nRunning End-to-End Inference on Inria Tile...")
        demo_image = root / "experiments/building_detection/dataset_report/samples/audit_sample_1_austin1.png"
        infer_out = root / "experiments/building_detection/predictions/champion_demo"
        infer_res = run_inference(
            image_path=demo_image,
            checkpoint_path=best_ckpt,
            output_dir=infer_out,
            threshold=0.5,
            patch_size=256,
            stride=192,
        )
        print(f"Inference complete: {infer_res['building_count']} building polygons generated.")

    print("\n=======================================================")
    print("ALL AUTONOMOUS EXPERIMENTS AND GIS EXTRACTIONS COMPLETE")
    print("=======================================================")


if __name__ == "__main__":
    main()
