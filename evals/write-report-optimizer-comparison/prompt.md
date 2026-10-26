---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

幫我寫期末報告 4.2 節的實驗結果分析（一到兩段就好），比較 SGD、Adam、AdamW。設定是 ResNet-18、CIFAR-10、訓練 100 epochs、5 個 seed 平均：

- SGD（lr=0.1、momentum=0.9、cosine decay）：最終 test accuracy 95.1 ± 0.2%，最後 train loss 0.002，第 10 個 epoch 的 test accuracy 71.3%
- Adam（lr=1e-3）：最終 test accuracy 93.4 ± 0.3%，最後 train loss 0.0008，第 10 個 epoch 84.6%
- AdamW（lr=1e-3、weight decay=5e-4）：最終 test accuracy 94.6 ± 0.2%，最後 train loss 0.003，第 10 個 epoch 83.9%

要解釋為什麼 Adam 前期比較快、最後反而比較差，還有 AdamW 為什麼能補回來。存成 optimizer_analysis.md。
