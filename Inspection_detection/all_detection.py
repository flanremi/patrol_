from ultralytics import YOLO
import os
from ultralytics.utils.plotting import Colors
import cv2

screw_model_path = "best_screw_detection.pt"
other_model_path = "best_other_detection.pt"
test_path = "./test_images"
save_path = "./test_results"
overall_class_names = ["chuanganqi", "sidescrew", "screw", "youchuang", "zhouxiang"]


screw_model = YOLO(screw_model_path)
other_model = YOLO(other_model_path)

def draw_detection_res(target_img, preds):
    colors = Colors()
    for result in preds:
        boxes = result.boxes.xyxy.detach().cpu().numpy() 
        confidences = result.boxes.conf.detach().cpu().numpy() 
        class_ids = result.boxes.cls.detach().cpu().numpy().astype(int)
        class_names = result.names  

    for i in range(len(boxes)):
        box = boxes[i]
        conf = confidences[i]
        cls_id = class_ids[i]
        cls_name = class_names[cls_id]

        if cls_name in overall_class_names:
            overall_cls_id = overall_class_names.index(cls_name)
        
            plot_one_box(
                box, 
                target_img,
                label=f"{cls_name} {conf:.2f}", 
                color=colors(overall_cls_id), 
                line_width=3
            )

def plot_one_box(box, img, label=None, color=None, line_width=3):
    # 转换为整数坐标
    x1, y1, x2, y2 = map(int, box)
    
    # 绘制边框
    cv2.rectangle(img, (x1, y1), (x2, y2), color, line_width)
    
    # 绘制标签
    if label:
        # 计算文本尺寸
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2
        (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, line_width)
        
        # 绘制标签背景（半透明填充）
        cv2.rectangle(
            img,
            (x1, y1 - text_height - 5),
            (x1 + text_width, y1),
            color,
            -1  # 填充整个矩形
        )
        
        # 绘制标签文本
        cv2.putText(
            img,
            label,
            (x1, y1 - 5),
            font,
            font_scale,
            (0, 0, 0),
            line_width
        )
    return img
  
img_size = 640
device = "0"

os.makedirs(save_path, exist_ok=True)
for file in os.listdir(test_path):
    if ".png" in file:
        test_image = os.path.join(test_path,file)
        
        if os.path.exists(test_image):
            target_img = cv2.imread(test_image)

            preds = screw_model(
                test_image,
                imgsz=img_size,
                device=device,
                conf=0.1, 
                iou=0.1
            )
            draw_detection_res(target_img, preds)

            other_preds = other_model(
                test_image,
                imgsz=img_size,
                device=device,
                conf=0.1, 
                iou=0.1
            )
            draw_detection_res(target_img, other_preds)
            
            cv2.imwrite(os.path.join(save_path, os.path.basename(test_image)),target_img)

