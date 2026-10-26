# 前後對照範例

左邊（✗）是 Codex 產生的 HW2 報告原文，右邊（✓）是作者親手改過的定稿，兩者引用的都是同一批實驗數字。每組後面標注用到 SKILL.md 的哪幾條原則，並簡短說明改了什麼。最後一組是一般心得的例子。

這些是用來抓口吻的範例，不是要照抄的句型。改別的文件時，學的是「為什麼這樣改」。

## 目錄

1. k-NN：三個預測錯誤的案例（原則 2、5、9）
2. k-NN：k 的大小（原則 1、4、9）
3. k-NN：加入雜訊維度（原則 1、5、8）
4. Naive Bayes：特徵翻轉 prior（原則 1、5）
5. Naive Bayes：尺度與 var_smoothing（原則 1、5）
6. Naive Bayes：選定 smoothing（原則 8）
7. Naive Bayes：假設不成立的證據（原則 8）
8. Naive Bayes：複製 energy 欄位（原則 1、6）
9. SVM：C 與 gamma 的區域（原則 3、結構）
10. SVM：support vector 比例的但書（原則 8）
11. Accuracy 與 macro-F1 結論不同（原則 1）
12. 電報體改成連貫句（原則 6、10）
13. ROC-AUC 高但 F1 低（原則 3）
14. 永遠猜負類的 baseline（原則 7、9）
15. 哪些指標看得出實用性（原則 3、8）
16. 策展人的聆聽成本（原則 7、8）
17. 一般心得（速查表、場合）
18. 作者逐句圈出的修辭套路（原則 8、11）
19. 心得：作者的微調與不喜歡的寫法（原則 10、12）
20. 給教授的信：作者評為「完美」的版本（場合）

---

## 1. k-NN：三個預測錯誤的案例

✗
```
- Case 1（row 5020）：true genre 為 `death-metal`，只得到 0/5 票；`techno` 得到 3/5 票。uniform voting 因此選擇該 genre。距離只決定哪些鄰居入選，入選後每位鄰居各有一票；feature-space 接近不保證 genre 相同。
- Case 2（row 1805）：true genre 為 `jazz`，只得到 0/5 票；`ambient` 得到 2/5 票。uniform voting 因此選擇該 genre。距離只決定哪些鄰居入選，入選後每位鄰居各有一票；feature-space 接近不保證 genre 相同。
- Case 3（row 2329）：true genre 為 `heavy-metal`，只得到 1/5 票；`punk` 得到 2/5 票。uniform voting 因此選擇該 genre。距離只決定哪些鄰居入選，入選後每位鄰居各有一票；feature-space 接近不保證 genre 相同。
```

✓
```
距離遠近只決定誰能擠進前 $k$ 名，一旦入選後每個鄰居都只有一票：
* **Case 1（row 5020）**：因為 `death-metal` 本身樣本很少，前 5 近鄰完全沒有同類認領他很可憐，反而被大類別 `techno` 拿走 3/5 票而誤判。
* **Case 2（row 1805）**：前 3 近鄰其實距離更近（0.85～1.04），但分別投給不同類別，反而是排第 4、5 名的 `ambient`（距離 > 1.23）因為湊到 2/5 票而勝出。
* **Case 3（row 2329）**：雖然第 4 近鄰真的是 `heavy-metal`（1/5 票），但因為曲風特徵重疊，距離最近的兩筆都是 `punk`（2/5 票），多數決依然猜錯。
```

改了什麼：重複三次的解釋抽到開頭講一次。每個案例各自找到不同的失敗原因（樣本太少、近的票太分散、特徵重疊），而不是重報票數。「擠進」「拿走」「湊到」讓投票過程看得見；「沒有同類認領他很可憐」是整節唯一的俏皮話，放在最不公平的那個案例。

## 2. k-NN：k 的大小

✗
```
小 k 的 local decision 受個別鄰居影響較大；增加 k 會平滑 decision boundary，降低對單一樣本的敏感度，但較大 neighborhood 也讓 frequent genres 更容易占據票數。Accuracy 按樣本加權，macro-F1 讓每個 genre 等權，因此上述 rare recall 可用來檢查不同 k 是否犧牲 rare genres。曲線不必單調，並以實際最大值選參；training–CV gap 是 overfitting 線索，fold SD 則描述這組固定 folds 的差異，並非 confidence interval。
```

✓
```
較小的 $k$ 容易受單一鄰居雜訊影響（overfitting），放大 $k$ 雖然能平滑 decision boundary，但在類別不平衡下，過大的搜尋範圍會讓常見類別更容易靠人數優勢（霸凌）主導投票（underfitting）。因此，對樣本等權的 accuracy 選出了較大的 $k=34$（mean CV accuracy = `0.4658`），但此時 rare genres 的平均 recall 掉到只剩 `0.0867` 找不到同伴被別人撿走，而對各類別等權的 macro-$F_1$ 則選出較小的 $k=16$，少數族群更能被注意到了（mean CV macro-$F_1$ = `0.3519`，rare mean recall 維持在 `0.1718`）。
```

