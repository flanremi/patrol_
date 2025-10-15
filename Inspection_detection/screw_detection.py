from ultralytics import YOLO
import os

model_path = "best_screw_detection.pt"
test_path = "./test_images"
save_path = "./test_results"

model = YOLO(model_path)

os.makedirs(save_path, exist_ok=True)
for file in os.listdir(test_path):
    if ".png" in file:
        test_image = os.path.join(test_path,file)
        
        if os.path.exists(test_image):
            preds = model(
                test_image,
                imgsz=640,
                device="0",
                conf=0.15,  # 置信度阈值
                iou=0.1   # NMS的IoU阈值 （因为算法容易漏检，这里两个阈值都设置的比较小）
            )
            
            preds[0].save(os.path.join(save_path,file))

