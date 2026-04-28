import { Alert, DashboardMetrics, InspectionRun, InspectionStatus, RunDetail } from "../types";

// Images from the provided context
export const IMAGES = {
    pcbBlue: "https://lh3.googleusercontent.com/aida-public/AB6AXuAYZFUi32HXA3eyKGIAmrkSW_BbtWrkSOZxJ4Xs_CpLBEybINVFDnERyGdi_yc5PPTL3GwUkZPm6vLCWTMKy0jby7GTLMgwqRpzZ4jYh7qqiXwe1rSgIQUJOu0KN4uU372N9cKp51XHwPEcE99HCRv9bzUFh18wSpTRsJ3Bh7MfT0ofJ1YJtJ2bti73t06bnWIu6pCJTA_chUTRfCgLJB-u5fUyNhmqkmsJzVY8tXuEindRCfhP0C-ccaKPlvTRDgzrIhsSye1lpv2Y",
    chip1: "https://lh3.googleusercontent.com/aida-public/AB6AXuBvQKWnNzW3ZFbNa5kevJD7TrPEb3C-OycbYpV1qbQuyqm0YVtTPxLNMt4XJcisuuEPWQ9ZgzQecViqNwgEDZw_0Mx-gMXCk6u1RtKfocMnlsd7sVypsSutXUftGzcFvp-efu-pYG61W31tnlSrhMuK-9ovOj8VOHbRyQF-k_rupeTr77yUEe_7djBvQI8mv7vxrVjfgLGkEKpdxP1C5On6YQm7vTDUiv11lHF4hu_GhyNotfn5q8DrSC993isirZtXD3yoU_te8QrG",
    chip2: "https://lh3.googleusercontent.com/aida-public/AB6AXuBeXioLkDo3cCRQKIJDCy2YiAtYPNwCuqLWCrH2OwtPjYFwSzPt098yX1SAg5R0MTgr28PV7bniiELX_26e5JvJzUW-JgGddkIW-U9miTnJG0xV6djcAt0Fk09ObXwYtMxXZvqDmoOpYuxHliSFkj5Vo8JffNHHLYWNvKotVO2Yp2AuZ2nEv9hQPwkUpDcniVd8_QRg8nDB0qOfHW7cpB8We0z98Z-9e99zMiuHz-lE2HjAcJjNMJzHJOgariCLTtGUFf4CZmDxGubd",
    chipDefect: "https://lh3.googleusercontent.com/aida-public/AB6AXuADsee2xxYwxY8UUS3NDpBayxeaNi79fYVmB1TEBUxaKg_c_TUKL9BfYLcVM655dfhkKScepjgCm9KvES2xO3W2k6xLofzpyUVn_iqn4NPU88L3JufFmY4L-1HhuIozOMpd2Yo0c5DcdgMenLyfXZvA_9RY40PsL9PryiWHXZumMZGEuJek9fzWysmYPbd1VNBay6MysR1yb4wN2mjSayYXc4BfwNle87I6UtV0IxkEFHSeqLhv0KVtOlXWl7emO4yW1_ht3Y939If5",
    chipMisalign: "https://lh3.googleusercontent.com/aida-public/AB6AXuBkW4ZYlU0-RjDaI2wzHx-nUfmCRa_kq6B4LshowQkQoPZorXUt4QaU2oYQ8BRUrkIwDQYawqUTopf1s6BO98apve_cnbat40cArJxztEsCRrLoCmoQ1hskHr4roiYUGqzgWePidzv67GjP6VU84V2UZuL6j0pbGFGmD7oPdJ0O8gApJXn585FPvii7GEJ_VZBebRi0zPb2J5I6szscl_Au4xv2dHB7qwk9_b5jhyhpU5DuW5YO58fCyuuphzweiaWmn1_BCXlOFeJw",
    chipGreen: "https://lh3.googleusercontent.com/aida-public/AB6AXuDMAEAPcqeVeYUZ-W9HYklIzifjNK6YEW9EPy2-9i--e5DI-hjqYs01wi08fWWiL16C9WUcFP5lsxC4RsCikvdnRBx7VCN-y7sbWti11SDb-V62PrmA5tkdsYrQdQGuWzh8vsEBQ36OR_FiWK_8xwriwdvrunsxZCI_zmuuDWI6bTQmxbdIvASfOC27A6FC9EBXkZRJSFlosH8KTWJ_7mtjO-l3xou5-4Nykxu5kNVnPyOAg3sJuXFHgCmMGsGVncr_xehF-4WTpzs1",
    chipBlack: "https://lh3.googleusercontent.com/aida-public/AB6AXuD1Q5T3YXfzPR7c7B12jJ1qdLmGDfPabg7eZPRRtLTs-3uejzcms2nxFuvQybpj8TNYS01fuzYqrdRz5WZHoIVHYAmf8_THxm6Rj2Hw6IfuY7r139thtOC3OoPAWHGz-jDFHiRwf0BywomHB-8lb8jcSRLMW1WpJksMxb31uc1QpfGAAnufJ8h_5k_P5tnVvYbE8Fo-IBjs7vPq2iFJAaY8hFH2J2mUjJKex609Sf0WH69hKMa9TMuZG2Q3ciqzMYk-zDMu6CAizaLf",
    userAvatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuBxamN0naylD1ojHrJqCb2sBDqSW67Z8utq10-M-WqSRxK58V8ycINCBPu_0OJp22N1yAB2KDG8r5Y4HFqvofzd03mTxfXgSRZ64D554fznt9zBtJezK5nvhGK0kcJqrTbjUkT6pE90kSr-7-DFLv4sFYlfsRehsKTgxCIz4k44_u3Va7NPguTVCLyIAtyTCvu_d3_X_XvXd7kFT1dOoKSS7MEHAg4Vx2anoFLpUV6bYlRIuTFrui-AQ7CXUyjOoLJ0zz74r3a2FdE9"
};

