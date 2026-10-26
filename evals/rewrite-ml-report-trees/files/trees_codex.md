#### b. Growing and pruning:

![Depth sweep: training and CV scores, leaf counts](hw2_outputs_113062131/figures/tree_depth_sweep.png)

| max_depth | accuracy_mean | accuracy_std | macro_f1_mean | macro_f1_std | train_accuracy_mean | train_accuracy_std | train_macro_f1_mean | train_macro_f1_std | mean_leaf_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.2026 | 0.0045 | 0.0556 | 0.0015 | 0.2032 | 0.0012 | 0.0559 | 0.0004 | 2.0000 |
| 2 | 0.2717 | 0.0051 | 0.0857 | 0.0014 | 0.2732 | 0.0013 | 0.0866 | 0.0005 | 4.0000 |
| 3 | 0.3347 | 0.0124 | 0.1398 | 0.0045 | 0.3394 | 0.0028 | 0.1427 | 0.0005 | 7.4000 |
| 5 | 0.3880 | 0.0173 | 0.2075 | 0.0157 | 0.4130 | 0.0076 | 0.2240 | 0.0235 | 21.4000 |
| 8 | 0.4429 | 0.0178 | 0.3043 | 0.0091 | 0.5390 | 0.0073 | 0.4018 | 0.0155 | 108.0000 |
| 12 | 0.4394 | 0.0208 | 0.3285 | 0.0178 | 0.7398 | 0.0116 | 0.6959 | 0.0134 | 487.8000 |
| 20 | 0.4182 | 0.0181 | 0.3141 | 0.0281 | 0.9897 | 0.0049 | 0.9878 | 0.0055 | 1150.8000 |
| None | 0.4224 | 0.0129 | 0.3148 | 0.0218 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1184.2000 |

![Minimum leaf size sweep](hw2_outputs_113062131/figures/tree_min_leaf_sweep.png)

| min_samples_leaf | accuracy_mean | accuracy_std | macro_f1_mean | macro_f1_std | train_accuracy_mean | train_accuracy_std | train_macro_f1_mean | train_macro_f1_std | mean_leaf_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.4224 | 0.0129 | 0.3148 | 0.0218 | 1.0000 | 0.0000 | 1.0000 | 0.0000 | 1184.2000 |
| 2 | 0.4198 | 0.0098 | 0.3138 | 0.0197 | 0.8630 | 0.0053 | 0.8266 | 0.0064 | 857.4000 |
| 5 | 0.4394 | 0.0224 | 0.3293 | 0.0208 | 0.7166 | 0.0034 | 0.6454 | 0.0087 | 426.6000 |
| 10 | 0.4465 | 0.0181 | 0.3283 | 0.0110 | 0.6278 | 0.0034 | 0.5355 | 0.0061 | 226.2000 |
| 20 | 0.4545 | 0.0249 | 0.3266 | 0.0198 | 0.5581 | 0.0045 | 0.4437 | 0.0112 | 117.0000 |
| 50 | 0.4278 | 0.0178 | 0.2972 | 0.0266 | 0.4884 | 0.0042 | 0.3521 | 0.0090 | 50.0000 |
| 100 | 0.4144 | 0.0158 | 0.2601 | 0.0175 | 0.4511 | 0.0047 | 0.2900 | 0.0191 | 27.4000 |

56 組聯合 grid 以 CV macro-F1 選出 `{'max_depth': 12, 'min_samples_leaf': 5}`，accuracy = 0.4526 ± 0.0219，macro-F1 = 0.3384 ± 0.0164。[完整 joint grid](hw2_outputs_113062131/tables/tree_joint_grid.csv) 包含每組 training／CV scores 與平均 leaf count。

`max_depth=1` 的 training/CV macro-F1 為 0.0559/0.0556；`min_samples_leaf=100` 為 0.2900/0.2601。fully grown tree 為 1.0000/0.3148，training–CV gap = 0.6852。限制過小的 depth 或過大的 leaf size 會降低可表達的 boundary 複雜度；同時出現低 training／CV scores 才支持 underfitting。較深 tree 的 training score 上升而 CV 未同步改善、甚至下降，則支持 overfitting；這些判斷需一併比較圖中的折間 SD，不能只由 hyperparameter 大小推論。

#### c. Many trees

此處的 single tree 固定為 fully grown tree，與前節 CV 選出的 tree 分開列示。Bagging 的每棵 tree 使用所有 features；Random Forest 每個 split 隨機考慮 `sqrt` features。兩者均使用 bootstrap、fully grown trees 與 `class_weight=None`。

