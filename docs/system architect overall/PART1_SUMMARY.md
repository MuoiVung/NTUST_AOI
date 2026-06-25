---
title: '第一章: 設備摘要 Aaron'
tags: [Documentation]

---

6/1 Suggestion: 
1. Contents: machine illustration with main sections marking. 
2. Information: components datasheet links
3. Contact: person in charge for each chapter
4. Installation environment: utilites requirements  

# 第一章: 設備摘要 Aaron
## 版本歷史
| 欄位 | 內容 |
|---|---|
| 文件標題 | 設備摘要 |
| 系統 | 整體概略 |
| 適用對象 | 所有人員|
| 版本 | Draft v1.0 |
| 日期 | 2026-06-03 |
| 編製者 | Aaron |
## 索引
| 章節 | 內容 |
| ---- | ---- |
| 第二章| 輸送帶使用手冊 Max    |
| 第三章| 人機(HMI)控制介面 羽健     |
| 第四章| XY table Kevin     |
| 第五章| 相機模組 Marnel     |
| 第六章| 檔案儲存 Peter, Vincent     |
| 第七章| 維修計畫 |

## 各項功能--(設備規格、性能)
DUO_AOI機台(以下簡稱本機台)
本機台有以下設備:
- 輸送帶
    - 長$2000mm$
    - 寬可從$100mm$至$600mm$之間調整
    - 高$560mm$
    - 運轉速度為$5000m/s$
    - 馬達型號: 東方 BLM6400S-GFV
    - 減速機型號: 東方 GFV6G50
    - 驅動器型號: 東方 BMUD400-S
- 人機介面(HMI)
    - 型號: 三菱 GT2512-WXTBD
    - 輸入電壓: DC24V
    - 長$299mm$，寬$219mm$，高$48mm$
    - 通訊介面: $RS-422/485 / RS-232 / Ethernet
    - 記憶體容量: ROM：32MB/RAM：128MB
- PLC
    - 型號: 三菱 FX5U-64MR/ES
    - 額定電壓: 100至240V AC
    - 最大I/O點數: 512點以下
    - 回應時間: 切換$10ms$
- 上下層XY_Table
    - 型號: 東佑達 CGLTH5AZC-L6-300-BR-MW
- 相機模組
    - 相機型號: IDS U3-3990CP-C-HQ Rev.2.2
    - 上層鏡頭: 肯定 ML-MC5020XR-18C
    - 下層鏡頭: OPT OPT-CDP7528
- PC
    - 型號: 研揚 OMNI-3125HTT-ADN-A2-1010
- 乙太交換器
    - 型號: 研華 EKI-2528
:::info
DUO_AOI機台一次側需配備三相電源220V(3相1線)，內部控制電源AC為220V，DC為24V，PC另外供電AC220V
:::

## 主要功能說明
本機台是一台可以拍攝成品PCB板正反面的機台，配有上下兩層平台的相機同時拍攝，並可以將拍攝完成的照片直接儲存於PC中，方便後續模型辨識使用。本機台拍攝一片板子大約花費7秒，並有進板區、拍攝區與出板區3個區塊，第一次拍攝新的板子時根據輸入板子大小可自動計算格數，往後相同產品僅需於HMI選擇該板即可進行，本機台所能拍攝的板子大小最大可達$300mm*300mm*$。
## 系統架構圖
![AOI_整體流程圖.drawio](https://hackmd.io/_uploads/By2viZNbGe.png)

## 硬體尺寸圖--(layout)

## 通訊架構
DUO_AOI系統通訊架構

| 設備A | 設備B    | 通訊方法 | 目的     |
| ----- | -------- | -------- | -------- |
| HMI   | router   | Ethernet | 設備處於相同網域下，便於溝通 |
| PLC   | router   | Ethernet | 設備處於相同網域下，便於溝通 |
| PC    | router   | Ethernet | 設備處於相同網域下，便於溝通 |
| PLC   | convery  | I/O      | 控制進板與出板邏輯 |
| PLC   | XY table | I/O      | 控制XY table上下層移動邏輯 |
| PlC   | Light    | I/O      | 控制燈光開關 |
| PLC   | Camera   | I/O      | 可手動控制相機拍照 |
| PC    | Camera   | USB      | 程式控制相機拍照並由PC存檔 |

與研揚的資訊系統對接部分

| 外部端A    | 內部端B | 通訊方法 | 目的                 |
| --------  | ----- | -------- | -------------------- |
| 研揚訂單    | HMI   |          | 研揚生產訂單編號導入 |
| 條碼槍    | PC      |          | 訂單編號與研揚系統確認  |
| AOI瑕疵檢測系統 | PC      |            | 進行PCB板瑕疵檢測       |
| 研揚伺服器雲端 | PC  |          | 瑕疵檢測圖片存檔  |
## 快速使用手冊
基本流程
請將電源打開，檢查所有硬體是否已經初始化，且機台進板區、檢測區、出板區皆無板子。
第二件事情是確認產品，如果沒有該產品編號，則在HMI中建立一個，手動輸入板子大小、相機FOV等參數，如果有則呼叫產品編號並加入設定。
還有掃描
根據板子的寬度調整輸送帶寬度後，將板子放上進板區域的定位塊上，於HMI主畫面按下自動啟動按鈕，機台將會啟動輸送帶運轉將進板區的板子送入檢測區中，待板子完全於檢測區停止後，上下方XY table自動移動並進行拍照，圖片將會自動儲存在PC，並同步到AOI檢測系統，顯示檢測結果後，板子離開檢測區並移動至出板區等待拿起。

## 復歸程序
DUO_AOI機台有3種狀態:
- 手動復歸
    - 
- 系統重置
- 自動模式

---

附錄
- PLC規格書
- 零件規格
- HMI規格書
- 電控資料--(線路)
- 相機規格
---