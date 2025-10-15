1.数据集在zhongche_annotated中，仅部分图像有标注信息。

2.数据集中目前一共标注了五类，分别是螺丝头（screw_head，59个）、侧身螺丝（screw_ce，191个）、传感器（chuanganqi，10个）、油窗（youchuang，1个）、轴箱（zhouxiang，11个）。

3.由于标注数据数目差异较大，这里我训练了两个模型，其中best_screw_detection.pt用于检测两类螺丝（重命名为screw和sidescrew），best_other_detection.pt用于检测剩余三类元件。

    best_screw_detection.pt检测效果：
    mAP@0.5: 0.988， mAP@0.5:0.95: 0.456
    
    best_other_detection.pt检测效果：
    mAP@0.5: 0.884， mAP@0.5:0.95: 0.556

4.screw_detection.py用于测试螺丝检测效果，all_detection.py能检测所有元件，并将两个模型的检测结果画在同一图像中。两个模型效果都不是太好，需要把阈值设置的比较低才能检测出尽可能多的元件。