![Ensemble scores versus number of trees](hw2_outputs_113062131/figures/ensemble_tree_count_sweep.png)

| model | n_estimators | accuracy_mean | accuracy_std | macro_f1_mean | macro_f1_std |
| --- | --- | --- | --- | --- | --- |
| Fully grown tree | 1 | 0.4224 | 0.0129 | 0.3148 | 0.0218 |
| Bagging | 300 | 0.5314 | 0.0226 | 0.4232 | 0.0326 |
| Random Forest | 200 | 0.5432 | 0.0204 | 0.4270 | 0.0323 |

不同 tree count 的完整分數見 [sweep table](hw2_outputs_113062131/tables/ensemble_tree_count_sweep.csv)。各 family 的 tree count 依相同 CV macro-F1 規則決定。

Bagging 的 CV macro-F1 從 1 tree 的 0.2922 變為 300 trees 的 0.4232（差 +0.1310）；200→300 trees 的差為 +0.0070。 Random Forest 的 CV macro-F1 從 1 tree 的 0.2738 變為 300 trees 的 0.4253（差 +0.1515）；200→300 trees 的差為 -0.0017。

Bootstrap sensitivity 使用 fold 0 的固定 validation set。從該 fold 的 training portion 產生 5 組獨立的 bootstrap pairs，每組 A／B 樣本供三種模型共用，estimator random seed 保持相同。disagreement 是 A／B 兩模型在同一 validation set 上預測不同的比例；它衡量 predictions 對抽樣的敏感度，並非 accuracy。

| model | pair | disagreement | validation_tracks | distinct_training_A | distinct_training_B |
| --- | --- | --- | --- | --- | --- |
| Fully grown tree | 1 | 0.6002 | 848 | 2138 | 2120 |
| Bagging | 1 | 0.3090 | 848 | 2138 | 2120 |
| Random Forest | 1 | 0.2311 | 848 | 2138 | 2120 |
| Fully grown tree | 2 | 0.6050 | 848 | 2181 | 2137 |
| Bagging | 2 | 0.3019 | 848 | 2181 | 2137 |
| Random Forest | 2 | 0.2700 | 848 | 2181 | 2137 |
| Fully grown tree | 3 | 0.6167 | 848 | 2145 | 2145 |
| Bagging | 3 | 0.2948 | 848 | 2145 | 2145 |
| Random Forest | 3 | 0.2618 | 848 | 2145 | 2145 |
| Fully grown tree | 4 | 0.6132 | 848 | 2147 | 2143 |
| Bagging | 4 | 0.3066 | 848 | 2147 | 2143 |
| Random Forest | 4 | 0.2358 | 848 | 2147 | 2143 |
| Fully grown tree | 5 | 0.5719 | 848 | 2169 | 2157 |
| Bagging | 5 | 0.3125 | 848 | 2169 | 2157 |
| Random Forest | 5 | 0.2583 | 848 | 2169 | 2157 |

| model | disagreement_mean | disagreement_std |
| --- | --- | --- |
| Fully grown tree | 0.6014 | 0.0177 |
| Bagging | 0.3050 | 0.0069 |
| Random Forest | 0.2514 | 0.0170 |

表中的 SD 是 5 組 paired bootstrap disagreement 的 sample SD，不是 confidence interval；因為只使用一個 validation fold，不代表所有資料切分的變動。

Random Forest 相對 Bagging 的 CV macro-F1 差為 +0.0038；平均 disagreement 差為 -0.0535。前者越高表示此評估下的分類效果越好，後者越低表示此 perturbation 下的 predictions 越穩定；兩者衡量不同面向，不能互相替代。

若 base-model outputs 各有 variance $\sigma^2$，pairwise correlation 近似 $\rho$，則平均 $B$ 個 outputs 的 variance 為

$$\operatorname{Var}(\bar f_B)=\frac{1}{B^2}\left[B\sigma^2+B(B-1)\rho\sigma^2\right]=\rho\sigma^2+\frac{1-\rho}{B}\sigma^2.$$

增加 trees 可以降低第二項，但受第一項限制，因此改善通常趨於飽和。Random Forest 的 feature subsampling 旨在降低 tree correlation，可能犧牲單棵 tree 的表現以換取較小的 ensemble variance。此公式適用於數值 outputs／class probability 的平均；經 argmax 轉成離散分類後，並不保證 accuracy 或 disagreement 隨 tree count 單調改善。本實驗的 paired disagreement 是上述機制的經驗檢查，沒有直接估計 $\rho$，因此不把較低 disagreement 當作已證明 correlation 較低。