改了什麼：「frequent genres」→「常見類別」、「neighborhood」→「搜尋範圍」。直接替兩端貼上 overfitting／underfitting 的標籤。結尾兩句「曲線不必單調」「並非 confidence interval」不影響結論，刪掉。用「因此」把指標的加權方式接到選出的 k，再接到 rare recall 的後果，變成一條因果鏈。

## 3. k-NN：加入雜訊維度

✗
```
N=50 相對 N=0 的 macro-F1 變化為 -0.1552，mean neighbor retention 由 1.0000 變成 0.0614。Euclidean squared distance 額外增加 ∑(zᵢ−zⱼ)²；兩筆不同資料的每個 independent standard-normal noise dimension 平均增加 2，因此期望額外距離平方為 2N。這些差異與 genre 無關，卻會改變鄰居排序。每筆 validation track 的 retention=|original neighbors ∩ noisy neighbors|/k 已完整保存於 `tables/knn_noise_per_track_retention.csv`；這是所有 training tracks 的 OOF 結果，未使用 test set。實驗只使用一個固定 noise draw，不能把單次變化視為所有 noise seeds 的保證。
```

✓
```
在 Euclidean distance 下，每多加 $N$ 個獨立的標準常態雜訊維度，兩筆不同樣本間的距離平方就會多出 $\sum_{m=1}^N (z_{im} - z_{jm})^2$，因為 $\operatorname{Var}(z_{im} - z_{jm}) = 2$、$\operatorname{E}(z_{im} - z_{jm}) = 0$，期望上會憑空增加 $2N$ 的距離平方誤差。當 $N=50$ 時，這些與曲風無關的隨機距離已經把原本 13 個特徵的真實距離淹沒，導致原本的 16 個最近鄰平均只剩 `6.14%`（`0.0614`）還留在名單內，macro-$F_1$ 也從 `0.3519` 大幅跌至 `0.1966`（rare mean recall 從 `0.1718` 跌至 `0.0149`）。
```

改了什麼：先講機制（期望多出 2N），再用 N=50 的數字證明機制的後果，順序從「報數字→補解釋」變成「解釋→數字佐證」。「淹沒」精準描述雜訊項壓過原本距離。CSV 路徑、「未使用 test set」、「單一 noise draw」這三句流水帳和但書都刪了。

## 4. Naive Bayes：特徵翻轉 prior

✗
```
此例的 prior term 為 -1.1486，偏向 `blues`；`speechiness`、`mode`、`instrumentalness` 分別提供 +0.9546、+0.6165、+0.5890，偏向 `country`。13 個 feature terms 加上 prior 後為 +2.4569，所以 feature evidence 克服 prior，讓 `country` 的 posterior 較高。
```

✓
```
雖然樣本數較多的 `blues` 在先驗項佔優勢（`prior = -1.1486`），但 `speechiness`（`+0.9546`）、`mode`（`+0.6165`）與 `instrumentalness`（`+0.5890`）等特徵大力支持 `country`。這是因為該樣本在這三個特徵的值不僅更接近 `country` 的 mean，且 `country` 在這些特徵的 variance 明顯比 `blues` 小得多（例如 `speechiness` 的 variance 為 `0.0122` vs. `0.0716`），拉高了高斯分布的峰值密度，使 14 項加總達到 `+2.4569`（與 `predict_log_proba` 差值僅 `2.22e-15`），成功翻轉 prior 讓 `country` 勝出。
```

改了什麼：用「雖然…但…」做出對抗感。最重要的是補上原稿沒說的「為什麼」：variance 小讓峰值密度變高。數字從句子主體退到括號裡當佐證。

## 5. Naive Bayes：尺度與 var_smoothing

✗
```
Default GaussianNB 使用 `epsilon_ = var_smoothing × max_j Var(X_j)`，再把同一個 epsilon 加到所有 class-feature variances。這個 global additive floor 不會隨各 feature 的尺度分別縮放，因此 raw 與 standardized 結果可能不同；沒有這個 floor 的理想 Gaussian density，在非零線性縮放下會多出所有 classes 共用的 Jacobian，posterior class ranking 才應不變。
```

✓
```
理論上 GaussianNB 對各特徵獨立建模，線性縮放只會多出各類別共用的常數項，不應改變預測排名。但 `scikit-learn` 為了數值穩定，會在所有類別與特徵的 variance 上加上同一個全域平滑項 $\epsilon = \text{var\_smoothing} \times \max_j \operatorname{Var}(X_j)$。在未標準化的 raw features 中，`duration_ms` 的變異數高達 $2.18 \times 10^{10}$，導致算出來的 $\epsilon \approx 21.83$，直接把 20*13 = 260 個 class-feature 變異數中的 214 個淹沒成平緩的分布（epsilon 占比過半），……只剩 `duration_ms`、`tempo` 與少數 genre 的 `loudness` 還能區分類別，造成分數崩跌。
```

