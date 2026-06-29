import uvicorn
import random
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Shopfloor Simulator")

# Mock data
MOCK_DATABASE = {
    "C26602074": {
        "SN": "C26602074",
        "M_NO": "MO-DEMO-001",
        "P_NO": "PO-DEMO-001",
        "SemiModel": "DUO-AOI-DEMO-BOARD",
        "PCB_Length": "84",
        "PCB_Width": "55",
        "HasData": "1",
        "Msg": "",
    },
    "BOARD_A_V2": {
        "SN": "BOARD_A_V2",
        "M_NO": "MO-DEMO-002",
        "P_NO": "PO-DEMO-002",
        "SemiModel": "DEMO-BOARD-A",
        "PCB_Length": "120",
        "PCB_Width": "80",
        "HasData": "1",
        "Msg": "",
    },
    "SN24_TEST": {
        "SN": "SN24_TEST",
        "M_NO": "MO-DEMO-24",
        "P_NO": "PO-DEMO-24",
        "SemiModel": "LARGE-BOARD-24-IMAGES",
        "PCB_Length": "160",
        "PCB_Width": "120",
        "HasData": "1",
        "Msg": "",
    },
}

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/ashx/WebAPI/Board/SerialTest/HandlerGetSerialInfo.ashx")
def get_serial_info(sn: str = Query(..., description="Serial Number")):
    sn_stripped = sn.strip()
    
    if sn_stripped in MOCK_DATABASE:
        return JSONResponse(content=MOCK_DATABASE[sn_stripped])
    elif sn_stripped.startswith("SN"):
        # Auto-accept any code starting with 'SN'
        m_no = random.choice(["MO-TEST-001", "MO-TEST-002", "MO-TEST-003"])
        return JSONResponse(content={
            "SN": sn_stripped,
            "M_NO": m_no,
            "P_NO": "PO-AUTO-GEN",
            "SemiModel": "AUTO_BOARD",
            "PCB_Length": "84",
            "PCB_Width": "60",
            "HasData": "1",
            "Msg": "",
        })
    else:
        return JSONResponse(content={
            "SN": "",
            "PCB_Length": "",
            "PCB_Width": "",
            "HasData": "0",
            "Msg": "查無此序號資料"
        })

def main():
    print("[Shopfloor Sim] Starting Shopfloor API Simulator on port 9090...")
    uvicorn.run(app, host="0.0.0.0", port=9090, log_level="warning")

if __name__ == "__main__":
    main()
