import time, threading, collections, statistics
import numpy as np
import cv2, mediapipe as mp

ECR_T1, T1_DUR = 1.30, 0.20
ECR_T2, T2_DUR = 1.15, 0.50
ECR_BROW       = 1.40
MAR_TH, MAR_DUR= 0.35, 0.50
BLG_COEF       = 1.25
BLG_CALIB      = 1.5
QUEUE_LEN      = 3
FPS_INTERVAL   = 0.02

_face_mesh = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1, refine_landmarks=True,
    min_detection_confidence=0.5, min_tracking_confidence=0.5
)

def mouth_ar(p):
    return np.linalg.norm(p[2]-p[3]) / (np.linalg.norm(p[0]-p[1]) or 1)

def iris_metrics(cidx, pidx, up, dn, lm, w, h, q):
    c = np.array([lm[cidx].x*w, lm[cidx].y*h])
    peri = np.array([[lm[i].x*w, lm[i].y*h] for i in pidx])
    rad = np.mean([np.hypot(*(c-p)) for p in peri]); q.append(rad)
    diam = 2*statistics.median(q); gap = (lm[dn].y - lm[up].y)*h
    return diam, gap

class EyelidEngine:
    CL, CR = 468, 473
    PL, PR = [469,470,471,472], [474,475,476,477]
    UL, UR = 159, 386
    DL, DR = 145, 374
    BL, BR = 70, 336
    LIP    = [61,291,13,14]

    COL_CENT = (  0,  0,255)
    COL_PERI = (255,  0,  0)
    COL_UP   = (  0,255,255)
    COL_DN   = (255,255,  0)
    COL_BROW = (255,255,255)
    COL_BOXA = (  0,  0,255)
    COL_BOXN = (  0,255,  0)

    def __init__(self):
        self._stop = threading.Event()
        self._thread = None

    def start(self, callback):
        self._thread = threading.Thread(target=self._loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self, callback):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened():
            return

        qL, qR = collections.deque(maxlen=QUEUE_LEN), collections.deque(maxlen=QUEUE_LEN)
        blg_base=None; blg_samples=[]; t0=time.time()
        t1=t2=tM=None

        while not self._stop.is_set():
            ok, frm = cap.read()
            if not ok:
                break
            h,w,_ = frm.shape
            res = _face_mesh.process(cv2.cvtColor(frm, cv2.COLOR_BGR2RGB))

            ecr=mar=blg=0.; alert=False; now=time.time()

            if res.multi_face_landmarks:
                lm=res.multi_face_landmarks[0].landmark

                dL,gL = iris_metrics(self.CL,self.PL,self.UL,self.DL,lm,w,h,qL)
                dR,gR = iris_metrics(self.CR,self.PR,self.UR,self.DR,lm,w,h,qR)
                ecr=max(dL/gL if gL else 0, dR/gR if gR else 0)

                blgL=(lm[self.UL].y-lm[self.BL].y)*h; blgR=(lm[self.UR].y-lm[self.BR].y)*h
                blg=(blgL+blgR)/2
                if blg_base is None:
                    if now-t0<BLG_CALIB: blg_samples.append(blg)
                    else: blg_base=np.median(blg_samples) if blg_samples else blg
                cheat_brow = blg_base and blg > BLG_COEF*blg_base

                if (ecr>=ECR_T1) or (ecr>=ECR_BROW and cheat_brow):
                    t1 = t1 or now
                    if now-t1>=T1_DUR: alert=True
                else:
                    t1=None

                if ecr>=ECR_T2:
                    t2 = t2 or now
                    if now-t2>=T2_DUR: alert=True
                else:
                    t2=None

                lip=np.array([[lm[i].x*w,lm[i].y*h] for i in self.LIP])
                mar=mouth_ar(lip)
                if mar>MAR_TH:
                    tM=tM or now
                    if now-tM>=MAR_DUR: alert=True
                else:
                    tM=None

                pts = [
                    (self.CL, self.COL_CENT), (self.CR, self.COL_CENT),
                    *[(i,self.COL_PERI) for i in self.PL+self.PR],
                    (self.UL, self.COL_UP), (self.UR, self.COL_UP),
                    (self.DL, self.COL_DN), (self.DR, self.COL_DN),
                    (self.BL, self.COL_BROW), (self.BR, self.COL_BROW)
                ]
                for idx,col in pts:
                    p=(int(lm[idx].x*w), int(lm[idx].y*h)); cv2.circle(frm,p,2,col,-1)

            cv2.putText(frm,f"ECR:{ecr:.2f}",(10,24),cv2.FONT_HERSHEY_SIMPLEX,0.6,self.COL_CENT,2)
            cv2.putText(frm,f"BLG:{blg:.0f}",(10,46),cv2.FONT_HERSHEY_SIMPLEX,0.6,self.COL_BROW,2)
            cv2.putText(frm,f"MAR:{mar:.2f}",(10,68),cv2.FONT_HERSHEY_SIMPLEX,0.6,self.COL_PERI,2)
            cv2.rectangle(frm,(5,5),(w-5,h-5), self.COL_BOXA if alert else self.COL_BOXN,3)
            if alert:
                cv2.putText(frm,"ALERT!",(60,110),cv2.FONT_HERSHEY_SIMPLEX,1.0,self.COL_BOXA,3)

            ok, buf = cv2.imencode(".jpg", frm)
            if ok:
                callback(buf.tobytes(), ecr, blg, mar)

            time.sleep(FPS_INTERVAL)

        cap.release()