改了什麼：「理論上…但…」先建立預期再翻轉，讀者會想知道為什麼。原稿抽象地說「可能不同」，定稿直接點名兇手 `duration_ms`，算出 ε≈21.83，再說它淹沒了 214 個 variance。

## 6. Naive Bayes：選定 smoothing

✗
```
依預先固定的 CV macro-F1 criterion，後續 GaussianNB 實驗使用 `var_smoothing=1.0e-01`，mean macro-F1=0.3623、fold SD=0.0182。提高 variance floor 可減輕極小 class-feature variance 的不穩定 penalty；過強 smoothing 也會抹平有辨識力的 distribution 差異。選參使用這組 folds，因此 selected CV score 可能偏樂觀，最終泛化結果需由獨立 test set 評估。
```

✓
```
當 `var_smoothing` 逐步調大到 `1e-1` 時，較高的 variance floor 壓制了極小變異數帶來的極端懲罰，讓 `punk` 的 recall 從 `0.0836` 大幅回升到 `0.5018`，整體 CV macro-$F_1$ 也達到最高點 `0.3623`（若繼續調大到 `1.0` 則會過度抹平特徵差異，掉回 `0.2606`，0.3623 是在同一組 CV 上選出的，屬於樂觀估計）。因此後續皆固定採用 `var_smoothing = 0.1`。
```

改了什麼：「可減輕…penalty」這種一般性陳述，換成具體發生的事：punk 的 recall 從 0.08 回升到 0.50。selection optimism 是真的會影響結論的但書，所以留下來，但縮成括號裡的半句。

## 7. Naive Bayes：假設不成立的證據

✗
```
`comedy` 中的 `instrumentalness` 有 skewness=19.532、excess kurtosis=381.650；搭配 histogram 與 fitted Gaussian，可直接檢查其不對稱、集中或尾端形狀，而 Gaussian 的 population skewness/excess kurtosis 都是 0。`black-metal` 內 `energy` 與 `acousticness` 的 Pearson r=-0.808，scatter plot 顯示兩者共同變動，支持 independence assumption 不成立。這些是描述性證據，探索多個 combinations 後挑選最明顯者，不能當成未校正的 confirmatory significance test；低 correlation 本身也不能證明 independence。
```

✓
```
高斯分布的理論 skewness 與 excess kurtosis 皆為 0，但 `comedy` 的 `instrumentalness` 有高達 `88.22%` 的樣本集中在 0，形成極度右偏且尖聳的分布（skewness = `19.53`、kurtosis = `381.65`）。另外，`black-metal` 內部的 `energy` 與 `acousticness` 呈現高度負相關（$r = -0.8079$），`ambient` 的 `energy` 與 `loudness` 則高度正相關（$r = 0.8043$），明顯違反特徵間條件獨立的假設。
```

改了什麼：先說高斯應該長怎樣，再說資料長怎樣，對比自己會說話。「88.22% 集中在 0」比 skewness 數字更好懂，所以放前面。「支持…不成立」這種迂迴說法改成「明顯違反」。最後一句關於 significance test 的但書刪掉，因為題目只要求舉例說明，不需要假設檢定。

## 8. Naive Bayes：複製 energy 欄位

✗
```
0 → 5 copies 時，OOF accuracy 為 0.4566 → 0.3979，mean confidence 為 0.5989 → 0.6606，confidence−accuracy gap 為 +0.1423 → +0.2627。Exact copies 完全 dependent，但 Naive Bayes 仍把同一個 `energy` likelihood 重複相乘，等同重複累加其 log-likelihood evidence；因此 confidence 可改變，卻沒有增加獨立資訊，也不保證 accuracy 提升。若新增 evidence 支持某 class，posterior 可能更尖銳；若它與其他 features 相衝突，個別樣本也可能變得較不確定或改變 predicted class，不能宣稱 confidence 必然單調增加。
```

✓
```
因為 Naive Bayes 假設所有特徵彼此獨立，複製 5 份 `energy` 會讓模型把同一個特徵的 log-likelihood 重複加權 6 次。這不僅沒有提供新資訊，反而破壞了原本特徵間的比重，使 OOF accuracy 從 `0.4566` 掉到 `0.3979`，同時重複累加的微弱證據把後驗機率推向極端，讓平均 confidence 從 `0.5989` 膨脹到 `0.6606`，圖中的可靠性曲線也更明顯地掉到對角線下方（overconfidence 差距從 `+0.1423` 惡化至 `+0.2627`）。
```

改了什麼：箭頭串列（A → B，C → D，E → F）改成一條因果鏈：假設獨立 → 重複加權 6 次 → 比重被破壞、accuracy 掉 → 機率被推向極端、confidence 膨脹 → 曲線掉到對角線下。「掉到」「推向極端」「膨脹」「惡化」都有方向。最後一句「不能宣稱必然單調增加」刪掉。

## 9. SVM：C 與 gamma 的區域

