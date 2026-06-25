---
title: '第三章:人機(HMI)控制介面, Yu'
tags: [Documentation]

---

Suggestion:
1. version control table
2. Create GUI manual with details
3. Create an error log
4. Status manual (connection status with other section of the machine)
5. Manual mode (PLC direct capture) - i/o to camera may be used
6. Auto  mode (PC capture)- via ethernet to communcate with camera




# HMI 使用說明書
::spoiler 主畫面/首頁(Home)
![image](https://hackmd.io/_uploads/Hkh7wc2a-x.png)
操作方式
如圖1所示為系統的起始頁面，開機時亦為此畫面，左上方為當天日期，中間上方為機台當前運作狀態，右上方為當前時間。畫面上提供五個程式核心功能:

- 主畫面: 回到主畫面(即此介面)

- 手動模式: 可手動控制上下層馬達正轉與反轉，手動運轉模式與緊急停止等功能。

- 參數設定: 可細微調整上下層馬達轉動速度，針對產品長寬、相機FOV長寬輸入，自動計算拍攝格數。

- 錯誤警報: 當系統運轉缺少需要資訊時，或受到外部干擾，警報會條列顯示於此畫面。

- 自動模式: 可選擇自動拍攝或自動啟動模式，並標示了相機拍攝格數等資訊。

---

狀態檢查
感測器狀態
:::
::spoiler 手動模式
手動模式
![image](https://hackmd.io/_uploads/B1oe5qhTWg.png)
於主畫面選擇手動模式模式後畫面切換如圖2所示:

---
第一頁(上層XY平台)

    -警報消除
    -復歸
    -手動模式
    -緊急停止
第二頁(下層XY平台)


參數設定
![image](https://hackmd.io/_uploads/BJgcY326bl.png)

錯誤警報
![image](https://hackmd.io/_uploads/BJ6hKh2aWl.png)

自動模式
![image](https://hackmd.io/_uploads/By99qn3a-l.png)