export const MOCK_ALERTS: Alert[] = [
    { id: '1', code: '#4022', type: 'Misaligned', time: '10:42 AM', lane: 'Lane 2', severity: 'critical' },
    { id: '2', code: '#4021', type: 'Solder Bridge', time: '10:38 AM', lane: 'Lane 1', severity: 'warning' },
    { id: '3', code: '#4018', type: 'Missing Part', time: '10:15 AM', lane: 'Lane 1', severity: 'critical' },
    { id: '4', code: '#4015', type: 'Flux Residue', time: '09:55 AM', lane: 'Lane 3', severity: 'info' },
    { id: '5', code: '#4009', type: 'Tombstone', time: '09:30 AM', lane: 'Lane 2', severity: 'critical' },
];

export const MOCK_RUNS: InspectionRun[] = [
    { id: 'RUN-2023-001', timestamp: '2023-10-27 08:30:12', pcbSerial: 'SN-99887766', result: InspectionStatus.PASS, operator: 'Op-12' },
    { id: 'RUN-2023-002', timestamp: '2023-10-27 08:35:45', pcbSerial: 'SN-99887767', result: InspectionStatus.FAIL, defectType: 'Solder Bridge', operator: 'Op-12' },
    { id: 'RUN-2023-003', timestamp: '2023-10-27 08:42:01', pcbSerial: 'SN-99887768', result: InspectionStatus.PASS, operator: 'Op-14' },
    { id: 'RUN-2023-004', timestamp: '2023-10-27 08:48:33', pcbSerial: 'SN-99887769', result: InspectionStatus.FAIL, defectType: 'Missing Component', operator: 'Op-14' },
    { id: 'RUN-2023-005', timestamp: '2023-10-27 08:55:10', pcbSerial: 'SN-99887770', result: InspectionStatus.PASS, operator: 'Op-12' },
    { id: 'RUN-2023-006', timestamp: '2023-10-27 09:10:22', pcbSerial: 'SN-99887772', result: InspectionStatus.FAIL, defectType: 'Misaligned', operator: 'Op-15' },
];

export const MOCK_METRICS: DashboardMetrics = {
    totalScanned: 12450,
    totalScannedChange: 5.1,
    passRate: 98.2,
    passRateChange: 0.4,
    defectCount: 224,
    defectCountChange: -2.1,
    throughputData: [
        { time: '00:00', value: 100 },
        { time: '02:00', value: 300 },
        { time: '04:00', value: 250 },
        { time: '06:00', value: 150 },
        { time: '08:00', value: 350 },
        { time: '10:00', value: 180 },
        { time: '12:00', value: 320 },
        { time: '14:00', value: 380 },
        { time: '16:00', value: 120 },
        { time: '18:00', value: 450 },
        { time: '20:00', value: 220 },
        { time: '22:00', value: 150 },
    ]
};

export const MOCK_RUN_DETAIL: RunDetail = {
    runId: 'RUN #8392-A',
    batchId: 'Batch 402',
    line: 'Line 3',
    startTime: 'Oct 27, 08:00',
    endTime: 'Oct 27, 12:30',
    totalBoards: 500,
    defectRate: 1.2,
    operator: 'J. Smith',
    images: [
        { id: '1', position: 'A-01', status: InspectionStatus.PASS, imageUrl: IMAGES.chip1, region: 'Region A-1' },
        { id: '2', position: 'A-02', status: InspectionStatus.PASS, imageUrl: IMAGES.chip2, region: 'Region A-2' },
        { id: '3', position: 'A-03', status: InspectionStatus.FAIL, label: 'Missing Component', imageUrl: IMAGES.chipDefect, region: 'Region A-3' },
        { id: '4', position: 'B-01', status: InspectionStatus.PASS, imageUrl: IMAGES.chip1, region: 'Region B-1' },
        { id: '5', position: 'B-02', status: InspectionStatus.PASS, imageUrl: IMAGES.chip2, region: 'Region B-2' },
        { id: '6', position: 'B-03', status: InspectionStatus.FAIL, label: 'Misalignment Detected', imageUrl: IMAGES.chipMisalign, region: 'Region B-3' },
        { id: '7', position: 'C-01', status: InspectionStatus.PASS, imageUrl: IMAGES.chipGreen, region: 'Region C-1' },
        { id: '8', position: 'C-02', status: InspectionStatus.PASS, imageUrl: IMAGES.chipBlack, region: 'Region C-2' },
        { id: '9', position: 'D-01', status: InspectionStatus.FAIL, label: 'Capacitor Lift', imageUrl: IMAGES.chip2, region: 'Region D-1' },
    ]
};