✗
```
RBF kernel 為 $K(x,z)=\exp(-\gamma\lVert x-z\rVert^2)$。小 gamma 使 influence range 寬、decision boundary 較平滑；大 gamma 使影響局部化，容易記住個別 training observations。C 控制 margin 與 training errors 的取捨：小 C 允許較多 margin violations、regularization 較強；大 C 更重視減少 violations。過小的 C／gamma 常導致 underfitting，過大的 gamma 配合足夠大的 C 常導致 overfitting，但仍需以實際 train/CV scores 判定。

本次 grid 中最低 training macro-F1 出現在 C=0.1、gamma=10，training/CV = 0.0118/0.0118，是檢查 underfitting 的代表設定。最大 training–CV macro-F1 gap 出現在 C=1、gamma=10，training/CV = 1.0000/0.0130，gap = 0.9870，顯示該設定相對較強的 overfitting 證據。這是同一 training split 的 model-selection 診斷，並非獨立 test performance。
```

✓
```
在 RBF kernel $K(x,z) = \exp(-\gamma \Vert{}x-z\Vert{}^2)$ 中，$\gamma$ 控制單一訓練樣本的影響半徑，$C$ 則控制對錯誤分類（margin violations）的懲罰強度：
* **Underfitting 區域**：當 $C$ 與 $\gamma$ 太小（如左下角 $C=0.1, \gamma=0.001$），或者當 $\gamma=10$ 搭配過小的 $C=0.1$ 時，模型過度受限於平滑邊界或高容錯，連訓練集都分不開（$C=0.1, \gamma=10$ 的 train/CV macro-$F_1$ 皆只有 `0.0118`）。
* **Overfitting 區域**：當 $\gamma$ 很大（$\gamma \in \{1, 10\}$）且 $C \ge 1$ 時，每個 support vector 只在自己周圍極小的範圍內產生尖峰，模型等於把訓練點死記下來（例如 $C=1, \gamma=10$ 的 train macro-$F_1$ 為 `1.0000`，但 CV macro-$F_1$ 只有 `0.0130`）。
* **最佳設定**：折衷邊界平滑度與錯誤懲罰後，CV 選出 `C=100, gamma=0.01`，得到 accuracy = `0.5142 ± 0.0150`、macro-$F_1$ = `0.3999 ± 0.0090`。
```

改了什麼：題目問三件事，就用三個粗體標籤直接對應。「influence range 寬」→「影響半徑」。「連訓練集都分不開」「把訓練點死記下來」比「是檢查 underfitting 的代表設定」「相對較強的 overfitting 證據」直接得多。兩句但書（「仍需以實際分數判定」「並非獨立 test performance」）刪掉。

## 10. SVM：support vector 比例的但書

✗
```
support-vector fraction 高，表示較多 training observations 參與 boundary 的決定，可能與 overlap、outliers、噪音或類別規模有關。然而小 C 允許大量 margin violations，也可能讓容易辨識的 genre 保有高 fraction；gamma、feature scaling 與 multiclass one-vs-one 子問題亦影響哪些點成為 support vectors。因此 fraction 不能單獨當成 genre overlap 的量尺，需同時看固定 C／gamma 下的 CV F1、training count 與混淆模式。相關係數只描述本資料 20 個 genres 的 association，不建立 causal relationship；不同 C 的 rows 也不能視為獨立抽樣。
```

✓
```
從數據可以看出，support vector 比例與各曲風的 CV $F_1$ 呈現強烈負相關（在 $C=100$ 時 $r = -0.8916$），與訓練樣本數也呈負相關（$r = -0.6980$）。像 `comedy`、`techno` 與 `sleep` 這些特徵鮮明、人數又多的大類別，大部分樣本都遠離 decision boundary，因此只有 `25%～49%` 會成為 support vectors，且辨識率極高（$F_1 > 0.78$）。相反地，像 `country`、`grunge`、`jazz` 或少數類別（如 `opera`、`black-metal`），幾乎 `95%～100%` 的樣本都落在 margin 內或被分錯而成為 support vectors。

因此，support vector 比例確實能反映該曲風與其他類別在特徵空間上的**重疊程度（overlap）**，但它同時也受到**類別樣本數大小**以及**超參數 $C$ 設定**的影響（例如當 $C=0.1$ 時 margin 極寬，高達 16 個類別的比例都是 `100%`），所以解讀時需要搭配固定 $C$ 下的類別人數與 $F_1$ 一起看。
```

改了什麼：先用具體的曲風對比（大類別 25–49% vs. 難分類別 95–100%）回答「能不能反映 overlap」，再給但書。留下的但書只有一個，而且用「C=0.1 時 16 類都是 100%」這個資料裡的證據撐住。「不建立 causal relationship」「不能視為獨立抽樣」刪掉。

## 11. Accuracy 與 macro-F1 結論不同

✗
```
較多 tracks 的 genres 對 accuracy 有較大的權重，但每個 genre 在 macro-F1 中都占 1/20。例如 GaussianNB accuracy=0.4566，低於 k-NN 的 0.4656，但 macro-F1=0.3623，高於 k-NN 的 0.3519。GaussianNB 的 black-metal／tango CV F1 為 0.1230／0.4716，k-NN 則為 0.0000／0.4095，呈現兩種 aggregate metrics 對逐類差異的反應。
```

✓
```
所有模型的 accuracy 都比 macro-$F_1$ 高出約 `0.094～0.116`。這是因為幾個樣本數最多的大類別（如 `techno`、`comedy`、`sleep`）在六種模型上的 CV $F_1$ 都高達 `0.73～0.86`，直接拉高了按樣本數加權的 accuracy，而許多中小類別（如 `country`、`grunge`、`opera`）的 CV $F_1$ 普遍只有 `0.02～0.19`，在 20 類等權平均的 macro-$F_1$ 中就會把分數拉下來。這也解釋了為什麼 GaussianNB 的 accuracy（`0.4566`）雖然輸給 k-NN（`0.4656`），但因為它在少數類別（如 `black-metal` 與 `tango`）有較高的召回率（rare mean recall 達 `0.3512` vs. k-NN 的 `0.1718`），算出的 macro-$F_1$（`0.3623`）反而贏過 k-NN（`0.3519`）。
```

改了什麼：「拉高」「拉下來」「輸給」「反而贏過」讓兩個指標像在拔河。斜線配對「0.1230／0.4716」拆掉了。「呈現兩種 aggregate metrics 對逐類差異的反應」這句什麼都沒說，改成「這也解釋了為什麼…」。

## 12. 電報體改成連貫句

✗
```
最佳模型為 **Random Forest**，選擇依據為 mean CV macro-F1=0.4270。
固定模型在 test set 的 accuracy=0.5387、macro-F1=0.4372。
```

✓
```
以 mean CV macro-$F_1$ 選出的最佳模型為 **Random Forest**（`0.4270`），在完整 training set 重新訓練後，於 held-out test set 得到 **accuracy = `0.5387`**、**macro-$F_1$ = `0.4372`**。
```

改了什麼：兩行各自獨立的陳述接成一句有先後順序的話（選模型 → 重新訓練 → 測試結果），還順手補上「在完整 training set 重新訓練」這個讀者需要的步驟。

## 13. ROC-AUC 高但 F1 低

✗
```
AUC−F1 差距最大的類別為 salsa：OvR ROC-AUC=0.9842，F1=0.1429。
OvR ROC-AUC 衡量該類相對所有 negatives 的 ranking；F1 則取決於實際 multiclass decision 的 TP/FP/FN。
即使 ranking 良好，class imbalance、與其他類競爭的 decision rule 或 probability calibration 仍可能使 F1 偏低；兩項指標不能互相替代。
這個數值差距本身不證明任何單一機制，必須同時查看 confusion counts 和 class support。
```

✓
```
**一個曲風完全可能同時擁有極高的 ROC-AUC 與極低的 $F_1$**。`salsa` 的 OvR ROC-AUC 高達 `0.9842`，$F_1$ 卻只有 `0.1429`，`black-metal` 也是如此（ROC-AUC = `0.9909`，$F_1$ = `0.4000`）。這是因為 OvR ROC-AUC 只看單一類別預測機率的**相對排序（ranking）**，只要真實的 `salsa` 拿到 `0.25` 的機率、而絕大多數非 `salsa` 樣本只拿到 `0.01`，AUC 就會非常接近 1。但在 20 類競爭的 argmax 決策下，`salsa` 因為樣本極少，機率很難衝到第一，如果大類別 `r-n-b` 同時拿到 `0.30`，這首歌最終還是會被判給 `r-n-b`，所以 recall 與 $F_1$ 依然偏低。
```

改了什麼：題目問「可不可能」，第一句加粗回答。用一組假設數字（0.25、0.01、0.30）讓機制一看就懂，比列出三個可能原因有說服力得多。結尾「不證明任何單一機制」刪掉。作者後來又把「最典型的例子就是 `salsa`（…）」改成讓 `salsa` 直接當主詞，「典型」和「就是」都拿掉。

## 14. 永遠猜負類的 baseline

✗
```
Test positive prevalence=0.0547；永遠預測 not hip-hop 的 accuracy=0.9453。
此 baseline 的 positive recall 為 0，說明高 accuracy 本身不代表能找到 hip-hop。
```

✓
```
在 test set（1,060 首中有 58 首 `hip-hop`、1,002 首 `not hip-hop`）上，一個永遠回答 `not hip-hop` 的無腦分類器就能拿到 **accuracy = `0.9453`**（$1002 / 1060$），但它的 recall 是 `0`。
```

改了什麼：prevalence 換成讀者能想像的「1,060 首中有 58 首」。「無腦分類器」一詞就把「高 accuracy 不代表什麼」講完了，不需要再寫「說明…不代表…」。

## 15. 哪些指標看得出實用性

✗
```
ROC-AUC 衡量 positive／negative ranking；PR curve 和 average precision 更直接顯示 rare positives 的 retrieval trade-off。
Average precision 使用 recall increments 加權 precision，梯形 PR-AUC 使用線性 interpolation，兩者計算方式不同。
是否有使用價值還需檢查實際 threshold 的 precision、recall 與人工聆聽成本；不能只看 accuracy 或 ranking area。

RandomForest／RBF SVM 的 ROC-AUC 為 0.9042／0.8813，高於 random ranking 的 0.5；average precision 為 0.4649／0.3550，也高於 positive prevalence 0.0547，顯示 scores 能將 hip-hop 排得較前面。但 default threshold 的 recall 僅 0.0690／0.0000，accuracy 0.9491／0.9453 幾乎等於 always-negative baseline 0.9453，不能據此認為 detectors 已完成搜尋目標。
```

✓
```
* **看不出實用性的指標**：預設閾值下的 **accuracy（`0.9491` / `0.9453`）**、**TNR（`1.0000`）** 與 **NPV（`~0.945`）** 幾乎跟永遠猜負類的 baseline（`0.9453`）一樣高，完全掩蓋了模型在預設閾值下漏抓了 93%～100% `hip-hop` 曲目的事實。
* **能看出模型潛力與表現的指標**：**ROC-AUC（`0.9042` / `0.8813`）** 與 **Average Precision（`0.4649` / `0.3550`，遠高於隨機猜測的先驗比例 `0.0547`）** 證明模型輸出的連續分數其實能把 `hip-hop` 排在很前面，只要根據任務需求調降決策 threshold（搭配 **TPR、PPV 與 $F_1$** 觀察），就能有效檢索出目標曲目。
```

改了什麼：題目要分出兩類指標，就直接用兩個粗體標籤回答。「recall 僅 0.0690」翻成讀者在乎的「漏抓了 93%～100%」。兩種 AUC 計算方式的差異跟問題無關，刪掉。

## 16. 策展人的聆聽成本

✗
```
依 CV average precision 選擇 **RandomForest**，用 OOF scores 選出的最高可行 threshold 為 **0.08333333333**。
採 `score >= threshold`，包含 ties；OOF recall=0.8095。
固定此 threshold 後，test recall=0.7586，**未達到 80%**。
Test precision=0.2211；共需聆聽 199 / 1060 tracks，漏掉 14 個 hip-hop tracks。
換算每 1,000 tracks，需聆聽 **187.74** 首，漏掉 **13.21** 首 hip-hop。

Threshold feasibility 是 training OOF 上的 empirical constraint，不是 test recall 的保證；
同一 training data 也參與 hyperparameter selection，因此 OOF threshold 的表現仍可能帶有 selection optimism。
無論 test 是否達標，都不回頭調整 threshold。Test 結果估計的是這份 catalog 分布下的成本，不保證其他 prevalence 下仍相同。
```

✓
```
根據 CV average precision 選出表現較好的 **Random Forest**，利用訓練集的 OOF predicted probabilities 找出能滿足 recall $\ge 80\%$ 的最高閾值為 **threshold = `0.083333`**（此時 OOF recall = `0.8095`）。

將這個 threshold 固定後套用到 test set（1,060 tracks，含 58 首 hip-hop）上：
* **是否達標**：Test recall 為 **`0.7586`**（抓到 $44 / 58$ 首），因為訓練集與測試集的樣本分布自然波動，略低於 80% 的目標。
* **實際聆聽成本**：模型在測試集共標記了 199 首曲目（test precision = `0.2211`），漏掉了 14 首 hip-hop。換算成**每 1,000 首曲目**，策展人只需要人工聆聽 **`187.74` 首**（省去超過 81% 的聽歌工作量），並會漏掉 **`13.21` 首** hip-hop 曲目。
```

改了什麼：題目問的兩件事（有沒有達標、要聽幾首）各給一個粗體標籤。「包含 ties」和後面四行但書全刪。「抓到 44/58 首」「省去超過 81% 的聽歌工作量」把數字翻成策展人在乎的事。注意「是否達標」這個題目要求的答案沒有被刪，反而更醒目。

## 17. 一般心得

✗
```
透過這次的期末專題，我不僅深入了解了推薦系統的運作原理，更深刻體會到團隊合作的重要性。值得一提的是，在專題進行的過程中，我們曾遇到資料不足的挑戰，但透過組員之間的有效溝通，我們成功克服了困難。綜上所述，這次專題讓我收穫良多，對我未來的學習具有重要意義。
```

✓
```
期末專題做到一半，我們才發現手上的評分資料只有三千筆，大部分使用者只評過一兩部電影，協同過濾幾乎跑不出結果。那個禮拜幾乎每天開會討論是否換題目，最後決定改用電影的類型和簡介做 content-based 推薦。準確度沒有原本預期的好，但每個使用者都推得出東西。這次最實際的收穫，是學會在資料不夠時先回頭檢查資料，再決定是否調整模型。
```

改了什麼：速查表裡的套話（透過、不僅…更…、值得一提的是、綜上所述、收穫良多、具有重要意義）全拿掉，換成一件真的發生過的事。「資料不足的挑戰」變成「只有三千筆、大部分人只評過一兩部」，「成功克服了困難」變成具體做了什麼決定。

**注意**：這些具體細節必須來自使用者。使用者只給了概括的內容時，先問他實際發生了什麼；問不到就保留概括但誠實的說法，絕對不要自己編故事、編數字。

## 18. 作者逐句圈出的修辭套路

這組來自作者審 Claude（沒有用這份 skill 時）改寫 Decision Tree 兩小節的結果。整段讀起來其實已經順了，但作者逐句圈出「盡量不要這樣寫」的地方，並總結：「：；「」和對比、列舉少一點，『我』盡量少出現。回答我時可以用你原本的說法，但報告不要。」

| ✗ Claude 的寫法 | 套路 | ✓ 改法（多數取自作者定稿） |
| --- | --- | --- |
| 最後把兩個參數放在一起掃，共 56 組，用 CV macro-F1 挑出來的是… | 插入的短片段 | 在 56 組聯合網格搜尋中，最佳設定為 `max_depth=12, min_samples_leaf=5`（…） |
| 兩張表講的其實是同一件事：樹放得愈自由… | 冒號揭曉 | 樹放得愈自由，葉節點就從 2 個長到 1184 個，training 分數一路升到 1，CV macro-F1 卻在… 附近到頂 |
| 兩個極端各看一個例子。 | 路標句 | 刪掉，直接寫兩個極端 |
| …代表樹太簡單，連訓練資料都沒學好，這才是 underfitting。另一頭，完全長滿的樹… | 強調副詞、口語轉折 | …連訓練集都切不開，training 與 CV 分數雙雙偏低，屬於明顯的 **underfitting**。相反地，當樹完全不設限時… |
| 訓練資料背得滾瓜爛熟，換一批資料就不靈了 | 花俏成語 | 把訓練集死背到 `1.0000` |
| 要注意的是，…這個差距還在折間 SD 之內，比較穩妥的說法是「不再進步」，而不是「明顯變差」。 | 路標句、引號、對比、把結論講軟 | CV macro-F1 卻從高點滑落至 `0.3148`（gap 高達 `0.6852`），屬於 **overfitting** |
| 所以判斷 under／overfitting 要看 training 和 CV 怎麼一起變、再對照 SD，不能光看 hyperparameter 設得多大多小就下結論。 | 段尾但書 | 刪掉，前面已經用分數判斷過了 |
| 這一節的 single tree 指的是完全長滿的那棵樹，跟上一節 CV 挑出來的樹分開看。 | 對讀者下指令 | 這裡的單棵樹指完全長滿、不加限制的樹 |
| CV macro-F1 從 0.2922 升到 0.4232，整整多了 0.1310 | 強調副詞 | CV macro-F1 從 `0.2922` 大幅提升至 `0.4232` |
| 接著看預測對抽樣有多敏感。我固定用 fold 0 的 validation set… | 路標句、第一人稱 | 單棵完全生長的樹對訓練資料抽樣極度敏感：在 5 組獨立的 bootstrap 訓練集對上，兩棵單樹對同一批 validation tracks 的預測有高達 `60.14%` 不一致 |
| disagreement…量的是預測穩不穩，跟準不準是兩回事。 | 對比句型 | 刪掉，或只留定義：disagreement 是兩個模型在同一批 validation tracks 上預測不同的比例 |
| 結果很直接：完全長滿的樹只要換一份 bootstrap 樣本… | 冒號揭曉 | 直接寫結果 |
| 表中的 SD 只是這 5 組 pair 之間的 sample SD，不是信賴區間 | 只是…不是、但書 | 刪掉 |
| 穩定度的差距明顯得多。這兩個數字量的是不同的東西，一個是分得準不準，一個是…，不能拿其中一個代替另一個。 | 強調副詞、一個是…一個是…、但書 | Random Forest 的 CV macro-F1 只比 Bagging 高 `0.0038`，不一致率卻從 `30.50%` 進一步降到 `25.14%` |
| 為什麼加樹的效果會飽和？假設每個 base model… | 自問自答 | 若假設每棵樹預測的機率輸出變異數為 $\sigma^2$、樹與樹之間的平均相關係數為 $\rho$，則平均 $B$ 棵樹後的 ensemble 變異數為… |
| 這個公式有兩個限制。第一，…第二，我沒有直接估計 ρ，所以…只能說跟「樹之間相關性較低」這個解釋一致，不能當成已經證明了。 | 預告列舉、第一人稱、引號、但書 | 刪掉；真的要留就縮成括號一句：（實驗沒有直接估計 $\rho$，不一致率下降是間接證據。） |

同一輪裡，用了這份 skill 的改寫被作者評為「完美」。它的做法：用 **Underfitting**／**Overfitting**／**選定的設定** 三個粗體標籤直接回答題目，把 15 列的 bootstrap 明細併進 ensemble 的主表，用「砍半到 30.50%」「互相抄答案」講出機制，全篇只留一句括號但書。

作者後來修定稿時又補了兩條：「最典型的例子就是」這種先鋪陳再揭曉的句子不要，「典型」兩個字也不要。定稿因此改成讓例子直接當主詞（「`salsa` 的 OvR ROC-AUC 高達 `0.9842`，$F_1$ 卻只有 `0.1429`，`black-metal` 也是如此」），「屬於典型的 overfitting」也改成「屬於 **overfitting**」。

## 19. 心得：作者的微調與不喜歡的寫法

作者把用了這份 skill 的心得評為「整體很完美」，只改了幾個字，方向都是「書面但不口語」：

| 原本 | 作者改成 |
| --- | --- |
| 這件事讓我學到兩個很實際的教訓 | 這件事讓我學到兩個教訓 |
| 不要假設它跟報表一樣 | 不能假設跟報表一樣 |
| 它只會安安靜靜地給你一個錯的數字 | 只會安靜地給我一個錯的數字 |
| 要停下來想一想它合不合理 | 要停下來想它是否合理 |
| 主管能抓到這個錯，靠的就是看到數字時那一下「不太對勁」的感覺 | 主管能抓到這個錯靠的就是看到數字時那不太對勁的感覺 |

改完的段落：

```
這件事讓我學到兩個教訓。第一，拿到資料要先確認每個時間欄位用的是哪個時區，不能假設跟報表一樣。時區沒對齊不會讓程式報錯，只會安靜地給我一個錯的數字。第二，數字算出來之後，要停下來想它是否合理。主管能抓到這個錯靠的就是看到數字時那不太對勁的感覺，這種對數字的直覺，是我接下來最想練起來的能力。
```

沒用 skill 的版本，作者圈出這些「盡量不要這樣寫」：

- 「我負責兩件事：」：預告列舉加冒號揭曉。
- 「覺得做完就能進入『真正的分析』」：引號拿來當反諷。
- 「這件事我是靠自己出錯才真正記住的。」：先吊胃口再揭曉的鋪陳句。
- 「點擊 log 記的是 UTC 時間，報表卻是照台灣時間切日期。」：刻意的對比句。
- 整篇的高潮太分散：幾乎每段結尾都有一句金句（「後面分析得再仔細也沒用」「比起算錯，更讓我在意的是我沒發現」「這種對數字的直覺，是我現在還欠缺的」）。作者希望高潮集中一點。

矯枉過正的例子。第二輪套用了更嚴的規則之後，心得變成這樣，作者看了認為「太平淡要改」：

```
這件事讓我學到，拿到資料時要先確認每個時間欄位用的是哪個時區，不能假設它和報表一致。時區沒對齊並不會讓程式報錯，報表照樣做得出來，只是裡面的數字是錯的。所以算完之後，還要先判斷結果是否合理，再放進週報。那次主管就是從數字本身看出問題的，這種對數字的判斷力，是我接下來最想練起來的能力。
```

每一句都沒有違規，但整段沒有一句讓人記得住。對照上面作者改過的版本，差別就在「只會安靜地給我一個錯的數字」和「看到數字時那不太對勁的感覺」這兩處：一個是錯誤的樣子，一個是主管的直覺，都具體、有畫面。心得的高潮要集中，但要留著。

## 20. 給教授的信：作者評為「完美」的版本

```
林老師您好：

我是專題生〇〇〇。下週三下午兩點的 meeting，想跟老師商量能不能改個時間。

那天早上我有計組期中考，考完還得趕去另一個校區，時間上怕會來不及，不想讓老師等。下週四或週五下午我都可以，看老師哪個時段方便，我就配合那個時間。

另外跟老師回報一下進度：上週提到的 baseline 我已經跑完了，但結果比論文上報的低了大概 3 個點。我目前還沒找出確切原因，想在 meeting 時跟老師討論看看可能是哪裡的問題，到時候也會把實驗設定和結果整理好帶過去。

不好意思臨時調整時間，麻煩老師了，謝謝老師！

敬祝 教安

學生 〇〇〇 敬上
```

值得學的地方：「您好」開頭、先自我介紹、「怕會來不及」的委婉、一句「不好意思…麻煩老師了」的禮貌、「敬祝 教安」與「學生 〇〇〇 敬上」的格式。給教授的信，禮貌比精簡重要；只是別疊到「百忙之中撥冗」「深感抱歉」「懇請見諒」那種程度。

另一封用了 skill 的版本比較精簡，作者改了這幾處：

| 原本 | 作者改成 |
| --- | --- |
| 想跟老師商量…能不能改時間 | 是否能改時間 |
| 兩點前會來不及 | 兩點前可能會來不及 |
| 我下週四或週五下午都可以，看老師哪個時段方便；如果… | 時間我下週四或週五下午都可以（不用分號） |
| 也麻煩告訴我其他時間，我再配合 | 刪掉「我再配合」，不要多開使用者沒提的條件 |
| 比論文報的數字低大約 3 個點 | 低大約 3% |

注意：上面那封「完美」的信也用了「能不能改個時間」「大概 3 個點」，作者並沒有挑。所以「是否能」「3%」是預設偏好，不是非改不可；真正不能出現的是分號、多開的條件和缺少的格式（您好、敬祝 教安、學生 敬上）。
